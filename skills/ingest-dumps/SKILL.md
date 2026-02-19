---
name: ingest-dumps
description: >
  Ingests dump files into long-term storage under ./dumps/ with lifecycle tracking. Detects minidump,
  ELF core, and Mach-O core files by header inspection. Asks for retention period and reminds about
  HBI/customer data policies. Creates deletion reminders via .bookkeeping/dumps.delete. Use when the
  user says "ingest dump", "store dump", "keep this dump", or "save dump for later".
---

# Ingest Dumps

Move dump files into long-term managed storage with lifecycle tracking.

## When to Use

- User has a dump file they want to keep for future analysis
- Migrating a repro dump to long-term storage ("keep this dump")
- Storing dumps received from external sources (customers, colleagues, CI)

## When Not to Use

- Generating dumps during reproduction (those stay in `repros/issue_<NUMBER>/dumps/`)
- Analyzing an existing dump (use a debugger or ClrMD)
- Configuring dump collection (use `collect-dumps`)

## Inputs

| Input | Required | Description |
|-------|----------|-------------|
| path | Yes | Path to a dump file or directory containing dump files |
| slug | No | Short description for the dump name (2-5 words, kebab-case). If omitted, ask the user. |
| retention | No | How long to keep the dump: duration (e.g., "30 days", "6 months") or "forever". If omitted, ask. |

## Workflow

### Step 0: Bookkeeping

Invoke `bookkeeping` to pull the triage repo and flush any pending `.bookkeeping/` logs from prior sessions.

### Step 1: Detect Dump Files

Run the detection script on the user-provided path:

```
python .agents/skills/ingest-dumps/scripts/detect_dumps.py <path>
```

The script inspects file headers and returns a JSON array of absolute paths to valid dump files (Windows minidump, ELF core, Mach-O core).

If no dump files are detected, tell the user and stop.

### Step 2: Confirm Ingestion

1. Report what was found: number of dump files, their names and sizes.
2. If **multiple dumps** were found, ask the user to confirm they want to ingest all of them. They will be stored together in a subdirectory.
3. If only **one dump** was found, proceed directly.

### Step 3: Get Slug

If `slug` was not provided:
1. Ask the user for a short description of what this dump is (e.g., "crash-during-gc-stress", "customer-oom-repro", "diagnostics-2515-sof").
2. Convert to kebab-case, 2-5 words.

### Step 4: Get Retention Period

If `retention` was not provided:
1. Ask the user how long to keep the dump.
2. **Remind them:** Dumps containing HBI (high business impact) data, customer data, or similar sensitive information **must** be deleted after use per company policy.
3. Offer choices:
   - "30 days"
   - "90 days"
   - "6 months"
   - "Forever (no sensitive data)"
4. "Forever" is valid — it means the dump has no sensitive data and can be kept indefinitely.

### Step 5: Copy and Rename

Determine the destination based on the number of dumps:

**Single dump:**
```
./dumps/YYYY-MM-DD_<slug>.dmp
```

**Multiple dumps:**
```
./dumps/YYYY-MM-DD_<slug>/
  ├── <original-name-1>.dmp
  ├── <original-name-2>.dmp
  └── ...
```

Rules:
1. Create the `./dumps/` directory if it doesn't exist.
2. **Always rename** the dump file to have a `.dmp` extension if it doesn't already. This ensures `.gitignore` rules work.
3. **Move** (not copy) the files to the destination. Do not leave originals behind. Use a safe two-step move: copy first, verify the destination file size matches, then delete the original.
4. For multiple dumps in a subdirectory, preserve original filenames (with `.dmp` extension fix).
5. Use today's date for the `YYYY-MM-DD` prefix.

### Step 6: Create Deletion Reminder (if not forever)

If the retention period is not "forever":

1. Calculate `delete_after` as the current timestamp plus the retention duration.
2. Read `.bookkeeping/dumps.delete` if it exists (JSON array), or start with an empty array.
3. Create the `.bookkeeping/` directory at repo root if it doesn't exist.
4. Append a new entry:
   ```json
   {
     "path": "<absolute path to the dump file or directory>",
     "ingested_at": "<current ISO 8601 timestamp>",
     "file_timestamp": "<oldest file modification time among ingested dumps>",
     "delete_after": "<calculated deletion timestamp>"
   }
   ```
5. For multi-dump directories, `path` points to the directory and `file_timestamp` is the oldest dump's modification time.
6. Write the updated array back to `.bookkeeping/dumps.delete`.

**Important:** Remind the user that this workflow is **not responsible** for deleting the dump when the time comes. This is a reminder system to help them remember — the bookkeeping skill will prompt them when the retention period expires, but will never auto-delete.

### Step 7: Confirm

Report to the user:
- Where the dump was stored
- The retention period and when the reminder will fire (or "forever" if no reminder)
- A reminder that `.bookkeeping/` tracks the deletion schedule and `bookkeeping` will prompt when it's time

## Validation

- [ ] Dump files were detected by header inspection (not just extension)
- [ ] Files copied to `./dumps/` with `.dmp` extension
- [ ] Slug follows `YYYY-MM-DD_<kebab-case>` convention
- [ ] `.bookkeeping/dumps.delete` updated with correct timestamps (unless forever)
- [ ] User was reminded about HBI/customer data policy
- [ ] User was reminded this is a reminder system, not enforcement

## Common Pitfalls

| Pitfall | Solution |
|---------|----------|
| File isn't actually a dump | The detection script checks headers — don't skip it |
| Missing `.dmp` extension | Always rename to `.dmp` regardless of original extension |
| Forgetting HBI reminder | Always mention data retention policy when asking for retention period |
| Auto-deleting dumps | NEVER auto-delete — the system only reminds |
| Leaving originals behind | Always move — copy, verify size, then delete original |
| Deleting before verifying | Always verify destination file size matches source before deleting original |
| Confusing with repro dumps | Repro dumps stay in `repros/issue_<NUMBER>/dumps/` — this skill is for long-term storage only |
| Single file in subdirectory | Single dumps are flat files, not in a subdirectory |
