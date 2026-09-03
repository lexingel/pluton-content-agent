"""
Builds the blog post HTML page (matching site style), maintains a
posts.json manifest of all posts, regenerates /blog/index.html from that
manifest, and uploads everything to Plesk hosting via plain FTP.

Uses Python's built-in ftplib -- no extra dependency needed. (Switched
from SFTP because many shared hosts disable external SSH access even
when SFTP works inside the hosting panel's own file manager.)

Requires env vars: SFTP_HOST, SFTP_USER, SFTP_PASSWORD, SFTP_REMOTE_BLOG_DIR
(names kept as SFTP_* for continuity with existing GitHub Secrets, but
these now configure a plain FTP connection.)
"""
import io
import json
import os
import re
from ftplib import FTP
from pathlib import Path

SFTP_HOST = os.environ.get("SFTP_HOST")
SFTP_USER = os.environ.get("SFTP_USER")
SFTP_PASSWORD = os.environ.get("SFTP_PASSWORD")
SFTP_REMOTE_BLOG_DIR = os.environ.get("SFTP_REMOTE_BLOG_DIR", "/httpdocs/blog")

LOGO_URL = "https://www.plutonpdrm.com.tr/logo.png"  # see note in README.md re: uploading this once
MANIFEST_FILENAME = "posts.json"

# ---------------------------------------------------------------------------
# Shared header/footer, exactly matching the live site's design system.
# ---------------------------------------------------------------------------

BASE_STYLE = """
  :root {
    --bg: #FFFDF9; --bg-soft: #FAF4E9; --surface: #FFFFFF; --surface-2: #FCF7ED;
    --text: #453E38; --text-muted: #8D8177; --border: #F2E9D9;
    --teal: #4E958D; --teal-deep: #2E6F68; --teal-tint: #ECF5F3;
    --coral: #F0A98D; --coral-tint: #FCEFE7; --gold: #E4B768; --gold-tint: #FBF1DD;
    --shadow: 0 20px 46px -26px rgba(78, 149, 141, 0.30);
    --focus: #2E6F68; --accent-solid: #2E6F68; --on-accent: #FFFDF8;
    --logo-plate: linear-gradient(135deg, #F6F1E7, #FCE9DD);
  }
  @media (prefers-color-scheme: dark) {
    :root:not([data-theme="light"]) {
      --bg: #21403B; --bg-soft: #1A332F; --surface: #2A4941; --surface-2: #30524A;
      --text: #F4EEE5; --text-muted: #B9AFA4; --border: #3D5F55;
      --teal: #6BC3B9; --teal-deep: #86D6CC; --teal-tint: #203935;
      --coral: #EFA987; --coral-tint: #33241C; --gold: #E6BD75; --gold-tint: #2F2717;
      --focus: #86D6CC; --accent-solid: var(--teal); --on-accent: #12211F;
      --logo-plate: linear-gradient(135deg, #F6F1E7, #FCE9DD);
    }
  }
  :root[data-theme="dark"] {
    --bg: #21403B; --bg-soft: #1A332F; --surface: #2A4941; --surface-2: #30524A;
    --text: #F4EEE5; --text-muted: #B9AFA4; --border: #3D5F55;
    --teal: #6BC3B9; --teal-deep: #86D6CC; --teal-tint: #203935;
    --coral: #EFA987; --coral-tint: #33241C; --gold: #E6BD75; --gold-tint: #2F2717;
    --focus: #86D6CC; --accent-solid: var(--teal); --on-accent: #12211F;
    --logo-plate: linear-gradient(135deg, #F6F1E7, #FCE9DD);
  }
  * { box-sizing: border-box; }
  html { scroll-behavior: smooth; }
  body { margin: 0; background: var(--bg); color: var(--text); font-family: "Mulish", "Segoe UI", system-ui, sans-serif; font-size: 17px; line-height: 1.65; -webkit-font-smoothing: antialiased; }
  img { max-width: 100%; display: block; }
  h1, h2, h3 { font-family: "Baloo 2", "Segoe UI", sans-serif; text-wrap: balance; margin: 0; color: var(--text); }
  a { color: inherit; }
  .wrap { max-width: 1180px; margin: 0 auto; padding: 0 28px; }

  header { position: sticky; top: 0; z-index: 40; background: color-mix(in srgb, var(--bg) 88%, transparent); backdrop-filter: blur(10px); border-bottom: 1px solid var(--border); }
  .nav-row { display: flex; align-items: center; justify-content: space-between; gap: 24px; padding: 14px 0; }
  .brand { display: flex; align-items: center; gap: 12px; text-decoration: none; flex-shrink: 0; }
  .logo-plate { display: inline-flex; align-items: center; background: var(--logo-plate); border-radius: 12px; padding: 6px 14px; }
  .brand img { height: 30px; width: auto; }
  nav.links { display: flex; gap: 8px; list-style: none; margin: 0; padding: 0; font-size: 15px; }
  nav.links a { text-decoration: none; color: var(--text-muted); padding: 9px 16px; border-radius: 999px; font-weight: 600; }
  nav.links a:hover { background: var(--teal-tint); color: var(--teal-deep); }
  .nav-cta { display: inline-flex; align-items: center; gap: 8px; background: var(--accent-solid); color: var(--on-accent) !important; padding: 10px 20px; border-radius: 999px; text-decoration: none; font-weight: 700; font-size: 14.5px; white-space: nowrap; }
  @media (max-width: 860px) { nav.links { display: none; } }

  main { padding: 24px 0 64px; }
  .back-link { display: inline-flex; align-items: center; gap: 8px; font-weight: 700; font-size: 14.5px; color: var(--text-muted); text-decoration: none; margin-bottom: 34px; }
  .back-link:hover { color: var(--teal-deep); }
  .blog-post { max-width: 760px; margin: 0 auto; }
  .post-date { color: var(--text-muted); font-size: 14px; margin: 8px 0 0; }
  .post-cover { width: 100%; aspect-ratio: 1 / 1; object-fit: cover; border-radius: 24px; margin: 24px 0 8px; box-shadow: var(--shadow); }
  .blog-post h2 { font-size: 1.4rem; font-weight: 600; margin: 40px 0 18px; }
  .blog-post p { color: var(--text-muted); font-size: 17px; margin: 0 0 18px; }
  .blog-post ul { padding-left: 20px; color: var(--text-muted); }
  .blog-post li { margin-bottom: 6px; }
  .btn { display: inline-flex; align-items: center; gap: 9px; padding: 14px 26px; border-radius: 999px; text-decoration: none; font-weight: 700; font-size: 15.5px; border: 1px solid transparent; }
  .btn-primary { background: var(--accent-solid); color: var(--on-accent); box-shadow: var(--shadow); margin-top: 20px; }
  .btn-primary:hover { filter: brightness(0.92); }

  .page-head { max-width: 760px; margin: 0 auto 40px; }
  .page-head h1 { font-size: clamp(1.9rem, 3.6vw, 2.6rem); font-weight: 600; }
  .page-head p { color: var(--text-muted); font-size: 17px; margin-top: 12px; }
  .blog-grid { max-width: 900px; margin: 0 auto; display: grid; gap: 18px; }
  .blog-card { display: flex; gap: 20px; align-items: center; background: var(--surface); border: 1px solid var(--border); border-radius: 22px; padding: 20px 26px; text-decoration: none; transition: transform 0.15s ease, box-shadow 0.15s ease; }
  .blog-card:hover { transform: translateY(-2px); box-shadow: var(--shadow); }
  .blog-card .card-thumb { width: 84px; height: 84px; border-radius: 16px; object-fit: cover; flex-shrink: 0; }
  .blog-card .card-text { min-width: 0; }
  .blog-card .card-date { color: var(--text-muted); font-size: 13.5px; font-weight: 700; letter-spacing: 0.02em; text-transform: uppercase; }
  .blog-card h2 { font-size: 1.2rem; font-weight: 600; margin: 8px 0 10px; }
  .blog-card p { color: var(--text-muted); font-size: 15.5px; margin: 0; }
  .blog-empty { max-width: 760px; margin: 0 auto; color: var(--text-muted); text-align: center; padding: 40px 0; }

  footer { padding: 32px 0; border-top: 1px solid var(--border); background: var(--bg); }
  .footer-row { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 16px; }
  .footer-brand { display: flex; align-items: center; gap: 10px; flex-shrink: 0; }
  .footer-brand img { height: 26px; width: auto; }
  footer p { margin: 0; font-size: 13.5px; color: var(--text-muted); }
  .footer-links { display: flex; gap: 18px; flex-wrap: wrap; }
  .footer-links a { font-size: 13.5px; color: var(--text-muted); text-decoration: none; }
  .footer-links a:hover { color: var(--teal); }
  .whatsapp-fab { position: fixed; bottom: 20px; right: 20px; width: 52px; height: 52px; border-radius: 50%; background: #25D366; color: #fff; display: flex; align-items: center; justify-content: center; box-shadow: var(--shadow); z-index: 50; }
"""

HEADER_HTML = """<header>
  <div class="wrap nav-row">
    <a class="brand logo-plate" href="https://www.plutonpdrm.com.tr/">
      <img src="{logo_src}" alt="Plüton PDRM logosu">
    </a>
    <nav class="links" aria-label="Ana menü">
      <a href="https://www.plutonpdrm.com.tr/#hakkimizda">Hakkımızda</a>
      <a href="https://www.plutonpdrm.com.tr/#hizmetler">Hizmetlerimiz</a>
      <a href="https://www.plutonpdrm.com.tr/#testler">Testler</a>
      <a href="https://www.plutonpdrm.com.tr/#ekibimiz">Ekibimiz</a>
      <a href="https://www.plutonpdrm.com.tr/okullar-icin.html">Okullar</a>
      <a href="https://www.plutonpdrm.com.tr/#sss">SSS</a>
      <a href="https://www.plutonpdrm.com.tr/#iletisim">İletişim</a>
    </nav>
    <a class="nav-cta" href="https://www.plutonpdrm.com.tr/#iletisim">Randevu Alın</a>
  </div>
</header>"""

FOOTER_HTML = """<footer>
  <a class="whatsapp-fab" href="https://wa.me/905365908797?text=Merhaba%2C%20web%20sitenizden%20yaz%C4%B1yorum." target="_blank" rel="noopener noreferrer" aria-label="WhatsApp'tan yazın">
    <svg width="26" height="26" viewBox="0 0 24 24" fill="currentColor"><path d="M12.04 2c-5.46 0-9.9 4.44-9.9 9.9 0 1.75.46 3.45 1.32 4.95L2 22l5.25-1.38a9.9 9.9 0 0 0 4.79 1.22h.01c5.46 0 9.9-4.44 9.9-9.9 0-2.64-1.03-5.12-2.9-6.99A9.82 9.82 0 0 0 12.04 2Zm0 1.67c2.19 0 4.25.85 5.8 2.4a8.2 8.2 0 0 1 2.41 5.83c0 4.55-3.7 8.25-8.24 8.25a8.2 8.2 0 0 1-4.2-1.15l-.3-.18-3.12.82.83-3.04-.2-.31a8.18 8.18 0 0 1-1.26-4.39c0-4.55 3.7-8.23 8.28-8.23Zm-4.7 4.6c-.16 0-.43.06-.66.31-.22.25-.86.84-.86 2.05 0 1.21.88 2.38 1 2.54.12.17 1.72 2.7 4.24 3.68 2.1.82 2.53.66 2.98.62.46-.04 1.48-.6 1.69-1.19.2-.58.2-1.08.14-1.19-.06-.1-.23-.17-.48-.29-.25-.13-1.48-.73-1.71-.81-.23-.08-.4-.13-.57.13-.17.25-.65.81-.8.98-.15.17-.29.19-.54.06-.25-.13-1.06-.39-2.02-1.25-.75-.66-1.25-1.48-1.4-1.73-.15-.25-.02-.39.11-.51.11-.11.25-.29.37-.44.12-.15.16-.25.24-.42.08-.17.04-.31-.02-.44-.06-.13-.57-1.4-.79-1.91-.2-.5-.42-.43-.57-.44-.15-.01-.32-.01-.48-.01Z"/></svg>
  </a>
  <div class="wrap footer-row">
    <div class="footer-brand logo-plate">
      <img src="{logo_src}" alt="Plüton PDRM logosu">
    </div>
    <p>© 2026 Plüton Psikolojik Danışmanlık ve Rehberlik Merkezi · Narlıdere, İzmir</p>
    <div class="footer-links">
      <a href="https://www.plutonpdrm.com.tr/#hakkimizda">Hakkımızda</a>
      <a href="https://www.plutonpdrm.com.tr/#hizmetler">Hizmetlerimiz</a>
      <a href="https://www.plutonpdrm.com.tr/#testler">Testler</a>
      <a href="https://www.plutonpdrm.com.tr/#ekibimiz">Ekibimiz</a>
      <a href="https://www.plutonpdrm.com.tr/okullar-icin.html">Okullar</a>
      <a href="https://www.plutonpdrm.com.tr/#sss">SSS</a>
      <a href="https://www.plutonpdrm.com.tr/#iletisim">İletişim</a>
    </div>
  </div>
</footer>"""

PAGE_HEAD = """<!doctype html>
<html lang="tr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<script>
(function(){{
  try {{
    var t = localStorage.getItem('pluton-theme');
    if (t === 'light' || t === 'dark') {{ document.documentElement.setAttribute('data-theme', t); }}
  }} catch (e) {{}}
}})();
</script>
<title>{page_title}</title>
<meta name="description" content="{page_description}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Baloo+2:wght@500;600;700;800&family=Mulish:ital,wght@0,400;0,500;0,600;0,700;1,400&display=swap" rel="stylesheet">
<style>{style}</style>
</head>
<body>
""" + HEADER_HTML

PAGE_TAIL = FOOTER_HTML + """
</body>
</html>
"""

POST_MAIN_TEMPLATE = """<main>
  <div class="wrap">
    <a class="back-link" href="https://www.plutonpdrm.com.tr/blog/">&larr; Blog'a Dön</a>
    <div class="blog-post">
      <h1>{title}</h1>
      <p class="post-date">{date}</p>
      {cover_image}
      {body}
      <a class="btn btn-primary" href="https://www.plutonpdrm.com.tr/#iletisim">Randevu Alın</a>
    </div>
  </div>
</main>
"""

COVER_IMAGE_TEMPLATE = '<img class="post-cover" src="{image_url}" alt="{title}">'

INDEX_MAIN_TEMPLATE = """<main>
  <div class="wrap">
    <div class="page-head">
      <h1>Blog</h1>
      <p>DEHB'den sınav kaygısına, aile danışmanlığından okul öncesi gelişime kadar ailelerin merak ettiği konularda yazılar.</p>
    </div>
    <div class="blog-grid">
      {cards}
    </div>
  </div>
</main>
"""

CARD_TEMPLATE = """<a class="blog-card" href="https://www.plutonpdrm.com.tr/blog/{slug}.html">
        {thumb}
        <div class="card-text">
          <div class="card-date">{date}</div>
          <h2>{title}</h2>
          <p>{excerpt}</p>
        </div>
      </a>"""

CARD_THUMB_TEMPLATE = '<img class="card-thumb" src="{image_url}" alt="{title}">'


def _excerpt(html_body: str, max_len: int = 160) -> str:
    text = re.sub(r"<[^>]+>", " ", html_body)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > max_len:
        text = text[:max_len].rsplit(" ", 1)[0] + "…"
    return text


def build_post_page(post: dict, image_url: str = "") -> Path:
    cover_image = (
        COVER_IMAGE_TEMPLATE.format(image_url=image_url, title=post["title"])
        if image_url
        else ""
    )
    html = (
        PAGE_HEAD.format(
            page_title=f"{post['title']} | Plüton PDRM",
            page_description=f"{post['title']} - Plüton Psikolojik Danışmanlık ve Rehberlik Merkezi",
            style=BASE_STYLE,
            logo_src=LOGO_URL,
        )
        + POST_MAIN_TEMPLATE.format(
            title=post["title"],
            date=post["date"],
            cover_image=cover_image,
            body=post["blog_html_body"],
        )
        + PAGE_TAIL.format(logo_src=LOGO_URL)
    )
    local_path = Path("build") / f"{post['slug']}.html"
    local_path.parent.mkdir(parents=True, exist_ok=True)
    local_path.write_text(html, encoding="utf-8")
    return local_path


def build_index_page(posts: list) -> Path:
    if posts:
        cards = "\n      ".join(
            CARD_TEMPLATE.format(
                slug=p["slug"],
                date=p["date"],
                title=p["title"],
                excerpt=p["excerpt"],
                thumb=(
                    CARD_THUMB_TEMPLATE.format(image_url=p["image_url"], title=p["title"])
                    if p.get("image_url")
                    else ""
                ),
            )
            for p in posts
        )
        main_html = INDEX_MAIN_TEMPLATE.format(cards=cards)
    else:
        main_html = (
            '<main><div class="wrap"><div class="page-head"><h1>Blog</h1>'
            '<p>Çok yakında burada olacak.</p></div>'
            '<p class="blog-empty">Henüz yazı eklenmedi.</p></div></main>'
        )

    html = (
        PAGE_HEAD.format(
            page_title="Blog | Plüton PDRM",
            page_description="Plüton PDRM blog - aile, gelişim ve danışmanlık konularında yazılar.",
            style=BASE_STYLE,
            logo_src=LOGO_URL,
        )
        + main_html
        + PAGE_TAIL.format(logo_src=LOGO_URL)
    )
    local_path = Path("build") / "index.html"
    local_path.parent.mkdir(parents=True, exist_ok=True)
    local_path.write_text(html, encoding="utf-8")
    return local_path


def _ftp_connect() -> FTP:
    ftp = FTP()
    ftp.connect(SFTP_HOST, 21, timeout=30)
    ftp.login(SFTP_USER, SFTP_PASSWORD)
    try:
        ftp.cwd(SFTP_REMOTE_BLOG_DIR)
    except Exception:
        # Some hosts chroot the FTP account straight into httpdocs, so a
        # path like "/httpdocs/blog" won't exist -- retry with that prefix
        # stripped (e.g. just "/blog" or "blog").
        stripped = re.sub(r"^/?(httpdocs/)?", "", SFTP_REMOTE_BLOG_DIR)
        ftp.cwd("/" + stripped)
    return ftp


def _download_manifest(ftp: FTP) -> list:
    try:
        buf = io.BytesIO()
        ftp.retrbinary(f"RETR {MANIFEST_FILENAME}", buf.write)
        return json.loads(buf.getvalue().decode("utf-8"))
    except Exception:
        return []  # no manifest yet (first run) or unreadable -- start fresh


def _upload_bytes(ftp: FTP, data: bytes, remote_filename: str):
    ftp.storbinary(f"STOR {remote_filename}", io.BytesIO(data))


def _upload_file(ftp: FTP, local_path: Path):
    with open(local_path, "rb") as f:
        ftp.storbinary(f"STOR {local_path.name}", f)


def _ig_images_remote_dir() -> str:
    """Derives the /ig-images sibling folder from SFTP_REMOTE_BLOG_DIR
    (e.g. /httpdocs/blog -> /httpdocs/ig-images)."""
    parent = SFTP_REMOTE_BLOG_DIR.rsplit("/", 1)[0] or "/"
    return f"{parent}/ig-images"


def _panel_data_remote_dir() -> str:
    """Derives the /panel/data sibling folder from SFTP_REMOTE_BLOG_DIR
    (e.g. /httpdocs/blog -> /httpdocs/panel/data). This must match where
    you upload the admin-panel/ folder in Plesk (panel lives at
    httpdocs/panel/, so its data subfolder is httpdocs/panel/data)."""
    parent = SFTP_REMOTE_BLOG_DIR.rsplit("/", 1)[0] or "/"
    return f"{parent}/panel/data"


def _cwd_with_fallback(ftp: FTP, remote_dir: str):
    try:
        ftp.cwd(remote_dir)
    except Exception:
        try:
            ftp.mkd(remote_dir)
            ftp.cwd(remote_dir)
        except Exception:
            stripped = re.sub(r"^/?(httpdocs/)?", "", remote_dir)
            ftp.cwd("/" + stripped)


def upload_image(local_path: Path) -> str:
    """Uploads the generated illustration to a public folder on the site
    (sibling of the blog folder) and returns its public URL -- Instagram's
    API needs to fetch the image from a real public address."""
    ftp = FTP()
    ftp.connect(SFTP_HOST, 21, timeout=30)
    ftp.login(SFTP_USER, SFTP_PASSWORD)
    _cwd_with_fallback(ftp, _ig_images_remote_dir())
    try:
        _upload_file(ftp, local_path)
    finally:
        ftp.quit()
    return f"https://www.plutonpdrm.com.tr/ig-images/{local_path.name}"


def upload_pending(pending: dict):
    """Writes pending.json into the panel's data folder on the server, so
    the PHP admin panel (reading the same file locally) can show it for
    review."""
    ftp = FTP()
    ftp.connect(SFTP_HOST, 21, timeout=30)
    ftp.login(SFTP_USER, SFTP_PASSWORD)
    _cwd_with_fallback(ftp, _panel_data_remote_dir())
    try:
        _upload_bytes(
            ftp,
            json.dumps(pending, ensure_ascii=False, indent=2).encode("utf-8"),
            "pending.json",
        )
    finally:
        ftp.quit()


def download_pending() -> dict | None:
    """Reads pending.json back from the server. Returns None if there is
    nothing pending (e.g. it was rejected, or already published)."""
    ftp = FTP()
    ftp.connect(SFTP_HOST, 21, timeout=30)
    ftp.login(SFTP_USER, SFTP_PASSWORD)
    _cwd_with_fallback(ftp, _panel_data_remote_dir())
    try:
        buf = io.BytesIO()
        ftp.retrbinary("RETR pending.json", buf.write)
        return json.loads(buf.getvalue().decode("utf-8"))
    except Exception:
        return None
    finally:
        ftp.quit()


def delete_pending():
    """Removes pending.json from the server once it's been published (or
    to clean up after a reject, though the panel also does this locally
    for an instant UI update)."""
    ftp = FTP()
    ftp.connect(SFTP_HOST, 21, timeout=30)
    ftp.login(SFTP_USER, SFTP_PASSWORD)
    _cwd_with_fallback(ftp, _panel_data_remote_dir())
    try:
        ftp.delete("pending.json")
    except Exception:
        pass
    finally:
        ftp.quit()


def publish_blog_post(post: dict, image_url: str = "") -> str:
    """Builds the post, updates the manifest + index, uploads everything.
    Returns the live URL of the new post."""
    post_path = build_post_page(post, image_url=image_url)

    ftp = _ftp_connect()
    try:
        manifest = _download_manifest(ftp)
        manifest = [p for p in manifest if p["slug"] != post["slug"]]  # dedupe
        manifest.append(
            {
                "slug": post["slug"],
                "title": post["title"],
                "date": post["date"],
                "excerpt": _excerpt(post["blog_html_body"]),
                "image_url": image_url,
            }
        )
        manifest.sort(key=lambda p: p["date"], reverse=True)

        index_path = build_index_page(manifest)

        _upload_file(ftp, post_path)
        _upload_file(ftp, index_path)
        _upload_bytes(
            ftp,
            json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8"),
            MANIFEST_FILENAME,
        )
    finally:
        ftp.quit()

    return f"https://www.plutonpdrm.com.tr/blog/{post_path.name}"


if __name__ == "__main__":
    demo_post = {
        "title": "Test Başlık",
        "date": "2026-09-03",
        "blog_html_body": "<p>Test içerik. Bu bir deneme yazısıdır ve blog sayfasının nasıl göründüğünü kontrol etmek için kullanılır.</p>",
        "slug": "test-baslik",
    }
    print(publish_blog_post(demo_post))
