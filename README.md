# The Lackey Law Firm — static site

A static copy of https://www.thelackeylawfirm.com/, moved off WordPress so it can be hosted on GitHub Pages.

## What's here

| Path | Contents |
|---|---|
| `index.html` | Home page |
| `<slug>/index.html` | Every page and blog post, at the same URL as on WordPress (e.g. `/gary-lackey/`, `/areas-we-serve/madison-al/`) |
| `blog/`, `blog/2/` … `blog/5/` | Blog index and its pagination |
| `404.html` | "Page not found" page |
| `images/` | **Image placeholders** (see below) |
| `wp-content/`, `wp-includes/` | The Elementor/theme CSS, JS and icon fonts the pages need to render as before |
| `sitemap.xml`, `robots.txt` | SEO files |

Old WordPress URLs that used to 301-redirect (e.g. `/dui-and-traffic/`, `/personal-injury-lawyer-in-madison-al/`) have small redirect pages so existing links keep working.

## Images

Most images from the WordPress site were replaced with a **blank, uniquely named placeholder** in `images/` (e.g. `18wheeler.png`, `auto-accident.png`). All sizes of one image share one placeholder.

Real images added so far are prefixed `u-` (site-wide), `h-` (home page), `l-` (lawyer pages), `a-` (About page), `au-` (auto-accident pages), `p-` (personal-injury pages), `b-` (blog posts) or `un-` (blog featured images). To put a real image back, overwrite the placeholder with the real file **using the same file name**. `images/README.md` lists every placeholder, its size, and the original WordPress file it stands in for.

## Hosting on GitHub Pages

1. Settings → Pages → Deploy from branch → pick the branch and `/ (root)`.
2. Set the custom domain to `www.thelackeylawfirm.com` (this creates a `CNAME` file) and point DNS at GitHub Pages.

Links between pages are relative, so the site also works when previewed at `https://<user>.github.io/lackeylaw/` (only the 404 page assumes it is served from the domain root).

## Third-party services still in use

These were embedded on the WordPress site and keep working unchanged: the JotForm consultation form, Google Maps embeds, Google Fonts, the Trustindex Google-reviews widget, the Collect.chat chat widget, and Google Analytics (`UA-147723908-1`, a Universal Analytics ID that Google no longer collects data for — swap in a GA4 ID if you want analytics).
