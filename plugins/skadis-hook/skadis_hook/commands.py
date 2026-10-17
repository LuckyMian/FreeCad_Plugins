"""FreeCAD command registration and user interaction."""

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtWidgets

from . import core, geometry


COMMAND_ID = "SkadisHook_Create"
_REGISTERED = False


def _selected_face():
    selection = Gui.Selection.getSelectionEx()
    if not selection:
        raise geometry.GeometryError("请先选择一个垂直平面。")
    if len(selection) != 1:
        raise geometry.GeometryError("请只选择一个面。")

    selected = selection[0]
    if len(selected.SubElementNames) != 1:
        raise geometry.GeometryError("请只选择一个面。")
    if len(selected.SubObjects) != 1:
        raise geometry.GeometryError("无法读取所选面，请重新选择。")

    face = selected.SubObjects[0]
    if face.ShapeType != "Face":
        raise geometry.GeometryError("当前选择不是面。")
    return face


class CreateSkadisHookCommand:
    def GetResources(self):
        return {
            "Pixmap": "skadis-hook.svg",
            "MenuText": "创建 Skadis 挂钩",
            "ToolTip": "在选中的垂直平面上创建宜家 Skadis 挂接件。",
        }

    def IsActive(self):
        return App.ActiveDocument is not None

    def Activated(self):
        document = App.ActiveDocument
        if document is None:
            QtWidgets.QMessageBox.warning(
                Gui.getMainWindow(),
                "Skadis 挂钩",
                "请先打开或创建一个文档。",
            )
            return

        try:
            face = _selected_face()
            result = geometry.build_mount(face)

            document.openTransaction("创建 Skadis 挂钩")
            try:
                obj = document.addObject("Part::Feature", "SkadisHook")
                obj.Label = "Skadis 挂钩"
                obj.Shape = result.shape
                obj.Placement = result.placement
                if obj.ViewObject is not None:
                    obj.ViewObject.ShapeColor = (0.35, 0.65, 0.85)
                    obj.ViewObject.LineColor = (0.12, 0.28, 0.38)
                document.recompute()
                document.commitTransaction()
            except Exception:
                document.abortTransaction()
                raise

            try:
                Gui.Selection.clearSelection()
                Gui.Selection.addSelection(obj)
                peg_count = result.layout.peg_count
                row_count = len(result.layout.row_centers)
                Gui.getMainWindow().statusBar().showMessage(
                    f"已创建 Skadis 挂接件：{row_count} 行交错，"
                    f"共 {peg_count} 个插销，行内间距 {core.PEG_PITCH_MM:.0f} mm。",
                    8000,
                )
            except Exception as exc:
                App.Console.PrintWarning(
                    f"Skadis Hook: 对象已创建，但更新选择状态失败：{exc}\n"
                )
        except (geometry.GeometryError, core.LayoutError, ValueError) as exc:
            App.Console.PrintWarning(f"Skadis Hook: {exc}\n")
            QtWidgets.QMessageBox.warning(
                Gui.getMainWindow(),
                "Skadis 挂钩",
                str(exc),
            )
        except Exception as exc:
            App.Console.PrintError(f"Skadis Hook: {exc}\n")
            QtWidgets.QMessageBox.critical(
                Gui.getMainWindow(),
                "Skadis 挂钩",
                f"创建失败：{exc}",
            )


def register():
    global _REGISTERED
    if _REGISTERED:
        return
    Gui.addCommand(COMMAND_ID, CreateSkadisHookCommand())
    _REGISTERED = True
