# Microsoft Learn Scraper Skill Design

## Goal

Create a reusable Codex skill that turns the existing `ms_learn_scraper.py`
behavior into a globally discoverable tool for searching and extracting
Markdown from `learn.microsoft.com`.

## Scope

The skill is general-purpose, not MCNA-specific. It should trigger when Codex
needs to:

- fetch a single Microsoft Learn article from a direct URL
- search Microsoft Learn for a query
- fetch full content for multiple search results
- save scraped Markdown to a caller-specified output path

The skill should not expand into general web scraping, summarization, or
non-Microsoft documentation research.

## Architecture

The skill uses a bundled Python script as the execution engine. `SKILL.md`
stays short and instructs Codex to prefer the bundled script over rewriting
Playwright scraping logic inline. The Python script keeps the current behavior:
headless Chromium via Playwright, DOM cleanup for Learn chrome, article body
selection, Markdown conversion, Learn search support, and optional file output.

The skill lives under `C:\Users\dlafferty.MCNA\.codex\skills` so it can be
auto-discovered anywhere in Codex. The workspace retains only the design and
planning artifacts for traceability.

## Files

- `SKILL.md`
  Triggering description plus usage workflow and limits.
- `scripts/ms_learn_scraper.py`
  Reusable executable adapted from the current project script.
- `agents/openai.yaml`
  UI metadata for skill discovery and invocation.

## Behavior

### Direct fetch

Given a `learn.microsoft.com` article URL, the script should return Markdown
with:

- title
- source URL
- fetch timestamp
- cleaned article body

### Search mode

Given a query, the script should return a numbered Markdown list of matching
Learn pages with titles, URLs, and summaries.

### Search plus fetch-all

Given a query and `--fetch-all`, the script should fetch each result and emit
the full formatted article blocks separated by horizontal rules.

## Non-Goals

- scraping arbitrary sites
- generating summaries or interpretations
- storing MCNA-specific defaults in the skill
- depending on project-local paths

## Validation

Validation should cover:

1. structural validation with `quick_validate.py`
2. a direct Learn article fetch
3. a Learn search query

If live network access or Playwright prerequisites block runtime validation,
that should be called out explicitly rather than hidden.
