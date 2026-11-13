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
  4. Every blog post: links the shared layout stylesheet (assets/css/blog-post.css) and has
     its body headings renumbered to H2 > H3 > H4 with no skipped levels; empty
     paragraphs and stray line breaks left by the old editor are removed (title lines
     typed as "Title<br>text" become real headings, typed lists become lists, and one-item lists used as subsection titles become subheadings), and in-article images narrower than
     600px are marked to show at their own size rather than stretched (and blurred), a
     "Back to Blog" link sits under the hero, and the schema breadcrumb is Home > Blog > Post.

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


# ------------------------------------------------- universal post layout
POST_CSS_LINK = '<link rel="stylesheet" id="llf-blog-post-css" href="../assets/css/blog-post.css?v=10" media="all" />'


def normalize_headings(s):
    """Make headings in the post body follow H2 > H3 > H4 without skipped levels.

    The post title is the page's only H1. Body headings keep their relative order of
    importance but are renumbered: a heading one step below the previous section heading
    becomes the next level down (H2 followed by H5 becomes H2 then H3), never deeper than H4.
    """
    start = s.find('data-widget_type="theme-post-content.default"')
    if start < 0:
        return s
    end = s.find("<footer", start)
    end = len(s) if end < 0 else end
    body = s[start:end]
    stack, out, last, current = [], [], 0, None
    for m in re.finditer(r"<(/?)h([1-6])\b", body):
        out.append(body[last:m.start()])
        closing, level = m.group(1), int(m.group(2))
        if not closing:
            while stack and stack[-1][0] >= level:
                stack.pop()
            new = min(4, stack[-1][1] + 1) if stack else 2
            stack.append((level, new))
            current = new
            out.append(f"<h{new}")
        else:
            out.append(f"</h{current or level}")
        last = m.end()
    out.append(body[last:])
    body = "".join(out)
    # drop empty paragraphs/divs left by the old editor; they add uneven gaps
    body = re.sub(r"<p\b[^>]*>(?:\s|\xa0|&nbsp;|<br\s*/?>)*</p>\s*", "", body)
    body = re.sub(r"<div>(?:\s|\xa0|&nbsp;)*</div>\s*", "", body)
    # a bare <div> holding only text is really a paragraph
    body = re.sub(r"<div>((?:(?!<(?:div|p|ul|ol|h[1-6]|table|figure)\b).)*?)</div>", r"<p>\1</p>", body, flags=re.S)
    return s[:start] + body + s[end:]



def image_size(path):
    """(width, height) of a PNG or JPEG using only the standard library; None if unknown."""
    import struct
    try:
        with open(path, "rb") as f:
            head = f.read(26)
            if head[:8] == b"\x89PNG\r\n\x1a\n":
                return struct.unpack(">II", head[16:24])
            if head[:2] == b"\xff\xd8":
                f.seek(2)
                while True:
                    marker = f.read(2)
                    if len(marker) < 2 or marker[0] != 0xFF:
                        return None
                    if marker[1] in (0xD8, 0x01) or 0xD0 <= marker[1] <= 0xD7:
                        continue
                    length = struct.unpack(">H", f.read(2))[0]
                    if marker[1] in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                        h, w = struct.unpack(">xHH", f.read(5))
                        return w, h
                    f.seek(length - 2, 1)
    except OSError:
        return None
    return None


SMALL_IMAGE = 600  # in-article images narrower than this show at their own size instead of being stretched


def mark_small_images(s):
    start = s.find('data-widget_type="theme-post-content.default"')
    if start < 0:
        return s
    end = s.find("<footer", start)
    end = len(s) if end < 0 else end

    def fix(m):
        tag = m.group(0)
        src = re.search(r'src="\.\./images/([^"?]+)', tag)
        if not src or "llf-img-native" in tag:
            return tag
        size = image_size(os.path.join(ROOT, "images", src.group(1)))
        if not size or size[0] >= SMALL_IMAGE:
            return tag
        if 'class="' in tag:
            return tag.replace('class="', 'class="llf-img-native ', 1)
        return tag.replace("<img", '<img class="llf-img-native"', 1)

    return s[:start] + re.sub(r"<img\b[^>]*>", fix, s[start:end]) + s[end:]



BC_START, BC_END = "<!-- breadcrumbs:start -->", "<!-- breadcrumbs:end -->"


def breadcrumbs(s, title):
    """A "Back to Blog" link under the hero, plus a Home > Blog > Post trail in the schema data."""
    trail = (f'{BC_START}<nav class="llf-breadcrumbs" aria-label="Back to the blog">'
             f'<a class="llf-back-btn" href="../blog/">Back to Blog</a></nav>{BC_END}')
    if BC_START in s:
        s = re.sub(re.escape(BC_START) + r".*?" + re.escape(BC_END), lambda m: trail, s, count=1, flags=re.S)
    else:  # place it just before the date line, i.e. right under the hero image
        anchor = '<div class="elementor-element elementor-element-7adee78 '
        if anchor in s:
            s = s.replace(anchor, trail + "\n\t\t\t\t" + anchor, 1)
    # schema: Home > Blog > Post
    def fix(m):
        items = m.group(2)
        if '"name":"Blog"' in items:
            return m.group(0)
        post = re.search(r'\{"@type":"ListItem","position":2,("name":"(?:[^"\\]|\\.)*")\}', items)
        if not post:
            return m.group(0)
        new = ('{"@type":"ListItem","position":1,"name":"Home","item":"https:\\/\\/www.thelackeylawfirm.com\\/"},'
               '{"@type":"ListItem","position":2,"name":"Blog","item":"https:\\/\\/www.thelackeylawfirm.com\\/blog\\/"},'
               '{"@type":"ListItem","position":3,' + post.group(1) + "}")
        return m.group(1) + new + "]"
    return re.sub(r'("@type":"BreadcrumbList".*?"itemListElement":\[)(.*?)\]', fix, s, count=1, flags=re.S)



# ------------------------------------------- tidy paragraphs left by the old editor
from html.parser import HTMLParser

_INLINE_VOID = {"br", "img", "wbr"}
_SMALL_WORDS = {"a", "an", "the", "and", "or", "of", "in", "on", "to", "for", "with", "at", "by",
                "from", "after", "about", "vs", "is", "are", "be", "your", "you", "can", "how", "what"}


class _Splitter(HTMLParser):
    """Split inline HTML at <br> tags, keeping inline wrappers (span, b, a...) balanced in each piece."""

    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.parts, self.cur, self.stack = [], [], []

    def _flush(self):
        self.cur.extend(f"</{t}>" for t, _ in reversed(self.stack))
        self.parts.append("".join(self.cur))
        self.cur = [raw for _, raw in self.stack]

    def handle_starttag(self, tag, attrs):
        if tag == "br":
            self._flush()
            return
        raw = self.get_starttag_text()
        self.cur.append(raw)
        if tag not in _INLINE_VOID:
            self.stack.append((tag, raw))

    def handle_startendtag(self, tag, attrs):
        if tag == "br":
            self._flush()
        else:
            self.cur.append(self.get_starttag_text())

    def handle_endtag(self, tag):
        self.cur.append(f"</{tag}>")
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                del self.stack[i]
                break

    def handle_data(self, d): self.cur.append(d)
    def handle_entityref(self, n): self.cur.append(f"&{n};")
    def handle_charref(self, n): self.cur.append(f"&#{n};")


def _split_br(inner):
    sp = _Splitter()
    sp.feed(inner)
    sp.close()
    sp.parts.append("".join(sp.cur))
    return sp.parts


def _plain(fragment):
    t = html.unescape(re.sub(r"<[^>]+>", " ", fragment)).replace("\xa0", " ")
    return re.sub(r"\s+", " ", t).strip()


def _empty_wrappers(fragment):
    """Drop inline wrappers that hold no text (e.g. <span></span> left after splitting)."""
    prev = None
    while prev != fragment:
        prev = fragment
        fragment = re.sub(r"<(span|b|strong|em|i)\b[^>]*>(?:\s|&nbsp;|\xa0)*</\1>", "", fragment)
    return fragment.strip()


def _strip_trailing_br(fragment):
    """Remove <br> tags that have no text after them, then any wrapper left empty."""
    while True:
        brs = list(re.finditer(r"<br\s*/?>", fragment))
        if not brs or _plain(fragment[brs[-1].end():]):
            break
        fragment = fragment[:brs[-1].start()] + fragment[brs[-1].end():]
    return _empty_wrappers(fragment)


def _looks_like_heading(text):
    if not (3 <= len(text) <= 90) or text.endswith((".", ":", ";", ",")) or text.startswith(("✓", "•", "-")):
        return False
    if text.endswith("?"):
        return True
    words = [w for w in re.findall(r"[A-Za-z][\w'’-]*", text)]
    big = [w for w in words if w.lower() not in _SMALL_WORDS]
    return len(words) >= 2 and big and sum(w[0].isupper() for w in big) / len(big) >= 0.75


def _rewrite_p(attrs, inner):
    segs = [_empty_wrappers(x) for x in _split_br(inner)]
    texts = [_plain(x) for x in segs]
    # trim breaks at the start/end; split into paragraphs at double breaks
    groups, cur = [], []
    for seg, t in zip(segs, texts):
        if t:
            cur.append(seg)
        elif cur:
            groups.append(cur)
            cur = []
    if cur:
        groups.append(cur)
    if not groups:
        return ""
    out = []
    first = groups[0]
    if len(first) > 1 and _looks_like_heading(_plain(first[0])):
        head = re.sub(r"</?(b|strong)\b[^>]*>", "", first[0])
        out.append(f"<h3>{_empty_wrappers(head)}</h3>")
        groups[0] = first[1:]
    for g in groups:
        short = [i for i, x in enumerate(g) if len(_plain(x)) <= 70]
        run = 0
        while run < len(g) and run in short:
            run += 1
        if run >= 3:  # three or more short lines in a row: a list typed with line breaks
            out.append("<ul>" + "".join(f"<li>{x}</li>" for x in g[:run]) + "</ul>")
            g = g[run:]
        if g:
            out.append(f"<p{attrs}>" + "<br>".join(g) + "</p>")
    return "\n".join(out)


def tidy_paragraphs(s):
    start = s.find('data-widget_type="theme-post-content.default"')
    if start < 0:
        return s
    end = s.find("<footer", start)
    end = len(s) if end < 0 else end
    body = s[start:end]

    def p_fix(m):
        before = body[:m.start()]
        if before.rfind("<li") > before.rfind("</li>"):  # paragraph inside a list item: leave its layout alone
            if "<br" not in m.group(2):
                return m.group(0)
            inner = _strip_trailing_br(m.group(2))
            return f"<p{m.group(1)}>{inner}</p>" if inner != m.group(2).strip() else m.group(0)
        if "<br" not in m.group(2):
            return m.group(0)
        return _rewrite_p(m.group(1), m.group(2))

    body = re.sub(r"<p(\b[^>]*)>(.*?)</p>", p_fix, body, flags=re.S)
    # list items: drop line breaks at the very end
    def li_fix(m):
        inner = m.group(2)
        if "<br" not in inner or "<li" in inner:
            return m.group(0)
        trimmed = _strip_trailing_br(inner)
        return f"<li{m.group(1)}>{trimmed}</li>" if trimmed != inner.strip() else m.group(0)
    body = re.sub(r"<li(\b[^>]*)>(.*?)</li>", li_fix, body, flags=re.S)
    # a list with a single short title-like item between paragraphs is really a subheading
    # ("• Neck and Soft Tissue Injuries", "2. Speeding and Aggressive Driving", an FAQ question)
    def single_item(m):
        kind, attrs, inner = m.group(1), m.group(2), m.group(3)
        text = _plain(inner)
        numbered_title = kind == "ol" and 2 <= len(text) <= 60 and not text.endswith((".", ":", ";", ","))
        if not (_looks_like_heading(text) or numbered_title):
            return m.group(0)
        head = _empty_wrappers(re.sub(r"</?(b|strong|p)\b[^>]*>", "", inner))
        if kind == "ol":
            num = re.search(r'start="(\d+)"', attrs)
            head = f"{num.group(1) if num else 1}. {head}"
        return f"<h3>{head}</h3>"
    body = re.sub(r"<(ul|ol)\b([^>]*)>\s*<li\b[^>]*>((?:(?!</?(?:li|ul|ol)\b).)*?)</li>\s*</\1>", single_item, body, flags=re.S)
    # empty headings (only spaces / line breaks) just add blank space
    body = re.sub(r"<(h[1-6])\b[^>]*>(?:\s|&nbsp;|\xa0|<br\s*/?>|<span[^>]*>|</span>|<b>|</b>|<strong>|</strong>)*</\1>", "", body)
    # runs of "$… Settlement" / "Confidential Settlement …" paragraphs: a list of results
    def results(m):
        items = re.findall(r"<p\b[^>]*>(.*?)</p>", m.group(0), re.S)
        return "<ul>" + "".join(f"<li>{x}</li>" for x in items) + "</ul>"
    item = r"<p\b[^>]*>\s*(?:\$[\d,]+(?:\.\d\d)?|Confidential)\s+(?:Settlement|Verdict|Recovery)\b[^<]*(?:<a\b[^>]*>[^<]*</a>[^<]*)*</p>\s*"
    body = re.sub(r"(?:" + item + r"){3,}", results, body)
    return s[:start] + body + s[end:]


def update_posts(changed):
    """Give every blog post the shared layout stylesheet and a clean heading hierarchy."""
    for p in read_posts():
        path = os.path.join(ROOT, p["slug"], "index.html")
        s = open(path, encoding="utf-8").read()
        new = s
        if 'id="llf-blog-post-css"' not in new:
            new = new.replace("</head>", POST_CSS_LINK + "\n</head>", 1)
        new = breadcrumbs(mark_small_images(normalize_headings(tidy_paragraphs(new))), p["title"])
        if new != s:
            changed.append(path)
            open(path, "w", encoding="utf-8").write(new)


# ------------------------------------------------------------- Latest News feed
NEWS_CSS = """<style>
  .llf-news{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:28px;width:100%;max-width:1100px;margin:0 auto;padding:0;box-sizing:border-box;text-align:left}
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
  @media (max-width:640px){.llf-news{grid-template-columns:1fr;gap:20px}.llf-news-title{font-size:18px}}
</style>"""


LISTING_CSS = """<style>
  /* blog listing pages: same cards as Latest News, 6 per page */
  .elementor-posts-container:has(> .llf-news){display:block !important}
  .llf-news--listing{max-width:1180px;margin:8px auto 0}
  .elementor-pagination{display:flex;justify-content:center;flex-wrap:wrap;gap:8px;margin-top:40px !important;font-family:"Montserrat",sans-serif}
  .elementor-pagination .page-numbers{display:inline-flex;align-items:center;justify-content:center;min-width:40px;height:40px;padding:0 12px;border:1px solid #eee6d6;border-radius:8px;background:#fff;color:#6F1200;font-weight:700;font-size:14px;text-decoration:none;margin:0 !important}
  .elementor-pagination a.page-numbers:hover,.elementor-pagination a.page-numbers:focus{border-color:#E9A825;color:#B8862B}
  .elementor-pagination .page-numbers.current{background:#E9A825;border-color:#E9A825;color:#fff}
</style>"""


def news_card(p, prefix, heading="h3"):
    """One post card. Used by both the Latest News feed and the blog listing pages."""
    url = f"{prefix}{p['slug']}/"
    title = html.escape(p["title"])
    thumb = ""
    if p["image"]:
        thumb = (f'<a class="llf-news-thumb" href="{url}" tabindex="-1" aria-hidden="true">'
                 f'<img src="{prefix}images/{p["image"]}" alt="{html.escape(p["alt"])}" loading="lazy" decoding="async"></a>')
    return (f'<article class="llf-news-card" role="listitem">{thumb}<div class="llf-news-body">'
            f'<time class="llf-news-date" datetime="{p["date"]:%Y-%m-%d}">{nice_date(p["date"])}</time>'
            f'<{heading} class="llf-news-title"><a href="{url}">{title}</a></{heading}>'
            f'<p class="llf-news-excerpt">{html.escape(p["excerpt"])}</p>'
            f'<a class="llf-news-more" href="{url}" aria-label="Read more about {title}">Read More &raquo;</a>'
            f"</div></article>")


def news_block(posts, prefix):
    cards = [news_card(p, prefix) for p in posts[:LATEST_COUNT]]
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
        cards = ("<!-- Generated by scripts/update_blog_feeds.py from the blog posts. Do not edit by hand. -->\n"
                 + NEWS_CSS + "\n" + LISTING_CSS + '\n<div class="llf-news llf-news--listing" role="list">\n'
                 + "\n".join(news_card(p, prefix, "h2") for p in posts[(n - 1) * PER_PAGE: n * PER_PAGE]) + "\n</div>\n")
        # the card list runs from the posts container to the load-more anchor + page-number nav after it
        pat = re.compile(r'(<div class="elementor-posts-container[^>]*>)(.*?)(</div>\s*)'
                         r'<div class="e-load-more-anchor"[^>]*></div>\s*<nav class="elementor-pagination".*?</nav>', re.S)
        m = pat.search(s)
        if not m:
            sys.exit(f"could not find the posts container in {path}")
        new = s[:m.start()] + m.group(1).replace(' role="list"', "") + "\n\t\t\t\t" + cards + "\t\t\t\t" + m.group(3).rstrip() + "\n" + listing_nav(n, total) + s[m.end():]
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
    changed = []
    update_posts(changed)
    posts = read_posts()
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
