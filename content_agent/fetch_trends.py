"""
Uses Claude's built-in web search (same Anthropic key you already have --
no new API/cost needed) to find a handful of currently-relevant topics in
psychology, child development, and parenting/education, suitable for a
Turkish psychological counseling center's blog. Also re-syncs the static
topics.json list to the panel, so both lists are available for you to
pick from when creating content.

Run by: .github/workflows/fetch-trends.yml
"""
import json
import os
import re
from datetime import date, datetime, timezone
from pathlib import Path

import anthropic

from publish_blog import panel_upload_json

MODEL = "claude-sonnet-4-6"
BASE_DIR = Path(__file__).parent
TOPICS_FILE = BASE_DIR / "topics.json"

PROMPT = """Web'de güncel arama yaparak, bir psikolojik danışmanlık ve
rehberlik merkezinin (çocuk/aile odaklı) blog'u için uygun, ŞU AN gündemde
olan veya mevsimsel olarak öne çıkan 6-8 konu bul. Şu alanlara odaklan:
çocuk/ergen psikolojisi, ebeveynlik, eğitim/okul dönemi konuları, dikkat/
öğrenme güçlükleri, ekran kullanımı, aile ilişkileri.

Her biri için:
- topic: Türkçe, blog yazısına dönüştürülebilecek somut bir başlık/konu cümlesi
- note: 1 cümlelik neden şu an güncel/ilgi çekici olduğuna dair kısa not

write_trends aracını kullanarak sonucu ilet."""


def fetch_trends() -> list[dict]:
    client_kwargs = {}
    workspace_id = os.environ.get("ANTHROPIC_WORKSPACE_ID")
    if workspace_id:
        client_kwargs["default_headers"] = {"anthropic-workspace-id": workspace_id}
    client = anthropic.Anthropic(**client_kwargs)

    tool = {
        "name": "write_trends",
        "description": "Bulunan güncel konu önerilerini kaydeder.",
        "input_schema": {
            "type": "object",
            "properties": {
                "trends": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "topic": {"type": "string"},
                            "note": {"type": "string"},
                        },
                        "required": ["topic", "note"],
                    },
                }
            },
            "required": ["trends"],
        },
    }

    response = client.messages.create(
        model=MODEL,
        max_tokens=2000,
        tools=[
            {"type": "web_search_20250305", "name": "web_search"},
            tool,
        ],
        messages=[{"role": "user", "content": PROMPT}],
    )

    tool_use_block = next(
        (b for b in response.content if b.type == "tool_use" and b.name == "write_trends"),
        None,
    )
    if not tool_use_block:
        return []
    return tool_use_block.input.get("trends", [])


def main():
    print("1/2 Fetching trends via web search...")
    trends = fetch_trends()
    print(f"    Found {len(trends)} trending topics")

    payload = {
        "trends": trends,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    panel_upload_json("trends.json", payload)

    print("2/2 Syncing static topics list...")
    topics_data = json.loads(TOPICS_FILE.read_text(encoding="utf-8"))
    panel_upload_json("topics.json", topics_data)
    print("Done.")


if __name__ == "__main__":
    main()
