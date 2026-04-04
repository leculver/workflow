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

### Step 1: Check for Running Training

Check if a `train.py` process is already running:

```bash
pgrep -f 'train\.py' -a
```

If a training process is found:
1. **Ask the user** whether they want to stop it and start a new run, or leave it running.
2. If they want to stop it, proceed to Step 2. Otherwise, stop — do not start a second training run.

### Step 2: Gracefully Stop Existing Training (if needed)

The training TUI listens for `q` keypresses. Send `q` twice to trigger a graceful shutdown:

1. Identify the tmux pane running training (top pane of the "training" session):
   ```bash
   tmux send-keys -t training:0.0 q
   sleep 1
   tmux send-keys -t training:0.0 q
   ```
2. Wait up to **2 minutes** for the process to exit. Poll every 5 seconds:
   ```bash
   # Check if train.py is still running
   pgrep -f 'train\.py'
   ```
3. If the process is still running after 2 minutes, **kill it**:
   ```bash
   kill $(pgrep -f 'train\.py')
   ```
4. Wait a few seconds and verify it's dead. If it's still running, use `kill -9`.

### Step 3: Create or Reset the tmux Session

Check if the "training" tmux session exists:

```bash
tmux has-session -t training 2>/dev/null
```

**If the session exists**, kill it and recreate it to get a clean layout:

```bash
tmux kill-session -t training
```

**Create the session** (detached, so it doesn't steal our terminal):

```bash
tmux new-session -d -s training -x 200 -y 50
```

### Step 4: Set Up the Pane Layout

Split into three panes — training (top), tensorboard (bottom-left), console (bottom-right):

```bash
# Split vertically: creates top (pane 0) and bottom (pane 1)
tmux split-window -v -t training:0.0

# Split the bottom pane horizontally: creates bottom-left (pane 1) and bottom-right (pane 2)
tmux split-window -h -t training:0.1

# Make the top pane larger (training output needs more space)
tmux resize-pane -t training:0.0 -y 70%
```

### Step 5: Start TensorBoard (bottom-left pane)

```bash
tmux send-keys -t training:0.1 'cd ~/work/git/triforce && source .venv/bin/activate && tensorboard --logdir training --host 0.0.0.0' Enter
```

### Step 6: Set Up Console (bottom-right pane)

```bash
tmux send-keys -t training:0.2 'cd ~/work/git/triforce && source .venv/bin/activate' Enter
```

### Step 7: Start Training (top pane)

Build the training command from the user's inputs. The pattern is:

```bash
tmux send-keys -t training:0.0 'cd ~/work/git/triforce && source .venv/bin/activate && ./train.py <scenario> [action_space] [model_kind] [extra_args]' Enter
```

**Example commands:**
```bash
# Basic scenario training
tmux send-keys -t training:0.0 'cd ~/work/git/triforce && source .venv/bin/activate && ./train.py dungeon1-circuit' Enter

# With specific action space and model
tmux send-keys -t training:0.0 'cd ~/work/git/triforce && source .venv/bin/activate && ./train.py overworld-room-walk basic shared-nature --iterations 100000' Enter

# Resume from checkpoint
tmux send-keys -t training:0.0 'cd ~/work/git/triforce && source .venv/bin/activate && ./train.py all-items-circuit --load training/all-items-circuit/2/checkpoints/latest.pt --resume' Enter
```

### Step 8: Confirm to User

Tell the user:
- Training has started on scenario/circuit `<name>`
- TensorBoard is running at `http://<hostname>:6006` (or the machine's IP)
- The tmux session is called "training" — attach with `tmux attach -t training`
- To stop training gracefully: press `q` twice in the top pane, or invoke this skill again

## Validation

- [ ] `pgrep -f 'train\.py'` shows the training process is running
- [ ] `tmux list-panes -t training` shows 3 panes
- [ ] TensorBoard is accessible on port 6006
- [ ] Training output is visible in the top pane (`tmux capture-pane -t training:0.0 -p | tail -5`)

## Common Pitfalls

| Pitfall | Solution |
|---------|----------|
| tmux session already exists with wrong layout | Kill and recreate the session (Step 3) |
| train.py won't die with `q` | Wait the full 2 minutes, then `kill`, then `kill -9` |
| TensorBoard port already in use | Kill old tensorboard process first: `pkill -f tensorboard` before starting new one |
| Wrong scenario name | Check the scenario/circuit lists above — names must match exactly |
| CUDA out of memory | Reduce `--parallel` (default 16), try `--parallel 8` or `--parallel 4` |
| Want to resume a circuit | Use `--load <checkpoint.pt> --resume` to continue where it left off |
| venv not activated | All commands source `.venv/bin/activate` first — ensure the venv exists |
| `./train.py` permission denied | Run `chmod +x ~/work/git/triforce/train.py` |
| Multiple train.py processes | This skill checks `pgrep -f 'train\.py'` — kill all before starting a new run |
