"""Pure-Python layout logic for the Skadis hook creator."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Sequence


SLOT_WIDTH_MM = 5.0
SLOT_HEIGHT_MM = 15.0
BOARD_THICKNESS_MM = 5.0
PEG_PITCH_MM = 40.0
# Measured from the supplied 200 x 240 mm 3MF board: adjacent staggered
# rows are 20 mm apart and shifted sideways by 20 mm.
ROW_PITCH_MM = 20.0
ROW_STAGGER_MM = 20.0

PEG_CELL_MM = 5.0
PEG_ARM_CELLS = 2
PEG_LEG_CELLS = 1
PEG_WIDTH_CLEARANCE_MM = 0.2
PEG_WIDTH_MM = PEG_CELL_MM - PEG_WIDTH_CLEARANCE_MM
BOARD_GAP_MM = 0.0

PEG_PROFILE_HEIGHT_MM = PEG_CELL_MM * (1 + PEG_LEG_CELLS)
PEG_TOTAL_DEPTH_MM = PEG_CELL_MM * PEG_ARM_CELLS

END_MARGIN_MM = 2.0
HOOK_ENVELOPE_HEIGHT_MM = PEG_PROFILE_HEIGHT_MM
HOOK_HALF_HEIGHT_MM = PEG_PROFILE_HEIGHT_MM / 2.0

VERTICAL_TOLERANCE_DEG = 0.5
RECT_INSET_MM = 0.5
MIN_RECT_WIDTH_MM = 12.0
MIN_RECT_HEIGHT_MM = HOOK_ENVELOPE_HEIGHT_MM


class LayoutError(ValueError):
    """Raised when the selected face cannot hold a usable hook."""


@dataclass(frozen=True)
class Rect2D:
    x_min: float
    x_max: float
    y_min: float
    y_max: float

    @property
    def width(self) -> float:
        return self.x_max - self.x_min

    @property
    def height(self) -> float:
        return self.y_max - self.y_min

    @property
    def center(self) -> tuple[float, float]:
        return (
            (self.x_min + self.x_max) / 2.0,
            (self.y_min + self.y_max) / 2.0,
        )

    def inset(self, margin: float) -> Rect2D | None:
        if margin < 0:
            raise ValueError("inset margin must not be negative")
        result = Rect2D(
            self.x_min + margin,
            self.x_max - margin,
            self.y_min + margin,
            self.y_max - margin,
        )
        if result.width <= 0 or result.height <= 0:
            return None
        return result


@dataclass(frozen=True)
class HookLayout:
    rect: Rect2D
    row_centers: tuple[float, ...]
    positions: tuple[tuple[float, float], ...]

    @property
    def peg_count(self) -> int:
        return len(self.positions)


def _normalized(vector: Sequence[float]) -> tuple[float, float, float]:
    if len(vector) != 3:
        raise ValueError("vector must contain three values")
    x, y, z = (float(value) for value in vector)
    length = math.sqrt(x * x + y * y + z * z)
    if length <= 1e-12:
        raise ValueError("vector must not be zero-length")
    return x / length, y / length, z / length


def face_tilt_degrees(normal: Sequence[float]) -> float:
    """Return the face's angular deviation from vertical."""
    _, _, z = _normalized(normal)
    return math.degrees(math.asin(min(1.0, max(-1.0, abs(z)))))


def is_vertical_normal(
    normal: Sequence[float],
    tolerance_deg: float = VERTICAL_TOLERANCE_DEG,
) -> bool:
    if tolerance_deg < 0:
        raise ValueError("tolerance_deg must not be negative")
    return face_tilt_degrees(normal) <= tolerance_deg + 1e-12


def face_frame(
    normal: Sequence[float],
) -> tuple[tuple[float, float, float], tuple[float, float, float], tuple[float, float, float]]:
    """Build local axes U (horizontal), V (up) and N (outward normal)."""
    nx, ny, nz = _normalized(normal)
    ux, uy, uz = _normalized((-ny, nx, 0.0))
    vx = ny * uz - nz * uy
    vy = nz * ux - nx * uz
    vz = nx * uy - ny * ux
    return (ux, uy, uz), (vx, vy, vz), (nx, ny, nz)


def largest_true_rectangle(mask: Sequence[Sequence[bool]]) -> Rect2D | None:
    """Find the largest all-True axis-aligned rectangle in a boolean mask.

    Returned indices are half-open. Rows correspond to the mask's second
    coordinate and columns to its first coordinate.
    """
    if len(mask) == 0:
        return None
    columns = len(mask[0])
    if columns == 0:
        return None
    if any(len(row) != columns for row in mask):
        raise ValueError("mask rows must have equal lengths")

    heights = [0] * columns
    best_area = 0
    best: Rect2D | None = None

    for row_index, row in enumerate(mask):
        for column_index, filled in enumerate(row):
            heights[column_index] = heights[column_index] + 1 if filled else 0

        stack: list[tuple[int, int]] = []
        for column_index in range(columns + 1):
            height = heights[column_index] if column_index < columns else 0
            start = column_index
            while stack and stack[-1][1] >= height:
                bar_start, bar_height = stack.pop()
                area = bar_height * (column_index - bar_start)
                if area > best_area:
                    best_area = area
                    best = Rect2D(
                        float(bar_start),
                        float(column_index),
                        float(row_index - bar_height + 1),
                        float(row_index + 1),
                    )
                start = bar_start
            stack.append((start, height))

    return best


def make_hook_layout(rect: Rect2D) -> HookLayout:
    if rect.width + 1e-9 < MIN_RECT_WIDTH_MM:
        raise LayoutError(
            f"所选面的可用宽度不足 {MIN_RECT_WIDTH_MM:.0f} mm，无法生成挂钩。"
        )
    if rect.height + 1e-9 < MIN_RECT_HEIGHT_MM:
        raise LayoutError(
            f"所选面的可用高度不足 {MIN_RECT_HEIGHT_MM:.0f} mm，无法生成挂钩。"
        )

    max_row_index = math.floor(
        (
            rect.height / 2.0
            - HOOK_HALF_HEIGHT_MM
        )
        / ROW_PITCH_MM
        + 1e-9
    )
    max_row_index = max(0, max_row_index)

    candidate_row_centers = tuple(
        row_index * ROW_PITCH_MM
        for row_index in range(-max_row_index, max_row_index + 1)
    )
    positions: list[tuple[float, float]] = []
    row_centers: list[float] = []
    max_horizontal_offset = (
        rect.width / 2.0 - END_MARGIN_MM - PEG_WIDTH_MM / 2.0
    )
    for row_center in candidate_row_centers:
        row_number = round(row_center / ROW_PITCH_MM)
        x_phase = ROW_STAGGER_MM if row_number % 2 else 0.0
        first_index = math.ceil((-max_horizontal_offset - x_phase) / PEG_PITCH_MM)
        last_index = math.floor((max_horizontal_offset - x_phase) / PEG_PITCH_MM)
        row_positions = [
            (
                x_phase + column_index * PEG_PITCH_MM,
                row_center + HOOK_HALF_HEIGHT_MM,
            )
            for column_index in range(first_index, last_index + 1)
        ]
        if row_positions:
            row_centers.append(row_center)
            positions.extend(row_positions)

    return HookLayout(
        rect=rect,
        row_centers=tuple(row_centers),
        positions=tuple(positions),
    )
