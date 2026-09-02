"""
Publishes a photo + caption to Instagram via the Meta Graph API.

Requires env vars:
  IG_BUSINESS_ACCOUNT_ID  -- your Instagram Business account's numeric ID
  IG_ACCESS_TOKEN         -- a long-lived Page access token with
                             instagram_basic + instagram_content_publish permissions
  PUBLIC_IMAGE_URL_BASE   -- Instagram requires the image to be reachable at a
                             public URL (it re-downloads it). Point this at
                             wherever you host the generated images -- easiest
                             is a public folder on your own site, e.g.
                             "https://plutonpdrm.com.tr/ig-images"

See README.md for the one-time Meta Developer / Business account setup steps
-- this is the most involved part of the whole project.
"""
import os
import time

import requests

GRAPH_API_VERSION = "v21.0"
IG_BUSINESS_ACCOUNT_ID = os.environ.get("IG_BUSINESS_ACCOUNT_ID")
IG_ACCESS_TOKEN = os.environ.get("IG_ACCESS_TOKEN")
BASE_URL = f"https://graph.facebook.com/{GRAPH_API_VERSION}"


def publish_to_instagram(image_public_url: str, caption: str) -> str:
    # Step 1: create a media container
    container_resp = requests.post(
        f"{BASE_URL}/{IG_BUSINESS_ACCOUNT_ID}/media",
        data={
            "image_url": image_public_url,
            "caption": caption,
            "access_token": IG_ACCESS_TOKEN,
        },
        timeout=30,
    )
    container_resp.raise_for_status()
    container_id = container_resp.json()["id"]

    # Step 2: poll until the container has finished processing
    for _ in range(10):
        status_resp = requests.get(
            f"{BASE_URL}/{container_id}",
            params={"fields": "status_code", "access_token": IG_ACCESS_TOKEN},
            timeout=30,
        )
        status = status_resp.json().get("status_code")
        if status == "FINISHED":
            break
        time.sleep(5)
    else:
        raise RuntimeError("Instagram media container never finished processing")

    # Step 3: publish the container
    publish_resp = requests.post(
        f"{BASE_URL}/{IG_BUSINESS_ACCOUNT_ID}/media_publish",
        data={"creation_id": container_id, "access_token": IG_ACCESS_TOKEN},
        timeout=30,
    )
    publish_resp.raise_for_status()
    return publish_resp.json()["id"]


if __name__ == "__main__":
    result = publish_to_instagram(
        "https://plutonpdrm.com.tr/ig-images/example.jpg",
        "Test caption #test",
    )
    print(f"Published, media id: {result}")
