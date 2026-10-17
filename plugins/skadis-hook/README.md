# Skadis 挂钩

FreeCAD 1.1 工作台，用于给模型背面添加宜家 SKÅDIS 洞洞板挂接接口。

## 使用

1. 打开或创建 FreeCAD 文档。
2. 切换到 `Skadis 挂钩` 工作台。
3. 只选择一个平面面；该面必须相对全局 Z 轴保持竖直。
4. 点击 `创建 Skadis 挂钩`。

插件会计算选中面的最大轴对齐内切矩形，在矩形中心放置第一个插销，然后按
40 mm 间距向左右扩展。生成对象是独立的 `Part::Feature`，原模型不会被修改，
一次操作可通过 FreeCAD 撤销。

## 接口尺寸

默认值来自社区对 SKÅDIS 的复测，并非宜家公开的完整工程图：

- 长孔：约 5 × 15 mm，竖向排列
- 孔距：40 mm
- 板材厚度：5 mm
- 插销侧视截面：3 个 5 × 5 mm 方块组成的直角 L
- 插销实际宽度：4.8 mm，宽度方向留 0.2 mm 装配余量
- L 形横臂向外 10 mm，末端竖脚向下 5 mm、深 5 mm
- 所有底面和端面均为直角平面，无斜切尖角
- 不生成共享底轨或背板，每个插销直接从选中面起始
- 总外伸：10 mm
- 同一条水平行内插销间距 40 mm
- 上下相邻行间距 20 mm，并横向错开 20 mm

所有插销的包络都会限制在选中面的内切矩形内。第一行位于矩形中心；如果上下
空间足够，会继续增加交错的上下行，直到下一行的 L 形包络无法完整放入矩形。

不同批次的板材、打印材料和打印机误差会影响松紧。尺寸常量集中在
`skadis_hook/core.py`，建议先用小件试装；若过紧，减小 `PEG_WIDTH_MM` 或增大
`BOARD_GAP_MM`。

## 限制

- “竖直”按 FreeCAD 全局 Z 轴向上判断，容差为 0.5°。
- 只支持平面面，不支持曲面。
- 插销只生成一行，不会自动增加第二排。
- 面宽不足以容纳左右两个 40 mm 间距插销时，自动退化为单个居中插销；单插销的
  防转能力较弱。
- 可用内切矩形小于 12 × 10 mm 时不会创建对象。

## 开发与验证

```powershell
py -3 -m unittest discover -s tests -v
& 'C:\Program Files\FreeCAD 1.1\bin\FreeCADCmd.exe' -c `
  "import runpy; runpy.run_path(r'F:\Codex\Freecad\plugins\skadis-hook\tests\integration_freecad.py', run_name='__main__')"
```

`tests/gui_smoke.FCMacro` 可在隔离的 FreeCAD GUI 实例中验证工作台注册、命令执行、
实体有效性和撤销/重做。宏通过 `SKADIS_GUI_SMOKE_LOG` 环境变量指定结果日志路径。

尺寸参考：

- <https://pegboardly.com/skadis/skadis-sizes-and-dimensions>
- <https://kapycad.com/en/academy/standards/ikea-skadis>
- <https://github.com/breckenedge/parametric-skadis-flat-mount>
