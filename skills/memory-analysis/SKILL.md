---
name: memory-analysis
description: >
  Investigates a memory dump (or pair of dumps) to determine why a process has high memory usage, a memory leak,
  or memory-related anti-patterns. Analyzes managed heap, native memory, virtual address space, finalizer queue,
  and GC root chains to find leaks, excessive allocations, or retention issues. Use when the user says
  "memory analysis", "memory leak", "high memory", "OOM", "OutOfMemoryException", or provides a dump and
  describes memory-related symptoms.
---

# Memory Analysis

Investigate a dump file (or pair of dumps) to determine why a process has high memory usage, a memory leak, or exhibits memory-related anti-patterns such as OutOfMemoryException or unexpectedly high resource consumption.

## When to Use

- User provides a dump and says the process has "high memory", "memory leak", "OOM", or similar
- User explicitly asks for "memory analysis"
- User has a before/after pair of dumps and wants to understand memory growth
- User reports `OutOfMemoryException` or unexpected memory pressure

## When Not to Use

- The user wants hang or deadlock analysis (use `hang-analysis` instead)
- The user wants CPU profiling from an ETL trace (use CPU analysis tools)
- The user wants general dump analysis without memory suspicion (use `dump-analysis` instead)

## Inputs

| Input | Required | Description |
|-------|----------|-------------|
| dump_uri | Yes | Path to the dump file. |
| dump2_uri | No | Optional second dump file for before/after comparison. |

## Workflow

### Step 1: Gather Baseline State

Call these tools to get the baseline picture of memory in the process:

1. **`get_basic_dump_info`** — CLR version, last event, active exceptions, GC heap size, overall health.
2. **`get_virtual_address_usage`** — Virtual memory breakdown by kind. Distinguishes native heap from GC heap and identifies the largest memory consumers.
3. **`get_gc_heap_statistics`** — Top types by size on the managed GC heap. Efficient overview of where managed memory lives.
4. **`dump_finalizer_queue`** — Finalizer thread stack and finalizable objects. Reveals blocked finalizers and objects awaiting finalization.

These four calls can be made in parallel since they are independent.

If a second dump file was provided, run the same tools on the second dump in parallel as well. Any tools that accept two dump files should be prioritized over running single-dump tools separately and comparing.

**Handling tool timeouts:** On large dumps, some of these tools may time out. A timeout does **not** mean the request failed — the server is still processing. Use this retry strategy:

1. Fire all tools in parallel.
2. If any tool times out, **do not retry immediately**. Continue analyzing the results from the tools that succeeded.
3. After you have finished processing all successful results, retry the timed-out tool(s).
4. If a tool times out a second time, wait **120 seconds**, then retry once more.
5. If a tool times out a third time, give up on that tool. Note in your output which tool(s) failed and that the analysis is incomplete in that area.

This means you may begin Step 2 with partial data and revisit your analysis once the retried tool(s) return.

### Step 2: Determine Managed vs. Native Memory Problem

Using the results from Step 1:

**a) Check virtual address breakdown:**
- If `get_virtual_address_usage` reports "Heap" as the largest consumer, this means the **native** (win32/glibc) heap, not managed memory. Managed memory is reported under "GC Heap".
- Compare GC Heap size vs. native Heap size vs. total commit to understand where memory is going.

**b) If managed memory dominates:**
- Use `get_gc_heap_statistics` results to identify the top types by size.
- Use `dump_heap` on suspicious types to find individual objects and their counts.
- Use `gc_root_for_type` to find what is rooting high-memory types and preventing collection.
- Look for types with abnormally high counts or sizes relative to what you'd expect.

**c) If native memory dominates:**
- Note that native leaks can be caused by managed code holding native resources (e.g., undisposed certificates, COM objects, SafeHandles).
- Check for managed types that wrap native resources (certificates, streams, handles) using `dump_heap`.
- `get_virtual_address_usage` is the primary tool for native memory investigation.
- Use the debugger (cdb or lldb) to check for heap fragmenetation.

**d) Mixed scenarios:**
- Native and managed memory can be related. A managed object may pin or reference native memory.
- Always check both sides before concluding.

### Step 3: Look for Common Anti-Patterns

Check for these known memory anti-patterns:

**a) Blocked finalizer thread:**
- If the finalizer thread stack shows it is blocked (waiting on a lock, stuck in native code, etc.), objects in the finalization queue cannot be reclaimed.
- This causes memory to grow indefinitely even though objects are unreachable.

**b) Excessive finalizable objects:**
- A very high count of finalizable objects suggests types implementing finalizers are being created faster than they can be finalized.
- Common with undisposed `IDisposable` types.

**c) Certificate leaks:**
- `X509Certificate2` and related types that are not disposed can hold significant native memory.
- Look for high counts of certificate-related types.

**d) Pinned objects:**
- Pinned objects prevent GC heap compaction and can cause fragmentation.
- Look for pinned object indicators in `get_basic_dump_info` or `get_gc_heap_statistics`.

**e) Large object heap (LOH) fragmentation:**
- Large objects (>85KB) go to the LOH which is not compacted by default.
- Frequent allocation and deallocation of large objects causes fragmentation.

**f) Event handler leaks:**
- Objects rooted through event subscriptions that were never unsubscribed.
- `gc_root_for_type` can reveal unexpected rooting through delegates and event handlers.

**g) Static collections growing unbounded:**
- Static `Dictionary`, `List`, `ConcurrentDictionary`, or cache objects that grow without eviction.
- Look for large collections rooted through static fields.

### Step 4: Deep Dive

Based on findings so far, perform targeted investigation:

- Use `dump_heap` with `dumpObjects: true` on specific suspicious types to see individual object contents.
- Use `gc_root_for_type` on the most suspicious types to trace rooting chains.
- Use `dump_obj` on specific object addresses to examine fields and values.
- If exceptions are present, use `dump_exceptions` to see if memory-related exceptions exist.

### Step 5: Multi-Dump Comparison (if two dumps provided)

If the user provided two dumps:

1. Assume they share the same underlying issue (typically a before/after or growth scenario).
2. Compare the top types by size between the two dumps.
3. Look for types whose count or total size grew significantly.
4. Types that grew proportionally to overall memory growth are the most likely leak sources.
5. Use differences to strengthen or weaken your confidence in root cause.

### Step 6: Sanity Check

**This is critical.** With all knowledge gathered:

1. Do rough calculations: add up the memory attributed to identified problems.
2. Ask yourself: does this account for the memory usage you're seeing?
3. If the identified issues only explain a fraction of the total memory, acknowledge the gap and note what remains unexplained.
4. Incorporate this accounting into your confidence level.

## Output Format

Present findings in this structure:

### Summary
1–3 sentences describing the issue and whether a root cause was found. Include any critical issues reported by tools.

### Findings
Up to 5 bullets summarizing the key observations.

### Root Cause Analysis
*(Only if a probable root cause was identified.)*
Detailed explanation of the memory issue — what types are leaking, what is rooting them, why they aren't being collected, and rough quantification of how much memory they account for.

### Critical Issues
*(Only if tools reported critical-severity issues.)*
Bold-titled section with details on each critical issue from tool output.

### Interesting Findings
*(Only if anomalies were found.)*
Observations that may not directly explain the memory issue but could be relevant to the user. The user knows their app better — reporting oddities may lead them to the root cause even if it seems unrelated to you.

### Next Steps
Actionable recommendations:
- If root cause found: how to fix it (dispose patterns, removing static references, configuration changes).
- If uncertain: what data to collect next (second dump after more time, ETL trace for allocation tracking, specific logging).
- Consider whether trace-based investigation (ETL) would complement dump analysis.

### Confidence
A score from 0–100 on how confident you are in the analysis and findings.

## Notes

- "Folded" memory: Some tools produce folded memory views. Objects with only a single parent are folded into the parent's size. For example, Object A (0x20) with sole child Object B (0x10) shows as Object A (0x30) in the folded view.
- `dump_finalizer_queue` provides both the finalizer thread callstack and the list of finalizable objects.
- Remember that some issues are better solved with dump files, and some may be better suited to trace-based investigations. When suggesting follow-ups, consider both possibilities.
- Native memory issues are often harder to diagnose from a dump alone. If native heap dominates and you can't identify the cause, suggest native memory profiling tools.
- The user has expert knowledge of the process being debugged. Providing detailed type breakdowns, rooting chains, and anomalies is valuable even without a definitive root cause.

## Validation

- [ ] Baseline tools called (get_basic_dump_info, get_virtual_address_usage, get_gc_heap_statistics, dump_finalizer_queue)
- [ ] Managed vs. native memory determination made
- [ ] Common anti-patterns checked (blocked finalizer, excessive finalizable objects, certificate leaks, pinned objects, LOH fragmentation, event handler leaks, static collections)
- [ ] Rooting chains examined for suspicious types (gc_root_for_type)
- [ ] Sanity check performed: do identified issues account for observed memory?
- [ ] Output follows the specified format with all applicable sections
- [ ] Confidence level provided

## Common Pitfalls

| Pitfall | Solution |
|---------|----------|
| Assuming all memory is managed | Always check `get_virtual_address_usage` first — native heap may dominate |
| Ignoring the finalizer thread | A blocked finalizer causes cascading memory growth — always check its state |
| Not quantifying findings | Rough-calculate whether identified issues account for the observed memory; report gaps |
| Missing native resources held by managed objects | Check for undisposed certificates, COM objects, SafeHandles wrapping native memory |
| Only looking at object count | Total size matters more than count — a few large objects can outweigh millions of small ones |
| Not checking rooting chains | High-count types aren't leaks unless they're unexpectedly rooted — use `gc_root_for_type` |
| Ignoring LOH fragmentation | Large object allocations can waste significant memory through fragmentation even if objects are freed |
| Not comparing dumps when available | Two dumps make leak identification much more reliable — compare type growth between them |
