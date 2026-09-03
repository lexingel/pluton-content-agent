"""
Generates the Instagram illustration from an image prompt.
Uses fal.ai hosting FLUX.1.1 [pro] as the default provider -- noticeably
richer, more detailed results than the "dev"/"schnell" tiers, at
~$0.05-0.06/image (~$1.50-1.80/month at 1 post/day -- still cheap).
Requires env var: FAL_KEY  (get one at fal.ai/dashboard/keys)

Cheaper alternative: swap FAL_MODEL below to "fal-ai/flux/dev"
(~$0.03/image) or "fal-ai/flux/schnell" (~$0.003/image) if cost ever
matters more than quality -- same code either way.

Swap-friendly: if you prefer a different provider entirely, just rewrite
generate_image() to call it instead -- it only needs to save a JPG/PNG to
`output_path` and return the path.
"""
import os
from pathlib import Path

import requests

FAL_KEY = os.environ.get("FAL_KEY")
FAL_MODEL = "fal-ai/flux-pro/v1.1"
FAL_URL = f"https://fal.run/{FAL_MODEL}"

# Pushes toward richer, more detailed illustrations instead of flat/simple
# ones -- vague style suffixes produce plain results, so this is specific
# about medium, complexity, and composition depth.
BRAND_STYLE_SUFFIX = (
    ", rich detailed illustration with layered composition and depth, "
    "textured digital painting style, intricate background elements that "
    "support the main scene, soft cinematic lighting, warm and calming "
    "color palette in soft teal/coral/gold tones, professional editorial "
    "illustration quality, gentle and reassuring mood appropriate for "
    "children and parents -- warm, hopeful, and supportive, never scary, "
    "sad, or distressing, no text, no real human faces, square 1:1 "
    "composition, suitable for a psychological counseling center's "
    "Instagram post"
)

# More inference steps = more detail (at a small extra cost/time). Only
# applies to the "dev"/"schnell" open-weight models -- the hosted "pro"
# endpoints (like flux-pro/v1.1, the current default) don't expose these
# knobs and ignore them, since they tune internally for consistent quality.
NUM_INFERENCE_STEPS = 42
GUIDANCE_SCALE = 4.2
SUPPORTS_STEP_TUNING = "/dev" in FAL_MODEL or "schnell" in FAL_MODEL


def generate_image(prompt: str, output_path: Path) -> Path:
    full_prompt = prompt.strip() + BRAND_STYLE_SUFFIX

    payload = {
        "prompt": full_prompt,
        "image_size": "square_hd",
    }
    if SUPPORTS_STEP_TUNING:
        payload["num_inference_steps"] = NUM_INFERENCE_STEPS
        payload["guidance_scale"] = GUIDANCE_SCALE
    else:
        # the "pro" endpoints support an explicit safety checker -- worth
        # keeping on given this is content aimed at families/children
        payload["enable_safety_checker"] = True

    response = requests.post(
        FAL_URL,
        headers={
            "Authorization": f"Key {FAL_KEY}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=90,
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
