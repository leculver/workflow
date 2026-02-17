---
name: dotnet-diagnostics-parallel-run-tests
description: >
  Temporarily patches the dotnet/diagnostics test runner to maximize xunit parallelism, runs the tests,
  then reverts the patch. Use when the user wants to run diagnostics tests faster on a multi-core machine.
  Only works on native Arch Linux (not WSL).
---

# Parallel Run Tests (dotnet/diagnostics)

Patch the Arcade-based test runner to enable aggressive xunit parallelism, run the tests, then cleanly revert.

## When to Use

- User says "run tests", "run diagnostics tests", "test in parallel", or similar while working in the diagnostics checkout
- User wants faster test execution on a multi-core Linux machine

## When Not to Use

- Running on Windows or WSL (this skill is native Arch Linux only)
- Running tests in other repos (this patches diagnostics' `eng/build.sh` specifically)
- User wants to run a single test without parallelism overhead

## Inputs

| Input | Required | Description |
|-------|----------|-------------|
| diagnostics_path | No | Path to the diagnostics repo checkout. Default: look for a `diagnostics/` directory under the current working directory or `~/git/work/diagnostics`. |
| test_args | No | Additional arguments to pass to `test.sh` (e.g., `--classfilter SOS.UnitTests.SOS`). |

## Workflow

### Step 0: Bookkeeping

Invoke `rt-bookkeeping` to pull the triage repo and flush any pending `.progress/` from prior sessions.

### Step 1: Validate Environment

This skill only works on **native Arch Linux**. Check both conditions:

1. Read `/etc/os-release` and confirm it contains `ID=arch`.
2. Check that `/proc/sys/fs/binfmt_misc/WSLInterop` does **NOT** exist. Its presence means WSL.

If either check fails, **stop** and tell the user:
- If not Arch: "This skill is designed for native Arch Linux. Detected: `<distro>`."
- If WSL: "This skill does not work under WSL. Run on a native Arch Linux machine."

### Step 2: Locate the Diagnostics Repo

1. If `diagnostics_path` is provided, use it.
2. Otherwise, look for `diagnostics/` under the current working directory.
3. Fall back to `~/git/work/diagnostics`.
4. Verify `eng/build.sh` exists at the resolved path. If not, abort.

### Step 3: Check for Dirty State

Run `git -C <diagnostics_path> diff --name-only eng/build.sh`.

If the file is already modified, **warn the user** and ask before proceeding. The revert step will discard their changes.

### Step 4: Apply Patch

In `<diagnostics_path>/eng/build.sh`, find this exact block (around lines 318–322):

```bash
    # Build the test filter argument if provided
    __TestFilterArg=
    if [[ -n "$__TestFilter" ]]; then
        __TestFilterArg="/p:TestRunnerAdditionalArguments=\"$__TestFilter\""
    fi
```

Replace it with:

```bash
    # Build the test filter argument if provided
    __TestFilterArg=
    if [[ -n "$__TestFilter" ]]; then
        __TestFilterArg="/p:TestRunnerAdditionalArguments=\"$__TestFilter -parallel all -maxthreads unlimited -parallelalgorithm aggressive\""
    else
        __TestFilterArg="/p:TestRunnerAdditionalArguments=\"-parallel all -maxthreads unlimited -parallelalgorithm aggressive\""
    fi
```

**What the xunit flags do:**
- `-parallel all` — parallelize both across collections AND assemblies
- `-maxthreads unlimited` — no cap on thread count per assembly
- `-parallelalgorithm aggressive` — start as many tests as possible immediately instead of conservative ramp-up

These flags are valid for xunit 2.9.3 (from Arcade SDK `DefaultVersions.props`).

**Why patching is necessary:** `TestRunnerAdditionalArguments` is only set if `--methodfilter` or `--classfilter` is provided. There is no way to pass it from the `test.sh` command line because `$__UnprocessedBuildArgs` is NOT forwarded to the test invocation (only to the managed build). The Arcade SDK's `XUnit.Runner.targets` passes `TestRunnerAdditionalArguments` directly to `xunit.console.dll` CLI args.

**Note:** MSBuild itself already runs with `/m` (all cores) via `eng/common/tools.sh` line 529, so cross-project parallelism is already handled. This skill adds **intra-project** test parallelism.

### Step 5: Run Tests

Execute `<diagnostics_path>/test.sh` with any user-provided `test_args`.

Use bash with `mode="sync"` and `initial_wait: 300` since tests take a long time. Use `read_powershell` to poll for completion if needed.

Capture the exit code.

### Step 6: Revert Patch (CRITICAL)

**This step MUST happen regardless of whether tests passed or failed.** Treat this as a finally block.

Run:
```bash
git -C <diagnostics_path> checkout eng/build.sh
```

This cleanly undoes the patch. **Always do this immediately after capturing the test exit code.** Do not skip this step for any reason.

### Step 7: Report Results

Tell the user:
- Whether tests passed or failed (based on exit code)
- Show any failure output if tests failed
- Confirm that `eng/build.sh` was reverted

## Validation

- [ ] Skill only activates on native Arch Linux (not WSL)
- [ ] `eng/build.sh` is patched before test run
- [ ] `eng/build.sh` is reverted after test run (even on failure)
- [ ] User-provided test filters still work alongside parallel flags
- [ ] Exit code from test run is preserved and reported

## Common Pitfalls

| Pitfall | Solution |
|---------|----------|
| Running on WSL instead of native Linux | Check for `/proc/sys/fs/binfmt_misc/WSLInterop` and abort if present |
| Forgetting to revert `eng/build.sh` | Always revert immediately after capturing exit code, even on failure |
| User has uncommitted changes to `eng/build.sh` | Check with `git diff` first and warn before overwriting |
| Test timeout | Use `initial_wait: 300` and poll with `read_powershell`; tests can take 10+ minutes |
| Patch doesn't match | The exact block may shift lines; search for the `# Build the test filter argument` comment rather than relying on line numbers |
