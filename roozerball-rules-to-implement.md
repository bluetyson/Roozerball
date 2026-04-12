# Roozerball — Rules to Implement

> Extracted from **Roozerball-rules.pdf** (©2010 J. P. Trostle).
> Check off each item as its logic is implemented in the game engine / GUI.

---

## Recommended GUI Front-End

**Godot Engine (GDScript / C#)** is the recommended choice for implementing this game.

**Rationale:**
- The game is played on a **circular, inclined track** divided into 12 pie-shaped sectors with concentric rings. Godot's 2D engine (with optional 3D for a tilted arena view) handles radial/polar layouts, custom drawing, and tile-based logic very well.
- Godot supports **custom board rendering** — the track's rings, sectors, slots, goals, cannon track, and incline can all be drawn procedurally or with tiled sprites.
- Built-in **scene/node system** makes it natural to model figures (skaters, catchers, bikers), the ball, markers/cones, and UI overlays as separate nodes.
- Godot ships with a **full GUI toolkit** (buttons, panels, labels, dialogs) for game-state HUD, dice rolls, turn phases, penalty boxes, and score displays.
- **Cross-platform** (desktop, web export via HTML5) — easy to share.
- Supports both **human-interactive play** (click-to-move, drag figures) and **AI/simulation mode** (computer vs computer) via scripted decision-making.
- Free and open-source with an active community; no licensing costs.

Alternative considered: Pygame (Python) — good for 2D board games and matches the repo's Python .gitignore, but Godot offers far superior rendering, UI, and scene management for a complex board with many moving pieces on an inclined circular track.

---

## A. The Game — Core Concepts

- [x] **A1. Game structure** — 60-minute game, three 20-minute periods *(constants.py: PERIOD_LENGTH, NUM_PERIODS, GAME_LENGTH)*
- [x] **A2. Team composition** — 10 players per team: 3 motorcyclists, 2 catchers, 5 skaters *(constants.py: MAX_FIGURES, MAX_SKATERS, MAX_CATCHERS, MAX_BIKERS; team.py)*
- [x] **A3. Circular track** — Counterclockwise movement around a circular track *(board.py: Board, constants.py: Direction)*
- [x] **A4. Two goals** — Located opposite each other in the outer wall *(board.py: Goal, home_goal_sector=0, visitor_goal_sector=6)*
- [x] **A5. Ball firing** — Steel game ball fired from cannon at start of each period *(ball.py: fire_cannon())*
- [x] **A6. Catcher fielding** — Only catchers can initially pick up a fresh ball *(ball.py: attempt_field(), figures.py: can_field_ball)*
- [x] **A7. Hand-off to skater** — Catcher hands ball to a skater; only skaters can score *(figures.py: can_score property)*
- [x] **A8. Ball activation** — Team with ball must complete one full lap to the sector where catcher fielded it to "activate" the ball and become the offense *(ball.py: activate())*
- [x] **A9. Three-lap limit** — Offense has three laps to make a scoring attempt or ball is declared dead *(ball.py: check_three_lap_limit(), constants.py: OFFENSE_LAP_LIMIT)*
- [x] **A10. Dead ball** — Ball declared dead if: rolls into gutter, dropped inside white line, or three-lap limit expires; new ball fired immediately *(ball.py: declare_dead())*
- [ ] **A11. Goal tending prohibition** — Defense cannot goal tend; if screen set up and no shot attempted that lap, defenders must chase and make another lap before screening again
- [x] **A12. Ball stealing** — Defense may steal the ball; stealing team must complete a lap from the steal sector to activate for their team (switches offense/defense) *(ball.py: steal())*
- [ ] **A13. Clock stoppages** — Clock stops only: (1) after failed scoring attempt results in dead ball, (2) after a successful goal; field is reset during these pauses

---

## A (cont.). The Game Turn Sequence

- [ ] **T1. Clock phase** — Start period or advance clock 1 minute; advance penalty box / shaken / rest figures 1 minute; figures reaching 0:00 are eligible to return
- [ ] **T2. Ball phase** — Fire cannon or move ball if in play but unfielded; catcher may attempt to field; non-catchers in ball's square must make skill roll to avoid ball (exception: catcher in same square protects teammates)
- [ ] **T3. Initiative phase** — Roll d12 to determine starting sector for this game turn
- [ ] **T4. Movement phase** — Move all figures in the initiative sector (inside ring to outside ring, left to right within each ring); mark moved figures with cones; rotate initiative clockwise through all 12 sectors
- [ ] **T5. Combat phase** — From same starting sector, rotate initiative again for combat; each figure gets one fight; remove cones after each figure has fought; continue through all 12 sectors
- [ ] **T6. Scoring phase** — Resolve any scoring attempts; if goal/dead ball/period end, clear board and reset to starting positions

---

## B. Rules & Penalties

- [x] **B1. Ball must remain in sight at all times** — No fakes or hidden ball tricks (automatic rule) *(penalties.py: penalty table)*
- [ ] **B2. Ball must remain in motion** — Ball carrier must move into a new sector each turn; exception: may stay in goal sector up to 2 turns during scoring attempt; if blocked, must Assault forward/parallel square; penalty: dead ball (automatic rule)
- [x] **B3. Ball may not be used as a weapon** — Penalty: 3 minutes + dead ball *(penalties.py: PENALTY_TIMES, combat.py: check_combat_penalties)*
- [ ] **B4. Counterclockwise movement only** — Figures may never move clockwise or backwards (automatic rule); penalty: 1st offense 3 min, 2nd offense 1 period
- [x] **B5. Max two figures stopped** — A team may have at most 2 figures stopped on track at any time; exceptions: defensive screen at activated goal (up to 5 skaters + 2 catchers), injured/unconscious/dead figures don't count; penalty: 3 min per extra figure *(penalties.py: check_stopped_figures)*
- [x] **B6. Skaters/catchers may not attack bikers** — Penalty: 3 minutes (includes grabbing a ride on opposing bike) *(combat.py: calculate_combat_modifiers, penalties.py)*
- [x] **B7. Bikers may not attack anyone** — No sideswipe, ram, or run over; penalty: 3 minutes *(combat.py: calculate_combat_modifiers, penalties.py)*
- [ ] **B8. Bikers cannot handle ball or be near goal** — Cannot enter 2 squares in front of goal, cannot pick up/carry/score with ball, cannot interfere with scoring; penalties: 3 min for entering goal squares or handling ball; goal disqualified + 3 min + 3 min per opponent involved for scoring interference on offense
- [x] **B9. Penalties on scoring attempts** — Any penalty on offense during the scoring turn negates the goal *(scoring.py: check_scoring_penalties)*
- [x] **B10. No attacking fallen/prone figures** — May not attack downed, injured, unconscious, or figures attempting to stand; "out of contention" hand-raise means immune from attack; penalty: 3 min; exception: biker knocked off motorcycle or crash landing on downed figure *(combat.py: calculate_combat_modifiers)*
- [x] **B11. Max figures on field** — Max 10 per team: 5 skaters, 2 catchers, 3 bikers (automatic rule); can field fewer due to penalties/injuries but cannot exceed type maximums; no extra figures sent to help injured off track *(penalties.py: check_field_composition)*
- [x] **B12. Keep it on the track** — No fighting in infield; refs cannot be attacked; attacking a ref = automatic immediate expulsion *(penalties.py: PENALTY_TIMES attack_referee=60)*

### Referees

- [x] **B13. Three referees** — Two on floor (180° view each), one controller in tower following ball (180° view facing ball) *(penalties.py: setup_referees)*
- [x] **B14. Referee detection** — Base rating 8; roll 2d6 ≤ 8 to spot infraction; -2 if infraction is on far side of track from ball *(penalties.py: check_infraction, dice.py: referee_check)*
- [x] **B15. Scoring attempt ref focus** — All three refs roll for violations in the goal sector during scoring attempts *(penalties.py: check_infraction during_scoring)*
- [x] **B16. Penalty enforcement** — Guilty figure removed to penalty box at appropriate time; moved 1 box per game turn; no substitutes for penalized figures; penalty times carry over between periods *(penalties.py: enforce_penalty, figures.py: penalty_time/advance_timers)*

---

## C. The Track / Game Board

- [x] **C1. 12 sectors** — Circular track divided into 12 equal pie-slice sectors (A through L) *(board.py: Board, constants.py: SECTORS)*
- [x] **C2. Rings/zones** — Each sector has 5 rings: floor/gutter (1 square), lower track (2 squares), middle track (3 squares), upper track (4 squares), cannon track/rail (4 squares, movement-restricted) *(board.py: Sector, constants.py: Ring, SQUARES_PER_RING)*
- [x] **C3. Total squares** — Floor: 12 total (1/sector), Lower: 24 (2/sector), Middle: 36 (3/sector), Upper: 48 (4/sector) *(board.py: Board._build)*
- [x] **C4. Square capacity** — Incline squares: 4 slots (4 skaters, or 2 bikers, or 2 skaters + 1 bike); Floor squares: 6 slots (6 skaters or 3 bikers) *(board.py: Square.capacity, constants.py: INCLINE_SLOTS, FLOOR_SLOTS)*
- [x] **C5. Slot placement** — Figures must be placed in a specific slot (quarter for incline, sixth for floor); default is lower-left if no preference; no rearranging after initiative moves on *(board.py: Square.add_figure, Slot)*
- [x] **C6. Controlling a square** — Team with >50% upright figures in a square controls it; opponents cannot pass through or stop in it without an Assault *(board.py: Square.is_controlled_by, controlling_team)*
- [x] **C7. Cannon track separation** — Cannon track is separate from upper track; cannot be used for normal movement; first turn after firing, ball is in cannon track and can't hit figures unless deliberately placed or thrown there via wreck *(board.py: squares_in_range excludes CANNON)*
- [x] **C8. Initiative order within a sector** — Floor ring first, then lower, middle, upper, cannon; within each ring: left to right; within same square: left to right, inside to outside *(board.py: Sector.all_squares)*
- [x] **C9. Orientation** — Left/right as seen from infield (center of circle); "behind"/"back" = to the right; "forward"/"ahead" = to the left *(board.py)*

### Incline Movement Effects

- [x] **C10. Downhill speed bonus** — Moving down 1 ring: +1; immediately down another: +2 more; immediately down a 3rd: +2 more (max +5 from upper to floor); non-consecutive downhill moves give +1 each *(board.py: calculate_incline_bonus, constants.py: DOWNHILL_CONSECUTIVE)*
- [x] **C11. Uphill speed cost** — Moving up 1 ring: costs 1 extra (2 total per square); immediately up another: costs 2 extra (3 total); immediately up a 3rd: costs 2 extra; non-consecutive uphill moves cost 1 extra each *(board.py: calculate_incline_bonus, constants.py: UPHILL_CONSECUTIVE_EXTRA)*

### Starting Positions & Ball Movement

- [x] **C12. Standard starting positions** — 1 bike + 1–3 skaters per team placed alternating teams in middle ring, cycling through sectors A, E, C *(board.py: place_starting_positions)*
- [x] **C13. Ball firing speed** — Roll 3d6 + 12 for initial ball speed; ball moves clockwise on cannon track, 1 square per movement point *(ball.py: fire_cannon, dice.py: roll_ball_speed)*
- [x] **C14. Ball deceleration** — Each new turn: subtract 2 from speed, slip ball down half a square; after 7 turns ball reaches gutter and is declared dead regardless of firing speed *(ball.py: move_ball, constants.py: BALL_DECEL_PER_TURN, BALL_MAX_TURNS)*
- [x] **C15. Hot ball rules** — Ball in cannon track or upper ring is "hot"; adds modifiers to catcher's attempt; risk of injury *(ball.py: update_temperature, constants.py: BallTemp)*
- [x] **C16. Unfielded ball obstacle** — Skaters/bikers entering a square with an unfielded ball must make skill roll (exception: catcher present in square) *(ball.py: attempt_field)*
- [x] **C17. Ball bounce on obstacle/bobble** — Roll 3d6, subtract from speed; if result > speed, ball stops; otherwise new speed = old speed - result; roll direction die for new direction; hot/very hot ball becomes not-hot after bobble *(ball.py: bounce)*
- [x] **C18. Dropped ball rolling** — Dropped ball rolls downhill next turn at speed 1 with normal downhill bonuses; reaches gutter same turn if nobody fields it *(ball.py: drop)*
- [x] **C19. Ball pickup after drop** — Figure in same square may attempt skill roll to pick up (requires an action); if they fail, other figures in square may attempt in order (left to right, bottom to top) *(ball.py: attempt_pickup)*
- [x] **C20. Goals** — Two goals opposite each other; home and visitor goals with scoring lines *(board.py: Goal)*

---

## D. The Men — Stats, Actions & Injuries

### Stats

- [x] **D1. Four stats** — Speed (green), Skill (yellow), Combat (orange), Toughness (blue) *(figures.py: Figure, constants.py: FigureType)*
- [x] **D2. Speed** — Max movement points per turn; skaters 5–7; figure can use any number up to max; no penalty for acceleration from standstill; entering track from infield = 1 square; standing up from fall = full movement; temporary boosts from downhill/towing *(figures.py: speed property)*
- [x] **D3. Skill** — Represents balance, skating, hand-eye coordination; range 6–11; skill check = roll 2d6 ≤ skill (± modifiers) *(dice.py: skill_check)*
- [x] **D4. Combat** — Fighting ability; range 5–10; each side sums combat values + modifiers + 2d6; compare totals; look up difference on Combat Table *(dice.py: combat_roll, constants.py: get_brawl_result)*
- [x] **D5. Toughness** — Conditioning/endurance; range 6–11; toughness check = roll 2d6 ≤ toughness; checked after fights/wrecks; failure leads to injury dice roll *(dice.py: toughness_check)*

### Injury System

- [x] **D6. Injury dice** — Roll pair of injury dice (6-sided: head, left arm, right arm, left leg, right leg, body); results depend on combination and fatality flag *(dice.py: roll_injury_dice, constants.py: InjuryFace)*
- [x] **D7. No-fatality injury results** — Body + any limb/head = Shaken 1–3 min; Body + body = Badly Shaken 4–6 min; Doubles of limb = limb injured (rest of game) + shaken 4–6 min; Doubles of head = knocked unconscious (out for game) *(dice.py: roll_injury_dice)*
- [x] **D8. Fatality injury results** — Body + any limb/head = Badly Shaken 4–6 min; Doubles of limb = broken (out for game); Doubles of body or head = Fatality (death) *(dice.py: roll_injury_dice)*
- [x] **D9. Blue Die of Death (BDD)** — Third injury die added when called for; increases likelihood of injury, not severity *(dice.py: roll_injury_dice bdd parameter)*
- [x] **D10. No injury on no combination** — If dice don't form a combination, no injury at all regardless of circumstances *(dice.py: roll_injury_dice)*

### Shaken / Injured / Recovery

- [x] **D11. Shaken** — Figure must leave field temporarily; if stays: -1 to all stats (badly shaken: -2); cumulative; must sit out full shaken time to recover *(figures.py: FigureStatus.SHAKEN/BADLY_SHAKEN, speed/skill/combat/toughness properties apply penalties)*
- [x] **D12. Injured** — -2 to all stats; toughness checks become automatic injury dice rolls; must make extra skill roll to hold ball; broken arm: -4 to all stats (can optionally play); broken leg or head injury: out for game *(figures.py: injuries list, stat properties)*
- [x] **D13. Recovery** — Place figure in time box; advance 1 box per game turn; at 0:00 may return; early return = still penalized *(figures.py: advance_timers, is_ready_to_return)*
- [x] **D14. Substitutions** — Same-type substitute enters when original leaves field; figure on track (any condition) = "in play", no substitute allowed *(team.py: get_available_substitute, substitute)*

### Falling Down & Getting Up

- [x] **D15. Falling** — Failed skill roll after fight or obstacle = fall; fallen figure may not be attacked (penalty check for attacker) *(figures.py: fall(), FigureStatus.FALLEN)*
- [ ] **D16. Standing up** — Attempt during movement phase; skill roll to stand (counts as full movement); failure: roll injury dice (no fatality) — may reveal hidden injury; if truly OK, automatic stand next turn
- [x] **D17. Fallen figure limitations** — No actions; fallen catcher can't field ball or protect teammates from unfielded ball; BUT can hand off ball, fight, and attempt to score (these are NOT actions) *(figures.py: can_act, can_field_ball properties)*
- [ ] **D18. Injured/shaken standing** — Must make adjusted skill roll to stand; continue attempting each turn until successful
- [x] **D19. "Out of contention"** — Shaken/injured figure attempting to leave can raise hand; immune from attack; drawing a penalty if attacked *(constants.py: FigureStatus.OUT_OF_CONTENTION)*

### Actions

- [x] **D20. One action per turn** — Each figure gets: one move, one fight, one scoring attempt (if applicable), plus one action *(figures.py: has_acted, can_act)*
- [x] **D21. Action definition** — Anything requiring skill check or effort outside of moving/fighting/scoring *(figures.py: has_acted flag)*
- [x] **D22. Non-actions** — Letting go of tow bar, handing off ball (without opponents present) are NOT actions *(figures.py)*
- [x] **D23. Action limit** — If action already used this turn, cannot attempt another even if in position to do so *(figures.py: can_act property)*

### Catchers

- [x] **D24. Catcher purpose** — Field game ball and hand off to skater; fielding = skill roll + action; must release bike tow bar to field *(ball.py: attempt_field, figures.py: can_field_ball)*
- [x] **D25. Ball moving through catcher's square** — May attempt to field during ball's movement; if caught, wait until movement phase to hand off *(ball.py: attempt_field)*
- [x] **D26. Hot ball fielding danger** — Cannon track ball: -4 skill + automatic fatal injury dice with BDD; Very hot (top half upper ring): -2 skill + toughness check -1; Hot (bottom half upper ring): -1 skill + toughness check *(ball.py: attempt_field temperature modifiers)*
- [x] **D27. Bobbled ball** — Miss skill by 1 or 2: ball loses 3d6 speed, bounces random direction; if hot/very hot: skip toughness check, roll 2 non-fatal injury dice *(ball.py: attempt_field bobble logic)*
- [x] **D28. Hand-off rules** — Not an action; no skill roll needed unless opposing player in same square; -1 per opposing player in square or base-to-base contact *(ball.py)*
- [x] **D29. Catcher drop rules** — Cannot re-attempt pickup same turn as fielding; otherwise can use action to attempt pickup *(ball.py)*
- [x] **D30. Four catchers per team** — Two on field at a time; if all 4 incapacitated, regular skater can substitute as catcher with -3 to fielding skill checks *(team.py: can_field_with_regular_skater, constants.py)*
- [x] **D31. Catcher chart implementation** — Roll ≤ skill: caught; 1–2 over: bobbled; 3+ over: complete miss; with all modifiers *(ball.py: attempt_field)*

---

## E. The Machines — Motorcycles

### Biker Stats

- [x] **E1. Biker stats** — Speed (2 min / 12 max), Skill (driving ability), Combat (low, +5 when using bike as weapon — illegal), Toughness (post-fight/wreck checks) *(figures.py: Biker, constants.py: BIKE_MIN_SPEED, BIKE_MAX_SPEED)*
- [x] **E2. Biker purpose** — Solely to help skaters go higher/faster; cannot score, cannot fight legally *(figures.py: Biker.can_score=False)*

### Motorcycle Movement

- [ ] **E3. First-square-straight rule** — At turn start, bike must move 1 square straight ahead before turning; if blocked, skill roll to go around
- [ ] **E4. Bike passing through squares** — Must use top or bottom half; if two skaters in left slots, bike cannot pass
- [x] **E5. Bike slot placement** — Bike takes 2 slots (half a square); must end in top or bottom half; must be within single square boundary *(figures.py: Biker.slots_required=2, board.py: Square.has_space_for)*
- [ ] **E6. Minimum speed 2** — Below 2 the biker must stop and put feet down; entering field or starting from standstill: max move is 2; subsequent turns: any speed 2–12
- [ ] **E7. 90-degree turning** — Can turn up to 90° only at speed ≤ 6; must move 1 square forward before another 90° turn; cannot end perpendicular to traffic flow
- [ ] **E8. Incline bonuses** — Bikes get same downhill/uphill movement bonuses as skaters

### Towing

- [ ] **E9. Tow bar** — Bike can pull up to 3 skaters; each towed skater reduces max bike speed by 1
- [ ] **E10. Towed figure placement** — Directly behind the bike; side by side; alternative: 2 on bar + 1 pulled by towed skater (third skater can't take handoff or fight without releasing)
- [ ] **E11. Grabbing tow bar** — Grab as bike starts moving, or end move behind already-moved bike; CANNOT grab bar of a bike that hasn't moved yet this turn
- [ ] **E12. Towed movement** — Move at bike's speed; can let go anytime; if held for ≥ half bike's movement this turn: skater gets bike's speed for remainder of that turn; if let go before half: only gets own max speed this turn
- [ ] **E13. Towed speed bonuses** — Skaters gain all downhill bonuses the bike picks up; max towing speed with 1 skater = 16 (11+1+2+2)
- [ ] **E14. Bike speed not recovered** — Bike doesn't get movement points back if towed skater lets go mid-move

### Crashes & Cycle Chart

- [ ] **E15. Crash triggers** — Biker must make skill roll for: obstacles in entering square, figure falls/wreck in current square; failure = roll 2d6 on Cycle Chart
- [ ] **E16. Towed skater crash effects** — Each towed skater makes skill check to maintain footing; -2 if biker thrown; -4 if Major Wreck
- [ ] **E17. Crash logic** — If obstacle stops cycle: biker thrown, cycle stays; if biker stopped (e.g., clotheslined): cycle continues, biker stays
- [ ] **E18. Bike recovery** — If no damage and biker in same square: skill roll to stand/start bike next turn (= movement for turn); next turn move minimum 2; if fail twice: something wrong, off-track 1–3 min to fix
- [x] **E19. Cycle Chart implementation** — Full 2d6 chart with modifiers (min speed -5, missed by 1: -1, unfielded ball top ring +5, 2+ bikes +2); results from OK (2–3) through Major Wreck (13+) *(dice.py: roll_cycle_chart)*
- [x] **E20. Explosion rules** — Roll d6 for explosion chance; fire area depends on severity; fire trickles downhill; Big Explosion covers 2 squares on ring + 2 below; biker in fire rolls injury dice again *(dice.py: roll_explosion)*
- [ ] **E21. Damaged bike removal** — Biker pushes at 3 sq/turn (+1 downhill per ring); on foot without bike: 4 sq/turn; badly damaged bike needs 2 figures at 2 sq/turn; substitute can't enter until ≥75% of bike off track
- [ ] **E22. Shaken biker** — Same shaken penalties as skaters until required rest time taken
- [ ] **E23. Bikers cannot be legally attacked (reiteration)** — Any attack on biker draws penalty check; dismounted biker still counts as biker; dismounted biker attacking = doubled penalties
- [ ] **E24. Biker scoring involvement prohibition** — Cannot ram defenders at goal, block goal, dismount to fight at goal, or "accidentally" crash into defenders
- [ ] **E25. Biker man-to-man** — If fight results in man-to-man: biker auto-rolls cycle chart at -1; if stays up, both move 2 squares next turn; second man-to-man = bike stops, ref auto-calls penalty on attacker
- [ ] **E26. Biker leaving fight** — If biker wins brawl and chooses to stay and fight next turn, biker can also be penalized

---

## F. The Teams — Scoring, Formations & Obstacles

### Scoring

- [x] **F1. Scoring requirements** — Ball must be activated; only skaters; only from squares touching scoring line in goal sector *(scoring.py: attempt_score checks)*
- [x] **F2. Scoring skill roll** — Roll ≤ modified skill to score; magnet triggers on success *(scoring.py: attempt_score)*
- [x] **F3. Scoring modifiers** — Distance from goal (-1/square), standing opponents between shooter and goal (-1 each), moving shot perpendicular (-1), prone (-4), engaged in man-to-man (-2), 3rd figure in m2m (-2), defense decisive (-1), defense block/breakaway (-2), offense decisive (+1), offense breakthrough/breakaway (+2), offense crush (+4), directly against goal (+2) *(scoring.py: calculate_scoring_modifiers)*
- [x] **F4. Combat effects on shooting** — Breakthrough/Breakaway/Crush for offense gives bonus even if shooter didn't fight; man-to-man with shooter interferes but doesn't prevent shot *(scoring.py: calculate_scoring_modifiers)*
- [x] **F5. Fallen shooter** — Can shoot at -4; shaken/injured during combat this turn also applies *(scoring.py: SCORE_MOD_PRONE)*
- [x] **F6. Broken arm auto-drop** — Figure with broken arm automatically drops ball before shooting *(scoring.py: attempt_score broken arm check)*
- [x] **F7. Standing defenders only** — Only standing opponents block shots; defenders get bonus from Block/Breakaway results *(scoring.py: calculate_scoring_modifiers)*

### Hit or Miss

- [x] **F8. Missed shot die** — 50% dead ball; 25% bounces to square left of line; 25% bounces to square right of line *(dice.py: roll_missed_shot, ball.py: resolve_missed_shot)*
- [x] **F9. Dropped ball after miss** — Rolls downhill to gutter next turn; figures in path may expend action + skill check to pick up (catchers get +2) *(ball.py: drop)*

### Base-to-Base Contact

- [ ] **F10. Contact definition** — At least 1/3 base overlap = in contact; two figures overlapping single slot below = all three in contact; diagonal (corner-to-corner only) = NOT in contact

### Timing / Hand-off Rules

- [ ] **F11. Hand-off timing** — Ball carrier can hand off anytime during movement when two figures come in base-to-base contact (start, finish, or passing a coned figure)
- [ ] **F12. Last-second hand-off on fall** — Falling ball carrier may attempt hand-off to teammate in base-to-base: check ball retention first, then receiving figure makes skill roll at -2
- [ ] **F13. Hand-off from prone** — Fallen ball carrier can hand off instead of standing; receiving figure gets -2 skill
- [ ] **F14. Loose ball pickup** — Use action to attempt pickup as ball passes through square during ball movement
- [ ] **F15. Initiative order tiebreaker** — Inside to out, left to right; for loose balls: order of figures ball would contact rolling to gutter

### Packs

- [ ] **F16. Skater packs** — 2–4 figures moving together at speed of slowest; must be same ring, bases touching (no diagonal); can rearrange during move but must end bases touching
- [ ] **F17. Pack obstacle rolls** — All figures in pack must make skill roll when passing over obstacle
- [ ] **F18. Bike-tow packs** — Move at cycle speed; towed skaters move with bike even if other figures in front would normally move first; skaters in sector behind bike can move at same time as bike

### Controlling a Square

- [ ] **F19. Control bonus** — Controlling team gets +1 combat bonus; fallen/unconscious/dead don't count toward control
- [ ] **F20. Control prevents passage** — Opponents cannot pass through or stop in controlled square without Assault

### Obstacles

- [ ] **F21. Obstacle skill check** — Skill check required when entering square with obstacle or when obstacle appears in current square
- [ ] **F22. Obstacle types** — Fallen bikes, flaming gas spills, sprawled figures (dead/unconscious/injured/badly injured), unfielded fast ball
- [ ] **F23. Non-obstacles** — Fallen figure still attempting to stand (turned 180°); fielded/slow ball
- [ ] **F24. Full/controlled squares** — Cannot enter full squares or controlled squares (no skill check, must go around); for bikes: 2 left slots occupied = cannot pass
- [ ] **F25. Random obstacle slot** — Optional: roll d6 for floor, d4 for incline to determine obstacle location

### Getting Injured Teammates Off Field

- [ ] **F26. Carrying injured figures** — 1 figure carries at half speed (no downhill bonus); 2 figures carry at lowest normal speed (no downhill bonus)
- [ ] **F27. Pickup and handoff timing** — 1 action + 1 full turn to pick up; 1 full turn to hand to infield teammates; passing over wall takes 2 turns

### Cannon Track Interactions

- [ ] **F28. Biker thrown to cannon track** — 50% chance if thrown from upper track; cycle 50/50 cannon track vs upper ring
- [ ] **F29. Major wreck through fence** — If thrown >3 squares from upper track: 50% chance of leaving track entirely (pulling fence down); otherwise 50% cannon track
- [ ] **F30. Dragging figure onto cannon track** — Same as attacking fallen figure (penalty check); requires skill check; speed halved while dragging (unless being towed)
- [ ] **F31. Ball hitting figure on cannon track** — Fatal injury dice with BDD; Very Hot ball = fatal injury (no BDD); Hot ball = non-fatal injury dice
- [ ] **F32. Ball hitting cycle on cannon track** — Explodes on 3–6 (Big Explosion); Very Hot = explodes on 5–6 (regular Explosion)
- [ ] **F33. Cannon track knockdown** — Any figure/cycle hit by ball on cannon track is knocked into top slot of upper track

---

## G. The Brawl — Combat

### General Combat

- [x] **G1. One fight per turn** — Each figure may engage in one fight per game turn (attacker or defender) *(figures.py: has_fought flag)*
- [x] **G2. Combat resolution** — Each side: sum combat values + modifiers + 2d6; higher total wins; difference looked up on combat chart *(combat.py: resolve_brawl, constants.py: get_brawl_result)*
- [x] **G3. Three combat chart columns** — Skill Checks (always first), then Brawl Results or Assault Results depending on fight type *(constants.py: get_skill_check_info, get_brawl_result, get_assault_result)*
- [x] **G4. Four combat types** — Brawling, Man to Man, Assault, The Swoop *(constants.py: CombatType, combat.py)*

### Combat Table — Skill Checks Column

- [x] **G5. Difference 0–2** — All make skill roll; fail = fall + toughness check; no fatalities on injury dice *(constants.py: get_skill_check_info, combat.py: _apply_skill_checks)*
- [x] **G6. Difference 3–5** — Losers roll skill; fail = fall + toughness check; no fatalities *(constants.py: get_skill_check_info)*
- [x] **G7. Difference 6–8** — Losers roll skill -1; fail = fall + toughness check; no fatalities *(constants.py: get_skill_check_info)*
- [x] **G8. Difference 9–11** — Losers roll skill -2; fall + toughness -1; fatality on injury dice *(constants.py: get_skill_check_info)*
- [x] **G9. Difference 12–14** — Losers roll skill -3; fall + toughness -2; fatality on injury dice *(constants.py: get_skill_check_info)*
- [x] **G10. Difference 15+** — Losers automatically fall; toughness -3; fatality with Blue Die of Death *(constants.py: get_skill_check_info)*

### Brawling

- [x] **G11. Base-to-base requirement** — Fight only between figures in base-to-base contact (side-by-side or end-to-end, NOT diagonal) *(combat.py: resolve_brawl)*
- [ ] **G12. Combat order** — Left to right, inside out; attacker picks ONE opposing figure; all teammates in base-to-base with target may join; all opponents in base-to-base with participants may also join
- [ ] **G13. Optional fighting** — A figure is not required to fight; may choose which fight to join if multiple options
- [x] **G14. Single roll per side** — One 2d6 roll for each side; results apply to all active participants *(combat.py: resolve_brawl)*

### Brawl Results Column

- [x] **G15. Difference 0–2: Indecisive** — All standing participants go man-to-man *(combat.py: resolve_brawl, constants.py: CombatResult.INDECISIVE)*
- [x] **G16. Difference 3–5: Marginal** — Winning side may choose to go man-to-man *(combat.py, constants.py: CombatResult.MARGINAL)*
- [x] **G17. Difference 6–8: Decisive** — If winners above or behind, may switch with losers *(combat.py, constants.py: CombatResult.DECISIVE)*
- [x] **G18. Difference 9–11: Breakthrough** — Winners may switch squares with losers *(combat.py, constants.py: CombatResult.BREAKTHROUGH)*
- [x] **G19. Difference 12–14: Breakaway** — Winners switch with losers + move 1 forward; losers move 1 back *(combat.py, constants.py: CombatResult.BREAKAWAY)*
- [x] **G20. Difference 15+: Breakaway** — Same as 12–14 *(combat.py, constants.py: CombatResult.CRUSH)*

### Man to Man

- [x] **G21. Man-to-man pairing** — Even numbers: pair off with nearest opponent; odd figure out may move or double up *(combat.py: _pair_man_to_man, resolve_man_to_man)*
- [x] **G22. Man-to-man drift** — First turn: drift 3 squares forward in same ring; second turn: 2; decreasing by 1 each turn until stopped; obstacle skill checks at -2 for both *(figures.py: man_to_man_drift)*
- [x] **G23. Man-to-man continuation** — Continue fighting until one or both fall; winner must break off or risk penalty for attacking fallen figure *(combat.py: resolve_man_to_man)*
- [x] **G24. Upper hand bonus** — Slightly higher result in man-to-man gets +1 next round; no positional advantage *(combat.py: resolve_man_to_man, figures.py: man_to_man_upper_hand)*
- [x] **G25. Joining man-to-man** — Additional figures joining = treated as regular brawl *(combat.py)*
- [x] **G26. Man-to-man limitations** — No actions; catchers can't field ball or protect teammates; CAN hand off ball (-2) and CAN make scoring attempt (-2) *(constants.py: SCORE_MOD_MAN_TO_MAN)*

### Assaults

- [x] **G27. Assault purpose** — Take over a controlled square *(combat.py: resolve_assault)*
- [x] **G28. Assault max participants** — 8 total (4 per side); nearby figures can support *(combat.py: resolve_assault max 4 per side)*
- [x] **G29. Assault winning side skill check** — ALL winners must make skill roll -1 to stay on feet regardless of result *(combat.py: resolve_assault)*
- [x] **G30. Assault results: 0–2 Fails** — All stay in original squares *(constants.py: AssaultResult.FAILS)*
- [x] **G31. Assault results: 3–5 Marginal** — Original team keeps control *(constants.py: AssaultResult.MARGINAL)*
- [x] **G32. Assault results: 6–8 Decisive** — Losers lose control; winners may switch 2 figures *(constants.py: AssaultResult.DECISIVE)*
- [x] **G33. Assault results: 9–11 Breakthrough/Block** — Winners gain/keep control *(constants.py: AssaultResult.BREAKTHROUGH_BLOCK)*
- [x] **G34. Assault results: 12–14 Breakthrough/Block** — Winners gain/keep; push losers back 1 square *(constants.py)*
- [x] **G35. Assault results: 15+ Crush** — Winners gain/keep; push losers back 1 square *(constants.py: AssaultResult.CRUSH)*
- [ ] **G36. Goal sector push direction** — If defense controlling goal square: 50% pushed left, 50% pushed right (even/odd die roll)

### The Swoop

- [x] **G37. Swoop definition** — Single figure uses incline to build speed and tackles/dropkicks opponent; swooper automatically falls *(combat.py: resolve_swoop)*
- [x] **G38. Swoop priority** — Resolved FIRST before any other combat in the sector; no other figures can join *(combat.py: resolve_swoop)*
- [ ] **G39. Swoop requirements** — Must move down at least 1 ring; attack from slot above target; must move individually (no pack, no tow); cannot participate in any other attack that turn as supporting figure
- [ ] **G40. One swoop per square/pack** — Only one swoop per square or single pack per turn
- [x] **G41. Swoop vs biker** — Decisive or higher = biker skips skill check, auto-rolls cycle chart *(combat.py: resolve_swoop)*
- [ ] **G42. Swoop vs man-to-man pair** — Can swoop the pair, but attack targets BOTH — risk injuring own teammate
- [x] **G43. Swoop winner** — Does not make toughness check (landed correctly); loser: toughness -1 penalty in addition to normal checks *(combat.py: resolve_swoop)*

### Combat Modifiers

- [ ] **G44. Supporting figures** — +1 per adjacent figure (including diagonal); not fallen/injured/unconscious; does NOT count as figure's fight; no skill checks after
- [ ] **G45. Holding cycle tow bar** — +1
- [ ] **G46. Slot directly above opponent** — +1
- [x] **G47. Using ball as weapon** — +3 (skill check + penalty check) *(constants.py: MOD_BALL_AS_WEAPON)*
- [ ] **G48. Team controls square** — +1
- [x] **G49. Upper hand in man-to-man** — +1 *(combat.py: resolve_man_to_man)*
- [x] **G50. Moving vs standing** — +2 (single modifier regardless of participant count) *(combat.py: calculate_combat_modifiers, constants.py: MOD_MOVING_VS_STANDING)*
- [ ] **G51. Slot directly behind opponent (skating)** — +2 (not in standing fistfight)
- [ ] **G52. Letting go of tow bar into fight** — +2 (must have held for ≥ half bike's move or ≥ 1 full turn before)
- [x] **G53. Swoop bonus** — +2 (attacker automatically falls) *(combat.py: resolve_swoop, constants.py: MOD_SWOOP)*
- [x] **G54. Shaken/injured penalty** — -1 / -2 *(combat.py: calculate_combat_modifiers, constants.py: MOD_SHAKEN, MOD_BADLY_SHAKEN)*
- [x] **G55. Attacking fallen figure (illegal)** — +4 (penalty check) *(combat.py: calculate_combat_modifiers)*
- [x] **G56. Skater hitting biker (illegal)** — +4 (penalty check) *(combat.py: calculate_combat_modifiers)*
- [x] **G57. Using bike as weapon (illegal)** — +5 (penalty check) *(constants.py: MOD_BIKE_AS_WEAPON)*

---

## H. Postgame — Optional Rules

- [ ] **H1. Stretcher bearers** — One pair at each infield entrance; 2 slots; move 3 sq/turn; move last in sector; can travel any direction; can dive over wall; 1 turn to pick up; only go to lower ring for bikes, middle ring for figures; attacking them = 1 period penalty + they refuse to help that team for rest of game
- [x] **H2. Maximum penalties allowed** — Figure ejected after 5 penalties (configurable: 4–6) *(penalties.py: ejection_threshold)*
- [ ] **H3. Endurance rules** — Max playing time = Toughness + 3 minutes; then rest 3–6 min; exceed limit: -1 to all stats per block exceeded; each combat subtracts 1 min from endurance; bikes = rolling rest stops (no endurance loss while towed); standing still = no endurance loss
- [ ] **H4. Compressing time — 2-minute rule** — Each game turn = 2 minutes; 3-min penalties round up to 4
- [ ] **H5. Compressing time — 3-hour rule** — Set real-time limit per period; play as many game turns as possible

### Team Generation

- [x] **H6. Team roster** — 20 members: 10 skaters (6 bruisers speed 5, 4 speeders speed 7), 6 bikers (speed 2/12), 4 catchers (speed 6) *(team.py: generate_roster)*
- [x] **H7. Stat generation** — Skill base 5 + d6 (bruiser -1 unless roll is 1); Combat base 4 + d6 (bruiser +1 unless 6, biker -2); Toughness base 5 + d6 (bruiser +1 unless 6) *(team.py: _make_figure, _make_biker)*
- [x] **H8. Team building points** — 6 points per team; spend 1 to keep a die result of 6 (otherwise that roll of 6 is reduced by 2 to a 4); spend 1 to reroll any die; once all 6 points are spent, any future rolls of 6 are automatically reduced by 2 *(team.py: _roll_stat)*
- [x] **H9. Stat maximums** — Skill max 11, Combat max 10, Toughness max 11 *(team.py: _make_figure, constants.py)*

### Season Play

- [ ] **H10. Season structure** — 10-game season + playoffs/championship
- [ ] **H11. Between games** — Empty slots filled; damaged cycles repaired/replaced; badly injured out for half season
- [ ] **H12. Replacement figures** — Same type; stats generated with die roll; 4 teambuilding points per entire season
- [ ] **H13. Season stat progression** — Surviving figure who played ≥50% of games: +1 to any stat (except speed) up to max; league leader (most points or kills): +1 to two stats
- [ ] **H14. Next season** — 6 new points for replacements; 10-year veteran may retire; if continues: speed -1 per season, all stats -1 per season

---

## I. Quantum Movement & Miscellaneous Reminders

- [ ] **I1. Unmoved figure rule** — Upright figure without cone is not considered "there" for blocking, controlling, hand-offs, or taking ball
- [x] **I2. Penalty dice always rolled** — Regardless of whether penalty is actually called, dice are rolled for every infraction *(penalties.py: check_infraction always rolls)*
- [ ] **I3. Dead ball field reset** — Full reset only after: successful goal or failed scoring attempt resulting in dead ball; all other dead balls: cannon fires next turn, players stay where they are
- [ ] **I4. Cone marking** — Always mark moved figures with cones; absolutely key to game flow

---

## Game Engine & GUI Implementation Tasks

- [ ] **GUI1. Circular track board rendering** — 12 sectors × 5 rings with correct square counts; slots within squares
- [ ] **GUI2. Figure rendering** — Skaters (bruisers/speeders), catchers, bikers with stats displayed; team colors
- [ ] **GUI3. Ball visualization** — Cannon fire animation, ball movement clockwise, hot/warm/cool state indicators
- [ ] **GUI4. Turn phase UI** — Clear indication of current phase (Clock, Ball, Initiative, Movement, Combat, Score)
- [ ] **GUI5. Initiative tracker** — Show current sector with initiative; highlight active sector
- [ ] **GUI6. Cone/marker system** — Visual markers for moved figures, man-to-man pairs, fallen figures, obstacles
- [ ] **GUI7. Dice rolling UI** — Animated dice rolls for 2d6, d12, d6, injury dice, direction die, missed-shot die
- [ ] **GUI8. Penalty box & timer display** — Off-track area showing penalized/shaken/resting figures with countdown
- [ ] **GUI9. Scoreboard** — Period, time remaining, score for each team
- [ ] **GUI10. HUD for selected figure** — Show stats (Speed, Skill, Combat, Toughness), current modifiers, status (shaken/injured/etc.)
- [ ] **GUI11. Movement highlighting** — Show legal move destinations when figure selected; show incline cost/bonus
- [ ] **GUI12. Combat resolution overlay** — Show combat totals, modifiers, result lookup, and outcome
- [ ] **GUI13. AI engine — computer player** — Decision-making for movement, combat initiation, scoring attempts, pack formation, tow bar usage
- [ ] **GUI14. Game mode selection** — Computer vs Computer (simulation) or Human vs Computer
- [ ] **GUI15. Team generation screen** — Create teams with stat rolling per rules H6–H9
- [ ] **GUI16. Replay / log** — Turn-by-turn game log for reviewing what happened
