---
name: collect-dumps
description: >
  Configures .NET crash dump collection via environment variables. Sets up full dumps (type 4),
  crash reports, and diagnostic logging. Use when setting up a repro environment, writing repro
  scripts, or helping a user configure dump collection. Handles both normal use and the special
  case where we're debugging createdump/diagnostics tooling itself.
---

# Collect .NET Crash Dumps

Configure environment variables for automatic .NET crash dump collection.

## When to Use

- Setting up a repro environment for an issue
- Writing `repro.sh` / `repro.bat` scripts
- Helping a user configure dump collection for their app
- Any time a .NET process needs to produce a dump on crash

## When Not to Use

- Collecting on-demand dumps from a running process (use `dotnet-dump collect` or `procdump`)
- Analyzing an existing dump (use ClrMD, `dotnet-dump analyze`, or a debugger)

## Quick Reference

### Standard Configuration

Set these environment variables before launching the .NET process:

**Linux/macOS (bash):**
```bash
export DOTNET_DbgEnableMiniDump=1
export DOTNET_DbgMiniDumpType=4
export DOTNET_DbgMiniDumpName="dumps/%e.%p.%t.dmp"
export DOTNET_EnableCrashReport=1
export DOTNET_CreateDumpDiagnostics=1
export DOTNET_CreateDumpVerboseDiagnostics=1
```

**Windows (cmd):**
```cmd
set DOTNET_DbgEnableMiniDump=1
set DOTNET_DbgMiniDumpType=4
set DOTNET_DbgMiniDumpName=dumps\%e.%p.%t.dmp
set DOTNET_EnableCrashReport=1
set DOTNET_CreateDumpDiagnostics=1
set DOTNET_CreateDumpVerboseDiagnostics=1
```

**Windows (PowerShell):**
```powershell
$env:DOTNET_DbgEnableMiniDump = "1"
$env:DOTNET_DbgMiniDumpType = "4"
$env:DOTNET_DbgMiniDumpName = "dumps\%e.%p.%t.dmp"
$env:DOTNET_EnableCrashReport = "1"
$env:DOTNET_CreateDumpDiagnostics = "1"
$env:DOTNET_CreateDumpVerboseDiagnostics = "1"
```

### When Debugging createdump / Diagnostics Tooling

When investigating issues in createdump itself, the dump process, or diagnostics infrastructure, verbose logging to console can interfere with the tool's own output. In this case, redirect diagnostic output to a file and only enable verbose diagnostics conditionally:

```bash
export DOTNET_DbgEnableMiniDump=1
export DOTNET_DbgMiniDumpType=4
export DOTNET_DbgMiniDumpName="dumps/%e.%p.%t.dmp"
export DOTNET_EnableCrashReport=1
export DOTNET_CreateDumpDiagnostics=1
export DOTNET_CreateDumpVerboseDiagnostics=1
export DOTNET_CreateDumpLogToFile="dumps/createdump-diag.log"
```

Key differences:
- **`DOTNET_CreateDumpLogToFile`** — Redirects diagnostic output to a file instead of the crashing process's console. Essential when the console output is being parsed or when debugging the dump tooling itself.
- You can toggle `DOTNET_CreateDumpVerboseDiagnostics` off (set to 0) if the verbose output is too noisy even in the log file.

## Environment Variable Reference

| Variable | Value | Description |
|----------|-------|-------------|
| `DOTNET_DbgEnableMiniDump` | `1` | Enable dump generation on crash. Required. |
| `DOTNET_DbgMiniDumpType` | `4` | **Always use 4 (Full).** Full dumps include all memory and module images. Required for ClrMD, SOS, and single-file/NativeAOT apps. |
| `DOTNET_DbgMiniDumpName` | path | Dump output path. Supports template specifiers (see below). |
| `DOTNET_EnableCrashReport` | `1` | Generate a `.crashreport.json` alongside the dump. Not supported on Windows. |
| `DOTNET_CreateDumpDiagnostics` | `1` | Enable diagnostic logging of the dump process. |
| `DOTNET_CreateDumpVerboseDiagnostics` | `1` | Enable verbose diagnostic logging. More detail than basic diagnostics. |
| `DOTNET_CreateDumpLogToFile` | path | Redirect diagnostic messages to a file instead of the crashing app's console. |

### Path Template Specifiers

Use these in `DOTNET_DbgMiniDumpName`:

| Specifier | Value |
|-----------|-------|
| `%p` | PID of the dumped process |
| `%e` | Process executable filename |
| `%h` | Hostname |
| `%t` | Time of dump (seconds since Unix epoch) |
| `%%` | Literal `%` character |

Our standard pattern is `dumps/%e.%p.%t.dmp` — this produces unique filenames per crash and keeps them in a `dumps/` subdirectory.

### Why Always Full Dumps (Type 4)

| Type | Value | Size | Usable with ClrMD/SOS | Single-file/NativeAOT |
|------|-------|------|-----------------------|-----------------------|
| Mini | 1 | Small | Limited — missing heap | ❌ |
| Heap | 2 | Large | Yes | ❌ |
| Triage | 3 | Small | Limited — missing heap | ❌ |
| **Full** | **4** | **Largest** | **Yes** | **✅** |

Full dumps are the only type that works reliably across all scenarios:
- Required for single-file applications
- Required for NativeAOT applications
- Contains module images needed for symbol resolution
- Contains all memory needed for heap analysis

The size cost is worth it — a dump you can't analyze is worthless.

## Platform Notes

### Linux
- `DOTNET_EnableCrashReport=1` produces a `.crashreport.json` with thread/stack info — always enable it.
- The default dump path is `/tmp/coredump.<pid>` if `DOTNET_DbgMiniDumpName` is not set.
- Rename output files to `.dmp` extension if the template doesn't include it.
- Ensure the target directory exists and is writable by the process user.
- **Do NOT set `ulimit -c` or modify `/proc/sys/kernel/core_pattern`.** The .NET runtime's `createdump` tool handles dump generation entirely on its own — it does not use the kernel's core dump mechanism. Setting kernel core flags or `ulimit` is always wrong: it either has no effect (because `createdump` ignores it) or produces a second, redundant kernel core dump alongside the one `createdump` already wrote. Only use the `DOTNET_*` environment variables above.

### Windows
- `DOTNET_EnableCrashReport` is not supported — omit it or leave it set (it's ignored).
- Windows Error Reporting (WER) may also capture dumps independently.

### macOS
- Same as Linux. `DOTNET_EnableCrashReport=1` is supported.

## NativeAOT Notes (.NET 11+)

- Use `DOTNET_DbgCreateDumpToolPath` to specify the directory containing the `createdump` binary if it's not shipped with the runtime.
- Only full dumps (type 4) are supported.
