---
name: local-tools
description: >
  Resolves local tool paths from config/local-tools.json. Handles lookup, search, user prompting, and
  registration in one flow. Use when any skill needs a local tool (cdb, lldb, dotnet-dump, etc.) —
  invoke this skill to get the path. Also handles "make X available" or "make X unavailable" requests.
---

# Local Tools

Resolve, search for, and register local tool paths. Single entry point for all tool resolution.

## When to Use

- Any skill needs to launch a local tool (debugger, dotnet tool, disassembler, etc.)
- User says "make X available" or "make X unavailable" to change a tool's status
- User says "where is X" or "find X" for a tool
- First-time setup on a new machine

## When Not to Use

- Tool is a GitHub MCP tool or built-in CLI command (those don't need path resolution)

## Inputs

| Input | Required | Description |
|-------|----------|-------------|
| tool | Yes | Name of the tool to resolve (e.g., `cdb`, `lldb`, `dotnet-dump`) |
| action | No | `resolve` (default), `set-available`, `set-unavailable`, `list` |
| path | No | Explicit path to register (only with `set-available`) |

## Schema: config/local-tools.json

This file is **local-only** (gitignored). It is created on first use if it doesn't exist.

```json
{
  "tools": [
    {
      "name": "cdb",
      "path": "C:\\Program Files (x86)\\Windows Kits\\10\\Debuggers\\x64\\cdb.exe",
      "available": true
    },
    {
      "name": "lldb",
      "path": "lldb",
      "available": true
    },
    {
      "name": "ghidra",
      "path": null,
      "available": false,
      "reason": "User declined installation"
    }
  ]
}
```

**Field rules:**
- `name` — canonical tool name (lowercase, no extension). Used as the lookup key.
- `path` — absolute path to the tool, OR just the tool name if it's in PATH. `null` if unavailable.
- `available` — `true` if the tool can be used, `false` if explicitly declined or not found.
- `reason` — optional, only present when `available` is `false`. Explains why.

## Workflow

### Action: `resolve` (default)

This is the main flow. Other skills call this to get a tool path.

**Step 1: Check local-tools.json**

1. Read `config/local-tools.json` from the triage repo root.
2. If the file doesn't exist, create it with an empty `{"tools": []}`.
3. Look for an entry matching `name`.

**Step 2: If found and available**

Return the path. Done.

**Step 3: If found and unavailable**

Return `null` and report: "`<tool>` is marked unavailable: `<reason>`. To re-enable, say 'make `<tool>` available'."
Do NOT prompt the user again. Do NOT search. Just skip silently.

**Step 4: If not found — search**

1. Consult [known tool hints](references/known-tools.md) for typical locations and search strategies.
2. Try the obvious first:
   - Run `which <tool>` (Linux/macOS) or `Get-Command <tool>` (Windows) to check PATH.
   - Check the platform-specific common paths from the hints file.
3. If found, register it (go to Step 6).
4. If not found, go to Step 5.

**Step 5: If search fails — ask the user**

Ask the user with choices:
- "Provide the path to `<tool>`" (freeform)
- "Install `<tool>`" (if an install method is known from the hints file)
- "`<tool>` is not available on this machine" (marks unavailable)

If the user provides a path, verify it exists. If they choose install, attempt the install using the method from the hints file, then verify. If they decline, mark unavailable with reason "User declined".

**Step 6: Register the tool**

1. Add or update the entry in `config/local-tools.json`.
2. Write the file.
3. Return the path.

### Action: `set-available`

1. If `path` is provided, set it. Otherwise, run the search flow (Steps 4–6) to find the tool.
2. Set `available: true`, remove `reason` if present.
3. Write `config/local-tools.json`.

### Action: `set-unavailable`

1. Set `available: false`, `path: null`, `reason: "Manually marked unavailable by user"`.
2. Write `config/local-tools.json`.

### Action: `list`

1. Read `config/local-tools.json`.
2. Display all registered tools with their paths and availability status.

## Validation

- [ ] `config/local-tools.json` is valid JSON after every write
- [ ] Tool paths are verified to exist before registering (for absolute paths)
- [ ] Unavailable tools are never re-prompted — just skipped
- [ ] File is gitignored (local-only)

## Common Pitfalls

| Pitfall | Solution |
|---------|----------|
| File doesn't exist yet | Create with empty `{"tools": []}` on first access |
| Tool in PATH on one machine but not another | Store just the name (e.g., `"lldb"`) — it will fail on the other machine and trigger re-search |
| User declines a tool | Mark `available: false` with reason — don't re-ask |
| Path changed after OS update | User can say "make X available" to re-trigger search |
| Concurrent writes from two sessions | Last writer wins — acceptable for a config file |
