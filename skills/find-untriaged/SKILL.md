---
name: find-untriaged
description: >
  Finds open GitHub issues that have not been triaged yet (no report.json in their issue folder).
  Queries all configured repos by default, or a single repo if specified. Outputs a summary
  with counts and issue lists. Use when you want to see what new work exists before starting
  a sprint, or to check coverage gaps.
---

# Find Untriaged Issues

Discover open issues that have no triage report yet.

## When to Use

- Before triaging, to see what's out there
- After a triage sprint, to check for stragglers
- Periodic check: "what haven't we looked at?"
- Quick answer to "how many untriaged issues are there?"

## When Not to Use

- Batch processing (run `triage-issue` repeatedly for multiple issues)
- Checking status of already-triaged issues (use `triage-status`)

## Inputs

| Input | Required | Description |
|-------|----------|-------------|
| repo  | No       | Limit to one repo in `owner/repo` format. Default: all configured repos. |

## Workflow

### Step 1: Run the Discovery Script

Run the Python script that does the actual work:

```
python .agents/skills/find-untriaged/find_untriaged.py [--repo owner/repo] [--show N]
```

The script:
1. Reads `config/repos.json` for the repo list
2. Calls `gh api --paginate` to get all open issues per repo
3. Scans `issues/<owner>-<repo>/*/report.json` for triaged issues
4. Prints a concise summary to stdout (10 newest untriaged per repo by default)
5. Writes full JSON data to a temp file (path printed at the end)

If you need the full issue list (e.g., for a repo with many untriaged), read the temp JSON file.

### Step 2: Present Results

Display a clean summary table:

```
Untriaged Issues
================

microsoft/clrmd:     2 untriaged  (14 open, 12 triaged)
  #1369  LinkedList reading                          2026-02-17
  #1368  Dictionary Fields Reading                   2026-02-17

dotnet/diagnostics: 63 untriaged (260 open, 197 triaged)
  #5727  dotnet-stack should function without...     2026-02-17
  #811   EventPipe stress test failures              2020-05-15
  ... (showing newest 10, 53 more)

Total: 65 untriaged across 2 repos
```

For repos with many untriaged issues, show the 10 newest by default.
If the user asks for all, show the full list.

### Step 3: Suggest Next Steps

Based on the results, suggest:
- If few untriaged: "Run `triage-issue` on #NNNN to triage it"
- If many untriaged: "Run `triage-issue` on each, or pick a subset to start with"
- If zero untriaged: "All caught up! 🎉"

## Validation

- Script exits 0 and produces valid JSON
- Untriaged count + triaged count ≤ open count (triaged issues may have been closed)
- No issue appears in both triaged and untriaged sets
