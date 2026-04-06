"""Summarize enriched data using Groq (Llama 3.3 70B)."""
import json

from groq import Groq
from digest.config import GROQ_API_KEY

MODEL = "llama-3.3-70b-versatile"

SYSTEM_PROMPT = """You are an investment analyst writing a weekly digest for retail investors.

For each entity in the data provided, write 2-4 sentences covering:
1. What they did (bought/sold/added/reduced position, assets and approximate size)
2. Why it likely happened (connect to provided news headlines; if no news say "no public context found this week")
3. What it might signal (brief, neutral — do NOT give investment advice)

Rules:
- Be factual and concise. No hype or speculation.
- Use plain English, no jargon without explanation.
- Never invent information not in the provided data.
- If a 13F shows no changes, say so in one sentence.
- If an entity had no activity this week, write one sentence saying so.

Respond ONLY with valid JSON matching this exact schema:
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
    client = Groq(api_key=GROQ_API_KEY)

    user_prompt = f"""Week of {start_date} to {end_date}.

=== INSIDER TRADES (Form 4) ===
{json.dumps(enriched["trades"], indent=2, default=str)}

=== INSTITUTIONAL HOLDINGS (13F diffs) ===
{json.dumps(enriched["institutional"], indent=2, default=str)}

=== CRYPTO TREASURY CHANGES ===
{json.dumps(enriched["crypto"], indent=2, default=str)}

=== COMMODITY PRICES THIS WEEK ===
{chr(10).join(f"{k}: {v:+.2f}%" for k, v in commodities.items()) if commodities else "No commodity data available."}

Write the digest now."""

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
    return json.loads(content)
