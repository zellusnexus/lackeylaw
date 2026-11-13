#!/usr/bin/env python3
"""Rebuild every blog feed on the site from the blog posts themselves.

Run from anywhere:   python3 scripts/update_blog_feeds.py
Check only:          python3 scripts/update_blog_feeds.py --check   (exit 1 if anything is out of date)

What it updates
  1. "Latest News" feeds: every HTML page containing the markers
         <!-- latest-news:start -->  ...  <!-- latest-news:end -->
     gets the 3 newest posts (image, date, title, excerpt, Read More link) between them.
  2. The blog listing pages blog/, blog/2/, blog/3/ ... : 6 posts per page, newest first,
     with page-number links. New pages are created (and surplus ones removed) as needed.
  3. sitemap.xml: every post and every blog listing page is listed.

What counts as a blog post
  A folder <slug>/index.html (at the site root) that uses the single-post template
  (data-elementor-type="single-post") and has "@type":"Article" schema with a "datePublished".
  Posts are ordered by datePublished, newest first. See README.md, "Adding a blog post".

Only the Python standard library is used, so it runs anywhere (including GitHub Actions).
"""
import glob
import html
import math
import os
import re
import shutil
import sys
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = "https://www.thelackeylawfirm.com"
LATEST_COUNT = 3
PER_PAGE = 6
START, END = "<!-- latest-news:start -->", "<!-- latest-news:end -->"


# ---------------------------------------------------------------- reading posts
def _text(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s))).strip()


def _excerpt(s, limit=150):
    m = re.search(r'<meta name="description" content="([^"]*)"', s)
    text = _text(m.group(1)) if m else ""
    if not text or "not set" in text.lower():
        body = s.split('data-elementor-type="single-post"', 1)[-1]
        for p in re.findall(r"<p\b[^>]*>(.*?)</p>", body, re.S):
            text = _text(p)
            if len(text) > 60:
                break
    if len(text) > limit:
        text = text[:limit].rsplit(" ", 1)[0].rstrip(",;:—–- ") + "…"
    return text


def read_posts():
    posts = []
    for path in glob.glob(os.path.join(ROOT, "*", "index.html")):
        s = open(path, encoding="utf-8").read()
        if 'http-equiv="refresh"' in s or 'data-elementor-type="single-post"' not in s:
            continue
        if '"@type":"Article"' not in s:
            continue  # single-post template but not a blog article (e.g. a practice page)
        m = re.search(r'"datePublished":"([^"]+)"', s)
        if not m:
            print(f"warning: {path} has no datePublished; skipped", file=sys.stderr)
            continue
        slug = os.path.basename(os.path.dirname(path))
        date = datetime.fromisoformat(m.group(1))
        t = re.search(r'<h1 class="elementor-heading-title[^>]*>(.*?)</h1>', s, re.S)
        title = _text(t.group(1)) if t else _text(re.search(r"<title>(.*?)</title>", s, re.S).group(1)).split(" - ")[0]
        # featured image: the template's featured-image widget, else og:image
        tag = re.search(r'theme-post-featured-image\.default">\s*(<img[^>]*>)', s)
        src = re.search(r'src="\.\./images/([^"]+)"', tag.group(1)) if tag else None
        if src:
            a = re.search(r'alt="([^"]*)"', tag.group(1))
            image, alt = src.group(1), html.unescape(a.group(1)) if a else ""
        else:
            og = re.search(r'og:image" content="[^"]*/images/([^"]+)"', s)
            image, alt = (og.group(1) if og else None), ""
        pid = re.search(r"\bpostid-(\d+)", s) or re.search(r'single-post"[^>]*\bpost-(\d+)', s)
        posts.append(dict(slug=slug, date=date, title=title, image=image, alt=alt or title,
                          excerpt=_excerpt(s), pid=pid.group(1) if pid else ""))
    posts.sort(key=lambda p: (p["date"], p["slug"]), reverse=True)
    return posts


def nice_date(d):
    return f"{d:%B} {d.day}, {d.year}"


# ------------------------------------------------------------- Latest News feed
NEWS_CSS = """<style>
  .llf-news{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:28px;width:100%;max-width:1100px;margin:8px auto 36px;padding:0;box-sizing:border-box;text-align:left}
  .llf-news *{box-sizing:border-box}
  .llf-news-card{display:flex;flex-direction:column;min-width:0;background:#fff;border:1px solid #eee6d6;border-radius:10px;overflow:hidden;box-shadow:0 2px 10px rgba(0,0,0,.05);transition:box-shadow .2s,transform .2s}
  .llf-news-card:hover{box-shadow:0 10px 26px rgba(0,0,0,.10);transform:translateY(-2px)}
  .llf-news-thumb{display:block;aspect-ratio:16/10;overflow:hidden;background:#f3efe7}
  .llf-news-thumb img{display:block;width:100%;height:100%;object-fit:cover;transition:transform .35s}
  .llf-news-card:hover .llf-news-thumb img{transform:scale(1.04)}
  .llf-news-body{display:flex;flex-direction:column;flex:1;padding:20px 22px 22px}
  .llf-news-date{font-family:"Montserrat",sans-serif;font-size:12px;font-weight:600;letter-spacing:.12em;text-transform:uppercase;color:#B8862B;margin:0 0 8px}
  .llf-news-title{font-family:"Mulish",sans-serif;font-size:19px;font-weight:800;line-height:1.3;margin:0 0 10px;color:#2b2b2b}
  .llf-news-title a{color:inherit;text-decoration:none}
  .llf-news-title a:hover,.llf-news-title a:focus{color:#6F1200}
  .llf-news-excerpt{font-family:"Montserrat",sans-serif;font-size:14.5px;line-height:1.6;color:#5f5f5f;margin:0 0 16px}
  .llf-news-more{margin-top:auto;font-family:"Montserrat",sans-serif;font-size:13px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;color:#6F1200;text-decoration:none}
  .llf-news-more:hover,.llf-news-more:focus{color:#B8862B}
  @media (max-width:1024px) and (min-width:641px){.llf-news{grid-template-columns:1fr;gap:20px}.llf-news-card{flex-direction:row}.llf-news-thumb{flex:0 0 38%;aspect-ratio:auto;min-height:190px}.llf-news-body{padding:18px 22px}}
  @media (max-width:640px){.llf-news{grid-template-columns:1fr;gap:22px;margin-bottom:28px}.llf-news-title{font-size:18px}}
</style>"""


def news_block(posts, prefix):
    cards = []
    for p in posts[:LATEST_COUNT]:
        url = f"{prefix}{p['slug']}/"
        title = html.escape(p["title"])
        thumb = ""
        if p["image"]:
            thumb = (f'<a class="llf-news-thumb" href="{url}" tabindex="-1" aria-hidden="true">'
                     f'<img src="{prefix}images/{p["image"]}" alt="{html.escape(p["alt"])}" loading="lazy" decoding="async"></a>')
        cards.append(
            f'<article class="llf-news-card" role="listitem">{thumb}<div class="llf-news-body">'
            f'<time class="llf-news-date" datetime="{p["date"]:%Y-%m-%d}">{nice_date(p["date"])}</time>'
            f'<h3 class="llf-news-title"><a href="{url}">{title}</a></h3>'
            f'<p class="llf-news-excerpt">{html.escape(p["excerpt"])}</p>'
            f'<a class="llf-news-more" href="{url}" aria-label="Read more about {title}">Read More &raquo;</a>'
            f"</div></article>")
    return (f"{START}\n<!-- Generated by scripts/update_blog_feeds.py from the blog posts. Do not edit by hand. -->\n"
            f"{NEWS_CSS}\n<div class=\"llf-news\" role=\"list\">\n" + "\n".join(cards) + f"\n</div>\n{END}")


def update_latest_news(posts, changed):
    for path in glob.glob(os.path.join(ROOT, "**", "*.html"), recursive=True):
        if "/wp-" in path:
            continue
        s = open(path, encoding="utf-8").read()
        if START not in s:
            continue
        depth = os.path.relpath(path, ROOT).count(os.sep)
        prefix = "../" * depth
        new = re.sub(re.escape(START) + r".*?" + re.escape(END), lambda m: news_block(posts, prefix), s, flags=re.S)
        if new != s:
            changed.append(path)
            open(path, "w", encoding="utf-8").write(new)


# --------------------------------------------------------- blog listing pages
def listing_card(p, prefix):
    url = f"{prefix}{p['slug']}/"
    title = html.escape(p["title"])
    pid = f" post-{p['pid']}" if p["pid"] else ""
    thumb_cls = " has-post-thumbnail" if p["image"] else ""
    thumb = ""
    if p["image"]:
        thumb = (f'\t\t\t\t<a class="elementor-post__thumbnail__link" href="{url}" tabindex="-1" >\n'
                 f'\t\t\t<div class="elementor-post__thumbnail"><img loading="lazy" decoding="async" src="{prefix}images/{p["image"]}" '
                 f'class="attachment-medium size-medium" alt="{html.escape(p["alt"])}" /></div>\n\t\t</a>\n')
    return (f'<article class="elementor-post elementor-grid-item{pid} post type-post status-publish format-standard{thumb_cls} hentry category-uncategorized" role="listitem">\n'
            f"{thumb}"
            f'\t\t\t\t<div class="elementor-post__text">\n\t\t\t\t<h3 class="elementor-post__title">\n'
            f'\t\t\t<a href="{url}" >\n\t\t\t\t{title}\t\t\t</a>\n\t\t</h3>\n'
            f'\t\t\t\t<div class="elementor-post__meta-data">\n\t\t\t\t\t<span class="elementor-post-date">\n'
            f'\t\t\t{nice_date(p["date"])}\t\t</span>\n\t\t\t\t<span class="elementor-post-avatar">\n\t\t\tNo Comments\t\t</span>\n\t\t\t\t</div>\n'
            f'\t\t<a class="elementor-post__read-more" href="{url}" aria-label="Read more about {title}" tabindex="-1" >\n'
            f"\t\t\tRead More »\t\t</a>\n\t\t\t\t</div>\n\t\t\t\t</article>\n")


def page_href(target, current):
    """Relative link from blog page `current` to blog page `target` (both 1-based)."""
    if current == 1:
        return "./" if target == 1 else f"{target}/"
    return "../" if target == 1 else f"../{target}/"


def listing_nav(n, total):
    links = []
    for k in range(1, total + 1):
        if k == n:
            links.append(f'<span aria-current="page" class="page-numbers current"><span class="elementor-screen-only">Page</span>{k}</span>')
        else:
            links.append(f'<a class="page-numbers" href="{page_href(k, n)}"><span class="elementor-screen-only">Page</span>{k}</a>')
    nxt = f' data-next-page="{page_href(n + 1, n)}"' if n < total else ""
    return (f'\t\t\t\t<div class="e-load-more-anchor" data-page="{n}" data-max-page="{total}"{nxt}></div>\n'
            f'\t\t\t\t<nav class="elementor-pagination" aria-label="Pagination">\n\t\t\t' + "\n".join(links) + "\t\t</nav>")


def update_listing(posts, changed):
    total = max(1, math.ceil(len(posts) / PER_PAGE))
    blog = os.path.join(ROOT, "blog")
    template = os.path.join(blog, "2", "index.html")
    if not os.path.exists(template):
        template = None
    for n in range(1, total + 1):
        path = os.path.join(blog, "index.html") if n == 1 else os.path.join(blog, str(n), "index.html")
        prefix = "../" if n == 1 else "../../"
        if os.path.exists(path):
            s = open(path, encoding="utf-8").read()
        else:
            if not template:
                sys.exit("blog/2/index.html is needed as a template for new blog pages")
            s = open(template, encoding="utf-8").read()
            s = re.sub(r"\bpaged-\d+ page-paged-\d+", f"paged-{n} page-paged-{n}", s)
            os.makedirs(os.path.dirname(path), exist_ok=True)
        cards = "".join(listing_card(p, prefix) for p in posts[(n - 1) * PER_PAGE: n * PER_PAGE])
        # the card list runs from the posts container to the load-more anchor + page-number nav after it
        pat = re.compile(r'(<div class="elementor-posts-container[^>]*>)(.*?)(</div>\s*)'
                         r'<div class="e-load-more-anchor"[^>]*></div>\s*<nav class="elementor-pagination".*?</nav>', re.S)
        m = pat.search(s)
        if not m:
            sys.exit(f"could not find the posts container in {path}")
        new = s[:m.start()] + m.group(1) + "\n\t\t\t\t" + cards + "\t\t\t\t" + m.group(3).rstrip() + "\n" + listing_nav(n, total) + s[m.end():]
        if new != s:
            changed.append(path)
            open(path, "w", encoding="utf-8").write(new)
    # remove listing pages that are no longer needed
    for d in glob.glob(os.path.join(blog, "*")):
        name = os.path.basename(d)
        if name.isdigit() and int(name) > total and os.path.isdir(d):
            shutil.rmtree(d)
            changed.append(d + "/ (removed)")
    return total


# ------------------------------------------------------------------- sitemap
def update_sitemap(posts, total, changed):
    path = os.path.join(ROOT, "sitemap.xml")
    if not os.path.exists(path):
        return
    s = open(path, encoding="utf-8").read()
    locs = set(re.findall(r"<loc>([^<]+)</loc>", s))
    want = [f"{SITE}/{p['slug']}/" for p in posts] + [f"{SITE}/blog/"] + [f"{SITE}/blog/{k}/" for k in range(2, total + 1)]
    # drop entries whose page no longer exists (a deleted post, or a blog page no longer needed)
    stale = [l for l in locs if l.startswith(SITE + "/")
             and not os.path.exists(os.path.join(ROOT, l[len(SITE) + 1:], "index.html"))]
    missing = [u for u in want if u not in locs]
    if not missing and not stale:
        return
    urls = sorted((locs - set(stale)) | set(missing), key=lambda u: (u != f"{SITE}/", u))
    s = re.sub(r"(<urlset[^>]*>).*(</urlset>)", lambda m: m.group(1) + "\n" + "".join(f"  <url><loc>{u}</loc></url>\n" for u in urls) + m.group(2), s, flags=re.S)
    changed.append(path)
    open(path, "w", encoding="utf-8").write(s)


def main():
    check = "--check" in sys.argv
    if check:  # work on a scratch copy so --check never modifies the site
        import tempfile
        tmp = tempfile.mkdtemp()
        for item in sorted(set(["index.html", "sitemap.xml"] + [p for p in os.listdir(ROOT) if os.path.isdir(os.path.join(ROOT, p))])):
            src = os.path.join(ROOT, item)
            if item.startswith((".", "wp-")) or not os.path.exists(src):
                continue
            if item == "images":
                continue  # not read or written; skip the copy
            (shutil.copytree if os.path.isdir(src) else shutil.copy2)(src, os.path.join(tmp, item))
        globals()["ROOT"] = tmp
    posts = read_posts()
    changed = []
    update_latest_news(posts, changed)
    total = update_listing(posts, changed)
    update_sitemap(posts, total, changed)
    print(f"{len(posts)} blog posts; latest: " + ", ".join(p["slug"] for p in posts[:LATEST_COUNT]))
    print(f"{total} blog listing page(s)")
    for c in changed:
        print(("out of date: " if check else "updated: ") + os.path.relpath(c, ROOT))
    if check and changed:
        sys.exit(1)


if __name__ == "__main__":
    main()
