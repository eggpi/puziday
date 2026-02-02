import pprint
from dataclasses import dataclass

GRID_ROWS = 8
GRID_COLS = 7
NUM_CELLS_TO_COVER = GRID_COLS * GRID_ROWS - 3 - 6

@dataclass(eq = True, frozen = True)
class Piece:
    name: str
    edges: tuple[str]

PIECES = [
    Piece(name = 'Pento L', edges = ('L', 'U', 'U', 'U')),
    Piece(name = 'Pento T', edges = ('R', 'R', 'U', 'DD')),
    Piece(name = 'Pento P', edges = ('R', 'R', 'D', 'L')),
    Piece(name = 'Pento N', edges = ('R', 'U', 'R', 'R')),
    Piece(name = 'Pento V', edges = ('R', 'R', 'D', 'D')),
    Piece(name = 'Pento U', edges = ('U', 'R', 'R', 'D')),
    Piece(name = 'Pento Z', edges = ('R', 'D', 'D', 'R')),
    Piece(name = 'Tetr I', edges = ('R', 'R', 'R')),
    Piece(name = 'Tetr S', edges = ('R', 'U', 'R')),
    Piece(name = 'Tetr L', edges = ('L', 'U', 'U')),
]

def rotate_90deg_counterclockwise(piece: Piece):
    edges = []
    for e in piece.edges:
        if e.startswith('L'):
            edges.append('D' * len(e))
        elif e.startswith('U'):
            edges.append('L' * len(e))
        elif e.startswith('R'):
            edges.append('U' * len(e))
        elif e.startswith('D'):
            edges.append('R' * len(e))
        else:
            raise ValueError(e)
    return Piece(piece.name, tuple(edges))

def mirror_vertically(piece: Piece):
    edges = []
    for e in piece.edges:
        if e.startswith('L'):
            edges.append('R' * len(e))
        elif e.startswith('U'):
            edges.append('U' * len(e))
        elif e.startswith('R'):
            edges.append('L' * len(e))
        elif e.startswith('D'):
            edges.append('D' * len(e))
    return Piece(piece.name, tuple(edges))

# Generate all possible orientations of each piece; they won't be distinct
# as the same (visual) orientation can be encoded as different sequences of
# edges. We will uniquify them later when we turn these orientations into
# placements on the board.
ORIENTATIONS = {}
for piece in PIECES:
    ORIENTATIONS[piece.name] = {piece}
    for i in range(4):
        piece = rotate_90deg_counterclockwise(piece)
        ORIENTATIONS[piece.name].add(piece)
    piece = mirror_vertically(piece)
    for i in range(4):
        piece = rotate_90deg_counterclockwise(piece)
        ORIENTATIONS[piece.name].add(piece)

@dataclass(eq = True, frozen = True)
class Cell:
    row: int
    col: int

@dataclass(eq = True, frozen = True)
class Placement:
    piece: Piece
    cells: frozenset[Cell]

    def satisfied_constraints(self):
        return [self.piece.name] + list(self.cells)

def compute_placement(cell, piece):
    cells = [cell]
    row, col = cell.row, cell.col
    for edge in piece.edges:
        if edge.startswith('U'):
            row -= len(edge)
        elif edge.startswith('D'):
            row += len(edge)
        elif edge.startswith('L'):
            col -= len(edge)
        elif edge.startswith('R'):
            col += len(edge)
        cells.append(Cell(row, col))

    # Validate all cells
    for cell in cells:
        row, col = cell.row, cell.col
        if row < 0 or row >= GRID_ROWS:
            return None
        if col < 0 or col >= GRID_COLS:
            return None
        if row in (0, 1) and col == GRID_COLS - 1:
            return None
        if row == GRID_ROWS - 1 and col < 4:
            return None
    return Placement(piece, frozenset(cells))

PLACEMENTS = set()
for row in range(GRID_ROWS):
    for col in range(GRID_COLS):
        cell = Cell(row, col)
        for piece_name, orientations in ORIENTATIONS.items():
            for piece in orientations:
                placement = compute_placement(cell, piece)
                if placement is not None:
                    PLACEMENTS.add(placement)

# 1 = January, 12 = December
def month_to_cell(month: int):
    return Cell((month - 1) // 6, (month - 1) % 6)

def day_to_cell(day: int):
    return Cell(2 + (day - 1) // GRID_COLS, (day - 1) % GRID_COLS)

# 1 = Sunday, 7 = Saturday
def day_of_week_to_cell(day_of_week: int):
    return [
        Cell(6, 3),
        Cell(6, 4),
        Cell(6, 5),
        Cell(6, 6),
        Cell(7, 4),
        Cell(7, 5),
        Cell(7, 6),
    ][day_of_week - 1]

def solve_for_day(month: int, day: int, day_of_week: int):
    month = month_to_cell(month)
    day = day_to_cell(day)
    day_of_week = day_of_week_to_cell(day_of_week)

    all_placements = set()
    for placement in PLACEMENTS:
        if month not in placement.cells and \
                day not in placement.cells and \
                day_of_week not in placement.cells:
            all_placements.add(placement)
    return solve_x(all_placements)

def solve_x(all_placements):
    # Build the adjacency matrix with one constraint (column) per cell and piece.
    # We represent it as a dict where keys are columns and rows are set values.
    constraint_to_placements = {}
    for piece in PIECES:
        constraint_to_placements[piece.name] = {
            p for p in all_placements if p.piece.name == piece.name}
    for placement in all_placements:
        for cell in placement.cells:
            constraint_to_placements.setdefault(cell, set()).add(placement)
    assert(len(constraint_to_placements) == len(PIECES) + NUM_CELLS_TO_COVER)

    def prune(satisfied_constraints, constraint_to_placements):
        removed_constraints = []
        for satisfied_constraint in satisfied_constraints:
            placements_to_remove = constraint_to_placements[satisfied_constraint]
            removed_constraints.append(set(placements_to_remove))
            # Remove all placements that could satisfy one of the
            # constraints of the next_placement.
            for placement_to_remove in list(placements_to_remove):
                for other_constraint in placement_to_remove.satisfied_constraints():
                    constraint_to_placements[other_constraint].remove(placement_to_remove)
            assert not constraint_to_placements[satisfied_constraint]
            del constraint_to_placements[satisfied_constraint]
        return removed_constraints

    def backtrack(satisfied_constraints, removed_constraints, constraint_to_placements):
        # Backtrack. removed_constraints contains the placements (rows) for each of
        # the satisfied_constraints, in reverse order.
        for satisfied_constraint in reversed(satisfied_constraints):
            assert satisfied_constraint not in constraint_to_placements
            constraint_to_placements[satisfied_constraint] = removed_constraints.pop()
            for placement_to_restore in list(constraint_to_placements[satisfied_constraint]):
                for other_constraint in placement_to_restore.satisfied_constraints():
                    constraint_to_placements[other_constraint].add(placement_to_restore)
        assert not removed_constraints

    def solve(constraint_to_placements, level = 0):
        if not constraint_to_placements:
            return []
        constraint = min(constraint_to_placements,
                         key = lambda c: len(constraint_to_placements[c]))
        if not constraint_to_placements[constraint]:
            return None
        for next_placement in list(constraint_to_placements[constraint]):
            print(' ' * level * 2 + f'{next_placement.piece.name}')
            satisfied_constraints = next_placement.satisfied_constraints()
            removed_constraints = prune(satisfied_constraints,
                                        constraint_to_placements)
            assert removed_constraints
            assert removed_constraints[0]
            solution = solve(constraint_to_placements, level = level + 1)
            if solution is not None:
                return [next_placement] + solution
            backtrack(satisfied_constraints, removed_constraints,
                      constraint_to_placements)
        return None
    return solve(constraint_to_placements)

def solve_naive(all_placements):
    cell_to_placements = {}
    for placement in all_placements:
        for cell in placement.cells:
            cell_to_placements.setdefault(cell, []).append(placement)

    piece_name_to_placements = {}
    for placement in all_placements:
        piece_name_to_placements.setdefault(placement.piece.name, []).append(placement)

    def solve(num_cells_to_cover, available_placements, level = 0):
        assert num_cells_to_cover >= 0, num_cells_to_cover
        if num_cells_to_cover == 0:
            return []
        if not available_placements:
            return None

        for next_placement in list(available_placements):
            removed_placements = set()
            # Remove all placements for next_placement's piece.
            for p in piece_name_to_placements[next_placement.piece.name]:
                if p in available_placements:
                    available_placements.remove(p)
                    removed_placements.add(p)
            # Remove all other placements that overlap with its cells.
            for c in next_placement.cells:
                for p in cell_to_placements[c]:
                    if p in available_placements:
                        available_placements.remove(p)
                        removed_placements.add(p)
            # print(' ' * level * 2 + next_placement.piece.name + f' ({len(next_placement.cells)})')
            solution = solve(num_cells_to_cover - len(next_placement.cells),
                             available_placements, level + 1)
            if solution is not None:
                return [next_placement] + solution
            available_placements.update(removed_placements)
        return None
    return solve(NUM_CELLS_TO_COVER, all_placements)

pprint.pprint(solve_for_day(month = 2, day = 3, day_of_week = 3))
