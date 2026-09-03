"""
Publishes whatever is currently staged in pending.json to the blog and
Instagram, then clears it and records it in history.json. Only runs when
triggered (by the admin panel's Approve button, via GitHub's
workflow_dispatch API).

Run by: .github/workflows/publish-approved.yml
"""
import sys
from datetime import datetime, timezone

from publish_blog import (
    clear_publishing_flag,
    delete_pending,
    download_pending,
    publish_blog_post,
    record_history,
)
from publish_instagram import publish_to_instagram


def main():
    print("1/3 Fetching pending content...")
    pending = download_pending()
    if not pending:
        print("    Nothing pending -- was it already published or rejected?")
        clear_publishing_flag()
        sys.exit(0)
    print(f"    -> {pending['title']}")

    print("2/3 Publishing to blog...")
    blog_url = publish_blog_post(pending, image_url=pending.get("image_url", ""))
    print(f"    Blog published: {blog_url}")

    print("3/3 Publishing to Instagram...")
    media_id = publish_to_instagram(pending.get("image_url", ""), pending["ig_caption"])
    print(f"    Instagram published: {media_id}")

    delete_pending()
    record_history(
        {
            "title": pending["title"],
            "topic": pending.get("topic", ""),
            "length": pending.get("length", "short"),
            "date": pending["date"],
            "slug": pending["slug"],
            "blog_url": blog_url,
            "image_url": pending.get("image_url", ""),
            "ig_caption": pending["ig_caption"],
            "ig_media_id": media_id,
            "published_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    clear_publishing_flag()
    print("Done.")


if __name__ == "__main__":
    main()
