"""
Generates a blog post + Instagram caption + illustration, then stages it
as pending.json on the server for review in the admin panel. Does NOT
publish anything -- that only happens when you click Approve in the
panel (which triggers publish_pending.py via GitHub Actions).

Run by: .github/workflows/generate-content.yml
Optional env var TOPIC: if set (the panel passes whatever you chose),
generates about that specific topic instead of picking the next one
from the round-robin list.
Optional env var LENGTH: "short" (default) or "long".
"""
import os
from pathlib import Path

from generate_content import generate
from generate_image import generate_image
from publish_blog import clear_generating_flag, upload_image, upload_pending

IMAGES_OUT_DIR = Path("build/images")


def main():
    topic = os.environ.get("TOPIC", "")
    length = os.environ.get("LENGTH", "short")

    print("1/3 Generating content...")
    post = generate(topic=topic, length=length)
    print(f"    -> {post['title']}")

    print("2/3 Generating illustration...")
    image_path = IMAGES_OUT_DIR / f"{post['slug']}.jpg"
    generate_image(post["image_prompt"], image_path)

    print("3/3 Staging for review...")
    image_url = upload_image(image_path)
    pending = {**post, "image_url": image_url}
    upload_pending(pending)
    clear_generating_flag()
    print(f"    Staged: {post['title']}")
    print("    Open the admin panel to review, approve, or reject it.")


if __name__ == "__main__":
    main()
