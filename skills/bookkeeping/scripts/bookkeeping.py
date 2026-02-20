#!/usr/bin/env python3
"""Bookkeeping processor: handles .log files (progress notes) and .delete files (deletion reminders).

Usage:
    python bookkeeping.py <repo_root> [--issues-only <owner-repo>]

Scans for:
  1. Per-issue .bookkeeping/*.log files — renames to .flushing.log, reads content,
     outputs structured JSON so the LLM can append to logs. Silent operation.
  2. Root .bookkeeping/*.delete files — checks for expired items and prints warnings.

Output format (JSON to stdout):
{
  "logs": [
    {
      "issue_dir": "issues/dotnet-diagnostics/1234",
      "files": [
        {"name": "2026-02-19T13-30-00Z.log", "content": "..."}
      ]
    }
  ],
  "expired_deletions": [
    {
      "source": "dumps.delete",
      "path": "/path/to/dump.dmp",
      "ingested_at": "2026-02-19T16:00:00Z",
      "file_timestamp": "2026-02-18T10:30:00Z",
      "delete_after": "2026-03-01T00:00:00Z"
    }
  ]
}
"""

import glob
import json
import os
import sys
from datetime import datetime, timezone


def process_log_files(repo_root: str, issues_filter: str | None = None) -> list[dict]:
    """Scan per-issue .bookkeeping/ directories for .log files.

    Renames each .log to .flushing.log before reading (claim-before-read pattern).
    Returns list of {issue_dir, files: [{name, content}]} for each issue with logs.
    """
    if issues_filter:
        pattern = os.path.join(repo_root, "issues", issues_filter, "*", ".bookkeeping", "*.log")
    else:
        pattern = os.path.join(repo_root, "issues", "*", "*", ".bookkeeping", "*.log")

    # Group by issue directory
    log_files_by_issue: dict[str, list[str]] = {}
    for log_path in sorted(glob.glob(pattern)):
        issue_dir = os.path.dirname(os.path.dirname(log_path))
        rel_issue = os.path.relpath(issue_dir, repo_root)
        if rel_issue not in log_files_by_issue:
            log_files_by_issue[rel_issue] = []
        log_files_by_issue[rel_issue].append(log_path)

    results = []
    for issue_dir, log_paths in sorted(log_files_by_issue.items()):
        files = []
        for log_path in log_paths:
            # Rename to .flushing.log (claim the file)
            flushing_path = log_path.replace(".log", ".flushing.log")
            try:
                os.rename(log_path, flushing_path)
            except OSError:
                # Another session claimed it
                continue

            try:
                with open(flushing_path, "r", encoding="utf-8") as f:
                    content = f.read()
                files.append({
                    "name": os.path.basename(log_path),
                    "content": content,
                    "flushing_path": flushing_path,
                })
            except OSError:
                continue

        if files:
            results.append({"issue_dir": issue_dir, "files": files})

    return results


def process_delete_files(repo_root: str) -> list[dict]:
    """Scan root .bookkeeping/ for *.delete files and check for expired items."""
    bookkeeping_dir = os.path.join(repo_root, ".bookkeeping")
    if not os.path.isdir(bookkeeping_dir):
        return []

    now = datetime.now(timezone.utc)
    expired = []

    for delete_file in sorted(glob.glob(os.path.join(bookkeeping_dir, "*.delete"))):
        source_name = os.path.basename(delete_file)
        try:
            with open(delete_file, "r", encoding="utf-8") as f:
                entries = json.load(f)
        except (OSError, json.JSONDecodeError):
            continue

        if not isinstance(entries, list):
            continue

        for entry in entries:
            delete_after = entry.get("delete_after")
            if delete_after is None:
                continue

            try:
                due = datetime.fromisoformat(delete_after)
                if due.tzinfo is None:
                    due = due.replace(tzinfo=timezone.utc)
            except (ValueError, TypeError):
                continue

            if now >= due:
                expired.append({
                    "source": source_name,
                    "path": entry.get("path", "<unknown>"),
                    "ingested_at": entry.get("ingested_at", "<unknown>"),
                    "file_timestamp": entry.get("file_timestamp", "<unknown>"),
                    "delete_after": delete_after,
                })

    return expired


def main():
    if len(sys.argv) < 2:
        print("Usage: bookkeeping.py <repo_root> [--issues-only <owner-repo>]", file=sys.stderr)
        sys.exit(1)

    repo_root = os.path.abspath(sys.argv[1])
    issues_filter = None

    if "--issues-only" in sys.argv:
        idx = sys.argv.index("--issues-only")
        if idx + 1 < len(sys.argv):
            issues_filter = sys.argv[idx + 1]

    logs = process_log_files(repo_root, issues_filter)
    expired = process_delete_files(repo_root)

    result = {
        "logs": logs,
        "expired_deletions": expired,
    }

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
