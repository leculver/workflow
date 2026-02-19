---
name: run-lldb
description: >
  Runs LLDB commands against a memory dump or live process on Linux/macOS. Use this as a
  fallback when no existing tool or skill provides the data you need, or when a tool's output
  is insufficient and you need to dig deeper with raw debugger commands. Supports both
  interactive sessions and one-shot command execution.
---

# Run LLDB

Launch LLDB to run debugger commands against dumps or live processes.

## When to Use

- Analyzing a crash dump with native or managed commands
- Running SOS commands (clrstack, dumpheap, gcroot, etc.)
- Inspecting a live .NET process on Linux/macOS
- Any debugging task requiring LLDB when other tools/skills don't cover it

## Workflow

### Step 1: Resolve LLDB

Use the `local-tools` skill to resolve the `lldb` tool path. This handles lookup, search, user prompting, and registration automatically.

If `local-tools` reports LLDB as unavailable, stop and inform the user.

### Step 2: Ensure SOS Is Installed

SOS commands require the SOS plugin to be loaded via `~/.lldbinit`. Check if it's already configured:

```bash
grep -q "sos" ~/.lldbinit 2>/dev/null && echo "SOS configured" || echo "SOS not configured"
```

If SOS is not configured, install it:

```bash
dotnet tool install -g dotnet-sos
dotnet-sos install
```

`dotnet-sos install` writes the necessary `plugin load` line into `~/.lldbinit` so SOS loads automatically in every LLDB session. No manual `.load` commands needed after this.

### Step 3: Run Commands

There are two modes for running LLDB commands:

#### Option A: One-Shot Command (preferred for simple queries)

Run commands and exit using `--batch` and `-o` (one `-o` per command):

```bash
lldb --core dump.dmp --batch -o "clrstack" -o "quit"
```

**Capture output to a file:**
```bash
lldb --core dump.dmp --batch -o "clrstack" -o "quit" > output.txt 2>&1
cat output.txt
```

**Multiple commands:**
```bash
lldb --core dump.dmp --batch \
  -o "dumpheap -stat" \
  -o "eeheap -gc" \
  -o "quit"
```

**Attach to a live process:**
```bash
lldb -p <pid> --batch -o "clrstack" -o "detach" -o "quit"
```

#### Option B: Interactive Session (for exploration or multi-step debugging)

Use async mode when you need to inspect output and decide what to run next:

```
# Start LLDB in async mode
powershell command: 'lldb --core dump.dmp', mode: "async"

# Wait for the prompt, then send commands
write_powershell input: "clrstack{enter}", delay: 10
write_powershell input: "dumpheap -stat{enter}", delay: 15

# When done
write_powershell input: "quit{enter}", delay: 5
```

In interactive mode:
- The LLDB prompt looks like `(lldb)`
- Wait for the prompt before sending the next command
- Some commands take time on large dumps — use longer delays
- Always quit with `quit` when finished

### SOS Commands Reference

SOS commands in LLDB are invoked **without** the `!` prefix used in CDB:

| Command | Description |
|---------|-------------|
| `clrstack` | Managed call stack for current thread |
| `clrstack -all` | Managed stacks for all threads |
| `dumpheap -stat` | Heap statistics by type |
| `dumpheap -type <TypeName>` | Find objects of a specific type |
| `dumpobj <addr>` | Inspect an object |
| `gcroot <addr>` | Find what's keeping an object alive |
| `eeheap -gc` | GC heap summary |
| `clrthreads` | List managed threads |
| `pe` | Print current exception |
| `dumpstack` | Full stack (native + managed) |

### Common LLDB Native Commands

| Command | Description |
|---------|-------------|
| `bt` | Backtrace (native call stack) |
| `bt all` | Backtrace for all threads |
| `thread list` | List all threads |
| `thread select <N>` | Switch to thread N |
| `image list` | List loaded modules |
| `register read` | Display registers |
| `memory read <addr>` | Read memory at address |
| `quit` | Quit |

## Tips

- **Output can be large.** For `dumpheap -stat` or `bt all`, redirect to a file and search it.
- **SOS auto-load.** After `dotnet-sos install`, SOS loads automatically via `~/.lldbinit`. Verify with `plugin list`.
- **No `!` prefix.** Unlike CDB, SOS commands in LLDB don't use `!` — just type the command name directly.
- **Core dump extensions.** Linux core dumps may have no extension or be named `core.<pid>`. LLDB accepts any filename with `--core`.
- **Timeout.** LLDB commands on large dumps can take minutes. Use appropriate delays in async mode.
