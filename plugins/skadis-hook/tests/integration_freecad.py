"""Headless FreeCAD geometry checks.

Run with:
    FreeCADCmd.exe tests/integration_freecad.py
"""

from pathlib import Path
import sys


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))

import FreeCAD as App
import Part
from FreeCAD import Vector

from skadis_hook import core, geometry


def _face_with_normal(shape, expected):
    expected = Vector(*expected)
    for face in shape.Faces:
        if face.normalAt(0, 0).dot(expected) > 0.9999:
            return face
    raise AssertionError(f"face with normal {expected} not found")


def main():
    document = App.newDocument("SkadisHookIntegration")
    try:
        box = document.addObject("Part::Feature", "TestBox")
        box.Shape = Part.makeBox(120, 20, 80, Vector(0, 0, 0))
        document.recompute()

        result = geometry.build_mount(_face_with_normal(box.Shape, (0, -1, 0)))
        assert result.shape.isValid()
        assert len(result.shape.Solids) == result.layout.peg_count
        assert result.layout.row_centers == (-20.0, 0.0, 20.0)
        assert result.layout.peg_count == 7
        assert abs(result.shape.BoundBox.ZMin) < 1e-6
        expected_depth = core.PEG_TOTAL_DEPTH_MM
        assert abs(result.shape.BoundBox.ZMax - expected_depth) < 1e-6
        local_normal = result.placement.Rotation.multVec(Vector(0, 0, 1))
        assert local_normal.dot(Vector(0, -1, 0)) > 0.9999

        u_axis, v_axis, _ = core.face_frame((0, -1, 0))
        face_origin = _face_with_normal(box.Shape, (0, -1, 0)).CenterOfMass
        for vertex in result.shape.Vertexes:
            world_point = result.placement.multVec(vertex.Point)
            offset = world_point - face_origin
            u_value = offset.dot(Vector(*u_axis))
            v_value = offset.dot(Vector(*v_axis))
            assert result.layout.rect.x_min - 1e-6 <= u_value <= result.layout.rect.x_max + 1e-6
            assert result.layout.rect.y_min - 1e-6 <= v_value <= result.layout.rect.y_max + 1e-6

        small_box = document.addObject("Part::Feature", "SmallBox")
        small_box.Shape = Part.makeBox(50, 20, 20, Vector(0, 0, 0))
        small_result = geometry.build_mount(
            _face_with_normal(small_box.Shape, (0, -1, 0))
        )
        assert small_result.layout.peg_count == 1

        try:
            geometry.build_mount(_face_with_normal(box.Shape, (0, 0, 1)))
        except geometry.GeometryError:
            pass
        else:
            raise AssertionError("horizontal face should be rejected")

        print("SKADIS_INTEGRATION_OK")
    finally:
        App.closeDocument(document.Name)


if __name__ == "__main__":
    main()
