# Setup Instructions

You are setting up a new issue triage workspace. Follow these steps exactly.

## Step 1: Initialize the Triage Repo

If the current directory is not already a git repo, initialize one:

```bash
git init
```

Create a **private** GitHub repo for the triage workspace and set it as origin. Ask the user what they want to name it (suggest `work`).

```bash
gh repo create <name> --private
git remote add origin <repo-url>
```

## Step 2: Generate config/user.json

```bash
mkdir -p config
gh api user --jq '{login: .login, name: .name}' > config/user.json
```

Read back the file and greet the user by name.

## Step 3: Create Directory Structure

```bash
mkdir -p .github config issues summaries notes
```

## Step 4: Create .gitignore

Write `.gitignore` with these rules (see the example in README.md for the full template):

- `.progress/` — in-progress notes (flushed by bookkeeping)
- `config/local-tools.json` and `config/user.json` — machine-specific
- Dump files (`*.dmp`, `*.crashreport.json`, `dumps/`)
- Trace files (`*.nettrace`, `*.etl`, `*.perfcollect`)
- .NET build artifacts (`bin/`, `obj/`, `*.dll`, `*.exe`, `*.pdb`, etc.)
- Python artifacts (`__pycache__/`, `*.py[cod]`)
- C++ build artifacts (`*.o`, `*.obj`, `*.lib`, `*.so`, etc.)
- OS junk (`Thumbs.db`, `.DS_Store`)
- Editor files (`.vscode/`, `*.swp`)
- Temp files (`*.tmp`, `tmp/`)

Do NOT add sub-repo checkout entries yet — the `add-repo` skill handles that.

## Step 5: Create .github/copilot-instructions.md

Write the copilot instructions file. Use the example from README.md as a starting point, but keep the sub-repo checkouts section empty (repos will be added in the next step).

## Step 6: Create config/repos.json

```json
{
  "repos": {}
}
```

## Step 7: Initial Commit

```bash
git add .gitignore .github/ config/repos.json
git commit -m "Initial triage workspace setup"
git push -u origin main
```

Note: `config/user.json` is gitignored — do not commit it.

## Step 8: Add First Repository

Ask the user which GitHub repository they want to triage (e.g., `dotnet/runtime`, `microsoft/clrmd`).

Then invoke the `add-repo` skill with that repository. The skill will:
- Clone the repo locally (or validate an existing checkout)
- Set up fork/upstream remotes
- Auto-detect area labels
- Update `config/repos.json`
- Add the checkout directory to `.gitignore`

## Step 9: Verify

Run a quick check:
1. `git status` — working tree should be clean
2. `config/user.json` exists and has the user's login
3. `config/repos.json` has at least one repo entry
4. The cloned repo directory exists and has correct remotes
5. `.gitignore` includes the cloned repo directory

Report the results and suggest next steps:

```
Workspace is ready!

Try:
  "find untriaged issues in <owner>/<repo>"
  "diagnose issue #<number>"
  "what's the triage status?"
```

## Important Notes

- The `.agents/` directory is a separate git repo (this one). Do NOT `git add .agents/` in the triage repo — it's its own clone.
- All skills read the GitHub username from `config/user.json`, never hardcode it.
- The `bookkeeping` skill runs automatically at the start of other skills. It pulls the triage repo and regenerates `config/user.json` if missing.
