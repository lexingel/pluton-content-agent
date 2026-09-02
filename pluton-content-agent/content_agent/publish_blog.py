"""
Builds the blog post HTML page (matching site style) and uploads it to
Plesk hosting via SFTP.

Requires: pip install paramiko
Requires env vars: SFTP_HOST, SFTP_USER, SFTP_PASSWORD, SFTP_REMOTE_BLOG_DIR

NOTE: adjust `PAGE_TEMPLATE` below to match your real site's header/nav/footer
HTML once you share it -- right now it's a reasonable placeholder using the
soft/warm palette already agreed for the site.
"""
import os
from pathlib import Path

import paramiko

SFTP_HOST = os.environ.get("SFTP_HOST")
SFTP_USER = os.environ.get("SFTP_USER")
SFTP_PASSWORD = os.environ.get("SFTP_PASSWORD")
SFTP_REMOTE_BLOG_DIR = os.environ.get("SFTP_REMOTE_BLOG_DIR", "/httpdocs/blog")

PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8">
<title>{title} | Plüton PDRM</title>
<meta name="description" content="{title} - Plüton Psikolojik Danışmanlık ve Rehberlik Merkezi">
<link rel="stylesheet" href="/style.css">
</head>
<body>
<header><!-- TODO: paste real site header/nav here --></header>
<main class="blog-post">
  <h1>{title}</h1>
  <p class="post-date">{date}</p>
  {body}
</main>
<footer><!-- TODO: paste real site footer here --></footer>
</body>
</html>
"""


def build_page(post: dict) -> Path:
    html = PAGE_TEMPLATE.format(
        title=post["title"], date=post["date"], body=post["blog_html_body"]
    )
    local_path = Path("build") / f"{post['slug']}.html"
    local_path.parent.mkdir(parents=True, exist_ok=True)
    local_path.write_text(html, encoding="utf-8")
    return local_path


def upload(local_path: Path, remote_filename: str):
    transport = paramiko.Transport((SFTP_HOST, 22))
    transport.connect(username=SFTP_USER, password=SFTP_PASSWORD)
    sftp = paramiko.SFTPClient.from_transport(transport)
    remote_path = f"{SFTP_REMOTE_BLOG_DIR}/{remote_filename}"
    sftp.put(str(local_path), remote_path)
    sftp.close()
    transport.close()


def publish_blog_post(post: dict) -> str:
    """Builds and uploads the post. Returns the live URL (best guess)."""
    local_path = build_page(post)
    upload(local_path, local_path.name)
    # TODO: also update /blog/index.html to list this new post (append a
    # <li><a href="...">) -- left as a manual or follow-up step since it
    # depends on your index page's exact markup.
    return f"https://plutonpdrm.com.tr/blog/{local_path.name}"


if __name__ == "__main__":
    demo_post = {
        "title": "Test Başlık",
        "date": "2026-09-03",
        "blog_html_body": "<p>Test içerik.</p>",
        "slug": "test-baslik",
    }
    print(publish_blog_post(demo_post))
