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


LENGTH_SPECS = {
    "short": {
        "label": "Kısa",
        "word_range": "500-700",
        "max_tokens": 3000,
        "style_note": (
            "Kısa, hızlı okunur, günlük sıcak dilde bir blog yazısı. Ailelere "
            "sohbet eder gibi hitap et."
        ),
    },
    "long": {
        "label": "Uzun / Akademik",
        "word_range": "1400-2000",
        "max_tokens": 5000,
        "style_note": (
            "Daha kapsamlı ve derinlemesine, akademik bir üslupta ama hâlâ "
            "ailelere hitap eden bir yazı. Konuyu birden fazla alt başlıkla "
            "(en az 4-5 <h2>) ele al: tanım/arka plan, belirtiler veya "
            "dinamikler, altta yatan psikolojik mekanizmalar, ailelerin "
            "yapabilecekleri, ne zaman uzman desteği alınmalı gibi bölümler "
            "olabilir. Genel psikolojik kavram ve çerçevelere değinebilirsin "
            "ama UYDURMA istatistik, sayısal oran veya spesifik çalışma adı "
            "EKLEME -- somut sayısal iddialarda bulunma, genel/niteliksel "
            "ifadeler kullan."
        ),
    },
}


def generate(topic: str = "", length: str = "short") -> dict:
    """Returns dict with: topic, title, slug, blog_html_body, ig_caption, image_prompt.
    If `topic` is given (e.g. chosen by the user in the panel), it's used
    as-is instead of picking the next one from the round-robin list.
    `length` is "short" (default, ~500-700 words) or "long" (~1400-2000
    words, more academic in tone)."""
    topic = topic.strip() or _next_topic()
    spec = LENGTH_SPECS.get(length, LENGTH_SPECS["short"])
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
                        f"{spec['word_range']} kelimelik blog yazısı, HTML "
                        "paragraf etiketleri (<p>, <h2>, <ul><li>) ile "
                        f"biçimlendirilmiş. <h1> kullanma, başlık ayrı zaten "
                        f"veriliyor. {spec['style_note']}"
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
                        "görsel üretim modeline verilecek DETAYLI ve SPESİFİK bir "
                        "prompt (4-6 cümle). Genel/soyut ifadelerden kaçın ("
                        "\"warm illustration\" gibi tek başına yetersiz) -- somut bir "
                        "SAHNE kur, DOĞRUDAN bu blog yazısının konusuyla ilgili "
                        "(genel bir 'aile' görseli değil, tam olarak bu konuyu "
                        "yansıtan bir an/metafor): örn. sınav kaygısı için bir "
                        "çocuğun masasında oturmuş, önünde açık bir defter, "
                        "pencereden gelen yumuşak ışık, yanında sakinleştirici bir "
                        "bitki; ekran bağımlılığı için bir aile oyun masasında bir "
                        "arada, tablet kapalı köşede duruyor, sıcak ışık. Şunları "
                        "MUTLAKA belirt: (1) ana konu/sahne, somut nesnelerle, konuyla "
                        "birebir bağlantılı, (2) kompozisyon (ön plan/arka plan, "
                        "açı), (3) sanat stili (örn. 'modern children's book "
                        "illustration', 'editorial illustration with rich linework "
                        "and texture', 'flat design with layered depth'), (4) ışık "
                        "ve atmosfer, (5) renk paleti (marka renkleri: yumuşak "
                        "teal/mercan/altın tonları). ÇOCUK VE EBEVEYN DOSTU OLMALI: "
                        "sıcak, umut verici, güven veren bir atmosfer -- asla ürkütücü, "
                        "üzücü, kaygı verici veya rahatsız edici görseller/semboller "
                        "kullanma (örn. ağlayan çocuk, karanlık/tekinsiz ortam, "
                        "tehdit edici imgeler yasak). Gerçek insan yüzü/fotoğraf "
                        "İÇERMEYEN, sıcak ve profesyonel bir illüstrasyon olmalı."
                    ),
                },
            },
            "required": ["title", "blog_html_body", "ig_caption", "image_prompt"],
        },
    }

    response = client.messages.create(
        model=MODEL,
        max_tokens=spec["max_tokens"],
        tools=[tool],
        tool_choice={"type": "tool", "name": "write_content"},
        messages=[{"role": "user", "content": prompt}],
    )

    tool_use_block = next(
        block for block in response.content if block.type == "tool_use"
    )
    data = dict(tool_use_block.input)

    data["topic"] = topic
    data["length"] = length
    data["slug"] = _slugify(data["title"])
    data["date"] = date.today().isoformat()
    return data


if __name__ == "__main__":
    result = generate()
    print(json.dumps(result, ensure_ascii=False, indent=2))
