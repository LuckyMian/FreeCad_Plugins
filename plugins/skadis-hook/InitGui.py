from pathlib import Path

import FreeCADGui as Gui
import skadis_hook


ICON_DIR = str(
    Path(skadis_hook.__file__).resolve().parents[1] / "resources" / "icons"
)
Gui.addIconPath(ICON_DIR)


class SkadisHookWorkbench(Gui.Workbench):
    MenuText = "Skadis 挂钩"
    ToolTip = "在选中的垂直平面上创建宜家 Skadis 挂接件"
    Icon = "skadis-hook.svg"

    def Initialize(self):
        from skadis_hook import commands

        commands.register()
        self.appendToolbar("Skadis 挂钩", ["SkadisHook_Create"])
        self.appendMenu("Skadis 挂钩", ["SkadisHook_Create"])

    def Activated(self):
        pass

    def Deactivated(self):
        pass

    def GetClassName(self):
        return "Gui::PythonWorkbench"


Gui.addWorkbench(SkadisHookWorkbench())
