"""FreeCAD geometry construction for Skadis hooks."""

from __future__ import annotations

from dataclasses import dataclass

import FreeCAD as App
import numpy as np
import Part
from FreeCAD import Vector
from shapely import contains_xy
from shapely.geometry import Point, Polygon
from shapely.validation import make_valid

from . import core


class GeometryError(RuntimeError):
    """Raised when selected geometry cannot produce a hook."""


@dataclass(frozen=True)
class MountResult:
    shape: Part.Shape
    placement: App.Placement
    layout: core.HookLayout


def _project_2d(
    point: Vector,
    origin: Vector,
    u_axis: tuple[float, float, float],
    v_axis: tuple[float, float, float],
) -> tuple[float, float]:
    offset = point - origin
    return (
        offset.dot(Vector(*u_axis)),
        offset.dot(Vector(*v_axis)),
    )


def _wire_points_2d(
    wire: Part.Wire,
    origin: Vector,
    u_axis: tuple[float, float, float],
    v_axis: tuple[float, float, float],
) -> list[tuple[float, float]]:
    points: list[tuple[float, float]] = []
    for point in wire.discretize(Deflection=0.05):
        projected = _project_2d(point, origin, u_axis, v_axis)
        if not points or math_is_distinct(points[-1], projected):
            points.append(projected)
    if len(points) > 1 and math_is_distinct(points[0], points[-1]) is False:
        points.pop()
    return points


def math_is_distinct(
    first: tuple[float, float],
    second: tuple[float, float],
    tolerance: float = 1e-7,
) -> bool:
    return abs(first[0] - second[0]) > tolerance or abs(first[1] - second[1]) > tolerance


def _face_polygon_2d(
    face: Part.Face,
    origin: Vector,
    u_axis: tuple[float, float, float],
    v_axis: tuple[float, float, float],
) -> Polygon:
    wire_polygons: list[Polygon] = []
    for wire in face.Wires:
        points = _wire_points_2d(wire, origin, u_axis, v_axis)
        if len(points) < 3:
            continue
        polygon = Polygon(points)
        if not polygon.is_valid:
            polygon = make_valid(polygon)
        if polygon.is_empty or polygon.area <= 1e-9:
            continue
        if polygon.geom_type == "MultiPolygon":
            polygon = max(polygon.geoms, key=lambda item: item.area)
        wire_polygons.append(polygon)

    if not wire_polygons:
        raise GeometryError("无法从所选面提取有效的二维轮廓。")

    outer = max(wire_polygons, key=lambda item: item.area)
    holes = [
        list(polygon.exterior.coords)
        for polygon in wire_polygons
        if polygon is not outer
    ]
    combined = Polygon(list(outer.exterior.coords), holes)
    if not combined.is_valid:
        combined = make_valid(combined)
    if combined.is_empty or combined.area <= 1e-9:
        raise GeometryError("所选面的二维轮廓无效。")
    if combined.geom_type == "MultiPolygon":
        combined = max(combined.geoms, key=lambda item: item.area)
    return combined


def _rectangle_is_inside(polygon: Polygon, rect: core.Rect2D) -> bool:
    samples_x = np.linspace(rect.x_min, rect.x_max, 5)
    samples_y = np.linspace(rect.y_min, rect.y_max, 5)
    for x in samples_x:
        for y in samples_y:
            if not polygon.covers(Point(float(x), float(y))):
                return False
    return True


def _largest_inscribed_rectangle(
    polygon: Polygon,
) -> core.Rect2D:
    x_min, y_min, x_max, y_max = polygon.bounds
    span = max(x_max - x_min, y_max - y_min)
    if span <= 1e-9:
        raise GeometryError("所选面没有可用的面积。")

    pitch = max(0.5, span / 600.0)
    xs = np.arange(x_min + pitch / 2.0, x_max, pitch)
    ys = np.arange(y_min + pitch / 2.0, y_max, pitch)
    if len(xs) == 0 or len(ys) == 0:
        raise GeometryError("所选面的尺寸过小，无法计算内切矩形。")

    grid_x, grid_y = np.meshgrid(xs, ys)
    mask = contains_xy(polygon, grid_x, grid_y)
    index_rect = core.largest_true_rectangle(mask)
    if index_rect is None:
        raise GeometryError("所选面没有可用的内切矩形。")

    rect = core.Rect2D(
        x_min + index_rect.x_min * pitch,
        x_min + index_rect.x_max * pitch,
        y_min + index_rect.y_min * pitch,
        y_min + index_rect.y_max * pitch,
    )
    inset = rect.inset(core.RECT_INSET_MM)
    if inset is None:
        raise GeometryError("所选面的内切矩形过小。")

    while not _rectangle_is_inside(polygon, inset):
        inset = inset.inset(core.RECT_INSET_MM)
        if inset is None:
            raise GeometryError("无法在所选面内找到安全的内切矩形。")
    return inset


def _make_peg() -> Part.Shape:
    z_start = 0.0
    z_turn = z_start + core.BOARD_THICKNESS_MM + core.BOARD_GAP_MM
    z_end = z_start + core.PEG_TOTAL_DEPTH_MM
    bottom_y = -core.PEG_PROFILE_HEIGHT_MM

    profile = (
        Vector(0, 0, z_start),
        Vector(0, 0, z_end),
        Vector(0, bottom_y, z_end),
        Vector(0, bottom_y, z_turn),
        Vector(0, -core.PEG_CELL_MM, z_turn),
        Vector(0, -core.PEG_CELL_MM, z_start),
        Vector(0, 0, z_start),
    )
    face = Part.Face(Part.makePolygon(profile))
    peg = face.extrude(Vector(core.PEG_WIDTH_MM, 0, 0))
    peg.translate(Vector(-core.PEG_WIDTH_MM / 2.0, 0, 0))
    return peg


def _build_hook_shape(layout: core.HookLayout) -> Part.Shape:
    peg = _make_peg()
    pegs: list[Part.Shape] = []
    for x_position, root_y in layout.positions:
        instance = peg.copy()
        instance.translate(Vector(x_position, root_y, 0))
        if not instance.isValid() or len(instance.Solids) != 1:
            raise GeometryError("生成的 Skadis 插销不是有效实体。")
        pegs.append(instance)

    shape = Part.makeCompound(pegs)
    if shape.isNull() or not shape.isValid() or len(shape.Solids) != len(pegs):
        raise GeometryError("生成的 Skadis 插销集合无效。")
    return shape


def build_mount(face: Part.Face) -> MountResult:
    if face.ShapeType != "Face":
        raise GeometryError("当前选择不是面。")
    if not isinstance(face.Surface, Part.Plane):
        raise GeometryError("当前选择不是平面。请选择一个垂直平面。")

    normal = face.normalAt(0, 0)
    if normal.Length <= 1e-12:
        raise GeometryError("无法确定所选面的法线方向。")
    normal.normalize()
    if not core.is_vertical_normal((normal.x, normal.y, normal.z)):
        tilt = core.face_tilt_degrees((normal.x, normal.y, normal.z))
        raise GeometryError(
            f"所选面不垂直（偏离竖直 {tilt:.2f}°）。请选择竖直平面。"
        )

    u_axis, v_axis, n_axis = core.face_frame((normal.x, normal.y, normal.z))
    origin = face.CenterOfMass
    polygon = _face_polygon_2d(face, origin, u_axis, v_axis)
    rect = _largest_inscribed_rectangle(polygon)
    layout = core.make_hook_layout(rect)
    shape = _build_hook_shape(layout)

    center_u, center_v = rect.center
    placement_origin = (
        origin
        + Vector(*u_axis) * center_u
        + Vector(*v_axis) * center_v
    )
    rotation = App.Rotation(
        Vector(*u_axis),
        Vector(*v_axis),
        Vector(*n_axis),
    )
    return MountResult(
        shape=shape,
        placement=App.Placement(placement_origin, rotation),
        layout=layout,
    )
