#!/usr/bin/env python3
"""
Generate triage summary dashboard for a repository.

Usage:
    python generate-summary.py <owner/repo> <triage_repo_root> <reports_json> <prs_json>

Arguments:
    owner/repo        Repository in owner/repo format (e.g., dotnet/diagnostics)
    triage_repo_root  Path to the triage repo root (e.g., D:\git\work)
    reports_json      Path to a JSON file containing all issue report data
    prs_json          Path to a JSON file containing open PR data with linked issues

The reports_json file should be an array of objects:
    [{"number": 123, "has_report_md": true, "data": <report.json contents>}, ...]

The prs_json file should be an array of objects:
    [{"number": 456, "url": "...", "title": "...", "author": "...", "linked_issues": [123, 789]}, ...]

Outputs:
    summaries/<owner>-<repo>/<YYYY-MM-DD>.md
    summaries/<owner>-<repo>/latest.md
"""
import json, os, re, sys
from datetime import datetime, timezone


def main():
    if len(sys.argv) != 5:
        print(f"Usage: {sys.argv[0]} <owner/repo> <triage_root> <reports_json> <prs_json>")
        sys.exit(1)

    full_repo = sys.argv[1]          # e.g., "dotnet/diagnostics"
    base = sys.argv[2]               # e.g., "D:\git\work"
    reports_path = sys.argv[3]       # path to reports JSON
    prs_path = sys.argv[4]           # path to PRs JSON

    owner, repo_name = full_repo.split("/")
    repo_key = f"{owner}-{repo_name}"
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Load data
    with open(reports_path, "r", encoding="utf-8") as f:
        reports = json.load(f)
    with open(prs_path, "r", encoding="utf-8") as f:
        prs = json.load(f)

    # Load area config
    config_path = os.path.join(base, "config", "repos.json")
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)
    areas_config = config["repos"][full_repo].get("areas", {})

    # Build PR -> issue map
    issue_to_prs = {}
    for pr in prs:
        for iss in pr.get("linked_issues", []):
            issue_to_prs.setdefault(iss, []).append(pr["number"])

    # Load previous summary issue numbers for diff
    summary_dir = os.path.join(base, "summaries", repo_key)
    prev_issues = set()
    prev_files = sorted(
        [f for f in os.listdir(summary_dir) if re.match(r"\d{4}-\d{2}-\d{2}\.md$", f)]
    ) if os.path.isdir(summary_dir) else []
    if prev_files:
        prev_path = os.path.join(summary_dir, prev_files[-1])
        with open(prev_path, "r", encoding="utf-8") as f:
            prev_content = f.read()
        for m in re.finditer(
            rf"\[#(\d+)\]\(https://github\.com/{re.escape(owner)}/{re.escape(repo_name)}/issues/\d+\)",
            prev_content,
        ):
            prev_issues.add(int(m.group(1)))

    # Helpers
    CLOSE_STATUSES = {"already-fixed", "already-implemented", "by-design", "stale", "wont-fix", "duplicate"}

    def truncate(text, maxlen=150):
        if not text:
            return ""
        m = re.match(r"^(.+?[.!?])(?:\s|$)", text)
        if m:
            text = m.group(1)
        if len(text) > maxlen:
            text = text[: maxlen - 3] + "..."
        return text

    def escape_pipe(text):
        return (text or "").replace("|", "&#124;")

    def act_icon(act):
        return {"high": "🔴", "medium": "🟡"}.get(act, "⚪")

    def state_icon(state):
        return "🔵 Open" if state and state.lower() == "open" else "🔴 Closed"

    class IssueRow:
        def __init__(self, r):
            d = r["data"]
            self.number = r["number"]
            self.has_report_md = r["has_report_md"]
            issue = d.get("issue", {})
            triage = d.get("triage", {})
            fix = d.get("fix", {})

            self.title = issue.get("title", "")
            self.state = issue.get("state", "open")
            self.url = issue.get("url", f"https://github.com/{owner}/{repo_name}/issues/{self.number}")
            self.labels = issue.get("labels", [])
            self.manually_investigated = issue.get("manually_investigated", False)

            self.category = triage.get("category", "")
            self.status = triage.get("status", "")
            self.status_reason = triage.get("status_reason", "")
            self.affected_repo = triage.get("affected_repo", "")
            self.actionability = triage.get("actionability", "low")
            self.blocked_reason = triage.get("blocked_reason", "")

            self.has_fix = fix.get("has_candidate", False)
            self.prs = issue_to_prs.get(self.number, [])

        def report_link(self):
            if self.has_report_md:
                return f"[{self.number}](../../issues/{repo_key}/{self.number}/report.md)"
            return str(self.number)

        def github_link(self):
            return f"[#{self.number}]({self.url})"

        def pr_links(self):
            if not self.prs:
                return ""
            return ", ".join(f"[#{n}](https://github.com/{owner}/{repo_name}/pull/{n})" for n in self.prs)

        def to_row(self):
            return (
                f"| {self.report_link()} "
                f"| {self.github_link()} "
                f"| {escape_pipe(self.title)} "
                f"| {state_icon(self.state)} "
                f"| {act_icon(self.actionability)} "
                f"| {self.pr_links()} "
                f'| {"✅" if self.has_fix else ""} '
                f'| {"🔍" if self.manually_investigated else ""} '
                f"| {self.status} "
                f"| {escape_pipe(truncate(self.status_reason))} |"
            )

        def to_blocked_row(self):
            blocked_on = self.blocked_reason or self.status_reason or ""
            return (
                f"| {self.report_link()} "
                f"| {self.github_link()} "
                f"| {escape_pipe(self.title)} "
                f"| {state_icon(self.state)} "
                f"| {act_icon(self.actionability)} "
                f"| {escape_pipe(truncate(blocked_on))} "
                f"| {escape_pipe(truncate(self.status_reason))} |"
            )

    # Classify
    all_issues = [IssueRow(r) for r in reports]
    should_close = [i for i in all_issues if i.status in CLOSE_STATUSES]
    should_close_open = [i for i in should_close if i.state.lower() == "open"]
    should_close_closed = [i for i in should_close if i.state.lower() != "open"]
    blocked = [i for i in all_issues if i.status == "blocked" and i.status not in CLOSE_STATUSES]
    docs = [i for i in all_issues if i.category == "docs" and i.status not in CLOSE_STATUSES and i.status != "blocked"]
    excluded = set(i.number for i in should_close) | set(i.number for i in blocked) | set(i.number for i in docs)
    area_issues = [i for i in all_issues if i.number not in excluded]

    def classify_area(issue):
        issue_labels = [l.lower() if isinstance(l, str) else l.get("name", "").lower() for l in issue.labels]
        for area_name, area_def in areas_config.items():
            for label in area_def.get("labels", []):
                if label.lower() in issue_labels:
                    return area_name
        for area_name, area_def in areas_config.items():
            match_repo = area_def.get("match_affected_repo", "")
            if match_repo and issue.affected_repo and match_repo.lower() in issue.affected_repo.lower():
                return area_name
        title_lower = issue.title.lower()
        for area_name, area_def in areas_config.items():
            for kw in area_def.get("title_keywords", []):
                if kw.lower() in title_lower:
                    return area_name
        return "Other / General"

    area_groups = {}
    for issue in area_issues:
        area_groups.setdefault(classify_area(issue), []).append(issue)
    sorted_areas = sorted(area_groups.items(), key=lambda x: -len(x[1]))

    # Stats
    total = len(all_issues)
    open_count = sum(1 for i in all_issues if i.state.lower() == "open")
    closed_count = total - open_count
    fix_count = sum(1 for i in all_issues if i.has_fix)
    manual_count = sum(1 for i in all_issues if i.manually_investigated)

    current_numbers = set(i.number for i in all_issues)
    new_issues = current_numbers - prev_issues

    # Build markdown
    TABLE_HEADER = "| Issue | GitHub | Title | State | Act | Open PR | Fix | 🔍 | Status | Summary |"
    TABLE_SEP = "|-------|--------|-------|-------|-----|---------|-----|-----|--------|---------|"
    BLOCKED_HEADER = "| Issue | GitHub | Title | State | Act | Blocked On | Summary |"
    BLOCKED_SEP = "|-------|--------|-------|-------|-----|------------|---------|"

    lines = [
        f"# {full_repo} Issues Summary",
        "",
        f"*Generated: {today}*",
        "",
        "## Overview",
        "",
        "| Metric | Count |",
        "|--------|-------|",
        f"| Total Issues Analyzed | {total} |",
        f"| 🔵 Open | {open_count} |",
        f"| 🔴 Closed | {closed_count} |",
        f"| ✅ Have Fix Candidate | {fix_count} |",
        f"| 🔍 Manually Investigated | {manual_count} |",
        f"| Should Be Closed | {len(should_close_open)} open ({len(should_close_closed)} already closed) |",
        f"| Blocked | {len(blocked)} |",
        f"| Documentation Issues | {len(docs)} |",
        "",
    ]

    # Changes since last summary
    if prev_issues:
        new_fix_count = sum(1 for i in all_issues if i.number in new_issues and i.has_fix)
        lines += [
            "## Changes Since Last Summary",
            "",
            f"- {len(new_issues)} new issues triaged",
            f"- {new_fix_count} new fix candidates",
            "",
        ]

    # Open PRs
    lines += ["## Open Pull Requests", ""]
    if prs:
        lines += ["| PR | Author | Title | Linked Issues |", "|----|--------|-------|---------------|"]
        for pr in prs:
            linked = ", ".join(f'[#{n}](https://github.com/{owner}/{repo_name}/issues/{n})' for n in pr.get("linked_issues", []))
            lines.append(f"| [#{pr['number']}]({pr['url']}) | {pr['author']} | {escape_pipe(pr['title'])} | {linked} |")
        lines.append("")
    else:
        lines += ["No open pull requests.", ""]

    # Should Be Closed
    lines.append(f"## Issues That Should Be Closed ({len(should_close_open)} issues open, {len(should_close_closed)} already closed)")
    lines.append("")
    if should_close_open:
        lines += [TABLE_HEADER, TABLE_SEP]
        for i in sorted(should_close_open, key=lambda x: x.number):
            lines.append(i.to_row())
        lines.append("")
    else:
        lines += ["No open issues that should be closed.", ""]

    # Blocked
    lines.append(f"## Blocked Issues ({len(blocked)} issues)")
    lines.append("")
    if blocked:
        lines += [BLOCKED_HEADER, BLOCKED_SEP]
        for i in sorted(blocked, key=lambda x: x.number):
            lines.append(i.to_blocked_row())
        lines.append("")
    else:
        lines += ["No blocked issues.", ""]

    # Areas
    for area_name, issues in sorted_areas:
        lines += [f"## {area_name} ({len(issues)} issues)", "", TABLE_HEADER, TABLE_SEP]
        for i in sorted(issues, key=lambda x: x.number):
            lines.append(i.to_row())
        lines.append("")

    # Docs
    lines.append(f"## Documentation Issues ({len(docs)} issues)")
    lines.append("")
    if docs:
        lines += [TABLE_HEADER, TABLE_SEP]
        for i in sorted(docs, key=lambda x: x.number):
            lines.append(i.to_row())
        lines.append("")
    else:
        lines += ["No documentation issues.", ""]

    # Write
    os.makedirs(summary_dir, exist_ok=True)
    content = "\n".join(lines)
    out_path = os.path.join(summary_dir, f"{today}.md")
    latest_path = os.path.join(summary_dir, "latest.md")

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(content)
    with open(latest_path, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"Written to {out_path}")
    print(f"Written to {latest_path}")
    print(f"{total} issues, {len(lines)} lines")


if __name__ == "__main__":
    main()
