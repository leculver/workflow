---
name: use-local-sos
description: >
  Configures CDB to use a locally built SOS and optionally a local DAC from the diagnostics repo.
  Windows only. Handles unloading pre-loaded SOS, loading the local build, and verifying via .chain.
  Use when debugging with CDB and you need the locally built SOS instead of the one CDB auto-loads.
---

# Use Local SOS

Unload the pre-loaded SOS from CDB and load the locally built one from the diagnostics repo.

## When to Use

- Debugging a dump or live process with CDB and you want the locally built SOS
- CDB auto-loaded an SOS from a different branch or runtime version
- You need a locally built DAC (mscordaccore.dll) for a specific runtime version
- Any time an SOS command is about to be run in CDB during triage or investigation

## When Not to Use

- On Linux/macOS (this is Windows + CDB only)
- Using lldb (lldb has a different SOS loading mechanism)
- The system SOS is acceptable (no local changes needed)

## Inputs

| Input | Required | Description |
|-------|----------|-------------|
| diagnostics_path | No | Path to the diagnostics repo checkout (default: `./diagnostics` or infer from config) |
| config | No | Build configuration: `Debug` (default) or `Release` |
| arch | No | Architecture: `x64` (default) or `x86` |
| dac_path | No | Path to directory containing a local `mscordaccore.dll`. Only needed when using a locally built runtime or a DAC that doesn't match the dump's runtime version. If omitted, DAC loading is skipped. |

## Paths

The locally built SOS is at:

```
<diagnostics_path>\artifacts\bin\Windows_NT.<arch>.<config>\sos.dll
```

Examples:
- `diagnostics\artifacts\bin\Windows_NT.x64.Debug\sos.dll`
- `diagnostics\artifacts\bin\Windows_NT.x86.Release\sos.dll`

Before using this skill, verify the SOS DLL exists at the expected path. If it doesn't, tell the user to build the diagnostics repo first.

## Workflow

### Step 0: Resolve Tools

Use `local-tools` to resolve the `cdb` path.

### Step 1: Determine SOS Path

1. Resolve `diagnostics_path` — from input, or `./diagnostics`, or from `config/repos.json`.
2. Build the SOS path: `<diagnostics_path>\artifacts\bin\Windows_NT.<arch>.<config>\sos.dll`
3. Verify the file exists. If not, tell the user: "SOS not found at `<path>`. Build with `build.cmd` first."

### Step 2: Choose Mode

**Use non-interactive mode** (`cdb -z <dump> -c "cmds;qq"`) for scripted test runs — running commands and checking results. Pipe output to a file and use `Select-String` to validate. This is the default for any automated or scripted work.

**Only use interactive mode** when you need to inspect results and decide next steps dynamically — exploratory debugging where the next command depends on what you see.

### Step 3: Interactive CDB Session

When running CDB interactively (e.g., attached to a dump for exploratory debugging):

**Before running ANY SOS command**, execute these steps in order:

```
.unload sos
.cordll -ve -u -lp <dac_directory>
.load <sos_path>
.chain
```

1. **`.unload sos`** — Remove the pre-loaded SOS. This is **critical** and must happen FIRST, before any `!command`. If SOS was not loaded, cdb will say so — that's fine, ignore the error.
2. **`.cordll -ve -u -lp <dac_directory>`** — Only if `dac_path` is provided. `-ve` enables verbose output, `-u` unloads the current DAC first, `-lp` sets the load path. This must happen before `.load sos` so the DAC is available when SOS initializes.
3. **`.load <sos_path>`** — Load our locally built SOS.
4. **`.chain`** — Verify the loaded extensions. **Check that our SOS is the only one loaded.** If you see another SOS in the chain, `.unload` it and retry.

After this, SOS commands (`!clrstack`, `!dumpheap`, `!dumpobj`, etc.) will use the local build.

### Step 4: Non-Interactive CDB (Quick Commands)

When running CDB non-interactively to capture output of a single command:

```
<cdb> -z <dump_path> -c ".unload sos;.cordll -ve -u -lp <dac_directory>;.load <sos_path>;.chain;!<COMMAND>;qq"
```

If no local DAC is needed, omit the `.cordll` portion:

```
<cdb> -z <dump_path> -c ".unload sos;.load <sos_path>;.chain;!<COMMAND>;qq"
```

**Output handling:** CDB output is verbose — debugger gallery init, symbol path, module loads, etc. Pipe to a file and use `Select-String` to validate results rather than reading raw output:

```powershell
& <cdb> -z <dump> -c ".unload sos;.load <sos_path>;.chain;!clrstack;qq" | Out-File cdb_output.txt
Select-String -Path cdb_output.txt -Pattern "sos\.dll" # verify .chain
Select-String -Path cdb_output.txt -Pattern "!clrstack" # find command output
```

**After capturing output:**
1. Parse the `.chain` output from the result.
2. Verify our SOS is listed and is the **only** SOS loaded.
3. If another SOS appears in `.chain`, **reject the output** — it may have used the wrong SOS. Fall back to interactive mode (Step 3) to manually unload the stale one.

`qq` quits CDB. Use `q` if you want CDB to terminate the target too (live debugging only — never with dumps).

### Step 5: Verify SOS Version

After loading, run `!soshelp` or check the `.chain` output path to confirm the loaded SOS matches the expected build path. This catches cases where `.load` silently loaded a cached version.

## Validation

- [ ] Pre-loaded SOS is unloaded before any SOS command runs
- [ ] `.cordll -ve -u -lp` is used when a local DAC is needed (before `.load sos`)
- [ ] `.chain` shows only our locally built SOS
- [ ] Non-interactive mode output is rejected if `.chain` shows multiple SOS instances
- [ ] SOS DLL path is verified to exist before attempting load

## Common Pitfalls

| Pitfall | Solution |
|---------|----------|
| Running `!clrstack` before unloading pre-loaded SOS | ALWAYS unload first — the pre-loaded SOS will answer the command and you'll get results from the wrong version |
| `.load` succeeds but wrong SOS is active | Check `.chain` — there may be two loaded. Unload the other one. |
| DAC version mismatch | Use `.cordll -ve -u -lp <path>` to point to the correct DAC directory |
| SOS DLL doesn't exist | User needs to build: `cd diagnostics && build.cmd` |
| Non-interactive `.chain` shows two SOS | Reject the output and retry interactively — the pre-loaded SOS may have handled the command |
| x86 vs x64 mismatch | Match the architecture to the dump's target architecture, not the host |
