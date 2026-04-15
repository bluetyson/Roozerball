# Roozerball

A fully-implemented Python engine with **two desktop GUIs** for **Roozerball** — the over-the-top Australian full-contact roller-skating sport from J. P. Trostle's tabletop game (©2010). Teams of skaters, catchers, and motorcyclists battle on a circular inclined track to fire a steel ball through the opposing goal.

The **Tier 2 Pygame GUI** (recommended) provides hardware-accelerated rendering, animated sprites, a camera system with smooth scrolling, incline lighting with shadows, and a spotlight on the ball carrier. The original **Tier 1 Tkinter GUI** remains available as a dependency-free fallback.

---

## What is Roozerball?

Roozerball is played on a **circular, inclined track** divided into 12 pie-shaped sectors (A–L) with five concentric rings (Floor, Lower, Middle, Upper, and Cannon track). Two teams of 10 — five skaters, two catchers, and three motorcyclists — race counter-clockwise around the track. A steel ball is fired from a cannon at the start of each period; catchers field it, hand it to a skater, complete a lap to activate it, then attempt to score by shooting through the goal on the outer wall.

The rules reward speed, positioning, controlled aggression, and knowing when to let the motorcycle tow you to safety.

---

## Implementation Status

All rules from the official Roozerball rulebook are implemented. The full checklist is in [`roozerball-rules-to-implement.md`](roozerball-rules-to-implement.md).

| Section | Rules | Status |
|---|---|---|
| A — Core game structure & turn sequence | A1–A13, T1–T6 | ✅ Complete |
| B — Rules & penalties (referees, detection, enforcement) | B1–B16 | ✅ Complete |
| C — The track (rings, squares, slots, incline bonuses, ball movement) | C1–C20 | ✅ Complete |
| D — Figures (stats, actions, injuries, standing up, catchers) | D1–D31 | ✅ Complete |
| E — Motorcycles (movement, towing, crashes, cycle chart) | E1–E26 | ✅ Complete |
| F — Scoring, formations, obstacles, packs, hand-offs | F1–F33 | ✅ Complete |
| G — Combat (brawl, man-to-man, assault, swoop, all modifiers) | G1–G57 | ✅ Complete |
| H — Optional rules (endurance, time compression, season play, team gen) | H1–H14 | ✅ Complete |
| I — Quantum movement & miscellaneous reminders | I1–I4 | ✅ Complete |
| GUI — All 16 GUI features | GUI1–GUI16 | ✅ Complete |

---

## Requirements

- **Python 3.11+** (modern type-hint syntax is used throughout)
- **Pygame 2.x** — for the Tier 2 GUI (`pip install pygame`)
- **Tkinter** *(optional)* — included with most Python distributions; only needed for the Tier 1 fallback GUI

---

## Installation

```bash
git clone https://github.com/RichardScottOZ/Roozerball.git
cd Roozerball

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

python -m pip install --upgrade pip
pip install pygame               # Required for the Tier 2 GUI
```

### Tkinter on Linux (Tier 1 fallback only)

If you want to use the original Tkinter GUI and Tkinter is not bundled with your Python install:

```bash
# Debian / Ubuntu
sudo apt install python3-tk

# Fedora / RHEL
sudo dnf install python3-tkinter

# Arch Linux
sudo pacman -S tk
```

Then re-activate the venv and run normally.

---

## Running the GUI

### Tier 2 — Pygame (recommended)

```bash
python -m roozerball.gui_pygame
```

The Pygame window opens at 1500 × 900 px with hardware-accelerated rendering, animated sprites, camera controls, incline lighting, and particle effects.

**Keyboard shortcuts:**
| Key | Action |
|---|---|
| `N` | Next Phase |
| `P` | Play Turn |
| `F` | Follow ball carrier (camera) |
| `R` | Reset camera |
| `Esc` | Cancel current interaction / skip movement |
| Mouse wheel | Zoom in / out |
| Right-click drag | Pan the board |

### Tier 1 — Tkinter (fallback)

```bash
python -m roozerball.gui
```

The window opens at 1500 × 900 px showing the circular board on the left and all game-state panels on the right.

---

## GUI Tour

### Top control bar

| Button | Action |
|---|---|
| **New Match** | Opens the match setup dialog (choose mode, team names, optional custom roster generation) |
| **Next Phase** | Advances one phase of the current turn (Clock → Ball → Initiative → Movement → Combat → Scoring) |
| **Play Turn** | Runs all six phases of one complete game turn in one click |
| **Gen Teams** | Opens the team generation dialog for the home team mid-match |

The label to the right of the buttons shows the current game mode (**Computer vs Computer** or **Human vs Computer**).

### Board canvas

The main canvas shows the full 12-sector × 5-ring circular track:

- **Sectors A–L** are labelled around the outer edge.
- **Goal squares** are highlighted green (home) and red (visitor).
- **Figures** appear as filled circles — blue for home, red for visitor — with a type letter in the centre:
  - `B` — Bruiser skater
  - `S` — Speeder skater
  - `C` — Catcher
  - `K` — Biker (motorcyclist)
- An **orange dot** inside a figure circle means that figure currently carries the ball.
- **Yellow dot** on a figure = moved this turn (cone marker, Rule I4).
- **Orange ring** = figure needs to stand up.
- **Purple box** = figure in man-to-man combat.
- **Green line** = figure holding a tow bar.
- **Red "E!"** = figure approaching endurance limit.
- **⚠ marker** on a square = obstacle present.
- **🔥 marker** = square is on fire (explosion aftermath).
- The **currently active sector** (initiative sector) is outlined in blue.
- Clicking a figure **selects** it and shows its stats in the right panel; **dashed cyan circles** appear on all legal movement destinations for that figure, with movement costs labelled below each option.
- Clicking empty canvas deselects.

### Right-side panels

| Panel | Contents |
|---|---|
| **Scoreboard** | Period number, time remaining, current turn, scores for both teams |
| **Phase** | Current phase name within the turn |
| **Initiative** | Which sector currently has initiative |
| **Ball** | Ball state (In Cannon / On Track / Fielded / Dead / Not in Play), temperature, and speed |
| **Selected Figure** | Name, type, all four stats (SPD / SKL / COM / TGH) with current modifiers, status, sector/ring/position, tow info, and endurance remaining |
| **Penalty / Recovery Box** | All figures currently serving penalties or recovering, with countdown timers |
| **Combat Resolution** | Summary of the last combat (type, totals, difference, and result) |
| **Dice Rolls** | Rolling log of every dice roll made during the match; **Roll 2d6** button for manual rolls |
| **Replay Log** | Full turn-by-turn event commentary — scroll up to review past turns |

---

## New Match Setup

Click **New Match** to open the setup dialog:

1. **Game Mode** — choose **Computer vs Computer** (watch both teams play themselves) or **Human vs Computer** (interactive move choices for the human side).
2. **Team Names** — enter names for the home and visitor teams.
3. **Generate home / visitor team** — tick either checkbox to open the Team Generation dialog before the match starts (see below).
4. Click **Start Match**.

---

## Team Generation

Click **Gen Teams** or tick a team checkbox in the New Match dialog to open the Team Generation screen.

The full roster of 20 figures is auto-generated according to Rules H6–H9:

- **10 skaters** — 6 Bruisers (SPD 5, higher Combat/Toughness) and 4 Speeders (SPD 7)
- **6 bikers** — SPD 2–12 (variable), lower combat
- **4 catchers** — SPD 6

Stats are rolled with **6 team-building points** (Rule H8): rolling a 6 costs 1 point to keep; otherwise a 6 is reduced to 4. Stat maximums are Skill 11, Combat 10, Toughness 11.

Click **Roll Team** to re-roll the roster. The preview pane shows every figure's stats before you commit. Click **Accept** to use that roster.

---

## Turn Phases in Detail

Each game turn has six phases, visible in the **Phase** display:

| Phase | What happens |
|---|---|
| **Clock** | Advances game time by 2 minutes (compressed mode). Penalty, shaken, and rest timers tick down. Figures at 0:00 become eligible to return. |
| **Ball** | If no ball is in play, the cannon fires. If the ball is on the track unfielded, it moves clockwise at its current speed, decelerates by 2, and slips down half a ring. Figures in its path make skill rolls to dodge. After 7 turns the ball dies regardless. |
| **Initiative** | A d12 roll selects the starting sector for this turn. |
| **Movement** | All 12 sectors are processed in initiative order. Figures in each sector move: inside ring to outside, left to right within each ring. Moved figures receive a cone marker. Bikers must lead with one straight square, can turn 90° at speed ≤ 6. Towed skaters move with the bike. The ball carrier must enter a new sector each turn (exception: up to 2 turns stationary in the goal sector for a scoring attempt). |
| **Combat** | Sectors rotate again from the initiative sector. Each figure may fight once. Brawl, man-to-man, assault, and swoop combat are resolved using the Combat Table. Cones are removed after each figure has fought. |
| **Scoring** | Any ball carrier in a goal-touching square with an activated ball may attempt a skill-roll-based shot. A goal increments the score and resets the field. A miss rolls the Missed Shot die (50% dead ball, 25% left, 25% right bounce). |

Click **Next Phase** to step through these one at a time; click **Play Turn** to run all six automatically.

---

## Playing a Match — Step-by-Step

1. Launch the GUI: `python -m roozerball.gui`
2. Click **New Match**, choose a mode and names, click **Start Match**.
3. Click **Play Turn** to run full turns automatically. Watch the **Replay Log** and **Scoreboard** for what's happening.
4. When you want to slow down and inspect a specific step, use **Next Phase** instead.
5. Click any figure on the board to see its full stats and legal move destinations.
6. Repeat until the three 20-minute periods are complete (30 turns in compressed / 2-minute-turn mode).

### Things to watch

- Which sector rolled initiative — it ripples through movement and combat order all turn.
- When the catcher fields the ball (or fumbles it).
- Whether the ball carrier completes a lap back to the fielding sector to activate the ball.
- The three-lap clock — after 3 laps without a scoring attempt, the ball dies.
- Brawl results: Indecisive → man-to-man; Breakaway → winners advance a square; Crush → decisive shunt.
- Penalty box: who got spotted, and for how long.
- Goal-sector combat — all three referees watch this sector closely.

---

## Quick "Wombats vs Dropbears" Smoke Test

For a classic backyard-broadcast feel:

1. Click **New Match**, set Home = `Wombats`, Visitor = `Dropbears`, mode = Computer vs Computer.
2. Click **Play Turn** three or four times to let the cannon fire and teams settle.
3. Switch to **Next Phase** once a catcher has the ball to watch activation lap-by-lap.
4. Click the ball carrier to see their move options highlighted.
5. Watch for: first brawl, first knockdown, first penalty, first goal attempt.

---

## Running the Tests

```bash
python -m unittest discover -s tests -q
```

The test suite covers all engine modules (283 tests across 11 files):

| Test file | Module tested | Tests |
|---|---|---|
| `test_game.py` | Full game phases (movement, ball, scoring) | 13 |
| `test_constants.py` | Lookup table helpers | 18 |
| `test_board.py` | Board, sectors, squares, incline bonuses | 27 |
| `test_figures.py` | Figure stats, status, capabilities, timers | 36 |
| `test_dice.py` | All dice functions, injury pairs, cycle chart | 30 |
| `test_ball.py` | Cannon, fielding, drop, bounce, activation | 33 |
| `test_combat.py` | Brawl, man-to-man, assault, swoop, modifiers | 22 |
| `test_scoring.py` | Scoring modifiers, attempt, penalty negation | 19 |
| `test_penalties.py` | Referee detection, enforcement, composition | 24 |
| `test_team.py` | Roster generation, lineup, substitution | 21 |
| `test_season.py` | Season records, playoffs, stat progression | 22 |

---

## Project Layout

```
Roozerball/
├── roozerball/
│   ├── engine/
│   │   ├── constants.py     # Enums, game constants, lookup tables
│   │   ├── board.py         # Track, sectors, squares, slots, incline movement
│   │   ├── figures.py       # Figure and Biker data classes, stat properties
│   │   ├── dice.py          # All dice roll functions and result types
│   │   ├── ball.py          # Ball state machine (cannon → track → fielded → dead)
│   │   ├── combat.py        # Brawl, man-to-man, assault, swoop resolution
│   │   ├── scoring.py       # Scoring attempt and modifier calculation
│   │   ├── penalties.py     # Referee system, penalty detection and enforcement
│   │   ├── team.py          # Team roster, lineup selection, substitution
│   │   ├── season.py        # Season structure, stat progression, aging
│   │   └── game.py          # Master game loop — all six turn phases
│   ├── gui/                 # Tier 1 — Tkinter GUI (fallback)
│   │   ├── app.py           # Tkinter application (board canvas, panels, dialogs)
│   │   └── __main__.py      # Entry point: python -m roozerball.gui
│   └── gui_pygame/          # Tier 2 — Pygame GUI (recommended)
│       ├── app.py           # Main game loop, event dispatch, callbacks
│       ├── renderer.py      # Board, sprites, camera, particles, lighting
│       ├── ui.py            # Side panels, dialog overlays, buttons
│       ├── constants.py     # Pygame-specific colours, layout, animation params
│       └── __main__.py      # Entry point: python -m roozerball.gui_pygame
├── tests/                   # 283-test regression suite
├── docs/
│   └── Roozerball-rules.pdf # Source rules reference (©2010 J. P. Trostle)
└── roozerball-rules-to-implement.md  # Full implementation checklist
```

---

## Key Rules Quick Reference

| Rule | Summary |
|---|---|
| A2 | 10 per team: 5 skaters, 2 catchers, 3 bikers |
| A3 | Movement is **counter-clockwise only** |
| A8 | Ball carrier must complete a full lap back to the fielding sector to **activate** the ball |
| A9 | Offence has **3 laps** after activation to score or the ball dies |
| B2 | Ball carrier must enter a new sector each turn (max 2 turns in goal sector) |
| B4 | Moving clockwise = penalty (3 min first offence, 1 period second) |
| B8 | Bikers cannot enter goal squares, handle the ball, or score |
| C10–C11 | Moving **downhill** (toward floor) grants +1 to +5 speed bonus; **uphill** costs extra |
| D3 | **Skill check**: roll 2d6 ≤ skill (± modifiers) |
| D4 | **Combat check**: sum each side's combat + modifiers + 2d6; higher total wins |
| E9 | Bike can **tow up to 3 skaters**; each skater reduces max bike speed by 1 |
| G37 | **The Swoop**: attacker moves down at least 1 ring and tackles from above; swooper always falls |
| H3 | **Endurance**: max playing time = Toughness + 3 minutes before mandatory rest |

For the complete rules, see `docs/Roozerball-rules.pdf`.

---

## Known Limitations

The following are automated or AI-controlled in the current build; manual human-interactive variants are the next major milestone:

- Combat choices (which figure to target, whether to go man-to-man on a marginal result)
- Tow bar grab/release timing
- Pack formation decisions

The Computer vs Computer mode is fully playable and a good way to stress-test the rules logic.

---

## Future Improvements

### Human-Interactive Play (Next Major Milestone)

- **Click-to-target combat** — let the human player pick which opposing figure to attack, and choose whether to escalate a marginal brawl to man-to-man
- **Tow bar controls** — grab/release tow bars on demand (click a biker, then click a skater to attach; click again to release)
- **Pack formation builder** — drag figures into desired formation patterns before movement resolves
- **Movement confirmation** — preview a move path with distance/cost shown, click to confirm instead of auto-resolving
- **Scoring shot control** — choose when to attempt a shot vs. continue circling for a better angle

### AI & Strategy

- **Difficulty levels** — Easy / Medium / Hard AI with progressively smarter targeting, positioning, and ball-carrier protection
- **Configurable AI profiles** — aggressive (more swoops, more fouls), defensive (pack-and-protect, tow-bar heavy), balanced
- **Replay analysis** — post-match breakdown showing possession time, combat win %, shot accuracy, and per-figure stat lines
- **Tactical heatmaps** — overlay showing combat frequency, ball-carrier paths, and scoring attempts by sector

### Quality of Life

- **Save / Load** — serialise full game state to JSON for mid-match saves and resume
- **Undo / Redo** — step backward through phases or entire turns
- **Speed controls** — adjustable auto-play speed (slow for watching, fast for stress-testing)
- **Sound effects** — cannon fire, crashes, goals, referee whistles, crowd noise
- **Hotkeys** — keyboard shortcuts for Next Phase (`N`), Play Turn (`P`), Undo (`Ctrl+Z`)
- **Configurable window size** — resizable layout that adapts to different screen resolutions

### Multiplayer & Sharing

- **Hot-seat mode** — two human players on the same machine, alternating turns
- **Network play** — LAN or internet multiplayer with a lightweight lobby
- **Match replay export** — save a full match replay as a shareable file or animated GIF
- **Season mode UI** — standings table, playoff bracket, and stat-leader boards for multi-match seasons

---

## Future Graphics Options

The Tier 1 (Tkinter) and Tier 2 (Pygame) GUIs are both implemented. Below are the remaining upgrade paths:

### Tier 1 — Stay in Python, enhance Tkinter ✅ Complete

Available via `python -m roozerball.gui`. Procedural sprites, smooth animation, particles, track texture, zoom & pan.

### Tier 2 — Python 2D game framework (Pygame) ✅ Complete

Available via `python -m roozerball.gui_pygame`. All Tier 2 enhancements implemented:

| Enhancement | Status |
|---|---|
| **Pygame migration** | ✅ Hardware-accelerated rendering with 60 FPS game loop |
| **Animated sprites** | ✅ Frame-by-frame animation for idle, movement, and combat states with wobble/pulse effects |
| **Camera system** | ✅ Follow ball carrier (`F`), lock sector, smooth scroll, zoom (`mouse wheel`), pan (`right-click drag`), reset (`R`) |
| **Lighting / shadows** | ✅ Ring-brightness incline lighting, figure shadows proportional to ring height, additive spotlight on ball carrier |
| **Particle system** | ✅ Pygame-native particles for cannon fire, crashes/knockdowns, and goal celebrations |

### Tier 3 — Dedicated game engine (Godot)

The [`roozerball-rules-to-implement.md`](roozerball-rules-to-implement.md) already recommends **Godot Engine** as the long-term target. Key graphics gains:

| Enhancement | Description |
|---|---|
| **2D scene graph** | Each figure, the ball, markers, and UI panels become individual nodes with transforms, collision shapes, and animation players. |
| **Tilemap / radial grid** | Custom radial tilemap shader for the 12-sector × 5-ring track with per-tile incline shading. |
| **Skeletal animation** | 2D skeleton rigs for skater/biker figures — smooth run cycles, combat swings, falls, and stand-up sequences. |
| **Shader effects** | GLSL shaders for ball heat glow, speed lines on fast-moving figures, goal-flash celebrations, and ring-incline gradients. |
| **3D isometric view** | Optional 3D camera looking down at the banked track at an angle, showing the physical incline of the rings. |
| **Particle systems** | GPU-accelerated particles for cannon sparks, motorcycle exhaust, dust clouds on falls, and crowd confetti on goals. |
| **UI / HUD** | Godot's Control nodes for score overlays, stat panels, dice-roll popups, and replay timelines — fully themeable. |
| **Web export** | One-click HTML5 build for browser play with no install required. |

### Tier 4 — Full 3D (Godot 3D / Unreal / Unity)

For a premium visual experience down the road:

- **3D banked track** — modelled circular arena with physical incline, crowd stands, and a central cannon turret
- **Ragdoll physics** — figures tumble realistically on knockdowns, swoops, and motorcycle crashes
- **Broadcast camera** — TV-style camera angles (overhead, trackside, goal-cam) with smooth transitions
- **Weather / atmosphere** — night matches with floodlights, rain on the track surface, pyrotechnics for goals
- **VR spectator mode** — watch the match from a virtual seat in the arena
