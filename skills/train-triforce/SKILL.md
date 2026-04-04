---
name: train-triforce
description: >
  Launches a training run for the Triforce deep RL project inside a tmux "training" session with
  tensorboard and a spare console. Detects running train.py processes and offers graceful shutdown
  (q → q → 2-min kill timeout). Use when the user says "train", "start training", "run training",
  or names a scenario/circuit to train on.
---

# Train Triforce

Launch (or restart) a training run for the Triforce Zelda RL agent. Sets up a tmux session with
three panes: training output (top), tensorboard (bottom-left), and a venv console (bottom-right).

## When to Use

- User wants to train a scenario or circuit (e.g., "train dungeon1-circuit", "start training overworld-room-walk")
- User says "start training", "run training", "train on X"
- User wants to restart or stop a running training session

## When Not to Use

- Evaluating a trained model — use `evaluate.py` directly
- Debugging training with the Qt GUI — use `debug.py`
- Investigating a GitHub issue — use `diagnose-and-fix`

## Inputs

| Input | Required | Description |
|-------|----------|-------------|
| scenario | No | The scenario or circuit name to train on (first positional arg to `train.py`). Default: `all-items-circuit`. |
| action_space | No | Action space name. Default: `all-items`. Options: `basic`, `move-only`, `all-items`. |
| model_kind | No | Model architecture. Default: `impala-multihead`. Options: `shared-nature`, `multihead`, `impala-shared`, `impala-multihead`. |
| extra_args | No | Any additional CLI flags for train.py (see reference below). |

## train.py Argument Reference

Positional (order matters):
1. `scenario` — scenario or circuit name (required)
2. `action_space` — action space name (optional, default: `all-items`)
3. `model_kind` — model kind name (optional, default: `impala-multihead`)

Named flags:
| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--output DIR` | str | `training` | Base output directory |
| `--iterations N` | int | per-scenario | Override iteration count |
| `--parallel N` | int | 16 | Number of parallel environments |
| `--load PATH` | str | — | Load a model checkpoint to continue training |
| `--resume` | flag | — | Resume circuit from saved position in `--load` checkpoint |
| `--skip-to SCENARIO` | str | — | Skip circuit legs until reaching SCENARIO |
| `--evaluate N` | int | — | Run N eval episodes after training |
| `--ent-coef F` | float | — | Entropy coefficient for PPO |
| `--frame-stack N` | int | — | Number of frames to stack |
| `--device cpu\|cuda` | str | auto | Device to use |
| `--render-mode MODE` | str | — | Render mode |
| `--obs-kind KIND` | str | auto | Observation kind: `viewport`, `gameplay`, `full-rgb` |
| `--verbose N` | int | 0 | Verbosity level |
| `--hook-exceptions` | flag | — | Dump tracebacks on unhandled exceptions |
| `--profile N` | int | — | Profile N env steps after 20K warmup, save to `training.prof`, exit |

## Available Scenarios and Circuits

### Training Circuits (curriculum sequences)
- `main-circuit` — Room nav → sword → overworld → dungeon1 → full game
- `dungeon1-circuit` — Dungeon room walk → entry → side rooms → wallmasters → full dungeon1
- `all-items-circuit` — All-items curriculum: room walk → skip-sword → dungeon1 → full game (all with items)
- `polish` — Weighted mix: 92% full-game, 5% dungeon1, 2% wallmaster, 1% sword
- `learn-items` — Weighted mix to teach item usage while retaining basics
- `dungeon1-with-wallmasters` — Dungeon1 + wallmaster focus
- `all-items-polish` — Polish with all items
- `dungeon1-dungeon2` — Dungeon1 then dungeon2 curriculum
- `skip-sword-to-triforce` — End-to-end from skip-sword through full game

### Individual Scenarios
- `overworld-room-walk` — Learn to walk through rooms correctly
- `overworld-sword` — Navigate to sword cave and pick up sword
- `overworld-skip-sword` — Overworld navigation, starting with sword
- `overworld-skip-sword-all-items` — Same but with all items available
- `overworld-skip-sword-finite-bombs` — Same but with finite bombs
- `dungeon1` — Full dungeon 1 completion
- `dungeon1-entry-room` — Just the dungeon1 entry room
- `dungeon1-side-room-opening` — Dungeon1 side room training
- `dungeon1-wallmaster` — Wallmaster-specific training
- `dungeon1-room-walk` — Walk through dungeon rooms
- `dungeon1-skip-opening` — Dungeon1 skipping the opening
- `dungeon1-all-items` — Dungeon1 with all items
- `dungeon1-finite-bombs` — Dungeon1 with finite bombs
- `full-game` — Full game from start to triforce
- `full-game-all-items` — Full game with all items
- `full-game-all-items-finite` — Full game with finite items
- `check-for-reward-hacking` — Diagnostic scenario for reward hacking detection
- `no-end-conditions` — Free play with no end conditions

## Training Output Layout

Training runs are saved under `~/work/git/triforce/training/`:

```
training/
  <scenario>/
    0/                    ← run #0
      checkpoints/        ← periodic checkpoint .pt files
        *.pt
      logs/               ← tensorboard logs
    1/                    ← run #1 (next run auto-increments)
      checkpoints/
      logs/
      *.pt                ← final model saved at run root when training completes
```

- **Partial runs**: checkpoints in `training/<scenario>/<run#>/checkpoints/*.pt`
- **Completed runs**: final model at `training/<scenario>/<run#>/*.pt`
- To resume a partial run, use `--load training/<scenario>/<run#>/checkpoints/<latest>.pt --resume`

## Workflow

### Step 0: Search for Resumable Checkpoints

Before starting a fresh training run, check if any saved checkpoints in `models/` **and** `training/` can give us a head start. Each `.pt` file contains a `training_history` list describing what scenarios it was already trained on. Training checkpoints from partial runs are often further along than models/, so both must be scanned.

**Scan `models/` and `training/` for compatible checkpoints:**

```bash
cd ~/work/git/triforce && source .venv/bin/activate && python3 -c "
import torch, os, sys, glob
from triforce.scenario_wrapper import TrainingCircuitDefinition

circuit_name = sys.argv[1]
circuit_def = TrainingCircuitDefinition.get(circuit_name)
if circuit_def is None:
    print(f'Not a circuit: {circuit_name}')
    sys.exit(0)

# Build ordered list of scenario names in the target circuit
circuit_scenarios = []
for entry in circuit_def.scenarios:
    if entry.circuit:
        circuit_scenarios.append(f'[circuit] {entry.circuit}')
    else:
        circuit_scenarios.append(entry.scenario)

print(f'Circuit legs: {circuit_scenarios}')
print()

def scan_checkpoint(path, best_match, best_count, best_steps):
    try:
        data = torch.load(path, weights_only=False)
    except Exception:
        return best_match, best_count, best_steps
    history = data.get('training_history') or []
    steps = data.get('steps_trained', 0)
    if not history:
        return best_match, best_count, best_steps

    match_count = 0
    for i, leg in enumerate(circuit_scenarios):
        if i >= len(history):
            break
        if history[i].get('scenario') == leg:
            match_count += 1
        else:
            break

    if match_count > 0:
        em = history[match_count - 1].get('exit_metric', {})
        metric_str = f\"{em.get('name')}: {em.get('actual')}\" if em.get('name') else 'no metric'
        print(f'{path}: covers {match_count}/{len(circuit_scenarios)} legs, steps={steps} ({metric_str})')
        if match_count > best_count or (match_count == best_count and steps > best_steps):
            best_count = match_count
            best_match = path
            best_steps = steps

    return best_match, best_count, best_steps

best_match = None
best_count = 0
best_steps = 0

# Scan models/
if os.path.isdir('models'):
    for f in sorted(os.listdir('models')):
        if f.endswith('.pt'):
            best_match, best_count, best_steps = scan_checkpoint(
                os.path.join('models', f), best_match, best_count, best_steps)

# Scan training/ (partial runs often have more progress)
for pt_file in sorted(glob.glob('training/**/*.pt', recursive=True), key=os.path.getmtime, reverse=True):
    best_match, best_count, best_steps = scan_checkpoint(pt_file, best_match, best_count, best_steps)

if best_match:
    print(f'\nBest resumable checkpoint: {best_match} ({best_count} legs, {best_steps} steps)')
else:
    print('\nNo resumable checkpoints found — training from scratch.')
" "<scenario>"
```

Replace `<scenario>` with the target circuit name (e.g., `all-items-circuit`).

**Decision logic:**
- If a resumable checkpoint is found, **ask the user**: "Found `<checkpoint>` covering N of M legs (last: `<scenario>` with `<metric>: <value>`). Resume from there or train from scratch?"
- If the user wants to resume, add `--load <checkpoint> --resume` to the training command.
- If no checkpoint matches or the user declines, train from scratch.

**What makes a good match:**
- The checkpoint's `training_history` scenarios must match the **first N legs** of the target circuit **in order**.
- More matched legs = more time saved (each leg can take hours).
- The exit metrics in the history show whether each leg met its threshold — prefer checkpoints where metrics were met.

### Step 1: Check for Running Training

Check if a `train.py` process is already running:

```bash
pgrep -f 'train\.py' -a
```

If a training process is found:
1. **Ask the user** whether they want to stop it and start a new run, or leave it running.
2. If they want to stop it, proceed to Step 2. Otherwise, stop — do not start a second training run.

### Step 2: Gracefully Stop Existing Training (if needed)

First, detect the tmux window number (varies depending on `base-index` config):

```bash
WIN=$(tmux list-windows -t training -F '#{window_index}' 2>/dev/null | head -1)
```

If `$WIN` is non-empty and a training session exists, use the TUI's `q` keypress to stop gracefully:

1. Send `q` twice to trigger shutdown:
   ```bash
   tmux send-keys -t training:${WIN}.0 q
   sleep 1
   tmux send-keys -t training:${WIN}.0 q
   ```
2. Wait up to **2 minutes** for the process to exit. Poll every 5 seconds:
   ```bash
   pgrep -f 'train\.py'
   ```
3. If the process is still running after 2 minutes, **kill it by PID**:
   ```bash
   kill <PID>   # use the PID from pgrep output
   ```
4. Wait a few seconds and verify it's dead. If it's still running, use `kill -9 <PID>`.

If no tmux session exists but `train.py` is running anyway, skip straight to `kill <PID>`.

### Step 3: Reuse or Create the tmux Session

Check if the "training" tmux session exists:

```bash
tmux has-session -t training 2>/dev/null
```

**If the session already exists — reuse it.** The tensorboard and console panes are long-lived and don't need
to be recreated. Detect the window number and skip to Step 7 to launch the new training command in the top pane:

```bash
WIN=$(tmux list-windows -t training -F '#{window_index}' | head -1)
# Now use training:${WIN}.0 for the top pane, .1 for tensorboard, .2 for console
```

**If the session does NOT exist**, create it and set up the full layout (Steps 4–6):

```bash
tmux new-session -d -s training -x 200 -y 50
```

Then detect the window number for subsequent pane references:

```bash
WIN=$(tmux list-windows -t training -F '#{window_index}' | head -1)
```

### Step 4: Set Up the Pane Layout (new session only)

Split into three panes — training (top), tensorboard (bottom-left), console (bottom-right):

```bash
tmux split-window -v -t training:${WIN}.0
tmux split-window -h -t training:${WIN}.1
tmux resize-pane -t training:${WIN}.0 -y 70%
```

### Step 5: Start TensorBoard (new session only, bottom-left pane)

```bash
tmux send-keys -t training:${WIN}.1 'cd ~/work/git/triforce && source .venv/bin/activate && tensorboard --logdir training --host 0.0.0.0' Enter
```

### Step 6: Set Up Console (new session only, bottom-right pane)

```bash
tmux send-keys -t training:${WIN}.2 'cd ~/work/git/triforce && source .venv/bin/activate' Enter
```

### Step 7: Start Training (top pane)

Build the training command from the user's inputs and send it to the top pane of the (existing or new) session:

```bash
tmux send-keys -t training:${WIN}.0 'cd ~/work/git/triforce && source .venv/bin/activate && ./train.py <scenario> [action_space] [model_kind] [extra_args]' Enter
```

**Example commands:**
```bash
# Basic scenario training
tmux send-keys -t training:${WIN}.0 'cd ~/work/git/triforce && source .venv/bin/activate && ./train.py dungeon1-circuit' Enter

# Resume from checkpoint
tmux send-keys -t training:${WIN}.0 'cd ~/work/git/triforce && source .venv/bin/activate && ./train.py all-items-circuit --load training/all-items-circuit/2/checkpoints/latest.pt --resume' Enter
```

### Step 8: Confirm to User

Tell the user:
- Training has started on scenario/circuit `<name>`
- TensorBoard is running at `http://<hostname>:6006` (or the machine's IP)
- The tmux session is called "training" — attach with `tmux attach -t training`
- To stop training gracefully: press `q` twice in the top pane, or invoke this skill again

## Validation

- [ ] `pgrep -f 'train\.py'` shows the training process is running
- [ ] `tmux list-panes -t training` shows 3 panes (reused or freshly created)
- [ ] TensorBoard is accessible on port 6006
- [ ] Training output is visible in the top pane (`tmux capture-pane -t training:0.0 -p | tail -5`)

## Common Pitfalls

| Pitfall | Solution |
|---------|----------|
| tmux session already exists | Reuse it — only the top pane needs a new command. Don't kill the session. |
| tmux session has wrong layout (not 3 panes) | Kill and recreate the session (Steps 3–6) |
| train.py won't die with `q` | Wait the full 2 minutes, then `kill`, then `kill -9` |
| TensorBoard port already in use | Kill old tensorboard process first: `pkill -f tensorboard` before starting new one |
| Wrong scenario name | Check the scenario/circuit lists above — names must match exactly |
| CUDA out of memory | Reduce `--parallel` (default 16), try `--parallel 8` or `--parallel 4` |
| Want to resume a circuit | Use `--load <checkpoint.pt> --resume` to continue where it left off |
| Resumable checkpoints exist | Always run Step 0 to check `models/` and `training/` before starting fresh — can save hours |
| venv not activated | All commands source `.venv/bin/activate` first — ensure the venv exists |
| `./train.py` permission denied | Run `chmod +x ~/work/git/triforce/train.py` |
| Multiple train.py processes | This skill checks `pgrep -f 'train\.py'` — kill all before starting a new run |
