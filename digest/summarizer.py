"""Summarize enriched data using NVIDIA NIM."""
import json
import time

from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    InternalServerError,
    OpenAI,
    RateLimitError,
)
from digest.config import GEMINI_API_KEY, NVIDIA_API_KEY

GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"

# Ordered (model, base_url, api_key) chain, tried in sequence. Every entry was verified
# against a FULL 25-entity payload — finish_reason=stop, valid JSON, all 25 summaries.
# A toy prompt is not sufficient evidence: mistralai/mistral-nemotron answered one in
# 1.4s, then timed out and returned HTTP 500 on the real payload.
#
# The chain deliberately spans TWO PROVIDERS. Provider-level failure is the recurring
# cause of outages here: Groq's token cap broke it 2026-05, NVIDIA end-of-lifed the
# pinned model 2026-08-07 (HTTP 410, three dead runs), and on 2026-08-17 gemini-3.7-flash
# and gemini-flash-latest were both returning 503 "high demand". Falling back within one
# provider would not have survived any of those.
#
# Pinned versions, not the gemini-flash-latest alias: the alias was itself 503ing when
# this was chosen, and an alias that silently changes model is its own failure mode.
PROVIDERS = (
    ("gemini-3.5-flash", GEMINI_BASE_URL, GEMINI_API_KEY),
    ("gemini-3.1-flash-lite", GEMINI_BASE_URL, GEMINI_API_KEY),
    ("nvidia/nemotron-3-super-120b-a12b", NVIDIA_BASE_URL, NVIDIA_API_KEY),
)

# The SDK default is 600s, which is longer than this job's entire budget: three
# attempts across two models could blow the workflow timeout before the fallback is
# ever reached, making the retry logic actively harmful. The primary answered the real
# payload in ~97s, so 150s leaves headroom while keeping the worst case bounded.
REQUEST_TIMEOUT_S = 150.0

# The whole run dies if this one call fails, after ~15 min of data fetching. Transient
# modes are retried on the same model; a model that is gone, gated, or end-of-lifed is
# abandoned immediately for the next one, so a silent EOL degrades instead of failing.
ATTEMPTS = 3

# 25 watchlist entities need ~5,300 completion tokens. The previous 4096 cap truncated
# the JSON mid-string (finish_reason=length), which surfaced as a JSONDecodeError and
# killed the 2026-07-27 run. Raise this if the watchlist grows substantially.
MAX_TOKENS = 16384


class EmptyCompletion(RuntimeError):
    """Model returned no content — retryable."""


RETRY_ON = (
    APIConnectionError,
    APITimeoutError,
    RateLimitError,
    InternalServerError,
    json.JSONDecodeError,
    EmptyCompletion,
)

SYSTEM_PROMPT = """You are a careful investment analyst writing a weekly Alpha Digest for retail investors.

For each entity in the provided data, write a plain-English summary of 2-4 sentences that covers:
1. WHAT changed: direction and approximate size of the insider trade, 13F position change, crypto treasury change, or other reported activity.
2. LIKELY WHY: ground the explanation only in the provided news and fields. If no public context is provided, say "no public context found this week".
3. NEUTRAL SIGNAL: briefly explain what the activity may indicate without hype and without investment advice.

Rules:
- Never invent tickers, figures, dates, entities, news, links, or facts not present in the input data.
- If a field or section is empty, say so in one concise sentence rather than fabricating context.
- Use only the provided news URLs in news_used.
- Be factual and concise. Use plain English, no jargon without explanation, no hype.
- Do not recommend buying, selling, holding, or timing any security.
- If a 13F shows no changes, say so in one sentence. If an entity had no activity this week, say so in one sentence.

Respond with a single valid JSON object only. Do not include markdown, code fences, or prose outside JSON. The JSON must match this exact schema and must not add, remove, or rename keys:
{
  "entity_summaries": [
    {
      "name": "string",
      "type": "string",
      "summary": "string",
      "news_used": ["url1", "url2"]
    }
  ],
  "macro_note": "1-2 sentence note on macro context based on commodity moves this week"
}"""


def summarize(enriched: dict, commodities: dict[str, float], start_date: str, end_date: str) -> dict:
    user_prompt = f"""Analyze the week of {start_date} to {end_date}.

=== INSIDER TRADES (Form 4) ===
{json.dumps(enriched["trades"], indent=2, default=str)}

=== INSTITUTIONAL HOLDINGS (13F diffs) ===
{json.dumps(enriched["institutional"], indent=2, default=str)}

=== CRYPTO TREASURY CHANGES ===
{json.dumps(enriched["crypto"], indent=2, default=str)}

=== COMMODITY PRICES THIS WEEK ===
{chr(10).join(f"{k}: {v:+.2f}%" for k, v in commodities.items()) if commodities else "No commodity data available."}

Write the digest now using only the data above."""

    primary_model = PROVIDERS[0][0]
    failures: list[str] = []
    for model, base_url, api_key in PROVIDERS:
        if not api_key:
            failures.append(f"{model}: skipped, no API key configured")
            continue
        client = OpenAI(
            base_url=base_url,
            api_key=api_key,
            timeout=REQUEST_TIMEOUT_S,
            max_retries=0,  # retries are handled below, per model, with backoff
        )
        last_error: Exception | None = None
        for attempt in range(1, ATTEMPTS + 1):
            try:
                response = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=0.3,
                    max_tokens=MAX_TOKENS,
                    response_format={"type": "json_object"},
                )

                content = response.choices[0].message.content
                if content is None or not content.strip():
                    raise EmptyCompletion(
                        f"Empty completion (finish_reason={response.choices[0].finish_reason})"
                    )
                summary = json.loads(content)
                if model != primary_model:
                    print(f"  [summarizer] WARNING: primary {primary_model} unusable; produced digest with {model}")
                return summary
            except RETRY_ON as exc:
                # RateLimitError/InternalServerError are APIStatusError subclasses but are
                # listed in RETRY_ON, so they match here before the permanent-error clause.
                last_error = exc
                if attempt == ATTEMPTS:
                    break
                backoff = 2 ** attempt
                print(f"  [summarizer] {model}: {type(exc).__name__} on attempt {attempt}/{ATTEMPTS}; retrying in {backoff}s")
                time.sleep(backoff)
            except APIStatusError as exc:
                # Gone (410), not found/gated (404), bad request — retrying cannot help.
                last_error = exc
                break

        failures.append(f"{model}: {type(last_error).__name__}: {last_error}")
        print(f"  [summarizer] {model} failed; falling through to next model")

    raise RuntimeError("summarize failed on every model:\n  " + "\n  ".join(failures))
