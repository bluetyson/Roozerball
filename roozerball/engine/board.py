"""Board / track model for Roozerball.

12-sector circular inclined track with concentric rings (Rules C1-C20).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from roozerball.engine.constants import (
    Ring, SECTORS, SQUARES_PER_RING, SLOTS_INCLINE, SLOTS_FLOOR,
    TeamSide, FigureType, FigureStatus,
    DOWNHILL_CONSECUTIVE, UPHILL_CONSECUTIVE_EXTRA, STARTING_SECTOR_CYCLE,
    NUM_SECTORS,
)


# ---------------------------------------------------------------------------
# Slot
# ---------------------------------------------------------------------------

@dataclass
class Slot:
    """One position within a square where a figure can stand."""
    index: int
    figure: Any = None            # Figure reference (duck typed)


# ---------------------------------------------------------------------------
# Square
# ---------------------------------------------------------------------------

@dataclass
class Square:
    """One square on the track."""
    sector_index: int
    ring: Ring
    position: int                  # 0-based position within ring for this sector
    slots: List[Slot] = field(default_factory=list)
    is_goal: bool = False
    goal_side: Optional[TeamSide] = None
    has_obstacle: bool = False
    obstacle_type: Optional[str] = None
    is_on_fire: bool = False

    def __post_init__(self) -> None:
        if not self.slots:
            cap = SLOTS_FLOOR if self.ring == Ring.FLOOR else SLOTS_INCLINE
            self.slots = [Slot(i) for i in range(cap)]

    # -- properties --
    @property
    def capacity(self) -> int:
        return SLOTS_FLOOR if self.ring == Ring.FLOOR else SLOTS_INCLINE

    @property
    def occupied_slots(self) -> int:
        return sum(1 for s in self.slots if s.figure is not None)

    @property
    def is_full(self) -> bool:
        return self.occupied_slots >= self.capacity

    def has_space_for(self, figure_type: FigureType) -> bool:
        needed = 2 if figure_type == FigureType.BIKER else 1
        return (self.capacity - self.occupied_slots) >= needed

    def figures_in_square(self) -> List[Any]:
        return [s.figure for s in self.slots if s.figure is not None]

    def team_figures(self, team_side: TeamSide) -> List[Any]:
        return [f for f in self.figures_in_square()
                if getattr(f, 'team', None) == team_side]

    def _upright_team_count(self, team_side: TeamSide) -> int:
        return sum(1 for f in self.team_figures(team_side)
                   if getattr(f, 'status', None) in
                   (FigureStatus.STANDING, FigureStatus.MAN_TO_MAN))

    def is_controlled_by(self, team_side: TeamSide) -> bool:
        """Rule C6: >50% upright figures = control."""
        total = sum(1 for f in self.figures_in_square()
                    if getattr(f, 'status', None) in
                    (FigureStatus.STANDING, FigureStatus.MAN_TO_MAN))
        if total == 0:
            return False
        return self._upright_team_count(team_side) / total > 0.5

    def is_controlled_by_active(self, team_side: TeamSide) -> bool:
        """Rule I1 variant: only count moved/coned figures for control check."""
        moved = [f for f in self.figures_in_square()
                 if getattr(f, 'has_moved', True)  # default True → count
                 and getattr(f, 'status', None) in (FigureStatus.STANDING, FigureStatus.MAN_TO_MAN)]
        if not moved:
            return False
        team_moved = sum(1 for f in moved if getattr(f, 'team', None) == team_side)
        return team_moved / len(moved) > 0.5

    def controlling_team(self) -> Optional[TeamSide]:
        for side in TeamSide:
            if self.is_controlled_by(side):
                return side
        return None

    def is_obstacle_square(self) -> bool:
        """Rule F22: Square is an obstacle if it has a fallen bike, fire, dead/unconscious figure,
        or a fast unfielded ball."""
        if self.is_on_fire:
            return True
        for f in self.figures_in_square():
            status = getattr(f, 'status', None)
            if getattr(f, 'is_biker', False) and (
                    getattr(f, 'feet_down', False) or getattr(f, 'cycle_damaged', False)):
                return True  # fallen bike
            if status in (FigureStatus.DEAD, FigureStatus.UNCONSCIOUS):
                return True  # sprawled figure
            if (status in (FigureStatus.INJURED, FigureStatus.BADLY_SHAKEN)
                    and not getattr(f, 'needs_stand_up', False)):
                return True  # sprawled injured
        return self.has_obstacle

    def is_non_obstacle(self, figure: Any) -> bool:
        """Rule F23: A figure in this square is NOT an obstacle if it's still trying to stand (180°)."""
        return (getattr(figure, 'needs_stand_up', False)
                and getattr(figure, 'status', None) not in (FigureStatus.DEAD, FigureStatus.UNCONSCIOUS))

    def add_figure(self, figure: Any, slot_index: Optional[int] = None) -> bool:
        """Place figure; default lower-left (Rule C5). Returns success."""
        needed = 2 if getattr(figure, 'figure_type', None) == FigureType.BIKER else 1
        if slot_index is not None:
            if slot_index + needed <= len(self.slots):
                if all(self.slots[slot_index + k].figure is None for k in range(needed)):
                    for k in range(needed):
                        self.slots[slot_index + k].figure = figure
                    return True
            return False
        # Auto-place in first available
        for i in range(len(self.slots) - needed + 1):
            if all(self.slots[i + k].figure is None for k in range(needed)):
                for k in range(needed):
                    self.slots[i + k].figure = figure
                return True
        return False

    def remove_figure(self, figure: Any) -> None:
        for s in self.slots:
            if s.figure is figure:
                s.figure = None

    def __repr__(self) -> str:
        return f"Square({SECTORS[self.sector_index]},{self.ring.name},{self.position})"


# ---------------------------------------------------------------------------
# Sector
# ---------------------------------------------------------------------------

@dataclass
class Sector:
    """Contains all squares for one sector."""
    index: int
    name: str
    rings: Dict[Ring, List[Square]] = field(default_factory=dict)

    def all_squares(self) -> List[Square]:
        """All squares in initiative order: floor→lower→middle→upper→cannon,
        left to right within each ring (Rule C8)."""
        result: List[Square] = []
        for ring in [Ring.FLOOR, Ring.LOWER, Ring.MIDDLE, Ring.UPPER, Ring.CANNON]:
            result.extend(self.rings.get(ring, []))
        return result

    def squares_in_ring(self, ring: Ring) -> List[Square]:
        return self.rings.get(ring, [])

    def all_figures(self) -> List[Any]:
        """All figures in initiative order."""
        figs: List[Any] = []
        for sq in self.all_squares():
            figs.extend(sq.figures_in_square())
        return figs


# ---------------------------------------------------------------------------
# Goal
# ---------------------------------------------------------------------------

@dataclass
class Goal:
    """A goal on the outer wall (Rule C20, A4)."""
    side: TeamSide
    sector_index: int
    scoring_squares: List[Square] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Board
# ---------------------------------------------------------------------------

class Board:
    """The complete 12-sector circular track."""

    def __init__(self) -> None:
        self.sectors: List[Sector] = []
        self.goals: Dict[TeamSide, Goal] = {}
        self.home_goal_sector = 0    # sector A
        self.visitor_goal_sector = 6 # sector G
        self._build()

    def _build(self) -> None:
        # Create sectors
        for i, name in enumerate(SECTORS):
            rings: Dict[Ring, List[Square]] = {}
            for ring in Ring:
                count = SQUARES_PER_RING[ring]
                rings[ring] = [Square(i, ring, p) for p in range(count)]
            self.sectors.append(Sector(i, name, rings))

        # Set up goals (Rule A4, C20)
        for side, si in [(TeamSide.HOME, self.home_goal_sector),
                         (TeamSide.VISITOR, self.visitor_goal_sector)]:
            sector = self.sectors[si]
            scoring_sqs = sector.squares_in_ring(Ring.UPPER)
            for sq in scoring_sqs:
                sq.is_goal = True
                sq.goal_side = side
            self.goals[side] = Goal(side, si, scoring_sqs)

    # -- access --
    def get_square(self, sector_index: int, ring: Ring, position: int) -> Square:
        return self.sectors[sector_index].rings[ring][position]

    def get_sector(self, sector_index: int) -> Sector:
        return self.sectors[sector_index]

    def next_sector(self, sector_index: int) -> int:
        """Counterclockwise (forward). Rule A3, C9."""
        return (sector_index + 1) % 12

    def prev_sector(self, sector_index: int) -> int:
        """Clockwise (backward)."""
        return (sector_index - 1) % 12

    def sector_distance(self, from_s: int, to_s: int) -> int:
        """Counterclockwise distance."""
        return (to_s - from_s) % 12

    def are_in_base_to_base_contact(self, sq1: Square, sq2: Square) -> bool:
        """Rule F10: At least 1/3 base overlap = in contact.

        Two squares are in contact if they share a side (same ring adjacent sector,
        or same sector adjacent ring). Diagonal (corner-to-corner) is NOT contact.
        """
        if sq1 is sq2:
            return True
        same_sector = sq1.sector_index == sq2.sector_index
        adj_sector = abs((sq1.sector_index - sq2.sector_index + 12) % 12) in (1, 11)
        same_ring = sq1.ring == sq2.ring
        adj_ring = abs(sq1.ring.value - sq2.ring.value) == 1

        # Side-by-side in same ring (different sectors)
        if same_ring and adj_sector and sq1.position == sq2.position:
            return True
        # Same sector, adjacent rings
        if same_sector and adj_ring and sq1.position == sq2.position:
            return True
        return False

    def get_adjacent_squares(self, square: Square) -> List[Square]:
        """Squares adjacent (same sector cross-ring, same ring adjacent sector)."""
        result: List[Square] = []
        si = square.sector_index
        ring = square.ring

        # Same sector, adjacent rings
        for r in Ring:
            if abs(r.value - ring.value) == 1 and r != Ring.CANNON:
                result.extend(self.sectors[si].rings[r])
            elif ring == Ring.CANNON and r == Ring.UPPER:
                result.extend(self.sectors[si].rings[r])
            elif r == Ring.CANNON and ring == Ring.UPPER:
                pass  # Cannon track separate (Rule C7)

        # Same ring, adjacent sectors
        for adj_si in [self.next_sector(si), self.prev_sector(si)]:
            for sq in self.sectors[adj_si].rings.get(ring, []):
                result.append(sq)

        return result

    def get_initiative_order(self, starting_sector: int) -> List[int]:
        """Return sector indices starting from given, clockwise through 12 (Rule T4)."""
        return [(starting_sector + i) % 12 for i in range(12)]

    def squares_in_initiative_order(self, sector_index: int) -> List[Square]:
        """Squares within a sector in initiative order (inside→outside, left→right)."""
        return self.sectors[sector_index].all_squares()

    def figures_in_initiative_order(self, starting_sector: int) -> List[Any]:
        """All figures ordered by sector initiative and square slot order."""
        figures: List[Any] = []
        seen: set[int] = set()
        for sector_index in self.get_initiative_order(starting_sector):
            for square in self.squares_in_initiative_order(sector_index):
                for slot in square.slots:
                    figure = slot.figure
                    if figure is None:
                        continue
                    fig_id = id(figure)
                    if fig_id in seen:
                        continue
                    seen.add(fig_id)
                    figures.append(figure)
        return figures

    def find_square_of_figure(self, figure: Any) -> Optional[Square]:
        """Locate the square currently holding a figure."""
        for sector in self.sectors:
            for square in sector.all_squares():
                if any(slot.figure is figure for slot in square.slots):
                    return square
        return None

    def place_figure(
        self,
        figure: Any,
        sector_index: int,
        ring: Ring,
        position: int,
        slot_index: Optional[int] = None,
    ) -> bool:
        """Place a figure on the specified square and update its position fields."""
        current_square = self.find_square_of_figure(figure)
        if current_square is not None:
            current_square.remove_figure(figure)

        square = self.get_square(sector_index, ring, position)
        if not square.add_figure(figure, slot_index):
            return False

        self._update_figure_position(figure, square)
        return True

    def move_figure(
        self,
        figure: Any,
        destination: Square,
        slot_index: Optional[int] = None,
    ) -> bool:
        """Move a figure from its current square to another square."""
        origin = self.find_square_of_figure(figure)
        if origin is None:
            return False
        origin.remove_figure(figure)
        if not destination.add_figure(figure, slot_index):
            origin.add_figure(figure)
            return False
        self._update_figure_position(figure, destination)
        return True

    def place_starting_positions(
        self,
        home_figures: List[Any],
        visitor_figures: List[Any],
    ) -> None:
        """Place figures in the standard middle-ring starting sectors."""
        self.clear_all_figures()
        self.clear_figure_positions(home_figures + visitor_figures)
        self._place_team_starting_figures(home_figures, TeamSide.HOME)
        self._place_team_starting_figures(visitor_figures, TeamSide.VISITOR)

    def calculate_incline_bonus(self, ring_changes: List[int]) -> int:
        """Compute speed bonus/cost for ring transitions.

        ring_changes: list of +1 (uphill) or -1 (downhill) per step.
        Returns net bonus (positive = extra squares, negative = extra cost).
        Rules C10-C11.
        """
        bonus = 0
        consecutive_down = 0
        consecutive_up = 0
        for change in ring_changes:
            if change < 0:  # downhill
                consecutive_up = 0
                if consecutive_down < len(DOWNHILL_CONSECUTIVE):
                    bonus += DOWNHILL_CONSECUTIVE[consecutive_down]
                else:
                    bonus += 1
                consecutive_down += 1
            elif change > 0:  # uphill
                consecutive_down = 0
                if consecutive_up < len(UPHILL_CONSECUTIVE_EXTRA):
                    bonus -= UPHILL_CONSECUTIVE_EXTRA[consecutive_up]
                else:
                    bonus -= 1
                consecutive_up += 1
            else:
                consecutive_down = 0
                consecutive_up = 0
        return bonus

    def clear_all_figures(self) -> None:
        for sector in self.sectors:
            for squares in sector.rings.values():
                for sq in squares:
                    for slot in sq.slots:
                        slot.figure = None

    def squares_in_range(self, from_square: Square, movement_points: int,
                         figure_type: FigureType = FigureType.SKATER_BRUISER
                         ) -> List[Tuple[Square, int]]:
        """All squares reachable with given movement points. Returns (square, cost) pairs.

        Uses BFS. Cannon track excluded for normal movement (Rule C7).
        Biker constraints: E3 (first-square-straight), E7 (90-degree turning).
        """
        from collections import deque
        from roozerball.engine.constants import BIKE_MAX_TURN_SPEED

        is_biker = figure_type == FigureType.BIKER

        # BFS state: (square, cost, last_changed_ring)
        visited: Dict[int, int] = {}   # id(square) -> min cost (ring-change state tracked in queue only)
        queue = deque([(from_square, 0, False)])
        visited[id(from_square)] = 0
        results: List[Tuple[Square, int]] = []

        while queue:
            sq, cost, last_changed_ring = queue.popleft()
            for adj in self._counterclockwise_adjacent_squares(sq):
                if adj.ring == Ring.CANNON:
                    continue  # Rule C7

                # E3: biker first step must be same ring + next sector counterclockwise
                if is_biker and cost == 0:
                    next_sector = (sq.sector_index + 1) % 12
                    if not (adj.ring == sq.ring and adj.sector_index == next_sector):
                        continue

                this_changes_ring = adj.ring != sq.ring

                # E7: biker turning constraints based on speed
                if is_biker and this_changes_ring:
                    if movement_points > BIKE_MAX_TURN_SPEED:
                        continue  # no ring changes at high speed
                    if last_changed_ring:
                        continue  # no consecutive ring changes at any speed

                step_cost = 1
                if adj.ring.value > sq.ring.value:
                    step_cost = 2  # uphill base cost
                new_cost = cost + step_cost
                if new_cost <= movement_points:
                    sq_id = id(adj)
                    if sq_id not in visited or visited[sq_id] > new_cost:
                        visited[sq_id] = new_cost
                        queue.append((adj, new_cost, this_changes_ring))
                        results.append((adj, new_cost))

        return results

    def _counterclockwise_adjacent_squares(self, square: Square) -> List[Square]:
        """Return legal movement adjacencies while preventing clockwise travel."""
        same_sector_ring_changes = [
            candidate
            for candidate in self.sectors[square.sector_index].all_squares()
            if abs(candidate.ring.value - square.ring.value) == 1
            and candidate.ring != Ring.CANNON
        ]
        forward_sector_squares = self.sectors[self.next_sector(square.sector_index)].rings.get(square.ring, [])
        return [*same_sector_ring_changes, *forward_sector_squares]

    def _place_team_starting_figures(
        self,
        figures: List[Any],
        team_side: TeamSide,
    ) -> None:
        sector_offset = 0 if team_side == TeamSide.HOME else 6
        placements = [
            ((cycle + sector_offset) % NUM_SECTORS, index % SQUARES_PER_RING[Ring.MIDDLE])
            for index, cycle in enumerate(STARTING_SECTOR_CYCLE * 4)
        ]
        for figure, (sector_index, position) in zip(figures, placements):
            if not self.place_figure(figure, sector_index, Ring.MIDDLE, position):
                fallback_positions = [
                    (position + offset) % SQUARES_PER_RING[Ring.MIDDLE]
                    for offset in range(1, SQUARES_PER_RING[Ring.MIDDLE])
                ]
                for fallback_position in fallback_positions:
                    if self.place_figure(figure, sector_index, Ring.MIDDLE, fallback_position):
                        break

    def clear_figure_positions(self, figures: List[Any]) -> None:
        for figure in figures:
            figure.sector_index = None
            figure.ring = None
            figure.square_position = None
            figure.slot_index = None

    def _update_figure_position(self, figure: Any, square: Square) -> None:
        figure.sector_index = square.sector_index
        figure.ring = square.ring
        figure.square_position = square.position
        figure.slot_index = next(
            (slot.index for slot in square.slots if slot.figure is figure),
            None,
        )
