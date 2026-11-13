# The Lackey Law Firm — static site

A static copy of https://www.thelackeylawfirm.com/, moved off WordPress so it can be hosted on GitHub Pages.

## What's here

| Path | Contents |
|---|---|
| `index.html` | Home page |
| `<slug>/index.html` | Every page and blog post, at the same URL as on WordPress (e.g. `/gary-lackey/`, `/areas-we-serve/madison-al/`) |
| `blog/`, `blog/2/` … | Blog index and its pagination (generated, see below) |
| `404.html` | "Page not found" page |
| `images/` | **Image placeholders** (see below) |
| `wp-content/`, `wp-includes/` | The Elementor/theme CSS, JS and icon fonts the pages need to render as before |
| `sitemap.xml`, `robots.txt` | SEO files (`sitemap.xml` is kept up to date by the blog-feed script) |
| `scripts/update_blog_feeds.py` | Rebuilds the Latest News feed, the blog listing pages and the sitemap from the posts, and keeps every post on the universal layout (see below) |
| `assets/css/blog-post.css` | The universal blog post layout |
| `.github/workflows/update-blog-feeds.yml` | Runs that script automatically on every push to `main` |

Old WordPress URLs that used to 301-redirect (e.g. `/dui-and-traffic/`, `/personal-injury-lawyer-in-madison-al/`) have small redirect pages so existing links keep working.

## Images

Most images from the WordPress site were replaced with a **blank, uniquely named placeholder** in `images/` (e.g. `18wheeler.png`, `breno-assis-r3wawu5fi5q-unsplash.png`). All sizes of one image share one placeholder.

The favicon (`favicon.png`) is real. Other real images added so far are prefixed `u-` (site-wide), `h-` (home page), `l-` (lawyer pages), `a-` (About page), `au-` (auto-accident pages), `p-` (personal-injury pages), `b-` (blog posts) or `un-` (blog featured images). To put a real image back, overwrite the placeholder with the real file **using the same file name**. `images/README.md` lists every placeholder, its size, and the original WordPress file it stands in for.

## Blog posts and the Latest News feed

The blog feeds are **generated, not hand-edited**. `scripts/update_blog_feeds.py` reads every blog post and rebuilds:

- the **Latest News** section on the home page: the 3 newest posts, each with its featured image, date, title, a short excerpt and a Read More link;
- the **blog listing pages** `blog/`, `blog/2/`, `blog/3/` …: 6 posts per page, newest first, using the same cards as Latest News, with page-number links. A new page is created automatically when the posts no longer fit, and a surplus one is removed;
- **`sitemap.xml`**: every post and blog page is listed, and entries for deleted pages are removed.

**It runs automatically.** The GitHub Action in `.github/workflows/update-blog-feeds.yml` runs the script on every push to `main`, commits any changes and asks GitHub Pages to rebuild. You can also run it yourself with `python3 scripts/update_blog_feeds.py` (only Python 3.11+ is needed, no packages). Running it twice changes nothing the second time. `--check` reports anything out of date without changing files.

### Adding a blog post

1. **Copy an existing post folder** at the site root, e.g. `more-than-20-million-recovered-in-2025-for-our-clients/`, and rename the copy to the new post's URL slug (lower case, hyphens, e.g. `what-to-do-after-a-truck-accident/`). The folder name is the post's URL.
2. In the copy's `index.html`, update:
   - **The publish date:** `"datePublished":"2026-11-20T09:00:00+00:00"` in the `application/ld+json` block. This date decides the post's place in every feed (newest first). Also update `"dateModified"` and the `article:published_time` / `article:modified_time` meta tags.
   - **The title:** the `<h1 class="elementor-heading-title …">` inside the post-title widget (this is what the feeds show), plus `<title>`, `og:title` and the schema `"headline"` and `"name"`.
   - **The featured image:** the `<img src="../images/…">` in the `theme-post-featured-image` widget at the top of the post, plus `og:image` and the schema image URLs. Put the image file in `images/`, prefixed `b-` (e.g. `images/b-truck-accident.jpg`), at least 1200px wide.
   - **The excerpt:** `<meta name="description" content="…">`. The feed shows its first ~150 characters, cut at a whole word, so make the first sentence count. If it's missing, the feed uses the post's first paragraph.
   - **The canonical and `og:url` links**, which must point at the new slug, and the post body itself.
3. **Keep these as they are**, or the post won't be detected: the `data-elementor-type="single-post"` template wrapper and `"@type":"Article"` in the schema.
4. **Push to `main`.** The Action updates the home page, the blog pages and the sitemap within a minute or two.

**To remove a post**, delete its folder and push. The feeds and sitemap drop it automatically.

### The universal post layout

Every post uses the same layout, from `assets/css/blog-post.css`:

- **One centred column**, 760px wide, for the date, title and text, with the same margins in every post.
- **Header:** the hero image is a wide banner (21:9, up to 1120px) that extends past the text column on desktop and runs edge to edge on phones, so it reads differently from the photos in the text. Under it come a **Back to Blog** button (added by the script, so readers can get back to the blog without scrolling to the footer), the date in gold capitals and the title (H1) with a thin rule under it.
- **Heading hierarchy:** the title is the only H1. Sections are H2 (large, dark), subsections are H3 (smaller, maroon) and anything below that is H4. Levels are never skipped.
- **Images in the text:** full column width, rounded, with the same spacing above and below. Images narrower than 600px, and badges or seals, show at their own size, centred, so they aren't stretched and blurred.
- **Spacing:** 22px between paragraphs, 48px above each H2, about 33px above each H3. Tables, lists and links are styled the same everywhere; links in the text are maroon with no underline (gold on hover).

The script enforces the parts that live in each post's HTML, so a copied or newly added post is brought into line automatically when it runs: it links the stylesheet, renumbers body headings to H2 > H3 > H4, removes empty paragraphs left by the old editor, and marks small images. When writing a post you only need to get the order of headings right: use H2 for main sections and H3 for points within a section.

### Putting the Latest News feed on another page

Add these two lines where the feed should appear. The script fills in the 3 newest posts, with links correct for that page's folder depth:

```html
<!-- latest-news:start -->
<!-- latest-news:end -->
```

Never edit anything between the markers, or the post cards on the blog pages, by hand: the next run overwrites it.

## Hosting on GitHub Pages

1. Settings → Pages → Deploy from branch → pick the branch and `/ (root)`.
2. Set the custom domain to `www.thelackeylawfirm.com` (this creates a `CNAME` file) and point DNS at GitHub Pages.

Links between pages are relative, so the site also works when previewed at `https://<user>.github.io/lackeylaw/` (only the 404 page assumes it is served from the domain root).

## Third-party services still in use

These were embedded on the WordPress site and keep working unchanged: the JotForm consultation form, Google Maps embeds, Google Fonts, the Trustindex Google-reviews widget, the Collect.chat chat widget, and Google Analytics (`UA-147723908-1`, a Universal Analytics ID that Google no longer collects data for — swap in a GA4 ID if you want analytics).
