# Microsoft Learn Scraper Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a reusable global Codex skill that exposes Microsoft Learn search and article scraping through a bundled Python script.

**Architecture:** Keep the scraper logic in a bundled script and keep the skill instructions thin. Create the skill in the global Codex skills directory, then validate both the skill metadata and the scraper runtime behavior.

**Tech Stack:** Markdown, Python, Playwright, Codex skill metadata

---

### Task 1: Write the design artifacts

**Files:**
- Create: `docs/superpowers/specs/2026-04-21-microsoft-learn-scraper-skill-design.md`
- Create: `docs/superpowers/plans/2026-04-21-microsoft-learn-scraper-skill.md`

- [ ] **Step 1: Confirm the approved skill shape**

Review the approved design:

```text
Create a general-purpose global skill under C:\Users\dlafferty.MCNA\.codex\skills
that wraps the existing Microsoft Learn scraper behavior without adding extra scope.
```

- [ ] **Step 2: Write the spec**

Include goal, scope, architecture, files, behavior, non-goals, and validation:

```text
Document that the skill handles direct fetch, search, and search + fetch-all,
using a bundled Playwright-backed Python script.
```

- [ ] **Step 3: Write the implementation plan**

Keep the plan focused on initialization, population, validation, and logging:

```text
Document the exact skill files, validation commands, and artifact logging.
```

### Task 2: Scaffold the global skill

**Files:**
- Create: `C:\Users\dlafferty.MCNA\.codex\skills\microsoft-learn-scraper\SKILL.md`
- Create: `C:\Users\dlafferty.MCNA\.codex\skills\microsoft-learn-scraper\scripts\ms_learn_scraper.py`
- Create: `C:\Users\dlafferty.MCNA\.codex\skills\microsoft-learn-scraper\agents\openai.yaml`

- [ ] **Step 1: Initialize the skill folder**

Run:

```powershell
python "C:\Users\dlafferty.MCNA\.codex\skills\.system\skill-creator\scripts\init_skill.py" microsoft-learn-scraper --path "C:\Users\dlafferty.MCNA\.codex\skills" --resources scripts --interface display_name="Microsoft Learn Scraper" --interface short_description="Search and scrape Microsoft Learn docs" --interface default_prompt="Use $microsoft-learn-scraper to search Microsoft Learn or fetch a Learn article as Markdown."
```

Expected:

```text
The skill directory is created with SKILL.md, agents/openai.yaml, and scripts/.
```

- [ ] **Step 2: Replace the generated script with the reusable scraper**

Copy the logic from the project script into:

```text
C:\Users\dlafferty.MCNA\.codex\skills\microsoft-learn-scraper\scripts\ms_learn_scraper.py
```

- [ ] **Step 3: Replace the generated SKILL.md**

Write frontmatter and usage guidance that tells Codex when to use the skill and
to prefer the bundled script over ad hoc scraping logic:

```markdown
---
name: microsoft-learn-scraper
description: Search and scrape Microsoft Learn documentation into Markdown. Use when Codex needs to fetch a learn.microsoft.com article, search Microsoft Learn for a topic, or extract full Learn article content with Playwright-backed cleanup.
---
```

- [ ] **Step 4: Refresh agent metadata if needed**

Ensure `agents/openai.yaml` matches the final skill:

```yaml
interface:
  display_name: "Microsoft Learn Scraper"
  short_description: "Search and scrape Microsoft Learn docs"
  default_prompt: "Use $microsoft-learn-scraper to search Microsoft Learn or fetch a Learn article as Markdown."
```

### Task 3: Validate the skill

**Files:**
- Test: `C:\Users\dlafferty.MCNA\.codex\skills\microsoft-learn-scraper\`

- [ ] **Step 1: Run structural validation**

Run:

```powershell
python "C:\Users\dlafferty.MCNA\.codex\skills\.system\skill-creator\scripts\quick_validate.py" "C:\Users\dlafferty.MCNA\.codex\skills\microsoft-learn-scraper"
```

Expected:

```text
Validation succeeds with no naming or frontmatter errors.
```

- [ ] **Step 2: Smoke-test direct fetch**

Run:

```powershell
python "C:\Users\dlafferty.MCNA\.codex\skills\microsoft-learn-scraper\scripts\ms_learn_scraper.py" "https://learn.microsoft.com/en-us/entra/identity/conditional-access/overview"
```

Expected:

```text
Markdown output begins with the article title and source metadata.
```

- [ ] **Step 3: Smoke-test search mode**

Run:

```powershell
python "C:\Users\dlafferty.MCNA\.codex\skills\microsoft-learn-scraper\scripts\ms_learn_scraper.py" --search "conditional access" --max 3
```

Expected:

```text
A numbered Markdown list of up to three learn.microsoft.com search results.
```

### Task 4: Record the task outcome

**Files:**
- Modify: `activity-log.md`

- [ ] **Step 1: Append the artifact log entry**

Append one line with timestamp, task name, outcome, and the main artifact path:

```text
YYYY-MM-DD HH:MM — Microsoft Learn scraper skill — Created and validated — C:\Users\dlafferty.MCNA\.codex\skills\microsoft-learn-scraper
```
