---
name: dump-analysis
description: >
  General-purpose investigation of a memory dump to determine what went wrong in a process. Covers crashes,
  exceptions, and other non-hang non-memory issues. This is the fallback analysis skill — use hang-analysis
  for hangs/deadlocks and memory-analysis for leaks/high memory. If during investigation the issue turns out
  to be a hang or memory problem, stop and switch to the appropriate specialized skill. Use when the user
  says "analyze this dump", "what happened", "why did it crash", or provides a dump without specifying
  the problem type.
---

# Dump Analysis

Investigate a dump file (or series of dump files) to determine what went wrong in a process. This is a general-purpose analysis for crashes, exceptions, and other issues that are not specifically hangs or memory problems.

## When to Use

- User provides a dump and asks "what happened?" or "why did it crash?" without specifying the problem type
- User explicitly asks for "dump analysis"
- The issue is a crash, unhandled exception, or unexpected termination
- The problem type is unknown and needs initial triage

## When Not to Use

- The user suspects a hang, deadlock, or unresponsive process → use **`hang-analysis`** instead
- The user suspects a memory leak, high memory, or OOM → use **`memory-analysis`** instead
- The user wants CPU profiling from an ETL trace → use CPU analysis tools

## Mid-Analysis Skill Switching

**Important:** If during your investigation you discover the issue is actually a hang or memory problem, **stop your current analysis, report your preliminary findings, and tell the user to switch to the appropriate skill:**

- If you find evidence of deadlock, blocked threads, or an unresponsive process → tell the user to run **`hang-analysis`** for a deeper investigation.
- If you find evidence of memory leaks, high memory usage, excessive allocations, or OOM → tell the user to run **`memory-analysis`** for a deeper investigation.

Include whatever findings you've gathered so far so the user has context.

## Inputs

| Input | Required | Description |
|-------|----------|-------------|
| dump_uri | Yes | Path to the dump file. May also be multiple paths if the user provides several dumps. |

## Workflow

### Step 1: Gather Baseline State

Call these tools to understand the basic state of the process:

1. **`get_basic_dump_info`** — CLR version, last event, active exceptions, GC heap size, overall health.
2. **`dump_exceptions`** — All CLR exceptions on the heap with callstacks and counts. Reveals both active and historical exceptions.

These two calls can be made in parallel since they are independent.

**Handling tool timeouts:** On large dumps, some of these tools may time out. A timeout does **not** mean the request failed — the server is still processing. Use this retry strategy:

1. Fire all tools in parallel.
2. If any tool times out, **do not retry immediately**. Continue analyzing the results from the tools that succeeded.
3. After you have finished processing all successful results, retry the timed-out tool(s).
4. If a tool times out a second time, wait **120 seconds**, then retry once more.
5. If a tool times out a third time, give up on that tool. Note in your output which tool(s) failed and that the analysis is incomplete in that area.

### Step 2: Classify the Problem

Using the results from Step 1, determine the issue category:

**a) Crash / Unhandled Exception:**
- `get_basic_dump_info` reports an active exception or the last event indicates a crash.
- `dump_exceptions` shows the exception type, message, and callstack.
- Proceed to Step 3a.

**b) Hang / Deadlock:**
- `get_basic_dump_info` suggests the process is still running but not making progress.
- No crash or exception is evident.
- **Stop here.** Report your preliminary findings and tell the user to run **`hang-analysis`** for specialized investigation.

**c) Memory Issue:**
- `get_basic_dump_info` shows very large GC heap or reports `OutOfMemoryException`.
- Exceptions include memory-related types (`OutOfMemoryException`, `InsufficientMemoryException`).
- **Stop here.** Report your preliminary findings and tell the user to run **`memory-analysis`** for specialized investigation.

**d) Other / Unknown:**
- The issue doesn't clearly fit the above categories.
- Continue with general investigation in Step 3b.

### Step 3a: Crash Investigation

If the issue is a crash or unhandled exception:

1. **Examine the crashing exception** from `dump_exceptions` — type, message, inner exceptions, and full callstack.
2. **Get the crashing thread's stack** using `get_stack_trace` with the specific thread ID from `get_basic_dump_info`.
3. **Look for patterns:**
   - `NullReferenceException` — what object was null? Check the faulting method's local variables.
   - `AccessViolationException` — native code crash. Look at native frames for the faulting module.
   - `StackOverflowException` — look for recursive call patterns in the stack.
   - `TypeLoadException` / `FileNotFoundException` — assembly loading issues. Check the exception message for the missing type or file.
   - `InvalidOperationException` — often indicates state corruption or thread-safety issues.
4. **Examine related objects** using `dump_obj` on relevant addresses from the exception or stack.
5. **Check for multiple exception types** — if many different exceptions exist on the heap, the crash may be a symptom of an earlier problem.

### Step 3b: General Investigation

If the issue type is unclear:

1. **Get all thread stacks** using `get_stack_trace` (all threads) to survey what the process was doing.
2. **Get threads and locks** using `get_threads_and_locks` to check for contention.
3. **Check async state** using `dump_async` to see if async operations are stuck.
4. **Look for patterns:**
   - Are many threads doing the same thing? (Possible contention or bottleneck)
   - Are threads idle or all blocked? (Possible hang — suggest `hang-analysis`)
   - Is the heap unusually large? (Possible memory issue — suggest `memory-analysis`)
5. **Examine the heap** if something looks suspicious — use `dump_heap` for specific types.

### Step 4: Look for Anomalies

Regardless of the issue type, look for additional interesting findings:

- **High exception counts** — Many exceptions of the same type suggest a recurring problem.
- **Unusual thread stacks** — Threads doing unexpected things (debugger threads, injected threads, threads stuck in module load).
- **GC state** — Is a GC in progress? Is the heap fragmented? Are there many pinned objects?
- **Multiple identical stacks** — Many threads at the same call site can indicate a systemic issue.
- **Performance indicators** — If the issue seems performance-related rather than a crash or hang, note that ETL/trace-based investigation may be more appropriate and that there are analysis prompts available for that.

### Step 5: Multi-Dump Correlation (if multiple dumps provided)

If the user provided more than one dump:

1. Assume they share the same underlying issue.
2. Analyze the first dump fully (Steps 1–4).
3. For subsequent dumps, focus on confirming or refuting findings from the first.
4. Use differences to strengthen or weaken your confidence.

## Output Format

Present findings in this structure:

### Summary
1–3 sentences describing the issue and whether a root cause was found. Include any critical issues reported by tools.

### Findings
Up to 5 bullets summarizing the key observations.

### Root Cause Analysis
*(Only if a probable root cause was identified.)*
Detailed explanation of the crash or issue. Include specific exception types, messages, thread IDs, method names, and the chain of events. If source information is available and you are confident in the cause, suggest a code fix.

### Critical Issues
*(Only if tools reported critical-severity issues.)*
Bold-titled section with details on each critical issue from tool output.

### Interesting Findings
*(Only if anomalies were found.)*
Observations that may not directly explain the issue but could be relevant to the user. The user knows their app better — reporting oddities may lead them to the root cause even if it seems unrelated to you.

### Next Steps
Actionable recommendations:
- If root cause found: how to fix it (code changes, configuration, error handling).
- If uncertain: what data to collect next (additional dumps, ETL traces, specific logging).
- If the issue appears to be a hang or memory problem: explicitly recommend switching to the specialized skill.
- If the issue seems performance-related: suggest ETL/trace-based investigation.

### Confidence
A score from 0–100 on how confident you are in the analysis and findings.

## Notes

- This is the **general-purpose fallback** analysis. The specialized `hang-analysis` and `memory-analysis` skills will produce better results for their respective problem types. Always recommend switching when appropriate.
- Remember that async operations may contribute to hangs, so run `dump_async` when considering whether a process is hung.
- If more than one dump file is provided, assume they have the same underlying issue.
- The user has expert knowledge of the process being debugged. Providing detailed stacks, exception info, and anomalies is valuable even without a definitive root cause.
- Native code can be at fault — don't limit analysis to managed code. Check native frames in stack traces.

## Validation

- [ ] Baseline tools called (get_basic_dump_info, dump_exceptions)
- [ ] Problem classified (crash, hang, memory, or unknown)
- [ ] If hang detected: user directed to hang-analysis skill
- [ ] If memory issue detected: user directed to memory-analysis skill
- [ ] Appropriate deeper investigation performed based on classification
- [ ] Anomalies checked
- [ ] Output follows the specified format with all applicable sections
- [ ] Confidence level provided

## Common Pitfalls

| Pitfall | Solution |
|---------|----------|
| Not classifying the problem early | Always determine if this is a crash, hang, or memory issue before deep-diving — use the specialized skill if applicable |
| Ignoring exceptions on the heap | Even non-active exceptions reveal the history of problems in the process |
| Only looking at managed code | Native frames often hold the key, especially for `AccessViolationException` and crashes |
| Missing async state | `dump_async` reveals async operations that won't be visible from thread stacks alone |
| Not checking for multiple exception types | The visible crash may be a symptom of an earlier, different exception |
| Spending too long on hang/memory issues | These have specialized skills — switch early rather than doing a shallow analysis |
| Not suggesting trace-based investigation | Some issues (performance, intermittent problems) are better diagnosed with ETL traces than dumps |
