"""
Generates the Instagram illustration from an image prompt.
Uses fal.ai hosting FLUX.1 [dev] as the default provider -- strong
illustration quality, simple single-call REST API (no polling), and cheap
(~$0.025-0.03/image; ~$1/month at 1 post/day).
Requires env var: FAL_KEY  (get one at fal.ai/dashboard/keys)

Cheaper alternative: swap FAL_MODEL below to "fal-ai/flux/schnell"
(~$0.003/image) if you ever want to cut cost further -- same provider,
same code, slightly lower fidelity.

Swap-friendly: if you prefer a different provider entirely, just rewrite
generate_image() to call it instead -- it only needs to save a JPG/PNG to
`output_path` and return the path.
"""
import os
from pathlib import Path

import requests

FAL_KEY = os.environ.get("FAL_KEY")
FAL_MODEL = "fal-ai/flux/dev"
FAL_URL = f"https://fal.run/{FAL_MODEL}"

BRAND_STYLE_SUFFIX = (
    ", soft pastel color palette, warm and calming, flat illustration style, "
    "no text, no real human faces, square 1:1 composition, suitable for a "
    "psychological counseling center's Instagram post"
)


def generate_image(prompt: str, output_path: Path) -> Path:
    full_prompt = prompt.strip() + BRAND_STYLE_SUFFIX

    response = requests.post(
        FAL_URL,
        headers={
            "Authorization": f"Key {FAL_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "prompt": full_prompt,
            "image_size": "square_hd",
        },
        timeout=60,
    )
    response.raise_for_status()
    image_url = response.json()["images"][0]["url"]

    image_response = requests.get(image_url, timeout=60)
    image_response.raise_for_status()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(image_response.content)
    return output_path


if __name__ == "__main__":
    test_path = Path("test_output.jpg")
    generate_image(
        "A gentle illustration of a parent and child sitting together reading a book",
        test_path,
    )
    print(f"Saved to {test_path}")
