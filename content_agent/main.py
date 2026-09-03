"""
Runs the full daily pipeline:
  1. Generate blog post + IG caption + image prompt (Claude API)
  2. Generate the illustration (Stability AI)
  3. Send you a review email
  4. Wait PUBLISH_DELAY_HOURS
  5. If nobody cancelled (no CANCEL_TODAY file committed to the repo),
     publish the blog post to Plesk and the post to Instagram.

Cancelling: from your phone, add a file named CANCEL_TODAY at the repo root
(e.g. via the GitHub mobile app or web UI) any time before the delay ends,
then delete it again for tomorrow. This script checks for that file's
existence right before publishing.
"""
import os
import sys
import time
from pathlib import Path

from generate_content import generate
from generate_image import generate_image
from notify import DELAY_HOURS, send_review_email
from publish_blog import publish_blog_post, upload_image
from publish_instagram import publish_to_instagram

REPO_ROOT = Path(__file__).parent.parent
CANCEL_FLAG = REPO_ROOT / "CANCEL_TODAY"
IMAGES_OUT_DIR = Path("build/images")


def main():
    print("1/5 Generating content...")
    post = generate()
    print(f"    -> {post['title']}")

    print("2/5 Generating illustration...")
    image_path = IMAGES_OUT_DIR / f"{post['slug']}.jpg"
    generate_image(post["image_prompt"], image_path)

    print("3/5 Sending review email...")
    send_review_email(
        post,
        cancel_instructions=(
            "Add a file named CANCEL_TODAY to the repo root before the delay ends."
        ),
    )

    print(f"4/5 Waiting {DELAY_HOURS} hours for review window...")
    time.sleep(DELAY_HOURS * 3600)

    if CANCEL_FLAG.exists():
        print("CANCEL_TODAY found -- skipping publish.")
        CANCEL_FLAG.unlink()  # reset for tomorrow
        sys.exit(0)

    print("5/5 Publishing...")
    blog_url = publish_blog_post(post)
    print(f"    Blog published: {blog_url}")

    image_public_url = upload_image(image_path)
    print(f"    Image uploaded: {image_public_url}")
    media_id = publish_to_instagram(image_public_url, post["ig_caption"])
    print(f"    Instagram published: {media_id}")


if __name__ == "__main__":
    main()
