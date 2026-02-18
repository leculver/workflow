# Reproduction Rules

## General Rules

- Always start on the main branch of any repo you work in.
- Record everything you attempt in the JSON report so we can review what was tried later.
- Prefer a minimal, deterministic repro.
- If the issue describes a failing scenario, try to write a tiny console repro or unit test that triggers it.
- If the issue is a suggestion, check if the suggestion has already been implemented or is still relevant.
- Clean up between attempts — don't pollute the main branch of git repos.

## Repro Directory Structure

```
<workspace>/repros/issue_<NUMBER>/
├── <repro app files>
├── dumps/
│   └── *.dmp, *.crashreport.json
└── artifacts/
    └── (relevant output files)
```

## Dump Capture Environment Variables

Set these to capture dumps from crashing .NET apps:

```
DOTNET_DbgEnableMiniDump=1
DOTNET_DbgMiniDumpType=4
DOTNET_DbgMiniDumpName=dumps/%e.%p.%t.dmp
DOTNET_CreateDumpDiagnostics=1
DOTNET_CreateDumpVerboseDiagnostics=1
DOTNET_EnableCrashReport=1
```

These should be set relative to the repro's working directory (e.g., `./repros/issue_####/dumps`).

## Dump File Naming

- All crashdump/coredump files MUST use the `.dmp` extension, regardless of platform.
- Linux core dumps default to no extension or `core.*` — rename them to `.dmp` after capture.
- This ensures consistent tooling (ClrMD, dotnet-dump, cdb) across platforms.

## Crash Artifact Handling

- If you trigger a crash, ensure dump/crash-report artifacts are captured.
- Store dumps in `./repros/issue_<NUMBER>/dumps/`.
- Copy or move relevant artifacts into `./repros/issue_<NUMBER>/artifacts/` and reference their paths in the JSON.
- You can write ClrMD apps/scripts to load the dumps you generate to reproduce issues.

**IMPORTANT: Dumps are NOT committed to the triage repo** (they are gitignored — too large). Instead, persist enough information to **regenerate** them:

1. **Always commit the repro app source code** to the triage repo under `issues/<owner>-<repo>/<issue_number>/repro/`. This is the minimal app that triggers the crash.
2. **Record the exact reproduction commands** in `reproduction.steps` in the JSON report, including:
   - The full command line used to run the repro app
   - All environment variables set (especially dump capture vars)
   - The working directory
   - The .NET SDK version and runtime version
   - Any input data or arguments needed
3. **Write a `repro.sh` / `repro.bat`** script in the repro directory that regenerates the dump from scratch. This script should:
   - Build the repro app
   - Set dump capture environment variables
   - Run the app to trigger the crash
   - Rename the resulting dump to `.dmp` if needed
4. **Commit the repro script and source** — these are small and reproducible. The dump itself stays local.
5. Reference dump paths in the JSON as relative paths under `repros/` — a developer on another machine can regenerate them by running the repro script.

## Fix Attempt Rules

Attempt a fix when:
- Reproduction succeeded and root cause is understood, OR
- Root cause is obvious from code inspection even without reproduction (e.g., clear null check, off-by-one), OR
- A feature request has a straightforward implementation path.

The goal is to produce a proposed fix the developer can review to understand the issue, even if the fix isn't verified by a repro. Use lower `fix.confidence` values (0.4–0.6) for unverified fixes.

1. Include a short explanation in the JSON `fix` section.
2. Include an optional unified diff string (do NOT apply it to main automatically).
3. Save the fix to an `issue_<NUMBER>` branch in the appropriate repo.
4. You can run targeted tests, but avoid full test suites (they can take 50+ minutes).
5. Do NOT include `Co-authored-by: Copilot` in fix commit messages — these are proposed fixes authored by the developer.
6. Don't leave the repo in an odd state — always return to main when done.

## Platform-Specific Notes

### Windows
- You may have access to `cdb.exe` for SOS debugging. Check `config/repos.json` for debugger paths.
- Use worktrees if other agents may be sharing the repo checkout.

### Linux
- Use `lldb` for debugging. SOS should be auto-loaded via `.lldbinit`.
- You can also use `dotnet-dump`, `dotnet-trace`, `dotnet-counters`, and other diagnostic tools.
- Build diagnostic tools from source with `./build.sh` in the diagnostics repo.
