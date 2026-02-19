---
name: run-cdb
description: >
  Runs CDB (Windows debugger) commands against a memory dump or live process. Use this as a
  fallback when no existing tool or skill provides the data you need, or when a tool's output
  is insufficient and you need to dig deeper with raw debugger commands. Supports both
  interactive sessions and one-shot command execution.
---

# Run CDB

Launch CDB to run debugger commands against dumps or live processes.

## When to Use

- Analyzing a crash dump with native or managed commands
- Running SOS commands (!clrstack, !dumpheap, !gcroot, etc.)
- Inspecting a live .NET process
- Any Windows debugging task requiring CDB

## Workflow

### Step 1: Resolve CDB

Use the `local-tools` skill to resolve the `cdb` tool path. This handles lookup, search, user prompting, and registration automatically.

If `local-tools` reports CDB as unavailable, stop and inform the user.

### Step 2: Run Commands

There are two modes for running CDB commands:

#### Option A: One-Shot Command (preferred for simple queries)

Run a single command and exit. Use `-z` for dumps, `-c` for commands, `-logo` for output capture:

```powershell
& $cdb -z "path\to\dump.dmp" -logo "output.txt" -c "!clrstack; q"
Get-Content "output.txt"
```

The command string passed to `-c` is a semicolon-separated list of debugger commands. Always end with `q` to quit CDB. SOS commands should work immediately if SOS is installed — no manual loading needed.

**Pattern for multiple commands:**
```powershell
& $cdb -z "dump.dmp" -logo "output.txt" -c "!dumpheap -stat; !eeheap -gc; q"
```

**Pattern for commands with arguments containing spaces:**
```powershell
& $cdb -z "dump.dmp" -logo "output.txt" -c "!dumpheap -type System.String; q"
```

#### Option B: Interactive Session (for exploration or multi-step debugging)

Use async mode when you need to inspect output and decide what to run next:

```
# Start CDB in async mode
powershell command: '& $cdb -z "path\to\dump.dmp"', mode: "async"

# Wait for the prompt, then send commands
write_powershell input: ".loadby sos coreclr{enter}", delay: 10
write_powershell input: "!clrstack{enter}", delay: 10
write_powershell input: "!dumpheap -stat{enter}", delay: 15

# When done
write_powershell input: "q{enter}", delay: 5
```

In interactive mode:
- CDB prompts look like `0:000>` or similar
- Wait for the prompt before sending the next command
- Some commands (like `!dumpheap`) take time — use longer delays
- Always quit with `q` when finished

### Step 3: SOS for Managed Debugging

SOS (Son of Strike) provides managed debugging commands. **CDB should load SOS automatically** when it detects a .NET process or dump — you typically don't need to do anything.

If SOS is not loaded (managed commands like `!clrstack` fail), install it:

```powershell
dotnet tool install -g dotnet-sos
dotnet-sos install
```

The output of `dotnet-sos install` tells you the path where SOS was installed. Use that path to load it manually in CDB:

```
.load C:\path\from\dotnet-sos\output\sos.dll
```

Verify SOS is loaded with `.chain` — it should appear in the extension DLL list.

Once loaded, common SOS commands:

| Command | Description |
|---------|-------------|
| `!clrstack` | Managed call stack for current thread |
| `!clrstack -all` | Managed stacks for all threads |
| `!dumpheap -stat` | Heap statistics by type |
| `!dumpheap -type <TypeName>` | Find objects of a specific type |
| `!dumpobj <addr>` | Inspect an object |
| `!gcroot <addr>` | Find what's keeping an object alive |
| `!eeheap -gc` | GC heap summary |
| `!threads` | List managed threads |
| `!pe` | Print current exception |
| `!dumpstack` | Full stack (native + managed) |

### Common CDB Native Commands

| Command | Description |
|---------|-------------|
| `~*k` | Native call stacks for all threads |
| `~Ns` | Switch to thread N |
| `lm` | List loaded modules |
| `!address -summary` | Virtual memory summary |
| `.ecxr` | Switch to exception context record |
| `r` | Display registers |
| `q` | Quit |

## Tips

- **Output can be large.** For `!dumpheap -stat` or `~*k`, use `-logo` to capture to a file, then read/search the file.
- **SOS auto-load.** SOS should load automatically. If it doesn't, run `dotnet-sos install` and load manually. Check with `.chain` to see loaded extensions.
- **Symbol path.** Set `_NT_SYMBOL_PATH` before launching CDB if symbols aren't resolving:
  ```
  set _NT_SYMBOL_PATH=srv*C:\symbols*https://msdl.microsoft.com/download/symbols
  ```
- **Timeout.** CDB commands on large dumps can take minutes. Use appropriate delays in async mode.
- **Local SOS.** If you need a locally built SOS instead of the installed one, use the `use-local-sos` skill.
