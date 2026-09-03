"""
Generates a blog post + Instagram caption for Plüton PDRM using the Claude API.
Requires: pip install anthropic
Requires env var: ANTHROPIC_API_KEY
"""
import json
import os
import re
import unicodedata
from datetime import date
from pathlib import Path

import anthropic

MODEL = "claude-sonnet-4-6"  # good quality/cost balance for this workload
BASE_DIR = Path(__file__).parent
TOPICS_FILE = BASE_DIR / "topics.json"
STATE_FILE = BASE_DIR / "state.json"  # tracks which topic index we're on

BRAND_RULES = """
Sen Plüton Psikolojik Danışmanlık ve Rehberlik Merkezi (Plüton PDRM) için içerik üreten bir asistansın.
Merkez İzmir Narlıdere'de bulunuyor. Hizmetler: DEHB, Anksiyete, Disleksi, Öğrenme Güçlüğü, Sınav Kaygısı,
Sınav Başarısı, Kariyer Planlama, Spor Psikolojisi, Gelişim Takibi & Testler, Sosyal Oyun Grupları,
Akran Uyum Grupları, Atölyeler, Ekran Bağımlılığı, Akran Zorbalığı, Aile Danışmanlığı. Okul öncesi
yaş grubuyla da çalışılıyor.

KURALLAR:
- "terapi" ve "oyun grubu" kelimelerini KESİNLİKLE kullanma.
- Ton: sıcak, samimi, güven verici, ama profesyonel. Ailelere hitap eder gibi yaz.
- Tıbbi teşhis koyma, kesin vaat verme (örn. "kesin çözer" gibi ifadelerden kaçın).
- İçerik Türkçe olmalı.
"""


def _next_topic() -> str:
    topics = json.loads(TOPICS_FILE.read_text(encoding="utf-8"))["topics"]
    state = {"index": 0}
    if STATE_FILE.exists():
        state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    idx = state.get("index", 0) % len(topics)
    topic = topics[idx]
    STATE_FILE.write_text(json.dumps({"index": idx + 1}), encoding="utf-8")
    return topic


def _slugify(title: str) -> str:
    text = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode()
    text = re.sub(r"[^a-zA-Z0-9\s-]", "", text).strip().lower()
    return re.sub(r"[\s-]+", "-", text)


def generate(topic: str = "") -> dict:
    """Returns dict with: topic, title, slug, blog_html_body, ig_caption, image_prompt.
    If `topic` is given (e.g. chosen by the user in the panel), it's used
    as-is instead of picking the next one from the round-robin list."""
    topic = topic.strip() or _next_topic()
    client_kwargs = {}
    workspace_id = os.environ.get("ANTHROPIC_WORKSPACE_ID")
    if workspace_id:
        client_kwargs["default_headers"] = {"anthropic-workspace-id": workspace_id}
    client = anthropic.Anthropic(**client_kwargs)  # reads ANTHROPIC_API_KEY from env

    prompt = f"""{BRAND_RULES}

Bugünün konusu: "{topic}"

Yukarıdaki kurallara uyarak bir blog yazısı, Instagram caption'ı ve görsel
prompt'u üret. write_content aracını kullanarak sonucu ilet."""

    # Use tool-calling (structured output) instead of asking the model to
    # hand-write JSON as text -- this guarantees valid, already-parsed
    # output and avoids JSON-escaping failures on long HTML content.
    tool = {
        "name": "write_content",
        "description": "Plüton PDRM için üretilen blog yazısı ve Instagram içeriğini kaydeder.",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Blog yazısının başlığı (kısa, ilgi çekici)",
                },
                "blog_html_body": {
                    "type": "string",
                    "description": (
                        "500-700 kelimelik blog yazısı, HTML paragraf etiketleri "
                        "(<p>, <h2>, <ul><li>) ile biçimlendirilmiş. <h1> kullanma, "
                        "başlık ayrı zaten veriliyor."
                    ),
                },
                "ig_caption": {
                    "type": "string",
                    "description": (
                        "Instagram için 80-150 kelimelik, sıcak ve davetkar bir "
                        "caption. Sonunda 5-8 ilgili Türkçe hashtag ekle "
                        "(#dehb, #ailedanismanligi gibi). Emoji ölçülü kullanılabilir."
                    ),
                },
                "image_prompt": {
                    "type": "string",
                    "description": (
                        "Bu blog yazısının Instagram görseli için, İngilizce, bir AI "
                        "görsel üretim modeline verilecek 1-2 cümlelik betimleyici "
                        "prompt. Sıcak, yumuşak renkli, illüstrasyon tarzı, gerçek "
                        "insan yüzü/fotoğraf İÇERMEYEN, marka rengi soft/pastel bir "
                        "görsel tarif et."
                    ),
                },
            },
            "required": ["title", "blog_html_body", "ig_caption", "image_prompt"],
        },
    }

    response = client.messages.create(
        model=MODEL,
        max_tokens=3000,
        tools=[tool],
        tool_choice={"type": "tool", "name": "write_content"},
        messages=[{"role": "user", "content": prompt}],
    )

    tool_use_block = next(
        block for block in response.content if block.type == "tool_use"
    )
    data = dict(tool_use_block.input)

    data["topic"] = topic
    data["slug"] = _slugify(data["title"])
    data["date"] = date.today().isoformat()
    return data


if __name__ == "__main__":
    result = generate()
    print(json.dumps(result, ensure_ascii=False, indent=2))
