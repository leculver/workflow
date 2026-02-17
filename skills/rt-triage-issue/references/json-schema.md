# JSON Report Schema

The canonical schema is at `config/schemas/issue-report.schema.json` in the triage repo root.

## Quick Reference

```json
{
  "issue": {
    "number": <int>,
    "url": "<github issue url>",
    "title": "<issue title>",
    "state": "open|closed",
    "labels": ["<label>", ...],
    "created_at_utc": "<ISO 8601>",
    "fetched_at_utc": "<ISO 8601>",
    "body_excerpt": "<max 500 chars>",
    "key_comments_excerpt": ["<comment>", ...],
    "manually_investigated": <bool>
  },
  "triage": {
    "category": "bug|feature-request|question|docs",
    "status": "<see triage-categories.md>",
    "status_reason": "<one sentence explanation>",
    "blocked_reason": "<why blocked — only when status is 'blocked'>",
    "blocked_url": "<url of blocking issue/PR/package, or null>",
    "affected_repo": "<repo short name or 'unknown'>",
    "requires_platform": ["any"],
    "staleness": "active|stale|superseded",
    "superseded_by": <int or null>,
    "actionability": "high|medium|low"
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
        "exit_code": <int>,
        "stdout_tail": "<last output lines>",
        "summary": "<one-line result>"
      }
    ],
    "artifacts": ["<relative path>", ...],
    "observations": ["<finding>", ...]
  },
  "fix": {
    "has_candidate": <bool>,
    "summary": "<fix description>",
    "confidence": <0.0-1.0>,
    "branch": "<branch name>",
    "diff": "<unified diff or description>"
  }
}
```

## Writing Rules

- `manually_investigated` is always `false` unless set by `rt-load-issue`. Only that skill sets it to `true` — all other automated skills leave it as `false` or preserve the existing value.
- Write atomically: write to `.json.tmp` then rename to `.json`.
- `affected_repo` should match a key in `config/repos.json` `related_repos` or the main repo name.
- `reproduction.artifacts` should list paths to repro source and scripts (committed), NOT dump files (gitignored).
- Always include a `repro/` directory with source code and a `repro.sh`/`repro.bat` to regenerate dumps.
