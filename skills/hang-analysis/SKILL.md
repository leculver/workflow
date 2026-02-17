---
name: hang-analysis
description: >
  Investigates a memory dump (or series of dumps) to determine why a process is hanging or unresponsive.
  Analyzes threads, locks, async state, finalizer queue, and native stacks to find deadlocks, blocked threads,
  or other causes of unresponsiveness. Use when the user says "hang analysis", "why is it hanging",
  "investigate hang", or provides a dump and says the process was unresponsive.
---

# Hang Analysis

Investigate a dump file (or series of dumps) to determine why a process appears to be hanging or unresponsive.

## When to Use

- User provides a dump and says the process was "hanging", "stuck", "frozen", "unresponsive", or similar
- User explicitly asks for "hang analysis"
- User has multiple dumps of the same process and suspects it stopped making progress

## When Not to Use

- The user wants general dump analysis without a hang suspicion (use a general dump analysis workflow instead)
- The user wants GC or memory analysis (use GC-specific tools)
- The user wants CPU profiling from an ETL trace (use CPU analysis tools)

## Inputs

| Input | Required | Description |
|-------|----------|-------------|
| dump_uri | Yes | Path to the dump file. May also be multiple paths if the user provides several dumps of the same process. |

## Workflow

### Step 1: Gather State

Call **all four** of these tools to get the baseline picture of the process:

1. **`get_basic_dump_info`** — CLR version, last event, active exceptions, GC heap size, overall health.
2. **`dump_async`** — Async state machines in flight or awaiting. Reveals async methods that never completed.
3. **`get_stack_trace`** (all threads) — Full thread stacks. The primary data source for hang analysis.
4. **`get_threads_and_locks`** — Threads, monitors held/waited, sync blocks. Reveals lock contention and deadlocks.

These four calls can be made in parallel since they are independent.

**Handling tool timeouts:** On large dumps, some of these tools may time out. A timeout does **not** mean the request failed — the server is still processing. Use this retry strategy:

1. Fire all four tools in parallel.
2. If any tool times out, **do not retry immediately**. Continue analyzing the results from the tools that succeeded.
3. After you have finished processing all successful results, retry the timed-out tool(s).
4. If a tool times out a second time, wait **120 seconds**, then retry once more.
5. If a tool times out a third time, give up on that tool. Note in your output which tool(s) failed and that the analysis is incomplete in that area.

This means you may begin Step 2 with partial data and revisit your analysis once the retried tool(s) return.

### Step 2: Analyze for Hang Causes

With the data from Step 1, look for these patterns (in priority order):

**a) Classic deadlock:**
- Thread A holds lock X, waits on lock Y; Thread B holds lock Y, waits on lock X.
- The `get_threads_and_locks` output directly shows held/waited monitors — cross-reference these.

**b) Async deadlock:**
- An async method is awaiting a result that can only be produced on the same synchronization context (e.g., UI thread blocked on `.Result` or `.Wait()` while the continuation needs to post back to that thread).
- Look for `Task.Wait()`, `Task.Result`, `GetAwaiter().GetResult()` on threads that own a synchronization context.
- Cross-reference with `dump_async` to find the other side of the await chain.

**c) Finalizer thread blocked:**
- Check the finalizer thread's stack from `get_stack_trace`.
- If the finalizer is blocked (waiting on a lock, doing a long operation, or stuck in native code), it can cause memory pressure and secondary hangs.
- `dump_finalizer_queue` can provide additional detail if the finalizer looks suspicious.

**d) Native locks and OS primitives:**
- Threads blocked on `WaitForSingleObject`, `WaitForMultipleObjects`, `EnterCriticalSection`, `RtlpWaitOnCriticalSection`, loader lock (`LdrpLoaderLock`), COM STA calls, etc.
- These won't show up in managed lock analysis — look at the native frames in `get_stack_trace`.

**e) GC suspension hang:**
- If threads are stuck in `SuspendEE` / `GCSuspendPending` / cooperative mode and the GC cannot proceed, the entire managed runtime is frozen.
- This is typically a **.NET Runtime bug**, not user code. Flag it as such.
- Look for threads that are in cooperative GC mode and executing a long-running native call without a GC-safe point.

**f) Thread pool starvation:**
- Many thread pool threads all blocked waiting on something (locks, I/O, synchronous waits).
- No available threads to process queued work items.
- `dump_async` may show many pending work items with no threads making progress.

**g) UI thread blocked (if applicable):**
- If the process has a UI thread (WPF, WinForms), check whether that thread is blocked.
- Common pattern: UI thread doing a synchronous wait (`Thread.Sleep`, `Task.Wait`, blocking I/O) or waiting on a background thread that itself needs the UI thread.

### Step 3: Check for Anomalies

Even if you found (or didn't find) a root cause, look for additional interesting findings:

- **High exception counts** — Use `dump_exceptions` if `get_basic_dump_info` reports many exceptions.
- **Unusual threads** — Threads with unexpected stacks (e.g., debugger-attached threads, injected threads, threads stuck in module load).
- **Heap indicators** — Very large GC heap, pinned object issues, or high finalization queue from `get_basic_dump_info`.
- **Multiple identical blocked stacks** — Many threads stuck at the same call site is a strong signal.

### Step 4: Multi-Dump Correlation (if multiple dumps provided)

If the user provided more than one dump:

1. Assume they share the same underlying issue.
2. Analyze the first dump fully (Steps 1–3).
3. For subsequent dumps, focus on confirming or refuting findings from the first:
   - Are the same threads still blocked in the same places? (Confirms a hang, not a transient slow path.)
   - Has progress been made? (If stacks changed, it's slow rather than hung.)
   - Are lock ownership patterns the same?
4. Use differences between dumps to strengthen or weaken your confidence.

### Step 5: Assess Non-Hang

If the process doesn't look like it's hanging:

- Inform the user that you couldn't find evidence of a hang.
- Note that you're proceeding with hang analysis anyway in case the issue is subtle.
- Suggest that if this wasn't intended, a general dump analysis might be more appropriate.

## Output Format

Present findings in this structure:

### Summary
1–3 sentences describing the issue and whether a root cause was found. Include any critical issues reported by tools.

### Findings
Up to 5 bullets summarizing the key observations.

### Root Cause Analysis
*(Only if a probable root cause was identified.)*
Detailed explanation of the deadlock, blocked thread, or hang mechanism. Include specific thread IDs, lock addresses, method names, and the chain of events that led to the hang.

### Critical Issues
*(Only if tools reported critical-severity issues.)*
Bold-titled section with details on each critical issue from tool output.

### Interesting Findings
*(Only if anomalies were found.)*
Observations that may not directly explain the hang but could be relevant to the user. The user knows their app better — reporting oddities may lead them to the root cause even if it seems unrelated to you.

### Next Steps
Actionable recommendations:
- If root cause found: how to fix it (code changes, configuration, design patterns).
- If uncertain: what data to collect next (additional dumps with time gap, ETL trace, specific logging).
- If GC suspension hang: file a runtime bug with the dump attached.

### Confidence
A score from 0–100 on how confident you are in the analysis and findings.

## Notes

- If the process looks like it's hanging due to the GC being unable to suspend a thread in Cooperative mode, this is a bug outside of the user's code. It typically happens due to a .NET Runtime bug, native handle double-free, etc. Flag this clearly.
- Remember that native code can be at fault — native locks, the loader lock, native events, etc. Don't limit your analysis to managed code.
- The user has expert knowledge of the process being debugged. Providing detailed thread stacks, lock chains, and anomalies is valuable even without a definitive root cause — it saves them investigation time.

## Validation

- [ ] All four baseline tools called (get_basic_dump_info, dump_async, get_stack_trace, get_threads_and_locks)
- [ ] Lock ownership cross-referenced for deadlock detection
- [ ] Finalizer thread status checked
- [ ] Native frames examined for OS-level blocking
- [ ] GC suspension state checked
- [ ] Output follows the specified format with all applicable sections
- [ ] Confidence level provided

## Common Pitfalls

| Pitfall | Solution |
|---------|----------|
| Only checking managed locks | Also examine native frames for `WaitForSingleObject`, `EnterCriticalSection`, loader lock, etc. |
| Ignoring async state | `dump_async` reveals async deadlocks that aren't visible from thread stacks alone |
| Missing finalizer thread issues | Always check whether the finalizer thread is blocked — it can cause cascading hangs |
| Declaring "no hang found" too early | The hang may be subtle (thread pool starvation, async deadlock). Check all patterns before concluding. |
| Ignoring GC suspension | A cooperative-mode thread preventing GC suspension freezes everything — check for `SuspendEE` |
| Not correlating multiple dumps | If multiple dumps are provided, compare them to distinguish true hangs from transient slowness |
| Reporting only the root cause | Also report anomalies and interesting findings — the user may connect dots you can't |
