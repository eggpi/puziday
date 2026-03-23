#!/usr/bin/env python3

import abc
import json
import os
import sys
import datetime
import pprint
from dataclasses import dataclass, asdict

CELL_SIZE_PX = 50

class Grid(abc.ABC):
    @abc.abstractmethod
    def grid_rows(self):
        pass

    @abc.abstractmethod
    def grid_cols(self):
        pass

    @abc.abstractmethod
    def validate_placement(self, placement: Placement):
        '''
        Validate that a placement doesn't cover a forbidden cell.

        Returns:
            valid: bool, whether the placement is valid.
        '''
        pass

    @abc.abstractmethod
    def month_to_cell(self, month: int):
        '''
        Compute the cell for a given month (1 = January, 12 = December).

        Returns:
            cell: Cell, the cell corresponding to that month in this grid.
        '''
        pass

    @abc.abstractmethod
    def day_to_cell(self, day: int):
        '''
        Compute the cell for a given day of the month (1 to 31).

        Returns:
            cell: Cell, the cell corresponding to the day in this grid.
        '''
        pass

    def day_of_week_to_cell(self, day_of_week: int):
        '''
        Compute the cell for a given day of the week (1 = Sunday, 7 = Saturday).

        Returns:
            cell: Cell, the cell corresponding to the day in this grid.
        '''
        pass

class PuzidayGrid(Grid):
    GRID_ROWS = 8
    GRID_COLS = 7

    def grid_rows(self):
        return self.GRID_ROWS

    def grid_cols(self):
        return self.GRID_COLS

    def validate_placement(self, placement):
        for cell in placement.cells:
            row, col = cell.row, cell.col
            if row < 0 or row >= self.GRID_ROWS:
                return False
            if col < 0 or col >= self.GRID_COLS:
                return False
            if row in (0, 1) and col == self.GRID_COLS - 1:
                return False
            if row == self.GRID_ROWS - 1 and col < 4:
                return False
        return True

    # 1 = January, 12 = December
    def month_to_cell(self, month: int):
        return Cell((month - 1) // 6, (month - 1) % 6)

    def day_to_cell(self, day: int):
        return Cell(2 + (day - 1) // self.GRID_COLS, (day - 1) % self.GRID_COLS)

    # 1 = Sunday, 7 = Saturday
    def day_of_week_to_cell(self, day_of_week: int):
        return [
            Cell(6, 3),
            Cell(6, 4),
            Cell(6, 5),
            Cell(6, 6),
            Cell(7, 4),
            Cell(7, 5),
            Cell(7, 6),
        ][day_of_week - 1]

class ExtraRow3PuzidayGrid(Grid):
    GRID_ROWS = 9
    GRID_COLS = 7

    def grid_rows(self):
        return self.GRID_ROWS

    def grid_cols(self):
        return self.GRID_COLS

    def validate_placement(self, placement):
        for cell in placement.cells:
            row, col = cell.row, cell.col
            if row == 3:
                return False
            if row < 0 or row >= self.GRID_ROWS:
                return False
            if col < 0 or col >= self.GRID_COLS:
                return False
            if row in (0, 1) and col == self.GRID_COLS - 1:
                return False
            if row == self.GRID_ROWS - 1 and col < 4:
                return False
        return True

    # 1 = January, 12 = December
    def month_to_cell(self, month: int):
        return Cell((month - 1) // 6, (month - 1) % 6)

    def day_to_cell(self, day: int):
        row = 2 + (day - 1) // self.GRID_COLS
        if row >= 3:
            row += 1
        return Cell(row, (day - 1) % self.GRID_COLS)

    # 1 = Sunday, 7 = Saturday
    def day_of_week_to_cell(self, day_of_week: int):
        return [
            Cell(7, 3),
            Cell(7, 4),
            Cell(7, 5),
            Cell(7, 6),
            Cell(8, 4),
            Cell(8, 5),
            Cell(8, 6),
        ][day_of_week - 1]

@dataclass(eq = True, frozen = True)
class Piece:
    name: str
    edges: tuple[str]
    rgb_color_hex: str

    @classmethod
    def from_python_dict(self, dct):
        self.__dict__.update(dct)

PIECES = [
    Piece('Pento L', ('L', 'U', 'U', 'U'), '#FAFF81'),
    Piece('Pento T', ('R', 'R', 'U', 'DD'), '#FFC53A'),
    Piece('Pento P', ('R', 'R', 'D', 'L'), '#E06D06'),
    Piece('Pento N', ('R', 'U', 'R', 'R'), '#B26700'),
    Piece('Pento V', ('R', 'R', 'D', 'D'), '#004E89'),
    Piece('Pento U', ('U', 'R', 'R', 'D'), '#177E89'),
    Piece('Pento Z', ('R', 'D', 'D', 'R'), '#412234'),
    Piece('Tetr I', ('R', 'R', 'R'), '#63A088'),
    Piece('Tetr S', ('R', 'U', 'R'), '#252F5F'),
    Piece('Tetr L', ('L', 'U', 'U'), '#5C8001'),
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
    return Piece(piece.name, tuple(edges), piece.rgb_color_hex)

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
    return Piece(piece.name, tuple(edges), piece.rgb_color_hex)

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
    return Placement(piece, frozenset(cells))

def generate_valid_placements(grid, start_placements, start_row):
    placements = set(start_placements)
    excluded_pieces = set(p.piece.name for p in start_placements)
    for row in range(grid.grid_rows()):
        for col in range(grid.grid_cols()):
            cell = Cell(row, col)
            for piece_name, orientations in ORIENTATIONS.items():
                if piece_name in excluded_pieces:
                    continue
                for piece in orientations:
                    placement = compute_placement(cell, piece)
                    if not grid.validate_placement(placement):
                        continue
                    if any(cell.row < start_row for cell in placement.cells):
                        continue
                    placements.add(placement)
    return placements

def solve_for_day(grid: Grid, placements: List[Placement], date: datetime.datetime):
    month = grid.month_to_cell(date.month)
    day = grid.day_to_cell(date.day)
    day_of_week = grid.day_of_week_to_cell(1 + (date.weekday() + 1) % 7)

    valid_placements = set()
    for placement in placements:
        if month not in placement.cells and \
                day not in placement.cells and \
                day_of_week not in placement.cells:
            valid_placements.add(placement)

    solution_placements = solve_x(valid_placements)
    if solution_placements is None:
        return None
    return Solution(date, 3 if isinstance(grid, ExtraRow3PuzidayGrid) else 0,
                    solution_placements)

def solve_x(placements):
    # Build the adjacency matrix with one constraint (column) per cell and piece.
    # We represent it as a dict where keys are columns and rows are set values.
    constraint_to_placements = {}
    for placement in placements:
        constraint_to_placements.setdefault(
            placement.piece.name, set()).add(placement)
        for cell in placement.cells:
            constraint_to_placements.setdefault(cell, set()).add(placement)

    # Validate the matrix: do the placements cover every available piece?
    for piece in PIECES:
        if piece.name not in constraint_to_placements:
            return None

    def prune(satisfied_constraints, constraint_to_placements):
        '''
        Remove constraints that were satisfied by a placement selection.

        We also remove all placements that satisfy those constraints, saving
        them for future backtracking.

        Returns:
            removed_placements: list[set[Placement]], the placements removed
                                from satisfied_constraints, in reverse order of
                                that list.
        '''
        removed_placements = []
        for satisfied_constraint in satisfied_constraints:
            placements_to_remove = constraint_to_placements[satisfied_constraint]
            removed_placements.append(set(placements_to_remove))
            for placement_to_remove in list(placements_to_remove):
                for other_constraint in placement_to_remove.satisfied_constraints():
                    constraint_to_placements[other_constraint].remove(placement_to_remove)
            assert not constraint_to_placements[satisfied_constraint]
            del constraint_to_placements[satisfied_constraint]
        return removed_placements

    def backtrack(satisfied_constraints, removed_placements, constraint_to_placements):
        '''
        Restore constraints_to_placements (aka incidence matrix) from a prune.

        We re-add all satisfied constraints, and re-add their satisfying placements to
        other constraints that were not removed.
        '''

        for satisfied_constraint in reversed(satisfied_constraints):
            assert satisfied_constraint not in constraint_to_placements
            constraint_to_placements[satisfied_constraint] = removed_placements.pop()
            for placement_to_restore in list(constraint_to_placements[satisfied_constraint]):
                for other_constraint in placement_to_restore.satisfied_constraints():
                    constraint_to_placements[other_constraint].add(placement_to_restore)
        assert not removed_placements

    def solve(constraint_to_placements, level = 0):
        if not constraint_to_placements:
            return []
        constraint = min(constraint_to_placements,
                         key = lambda c: len(constraint_to_placements[c]))
        if not constraint_to_placements[constraint]:
            return None
        for next_placement in list(constraint_to_placements[constraint]):
            # print(' ' * level * 2 + f'{next_placement.piece.name}')
            satisfied_constraints = next_placement.satisfied_constraints()
            removed_placements = prune(satisfied_constraints,
                                       constraint_to_placements)
            assert removed_placements
            assert removed_placements[0]
            solution = solve(constraint_to_placements, level = level + 1)
            if solution is not None:
                return [next_placement] + solution
            backtrack(satisfied_constraints, removed_placements,
                      constraint_to_placements)
        return None
    return solve(constraint_to_placements)

def hext_to_rgb_tuple(rgb_color_hex):
    rgb_color_hex = rgb_color_hex.lstrip('#')
    return tuple(int(hh, 16)
         for hh in (rgb_color_hex[:2], rgb_color_hex[2:4], rgb_color_hex[4:]))

def render_to_ppm(grid, solution):
    cell_to_rgb_color = {}
    for placement in solution.placements:
        for cell in placement.cells:
            cell_to_rgb_color[cell] = hext_to_rgb_tuple(placement.piece.rgb_color_hex)

    ppm = []
    ppm.append(f'P3\n{grid.grid_cols() * CELL_SIZE_PX} {grid.grid_rows() * CELL_SIZE_PX}\n255')
    for row in range(grid.grid_rows()):
        for _ in range(CELL_SIZE_PX):
            for col in range(grid.grid_cols()):
                rgb = cell_to_rgb_color.get(Cell(row, col), (0, 0, 0))
                ppm.append(f'{" ".join(map(str, rgb))}\n' * CELL_SIZE_PX)
    return '\n'.join(ppm)

@dataclass
class Solution:
    date: datetime.datetime
    straight_line_row: int
    placements: list[Placement]

    DATE_FORMAT = '%Y-%m-%d'

    def date_str(self):
        return self.date.strftime(self.DATE_FORMAT)

    def to_puziday_grid(self):
        if not self.straight_line_row:
            return self

        placements = []
        for placement in self.placements:
            cells = []
            for cell in placement.cells:
                row = cell.row
                if row >= 3:
                    row -= 1
                cells.append(Cell(row, cell.col))
            placements.append(Placement(placement.piece, frozenset(cells)))
        return Solution(self.date, self.straight_line_row, placements)

    def serialize(self):
        result = {
            'date': self.date_str(),
            'straight_line_row': self.straight_line_row,
            'placements': []
        }
        for placement in self.placements:
            dct = asdict(placement)
            dct['cells'] = [asdict(cell) for cell in placement.cells]
            result['placements'].append(dct)
        return result

    @classmethod
    def deserialize(klass, solution):
        placements = []
        for dct in solution['placements']:
            cells = frozenset(Cell(c['row'], c['col']) for c in dct['cells'])
            piece = Piece(dct['piece']['name'],
                          tuple(dct['piece']['edges']),
                          dct['piece']['rgb_color_hex'])
            placements.append(Placement(piece, cells))
        date = datetime.date.strptime(solution['date'], Solution.DATE_FORMAT)
        return Solution(date,
                        solution['straight_line_row'],
                        placements)

def solution_json_path(date: datetime.datetime):
    return os.path.join('solutions', date.strftime(Solution.DATE_FORMAT + '.json'))

def solution_ppm_path(date: datetime.datetime):
    return os.path.join('solutions', date.strftime(Solution.DATE_FORMAT + '.ppm'))

def try_load_solution(solution_json_path: str):
    try:
        with open(solution_json_path) as input:
            return Solution.deserialize(json.load(input))
    except FileNotFoundError:
        print(f"Could not load {solution_json_path}, starting over...",
              file = sys.stderr)
    return None

def main(argv):
    if len(argv) < 2:
        date = datetime.datetime.today()
    else:
        date = datetime.date.strptime(argv[1], Solution.DATE_FORMAT)

    yesterday = date - datetime.timedelta(days = 1)
    yesterdays_solution = try_load_solution(solution_json_path(yesterday))
    if yesterdays_solution and not yesterdays_solution.straight_line_row:
        print("Loaded yesterday's solution, but can't reuse it!")
        yesterdays_solution = None

    start_placements = set()
    if yesterdays_solution:
        for placement in yesterdays_solution.placements:
            for cell in placement.cells:
                if cell.row < yesterdays_solution.straight_line_row:
                    start_placements.add(placement)

    attempts = [
        ('Solving from scratch with a straight line row constraint...',
         ExtraRow3PuzidayGrid, set(), 0),
        ('Solving from scratch without constraints...',
         PuzidayGrid, set(), 0),
    ]
    if start_placements:
        attempts.insert(0,
            ("Solving with yesterday's solution as starting point...",
             ExtraRow3PuzidayGrid, start_placements,
             yesterdays_solution.straight_line_row))

    for (message, grid_class, start_placements, straight_line_row) in attempts:
        print(message, flush = True, end = ' ')
        grid = grid_class()
        placements = generate_valid_placements(
            grid, start_placements, straight_line_row)
        solution = solve_for_day(grid, placements, date)
        if solution is not None:
            print('OK!')
            break
        print('No solution')

    if solution is None:
        sys.exit(1)

    solution = solution.to_puziday_grid()
    grid = PuzidayGrid()

    with open(solution_json_path(date), 'w') as output:
        json.dump(solution.serialize(), output)

    with open(solution_ppm_path(date), 'wb') as output:
        output.write(render_to_ppm(grid, solution).encode('utf-8'))

main(sys.argv)
