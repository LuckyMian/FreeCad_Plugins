import math
import unittest

from skadis_hook import core


class VerticalNormalTests(unittest.TestCase):
    def test_horizontal_normals_are_vertical_faces(self):
        for normal in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0)):
            with self.subTest(normal=normal):
                self.assertTrue(core.is_vertical_normal(normal))

    def test_horizontal_face_is_rejected(self):
        self.assertFalse(core.is_vertical_normal((0, 0, 1)))
        self.assertFalse(core.is_vertical_normal((0, 0, -1)))

    def test_tolerance_boundary(self):
        inside_angle = math.radians(0.4)
        outside_angle = math.radians(0.6)
        self.assertTrue(
            core.is_vertical_normal((math.cos(inside_angle), 0, math.sin(inside_angle)))
        )
        self.assertFalse(
            core.is_vertical_normal((math.cos(outside_angle), 0, math.sin(outside_angle)))
        )

    def test_zero_normal_is_rejected(self):
        with self.assertRaises(ValueError):
            core.is_vertical_normal((0, 0, 0))


class FrameTests(unittest.TestCase):
    def test_frame_is_right_handed_and_vertical(self):
        for normal in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0)):
            with self.subTest(normal=normal):
                u, v, n = core.face_frame(normal)
                self.assertAlmostEqual(u[2], 0.0)
                self.assertAlmostEqual(v[2], 1.0)
                self.assertAlmostEqual(n[2], 0.0)
                cross = (
                    u[1] * v[2] - u[2] * v[1],
                    u[2] * v[0] - u[0] * v[2],
                    u[0] * v[1] - u[1] * v[0],
                )
                for actual, expected in zip(cross, n):
                    self.assertAlmostEqual(actual, expected)


class RectangleTests(unittest.TestCase):
    def test_full_mask(self):
        mask = [[True] * 4 for _ in range(3)]
        rect = core.largest_true_rectangle(mask)
        self.assertEqual(rect, core.Rect2D(0, 4, 0, 3))

    def test_l_shape_selects_largest_arm(self):
        mask = [
            [True, True, True, False],
            [True, True, True, False],
            [True, True, False, False],
            [True, True, False, False],
            [True, True, False, False],
        ]
        rect = core.largest_true_rectangle(mask)
        self.assertEqual(rect, core.Rect2D(0, 2, 0, 5))

    def test_empty_mask(self):
        self.assertIsNone(core.largest_true_rectangle([[False, False]]))
        self.assertIsNone(core.largest_true_rectangle([]))


class LayoutTests(unittest.TestCase):
    def test_peg_profile_fits_through_slot(self):
        self.assertLess(
            core.PEG_PROFILE_HEIGHT_MM,
            core.SLOT_HEIGHT_MM,
        )

    def test_single_peg_for_narrow_face(self):
        layout = core.make_hook_layout(core.Rect2D(-30, 30, -5, 5))
        self.assertEqual(layout.row_centers, (0.0,))
        self.assertEqual(layout.positions, ((0.0, 5.0),))

    def test_staggered_rows_are_added_when_height_allows(self):
        layout = core.make_hook_layout(core.Rect2D(-50, 50, -25, 25))
        self.assertEqual(layout.row_centers, (-20.0, 0.0, 20.0))
        self.assertEqual(layout.peg_count, 7)
        row_zero = [x for x, y in layout.positions if y == 5.0]
        row_above = [x for x, y in layout.positions if y == 25.0]
        row_below = [x for x, y in layout.positions if y == -15.0]
        self.assertEqual(row_zero, [-40.0, 0.0, 40.0])
        self.assertEqual(row_above, [-20.0, 20.0])
        self.assertEqual(row_below, [-20.0, 20.0])

    def test_row_parity_follows_board_lattice(self):
        layout = core.make_hook_layout(core.Rect2D(-100, 100, -50, 50))
        self.assertEqual(
            layout.row_centers,
            (-40.0, -20.0, 0.0, 20.0, 40.0),
        )
        positions_by_root = {}
        for x, root_y in layout.positions:
            positions_by_root.setdefault(root_y, []).append(x)
        for root_y in (-35.0, 5.0, 45.0):
            self.assertTrue(
                all(round(x / 40.0) * 40.0 == x for x in positions_by_root[root_y])
            )
        for root_y in (-15.0, 25.0):
            self.assertTrue(
                all((x - 20.0) % 40.0 == 0 for x in positions_by_root[root_y])
            )

    def test_five_pegs_at_wide_face(self):
        layout = core.make_hook_layout(core.Rect2D(-90, 90, -5, 5))
        self.assertEqual(
            [x for x, _ in layout.positions],
            [-80.0, -40.0, 0.0, 40.0, 80.0],
        )

    def test_too_small_face_is_rejected(self):
        with self.assertRaises(core.LayoutError):
            core.make_hook_layout(core.Rect2D(0, 11.9, -7, 7))
        with self.assertRaises(core.LayoutError):
            core.make_hook_layout(
                core.Rect2D(
                    -6,
                    6,
                    -core.HOOK_ENVELOPE_HEIGHT_MM / 2.0 + 0.1,
                    core.HOOK_ENVELOPE_HEIGHT_MM / 2.0 - 0.1,
                )
            )


if __name__ == "__main__":
    unittest.main()
