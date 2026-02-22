# Issue File Schema

Issues are stored across two JSON files per issue directory, plus a markdown summary.

## `github.json` — Raw GitHub API Data

```json
{
  "issue": {
    "fetched_at": "<ISO 8601>",
    "data": { /* raw response from issue_read(method="get") */ }
  },
  "comments": {
    "fetched_at": "<ISO 8601>",
    "data": [ /* raw response from issue_read(method="get_comments") */ ]
  }
}
```

- `fetched_at` is per-section so issue and comments can be refreshed independently.
- `data` is the raw API response — do not transform or cherry-pick fields.
- Staleness check: compare `issue.fetched_at` vs `issue.data.updated_at`.

## `analysis.json` — Our Analysis

```json
{
  "triage": {
    "category": "bug|feature-request|question|docs",
    "status": "<see triage-categories.md>",
    "status_reason": "<one sentence explanation>",
    "blocked_reason": "<why blocked — only when status is 'blocked'>",
    "blocked_url": "<url of blocking issue/PR/package, or null>",
    "affected_repo": "<repo short name or 'unknown'>",
    "requires_platform": ["any"],
    "staleness": "active|stale|superseded",
    "superseded_by": null,
    "actionability": "high|medium|low",
    "manually_investigated": false
  },
  "environment": {
    "os": "<OS description>",
    "dotnet_sdk": "<SDK version>",
    "repo_head_sha": "<git SHA>",
    "dump_env": {
      "DOTNET_DbgEnableMiniDump": "<value>",
      "DOTNET_DbgMiniDumpType": "<value>",
      "DOTNET_DbgMiniDumpName": "<value>",
      "DOTNET_CreateDumpDiagnostics": "<value>",
      "DOTNET_CreateDumpVerboseDiagnostics": "<value>",
      "DOTNET_EnableCrashReport": "<value>"
    }
  },
  "reproduction": {
    "started_at_utc": "<ISO 8601>",
    "finished_at_utc": "<ISO 8601>",
    "steps": [
      {
        "description": "<what was done>",
        "cmd": "<command run>",
        "cwd": "<working directory>",
        "exit_code": 0,
        "stdout_tail": "<last output lines>",
        "summary": "<one-line result>"
      }
    ],
    "artifacts": ["<relative path>"],
    "observations": ["<finding>"]
  },
  "fix": {
    "has_candidate": false,
    "summary": "<fix description>",
    "confidence": 0.0,
    "branch": "<branch name>",
    "fix_repo": "<owner/repo where the branch was created, if different>",
    "diff": "<unified diff or description>"
  },
  "log": [
    {
      "heading": "<ISO 8601 timestamp> — <platform> — <session type>",
      "body": "<session notes, findings, status changes>"
    }
  ]
}
```

## `analysis.md` — Human-Readable Summary

Markdown report following the learning-focused format defined in `diagnose-and-fix` Step 9.

## Writing Rules

- `manually_investigated` is always `false` unless set by `load-issue`. Only that skill sets it to `true` — all other automated skills leave it as `false` or preserve the existing value.
- Write atomically: write to `.json.tmp` then rename to `.json`.
- `affected_repo` should match a key in `config/repos.json` `related_repos` or the main repo name.
- `reproduction.artifacts` should list paths to repro source and scripts (committed), NOT dump files (gitignored).
- Always include a `repro/` directory with source code and a `repro.sh`/`repro.bat` to regenerate dumps.
- Log entries are appended to the `log` array in `analysis.json` — never overwrite prior entries.
- `github.json` stores raw API responses — do not transform or cherry-pick fields into it.
