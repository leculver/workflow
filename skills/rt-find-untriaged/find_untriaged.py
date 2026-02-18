#!/usr/bin/env python3
"""Find open GitHub issues that haven't been triaged yet.

Outputs a concise summary to stdout and writes full JSON data to a temp file.
"""

import argparse, json, os, shutil, subprocess, sys, tempfile


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


def print_summary(results, show_max=10):
    """Print a concise human-readable summary to stdout."""
    total = sum(r["untriaged_count"] for r in results)
    print(f"Untriaged Issues: {total}")
    print("=" * 40)
    for r in results:
        print(f"\n{r['repo']}: {r['untriaged_count']} untriaged  "
              f"({r['open_count']} open, {r['triaged_count']} triaged)")
        shown = r["untriaged"][:show_max]
        for i in shown:
            date = i["created_at"][:10]
            title = i["title"][:60]
            print(f"  #{i['number']:<6} {title:<60} {date}")
        remaining = len(r["untriaged"]) - len(shown)
        if remaining > 0:
            print(f"  ... ({remaining} more, see JSON output)")


def main():
    parser = argparse.ArgumentParser(description="Find open GitHub issues that haven't been triaged yet.")
    parser.add_argument("--repo", help="owner/repo to check (default: all)")
    parser.add_argument("--config", default="config/repos.json")
    parser.add_argument("--issues-dir", default="issues")
    parser.add_argument("--show", type=int, default=10, help="Max issues to show per repo (default: 10)")
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

    # Write full JSON to temp file
    output = {
        "repos": results,
        "total_untriaged": sum(r["untriaged_count"] for r in results)
    }
    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".json", prefix="untriaged-",
                                      delete=False, encoding="utf-8")
    json.dump(output, tmp, indent=2)
    tmp.close()

    # Print concise summary to stdout
    print_summary(results, show_max=args.show)
    print(f"\nFull data: {tmp.name}")


if __name__ == "__main__":
    main()
