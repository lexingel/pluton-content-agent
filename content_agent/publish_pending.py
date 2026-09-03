"""
Publishes whatever is currently staged in pending.json to the blog and
Instagram, then clears it. Only runs when triggered (by the admin panel's
Approve button, via GitHub's workflow_dispatch API).

Run by: .github/workflows/publish-approved.yml
"""
import sys

from publish_blog import delete_pending, download_pending, publish_blog_post
from publish_instagram import publish_to_instagram


def main():
    print("1/3 Fetching pending content...")
    pending = download_pending()
    if not pending:
        print("    Nothing pending -- was it already published or rejected?")
        sys.exit(0)
    print(f"    -> {pending['title']}")

    print("2/3 Publishing to blog...")
    blog_url = publish_blog_post(pending, image_url=pending.get("image_url", ""))
    print(f"    Blog published: {blog_url}")

    print("3/3 Publishing to Instagram...")
    media_id = publish_to_instagram(pending.get("image_url", ""), pending["ig_caption"])
    print(f"    Instagram published: {media_id}")

    delete_pending()
    print("Done.")


if __name__ == "__main__":
    main()
