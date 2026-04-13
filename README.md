# Roozerball

An over-the-top Australian-flavoured Python Roozerball engine with a minimal desktop GUI, auto-generated teams, and enough rules in place to start flinging steel around the track and seeing what breaks.

## What is in the repo right now?

Current playable slice:

- Full turn loop: clock, ball, initiative, movement, combat, and scoring
- Auto-generated squads and starting lineups
- Ball cannon, fielding, activation, lap tracking, dead-ball handling, and scoring attempts
- Tkinter GUI with the board, scorebox, initiative display, movement highlighting, figure selection HUD, penalty/recovery display, and replay log
- A growing implementation checklist in `roozerball-rules-to-implement.md`

It is still a work in progress, but it is absolutely at the point where you can run matches, click around the board, and sanity-check how the current rules feel.

## Requirements

- Python 3.11+ recommended
- Tkinter available in your Python install for the GUI

No third-party Python packages are currently required.

## Install / setup

From the repository root:

```bash
cd /path/to/Roozerball
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
```

There are no package dependencies to install after that.

## Run the GUI

From the repo root:

```bash
cd /path/to/Roozerball
python -m roozerball.gui
```

If Tkinter is missing on Linux, install the distro package that provides it, then run the command again.

## How to use the GUI

The GUI is intentionally simple at this stage:

- **Next Phase**: advances one phase at a time
- **Play Turn**: runs through a full turn
- **New Match**: spins up a fresh match with new generated teams
- **Click a figure**: shows its stats, status, and location
- **Highlighted circles**: legal movement destinations for the selected figure
- **Replay Log**: the running commentary of the latest chaos

### What to watch for while testing

- Which sector won initiative
- Who fields the ball and when it activates
- Whether a carrier keeps pushing into new sectors
- Brawls, knockdowns, penalties, and dropped-ball moments
- Scoring attempts in the goal sector

## How to run the tests

```bash
cd /path/to/Roozerball
python -m unittest discover -s tests -q
```

## Quick “Wombats vs Dropbears” smoke test

If you want a proper backyard-broadcast feel, start the GUI and treat the default match as:

- **Home**: Wombats
- **Visitor**: Dropbears

Then:

1. Launch a new match
2. Click **Play Turn** a few times to let the cannon do its thing
3. Use **Next Phase** when you want to inspect a specific step in slow motion
4. Click likely suspects on the board to inspect movement and statuses
5. Watch the log to see who got flattened, who copped a penalty, and whether the ball went dead or stayed live

## Project layout

- `roozerball/engine/` — core rules and match engine
- `roozerball/gui/` — Tkinter desktop viewer
- `tests/` — regression tests
- `docs/Roozerball-rules.pdf` — source rules reference
- `roozerball-rules-to-implement.md` — implementation checklist

## Current limitations

Still to come:

- richer combat choices beyond the current automated flow
- more bike-specific rules and wreck handling
- fuller obstacle, hand-off, and pack mechanics
- more GUI affordances, overlays, and game-mode options

So, yes: it is playable enough to have a laugh and start validating the rules, but there is still plenty of wild Aussie sports nonsense left to wire in.
