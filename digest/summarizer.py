"""Summarize enriched data using NVIDIA NIM."""
import json

from openai import OpenAI
from digest.config import NVIDIA_API_KEY

MODEL = "mistralai/mistral-medium-3.5-128b"

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
    client = OpenAI(base_url="https://integrate.api.nvidia.com/v1", api_key=NVIDIA_API_KEY)

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

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.3,
        max_tokens=4096,
        response_format={"type": "json_object"},
    )

    content = response.choices[0].message.content
    if content is None or not content.strip():
        raise RuntimeError(f"Empty completion from {MODEL} (finish_reason={response.choices[0].finish_reason})")
    return json.loads(content)
