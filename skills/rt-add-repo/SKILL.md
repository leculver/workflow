---
name: rt-add-repo
description: >
  Adds a new repository to the triage system configuration. Prompts for repo details, local checkout paths,
  area classification rules, and scope filters. Writes the config entry and creates directory structure.
  Use when starting triage on a new repository like dotnet/runtime or microsoft/clrmd.
---

# Add Repo

Configure a new repository for the issue triage system.

## When to Use

- Starting triage on a new repository for the first time
- Adding a related repo (e.g., adding `dotnet/runtime` alongside `dotnet/diagnostics`)
- Reconfiguring an existing repo's settings

## When Not to Use

- The repo is already configured (edit `config/repos.json` directly instead)
- Running triage (use `rt-sprint-setup` then `rt-triage-issue`)

## Inputs

| Input | Required | Description |
|-------|----------|-------------|
| repo | Yes | Repository in `owner/repo` format |
| source_path | Yes | Local path to the repo checkout (relative to workspace root) |
| source_alt_path | No | Alternative checkout path (for parallel work, e.g., `./diagnostics2`) |
| related_repos | No | Map of related repos and their local paths |
| scope | No | Default GitHub search scope for this repo |
| areas | No | Area classification rules (or auto-generate from labels) |
| debugger_windows | No | Path to Windows debugger (e.g., `d:\amd64\cdb.exe`) |
| debugger_linux | No | Linux debugger command (e.g., `lldb`) |
| auto_detect_areas | No | If true, fetch labels from GitHub and generate area rules (default: true) |

## Workflow

### Step 0: Bookkeeping

Invoke `rt-bookkeeping` to pull the triage repo and flush any pending `.progress/` from prior sessions.

### Step 1: Validate Inputs

1. Check that `repo` is in valid `owner/repo` format.
2. Verify the repo exists on GitHub using GitHub MCP tools.
3. Check that the local checkout path exists on disk (warn if not, but don't fail — user may set up later).

### Step 2: Auto-Detect Areas (if auto_detect_areas)

1. Fetch all labels from the GitHub repo.
2. Group labels by common prefixes (e.g., `area-`, `os-`, `feature-`).
3. Suggest area classification rules based on label patterns.
4. Present to the user for review/modification.

### Step 3: Build Configuration Entry

Create the repo entry for `config/repos.json`:

```json
{
  "<owner>/<repo>": {
    "owner": "<owner>",
    "name": "<repo>",
    "local_paths": {
      "source": "<source_path>",
      "source_alt": "<source_alt_path or null>"
    },
    "related_repos": { ... },
    "scope": {
      "default_query": "is:issue is:open",
      "exclude_labels": []
    },
    "areas": {
      "<Area Name>": {
        "labels": ["<matching-labels>"],
        "title_keywords": ["<matching-keywords>"]
      }
    },
    "debugger": {
      "windows": "<path or null>",
      "linux": "<command or null>"
    },
    "dump_env": {
      "DOTNET_DbgEnableMiniDump": "1",
      "DOTNET_DbgMiniDumpType": "4",
      "DOTNET_DbgMiniDumpName": "dumps/%e.%p.%t.dmp",
      "DOTNET_CreateDumpDiagnostics": "1",
      "DOTNET_CreateDumpVerboseDiagnostics": "1",
      "DOTNET_EnableCrashReport": "1"
    }
  }
}
```

### Step 4: Update repos.json

1. Read the existing `config/repos.json`.
2. Add (or update) the entry for this repo under the `repos` key.
3. Write the file back (preserve formatting).

### Step 5: Validate Git Remote Configuration

The local checkout must follow the fork workflow convention:

1. **`upstream`** must point to the target repo (the `owner/repo` being triaged).
   - e.g., `upstream = https://github.com/dotnet/diagnostics.git`
2. **`origin`** must point to a **different** repo (the user's fork).
   - e.g., `origin = https://github.com/leculver/diagnostics.git`
3. `origin` and `upstream` must NOT be the same URL.

**Validation steps:**
1. `cd` to the local checkout path.
2. Run `git remote get-url upstream` — must match `https://github.com/<owner>/<repo>.git` (or the SSH equivalent).
3. Run `git remote get-url origin` — must NOT match upstream. This is the user's fork where fix branches are pushed.
4. If `upstream` is missing or wrong, offer to fix it: `git remote add upstream <url>` or `git remote set-url upstream <url>`.
5. If `origin` equals `upstream`, warn the user: "origin and upstream are the same — you need a fork to push fix branches. Fork the repo on GitHub first, then set origin to your fork."
6. Validate the same for any `source_alt` paths and related repo checkouts.

### Step 6: Update .gitignore

If the local checkout path is under the triage repo (e.g., `./clrmd`, `./diagnostics`), add it to `.gitignore` so the cloned repo isn't accidentally committed to the triage repo. Skip if already listed.

### Step 7: Create Directory Structure

Create the issue and summary directories:

```
issues/<owner>-<repo>/
summaries/<owner>-<repo>/
```

### Step 8: Validate and Commit

1. Verify `config/repos.json` is valid JSON.
2. Commit: `config: add repo <owner>/<repo>`
3. Push to the remote. If the push fails (e.g., remote is ahead), ask the user whether to rebase and retry or skip the push.

### Step 9: Report

```
Repository configured: dotnet/runtime
  Local path: ./runtime
  Areas: 15 auto-detected from labels
  Scope: is:issue is:open label:area-Diagnostics-coreclr

Ready! Run: "set up a sprint for dotnet/runtime"
```

## Validation

- [ ] `config/repos.json` is valid JSON after modification
- [ ] Repo entry has at minimum: owner, name, local_paths.source
- [ ] Directory structure created in triage repo
- [ ] Committed to triage repo

## Common Pitfalls

| Pitfall | Solution |
|---------|----------|
| Repo doesn't exist on GitHub | Validate with GitHub API first |
| Local path doesn't exist yet | Warn but allow — user may clone later |
| Clobbering existing config | Read-modify-write, don't overwrite |
| Too many auto-detected areas | Let user review and prune |
| origin == upstream | User needs a fork; warn and link to GitHub fork page |
| upstream missing | Add it automatically with `git remote add upstream` |
| Checkout under triage repo | Add to `.gitignore` so it's not committed |
