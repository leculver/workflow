#!/usr/bin/env python3
"""Find open GitHub issues that haven't been triaged yet."""

import argparse, json, os, shutil, subprocess, sys


def get_open_issues(owner, repo):
    """Use `gh` to get all open issue numbers + titles."""
    gh = shutil.which("gh")
    if not gh:
        print("Error: 'gh' CLI not found. Install from https://cli.github.com/", file=sys.stderr)
        sys.exit(1)
    result = subprocess.run(
        [gh, "api", "--paginate",
         f"/repos/{owner}/{repo}/issues?state=open",
         "--jq", '.[] | select(.pull_request == null) | {number, title, created_at}'],
        capture_output=True, text=True, check=True
    )
    issues = []
    for line in result.stdout.strip().split('\n'):
        if line:
            issues.append(json.loads(line))
    return issues


def get_triaged_issues(issues_dir, dir_name):
    """Scan issues/<owner>-<repo>/ for folders with report.json."""
    repo_dir = os.path.join(issues_dir, dir_name)
    triaged = set()
    if os.path.isdir(repo_dir):
        for entry in os.listdir(repo_dir):
            report = os.path.join(repo_dir, entry, "report.json")
            if os.path.isfile(report):
                try:
                    triaged.add(int(entry))
                except ValueError:
                    pass
    return triaged


def main():
    parser = argparse.ArgumentParser(description="Find open GitHub issues that haven't been triaged yet.")
    parser.add_argument("--repo", help="owner/repo to check (default: all)")
    parser.add_argument("--config", default="config/repos.json")
    parser.add_argument("--issues-dir", default="issues")
    args = parser.parse_args()

    with open(args.config) as f:
        config = json.load(f)

    results = []
    for repo_key, repo_cfg in config["repos"].items():
        if args.repo and repo_key != args.repo:
            continue

        owner = repo_cfg["owner"]
        name = repo_cfg["name"]
        dir_name = f"{owner}-{name}"

        open_issues = get_open_issues(owner, name)
        triaged = get_triaged_issues(args.issues_dir, dir_name)

        open_numbers = {i["number"] for i in open_issues}
        untriaged_numbers = open_numbers - triaged

        untriaged = sorted(
            [i for i in open_issues if i["number"] in untriaged_numbers],
            key=lambda i: i["number"], reverse=True
        )

        results.append({
            "repo": repo_key,
            "open_count": len(open_issues),
            "triaged_count": len(triaged & open_numbers),
            "untriaged": untriaged,
            "untriaged_count": len(untriaged)
        })

    output = {
        "repos": results,
        "total_untriaged": sum(r["untriaged_count"] for r in results)
    }
    json.dump(output, sys.stdout, indent=2)


if __name__ == "__main__":
    main()
