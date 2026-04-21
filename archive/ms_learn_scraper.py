"""
ms_learn_scraper.py — MCNA Tenant Intel
Scrapes documentation from learn.microsoft.com using Playwright (headless Chromium).

Usage:
    python ms_learn_scraper.py <url>
    python ms_learn_scraper.py <url> --output reports/some-doc.md
    python ms_learn_scraper.py --search "conditional access policy" --max 10

Output is clean Markdown extracted from the article body. Tables, code blocks,
and heading hierarchy are preserved. Nav chrome, ads, and feedback widgets are stripped.

Writes output to stdout by default; use --output to save to a file.
"""

import argparse
import asyncio
import datetime
import pathlib
import re
import sys
import urllib.parse

from playwright.async_api import async_playwright, Error as PlaywrightError


BASE_URL = "https://learn.microsoft.com"
SEARCH_URL = "https://learn.microsoft.com/en-us/search/"

STRIP_SELECTORS = [
    "nav",
    "header",
    "footer",
    ".breadcrumb",
    ".feedback-section",
    ".action-container",
    ".is-hidden-print",
    "#side-doc-outline",
    ".sidebar",
    "#right-column",
    ".contributors",
    ".page-metadata",
    ".alert-info.is-flex",   # "In this article" sidebar
    "button",
    "[data-bi-name='feedback']",
]


async def fetch_article(url: str, browser) -> dict:
    """
    Fetch a single learn.microsoft.com article and return:
      {
        "url": str,
        "title": str,
        "content_md": str,   # clean Markdown
        "fetched_at": str,   # ISO timestamp
      }
    Raises RuntimeError on HTTP error or content not found.
    """
    page = await browser.new_page()
    try:
        response = await page.goto(url, wait_until="domcontentloaded", timeout=45000)
        if response.status >= 400:
            raise RuntimeError(f"HTTP {response.status} fetching {url}")

        # Wait for article content to load — div.content is the article body on learn.microsoft.com
        await page.wait_for_selector("div.content", timeout=20000)

        # Strip nav chrome before extraction
        for sel in STRIP_SELECTORS:
            try:
                elements = await page.query_selector_all(sel)
                for el in elements:
                    await page.evaluate("el => el.remove()", el)
            except PlaywrightError:
                pass

        title = await page.title()
        # Clean up the title — learn.microsoft.com appends " | Microsoft Learn"
        title = re.sub(r"\s*\|\s*Microsoft Learn$", "", title).strip()

        # Extract article HTML and convert to Markdown via JS.
        # learn.microsoft.com uses div.content for the article body; pick the largest one
        # to avoid matching the small decorative content divs.
        content_md = await page.evaluate(
            """() => {
            const candidates = Array.from(document.querySelectorAll('div.content'));
            const article = candidates.length
                ? candidates.reduce((a, b) => a.textContent.length >= b.textContent.length ? a : b)
                : (document.querySelector('main') || document.body);

            if (!article) return '';

            // Walk the DOM and emit Markdown-ish text
            function nodeToMd(node) {
                if (node.nodeType === Node.TEXT_NODE) {
                    return node.textContent;
                }
                if (node.nodeType !== Node.ELEMENT_NODE) return '';

                const tag = node.tagName.toLowerCase();
                const children = () =>
                    Array.from(node.childNodes).map(n => nodeToMd(n)).join('');

                if (tag === 'script' || tag === 'style' || tag === 'noscript') return '';
                if (['h1','h2','h3','h4','h5','h6'].includes(tag)) {
                    const level = parseInt(tag[1]);
                    return '\\n\\n' + '#'.repeat(level) + ' ' + children().trim() + '\\n';
                }
                if (tag === 'p') return '\\n\\n' + children().trim() + '\\n';
                if (tag === 'br') return '\\n';
                if (tag === 'strong' || tag === 'b') return '**' + children() + '**';
                if (tag === 'em' || tag === 'i') return '*' + children() + '*';
                if (tag === 'code') {
                    const text = node.textContent;
                    if (text.includes('\\n')) return '\\n```\\n' + text + '\\n```\\n';
                    return '`' + text + '`';
                }
                if (tag === 'pre') {
                    const code = node.querySelector('code');
                    const lang = code
                        ? (code.className.match(/language-(\\w+)/) || ['',''])[1]
                        : '';
                    const text = code ? code.textContent : node.textContent;
                    return '\\n\\n```' + lang + '\\n' + text.trim() + '\\n```\\n';
                }
                if (tag === 'a') {
                    const href = node.getAttribute('href') || '';
                    const text = children().trim();
                    if (!text) return '';
                    if (href.startsWith('/')) return '[' + text + '](https://learn.microsoft.com' + href + ')';
                    return '[' + text + '](' + href + ')';
                }
                if (tag === 'ul') return '\\n' + children() + '\\n';
                if (tag === 'ol') {
                    const items = Array.from(node.querySelectorAll(':scope > li'));
                    return '\\n' + items.map((li, i) =>
                        '\\n' + (i + 1) + '. ' + Array.from(li.childNodes).map(n => nodeToMd(n)).join('').trim()
                    ).join('') + '\\n';
                }
                if (tag === 'li') return '\\n- ' + children().trim();
                if (tag === 'table') {
                    // Basic table — header row only gets the separator
                    const rows = Array.from(node.querySelectorAll('tr'));
                    if (!rows.length) return '';
                    const md_rows = rows.map((row, idx) => {
                        const cells = Array.from(row.querySelectorAll('th,td'))
                            .map(c => c.textContent.replace(/\\|/g,'\\\\|').replace(/\\n/g,' ').trim());
                        const line = '| ' + cells.join(' | ') + ' |';
                        if (idx === 0) {
                            const sep = '| ' + cells.map(() => '---').join(' | ') + ' |';
                            return line + '\\n' + sep;
                        }
                        return line;
                    });
                    return '\\n\\n' + md_rows.join('\\n') + '\\n';
                }
                if (tag === 'blockquote') return '\\n\\n> ' + children().trim().replace(/\\n/g,'\\n> ') + '\\n';
                if (tag === 'hr') return '\\n\\n---\\n';
                return children();
            }

            return nodeToMd(article);
        }"""
        )

        # Clean up whitespace — collapse 3+ blank lines to 2
        content_md = re.sub(r"\n{3,}", "\n\n", content_md).strip()

        return {
            "url": url,
            "title": title,
            "content_md": content_md,
            "fetched_at": datetime.datetime.utcnow().isoformat() + "Z",
        }
    finally:
        await page.close()


async def search_ms_learn(query: str, max_results: int, browser) -> list[dict]:
    """
    Search learn.microsoft.com and return a list of result dicts:
      [{"title": str, "url": str, "summary": str}, ...]
    """
    page = await browser.new_page()
    try:
        search_url = f"{SEARCH_URL}?terms={urllib.parse.quote_plus(query)}&locale=en-us"
        await page.goto(search_url, wait_until="domcontentloaded", timeout=30000)

        # Wait for search results
        await page.wait_for_selector(
            "ul.results-list li, .search-result, [data-bi-name='result']",
            timeout=15000,
        )

        results = await page.evaluate(
            f"""() => {{
            const items = Array.from(document.querySelectorAll(
                'ul.results-list li, .search-result, [data-bi-name="result"]'
            )).slice(0, {max_results});

            return items.map(item => {{
                const a = item.querySelector('a[href]');
                const summary = item.querySelector('.result-summary, p, .summary');
                return {{
                    title: a ? a.textContent.trim() : '',
                    url: a ? a.href : '',
                    summary: summary ? summary.textContent.trim() : '',
                }};
            }}).filter(r => r.url.includes('learn.microsoft.com'));
        }}"""
        )
        return results
    finally:
        await page.close()


def format_article_output(article: dict) -> str:
    lines = [
        f"# {article['title']}",
        f"",
        f"**Source:** {article['url']}  ",
        f"**Fetched:** {article['fetched_at']}",
        f"",
        "---",
        "",
        article["content_md"],
    ]
    return "\n".join(lines)


async def main():
    parser = argparse.ArgumentParser(
        description="Scrape learn.microsoft.com documentation."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("url", nargs="?", help="Direct URL to fetch")
    group.add_argument("--search", metavar="QUERY", help="Search query")

    parser.add_argument(
        "--output",
        metavar="PATH",
        help="Write output to file instead of stdout",
    )
    parser.add_argument(
        "--max",
        type=int,
        default=10,
        metavar="N",
        help="Max search results to return (default: 10)",
    )
    parser.add_argument(
        "--fetch-all",
        action="store_true",
        help="With --search, fetch and return full content of each result",
    )

    args = parser.parse_args()

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        try:
            if args.url:
                article = await fetch_article(args.url, browser)
                output = format_article_output(article)

            elif args.search:
                results = await search_ms_learn(args.search, args.max, browser)
                if not results:
                    print(f"No results for: {args.search}", file=sys.stderr)
                    sys.exit(1)

                if args.fetch_all:
                    parts = []
                    for r in results:
                        try:
                            article = await fetch_article(r["url"], browser)
                            parts.append(format_article_output(article))
                        except Exception as e:
                            parts.append(f"# {r['title']}\n\nFetch failed: {e}\n")
                    output = "\n\n---\n\n".join(parts)
                else:
                    lines = [f"# Search results: {args.search}\n"]
                    for i, r in enumerate(results, 1):
                        lines.append(f"{i}. [{r['title']}]({r['url']})")
                        if r["summary"]:
                            lines.append(f"   {r['summary']}")
                        lines.append("")
                    output = "\n".join(lines)

        finally:
            await browser.close()

    if args.output:
        out_path = pathlib.Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(output, encoding="utf-8")
        print(f"Written to {out_path}", file=sys.stderr)
    else:
        print(output)


if __name__ == "__main__":
    asyncio.run(main())
