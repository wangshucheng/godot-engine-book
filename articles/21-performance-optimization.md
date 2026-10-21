# 第 21 篇：渲染性能优化

> **本章导读**：渲染性能优化最怕两件事：一是**用错的心智模型**（以为引擎会自动合批、以为 Draw Call 越少越好），
> 二是**没有测试条件的数字**（「优化后快了 30%」——在哪台机器、哪个分辨率、什么场景下测的？）。
> 本章先把 Godot 4.x 的渲染成本模型讲清楚，再逐条落地三条主线：
> **实例化与绘制提交**（`MultiMesh` / `MultiMeshInstance3D` / 材质共享 / 状态切换）、
> **可见性剔除与距离 LOD**（`visibility_range_*` / `lod_bias` / 基于 **Embree** 的遮挡剔除）、
> **统一性能数字口径与测试条件模板**（引擎版本 / GPU / 分辨率 / 场景规模 / 采样方式）。
> 读完你应该能自己产出一份「可复现」的性能报告，而不是一句「好像变快了」。
> **前置知识**：第 11 篇《Godot 渲染架构概述》、第 14 篇《场景渲染流程》。
> **难度**：进阶。

---

## 一、先建立正确的心智模型

### 1.1 一帧的钱花在哪

```
每个 DrawCall
    ↓
CPU 准备数据
    ↓
GPU 执行渲染
    ↓
瓶颈：CPU 准备时间
```

把这个直觉展开成更完整的版本：

```
一帧的总时间 ≈ max(CPU 侧准备时间, GPU 侧执行时间) + 同步等待
    │
    ├── CPU 侧准备（主线程 + 渲染线程）
    │     ├── 场景树遍历、可见性判定
    │     ├── 剔除（视锥 / 距离 / 遮挡）
    │     ├── 材质与着色器绑定、状态切换
    │     └── 绘制命令录制（Forward+ 是渲染线程）
    │
    ├── GPU 侧执行
    │     ├── 顶点处理（VS）
    │     ├── 像素填充（PS）—— 过度绘制在这里爆炸
    │     └── 后处理（Bloom / DOF / SSR / 雾）
    │
    └── 同步等待
          ├── present 时的管线等待
          └── 任何 readback（截图、GPU 计时回读）
```

**结论一**：CPU 忙和 GPU 忙是两种完全不同的病。
CPU 忙 → 少画东西、少提交、少设状态；GPU 忙 → 少填像素、少算像素、少做后处理。
**不看数据就优化，等于瞎猜。**

**结论二**：Godot 4 的 `RenderingServer` 跑在**独立渲染线程**上（线程模型见第 11 篇），
主线程调用 `RenderingServer` 上的接口只是「记录命令」，真正的 GPU 提交在渲染线程。
所以「主线程很闲但帧率上不去」是完全正常的——瓶颈在渲染线程或 GPU。

### 1.2 Godot 4 没有 3D 通用合批器（必须先讲清的事实）

> Godot 4.x 的渲染器**没有**运行时合批器（Godot 3.x 的 batcher 已移除）：`renderer_canvas_cull.cpp`、`renderer_canvas_render_rd.cpp`、`renderer_scene_render_rd.cpp` 与 `servers/rendering_server.h` 中 "batch" 的命中数**全部为 0**。削减 Draw Call 只能靠下面的场景组织手段。

这句话要展开成三个可操作的结论：

| 结论 | 说明 |
|------|------|
| **没有「自动合批」** | 100 个 `MeshInstance3D` 就是 100 个实例，各提交各的；引擎不会偷偷把它们并成一次绘制 |
| **有「实例化」** | `MultiMesh` 把 N 个实例塞进一个 buffer，一次绘制全部画出来——这是 Godot 4 的「合批」等价物 |
| **有「共享材质」** | 同一个 `Material` 实例被多个物体引用时，管线状态可以复用，减少状态切换 |

| 方法 | 说明 | 效果 |
|------|------|------|
| **MultiMesh / MultiMeshInstance3D** | 同质网格的 N 个实例合并成 1 次实例化绘制 | 80-95% |
| **共享材质** | 多个实例引用同一个 `StandardMaterial3D`，减少 GPU 状态切换 | 40-70% |
| **离线合面** | 用 `SurfaceTool` / 建模软件把静态小物件合并成一个大网格 | 60-90% |
| **可见性范围** | `visibility_range_begin/end` 让远处物体整体不参与渲染 | 视场景而定 |
| **纹理图集** | 合并纹理，减少采样与切换 | 40-70% |

> ⚠️ 下表"效果"列为**示意数据**（未附测试环境），实际收益取决于场景是否真的同质化，请在目标平台实测。
> 完整的测试条件模板见本章第五节。

> 📌 **和 Unity 的对照**：Unity 的 SRP Batcher 复用「材质变体 + 常量缓冲」，Godot 4 的对应物是
> **共享同一个材质资源**（而不是复制一份再改参数）+ **减少 `material_override`**。
> Unity 也没有「自动把 100 个 GameObject 合批成 1 次绘制」的通用能力（静态合批要手动打标记）。

### 1.3 Draw Call 到底怎么量

三个口径，用途完全不同，别混：

| 口径 | API | 范围 | 用途 |
|------|-----|------|------|
| 整个渲染服务器 | `Performance.get_monitor(Performance.RENDER_TOTAL_DRAW_CALLS_IN_FRAME)` | 本帧全局 | 看总量趋势 |
| 渲染服务器细分 | `RenderingServer.get_rendering_info(RenderingServer.RENDERING_INFO_TOTAL_DRAW_CALLS_IN_FRAME)` | 本帧全局 | 和上面同源，做长期记录 |
| 当前视口细分 | `Viewport.get_render_info(Viewport.RENDER_INFO_TYPE_VISIBLE, Viewport.RENDER_INFO_DRAW_CALLS_IN_FRAME)` | **只看这个视口** | 分场景对比最常用 |

按渲染通道再细分（阴影、Canvas 分别是多少）：

```gdscript
# 可见通道的绘制调用
var visible_draws := get_viewport().get_render_info(
	Viewport.RENDER_INFO_TYPE_VISIBLE,
	Viewport.RENDER_INFO_DRAW_CALLS_IN_FRAME)

# 阴影通道的绘制调用
var shadow_draws := get_viewport().get_render_info(
	Viewport.RENDER_INFO_TYPE_SHADOW,
	Viewport.RENDER_INFO_DRAW_CALLS_IN_FRAME)

# 2D Canvas 通道的绘制调用
var canvas_draws := get_viewport().get_render_info(
	Viewport.RENDER_INFO_TYPE_CANVAS,
	Viewport.RENDER_INFO_DRAW_CALLS_IN_FRAME)
```

> 💡 **「阴影的绘制调用比可见通道还多」** 是极常见的场景：大量小物件各自投影，
> 阴影 pass 会把它们全部再画一遍。合并网格或关掉小物件的投影
> （`GeometryInstance3D.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF`）往往比优化主视图更有效。

### 1.4 三种「优化对象」的区分

| 优化对象 | 手段 | 典型收益来源 |
|----------|------|--------------|
| **提交次数** | `MultiMesh`、合面、可见性范围 | 减少 CPU 侧命令录制与状态切换 |
| **几何量** | 网格 LOD、`lod_bias`、减面 | 减少 VS 与三角形装配 |
| **填充量** | 降分辨率、关后处理、透明排序、减少屏幕覆盖 | 减少 PS 执行 |

三者互相独立：把 1000 个 draw call 降到 10 个，如果屏幕上还是铺满同样的像素，GPU 时间一点都不会降。

### 1.5 三个基本的分析入口

| 工具 | 说明 |
|------|------|
| **Profiler** | Godot 内置性能分析器（编辑器 Debugger 面板），按节点/流程拆帧时间 |
| **Monitor** | 实时性能监控（引擎内的 `Performance` 监视器），可看 Draw Call、对象数、内存 |
| **Vulkan Layer** | Vulkan 调试层，检查 API 使用错误与资源泄漏 |

> 📌 这三个入口分别回答不同的问题：
> **Profiler** 回答「哪一步慢」，**Monitor** 回答「量级对不对」，**Vulkan Layer** 回答「有没有用错 API」。
> 更细的 GPU 侧分析（抓帧、逐 pass 耗时）需要第 22 篇介绍的工具链。

---

## 二、实例化与绘制提交

### 2.1 `MultiMesh` 的数据模型

`MultiMesh` 是一个 `Resource`，它把「同一个网格的 N 个实例」的数据打包进一块 buffer：

| 属性 | 类型 | 说明 |
|------|------|------|
| `instance_count` | int | 实例数量（分配 buffer） |
| `transform_format` | int | `MultiMesh.TRANSFORM_2D` / `MultiMesh.TRANSFORM_3D` |
| `use_colors` | bool | 是否启用逐实例颜色 |
| `use_custom_data` | bool | 是否启用逐实例自定义数据 |
| `visible_instance_count` | int | 实际绘制前 N 个实例（用来做「按需显示」） |
| `mesh` | Mesh | 被实例化的网格 |
| `custom_aabb` | AABB | 自定义包围盒（影响视锥剔除） |
| `color_array` | PackedColorArray | 逐实例颜色缓冲 |
| `custom_data_array` | PackedColorArray | 逐实例自定义数据缓冲 |
| `transform_array` | PackedVector3Array | 3D 变换缓冲（每实例 12 个 float，按 4 行存） |

```gdscript
# 1000 棵树的 MultiMesh
var mm := MultiMesh.new()
mm.transform_format = MultiMesh.TRANSFORM_3D
mm.use_colors = true
mm.use_custom_data = true
mm.instance_count = 1000
mm.mesh = tree_mesh

# 逐实例设置变换
for i in range(1000):
	var basis := Basis.from_euler(Vector3(0, randf() * TAU, 0))
	mm.set_instance_transform(i, Transform3D(basis, spawn_points[i]))

# 逐实例颜色（草地的深浅）
var color := Color(0.4, 0.7, 0.2)
mm.set_instance_color(0, color)

# 逐实例自定义数据（存血量 / 湿度 / 动画相位）
mm.set_instance_custom_data(0, Vector4(1.0, 0.0, 0.0, 0.0))
```

> ⚠️ `instance_count` 一旦分配，buffer 大小就定了；改数量要重新赋值。
> 逐实例颜色与自定义数据**必须在 `use_colors` / `use_custom_data` 为 true 时**才有效。

### 2.2 `MultiMeshInstance3D`：把它放进场景

```gdscript
var mmi := MultiMeshInstance3D.new()
mmi.multimesh = mm
mmi.material_override = shared_material
mmi.visibility_range_end = 120.0
mmi.lod_bias = 0.8
add_child(mmi)
```

要点：

- **一个 `MultiMesh` 可以被多个 `MultiMeshInstance3D` 引用**——但这样它们会画在同一批实例上（重复绘制），
  除非你用 `visible_instance_count` 分段；
- **材质**：优先用 `MultiMesh` 里网格自带的表面材质（保证所有实例一致），
  或者用 `material_override` 覆盖整批；
- **`MultiMeshInstance2D`** 是 2D 版本，额外有 `texture` 属性（2D 用贴图而不是网格）。

### 2.3 逐实例颜色与自定义数据

| 通道 | 写入方法 | 着色器里怎么读 |
|------|----------|----------------|
| 颜色 | `MultiMesh.set_instance_color(index, color)` | 走顶点色通道；材质的 `vertex_color_use_as_albedo` 打开后会乘进 albedo |
| 自定义数据 | `MultiMesh.set_instance_custom_data(index, data)` | spatial 着色器的内置量 `INSTANCE_CUSTOM`（vec4） |

```glsl
shader_type spatial;
render_mode blend_mix, depth_draw_opaque, cull_back, diffuse_burley, specular_schlick_ggx;

uniform float tint_strength : hint_range(0.0, 1.0) = 0.5;

void vertex() {
	// INSTANCE_CUSTOM 只有在用 MultiMesh 绘制时才有值
	float phase = INSTANCE_CUSTOM.x;
	// 按实例做一点上下浮动（用 VERTEX 偏移）
	VERTEX += vec3(0.0, sin(phase + TIME * 2.0) * 0.05, 0.0);
}

void fragment() {
	// 逐实例颜色与 albedo 相乘
	ALBEDO *= COLOR.rgb;
}
```

> 📌 `INSTANCE_CUSTOM` 在**非 MultiMesh** 的普通网格上恒为 0，写了也不会报错——但也拿不到数据。
> 逐实例数据是 `MultiMesh` 的独有能力。

### 2.4 RID 级 API：什么时候该下沉到 `RenderingServer`

脚本层的 `MultiMesh` 是一层封装；底层有一整套 `RenderingServer` 上的 `multimesh_*` 方法：

| RID 级方法 | 作用 |
|------------|------|
| `multimesh_create()` | 创建一个多网格 RID |
| `multimesh_allocate_data(multimesh, instances, transform_format, use_colors, use_custom_data)` | 分配 buffer |
| `multimesh_set_mesh(multimesh, mesh)` | 设置被实例化的网格 |
| `multimesh_set_buffer(multimesh, data)` | 整块写入 buffer（批量更新最快） |
| `multimesh_get_buffer(multimesh)` | 读回 buffer |
| `multimesh_instance_set_transform(multimesh, index, transform)` | 写单个实例 |
| `multimesh_instance_set_color` / `multimesh_instance_set_custom_data` | 写单个实例的颜色 / 自定义数据 |
| `multimesh_set_visible_instances(multimesh, visible)` | 设定可见实例数 |
| `multimesh_set_custom_aabb(multimesh, aabb)` | 自定义包围盒 |
| `multimesh_get_aabb(multimesh)` | 读包围盒 |

**什么时候用 RID 级 API**：

1. 需要**一次性写入几千个实例**——`set_buffer` 一把梭，比循环调用 `set_instance_transform` 快一个量级；
2. 在 GDExtension / C++ 里做高频更新；
3. 需要绕开 `Resource` 的序列化（运行时生成、不落盘）。

```gdscript
# 用 RID 级 API 建一个多网格
var mm_rid := RenderingServer.multimesh_create()
RenderingServer.multimesh_allocate_data(
	mm_rid, 500, MultiMesh.TRANSFORM_3D, true, false)
RenderingServer.multimesh_set_mesh(mm_rid, tree_mesh)
RenderingServer.multimesh_instance_set_transform(mm_rid, 0, Transform3D.IDENTITY)
```

> 💡 脚本层的 `MultiMesh` 与 RID 层是**一一对应**的：`MultiMesh` 内部就持有一个 RID。
> 混用两套 API 时要特别小心「谁负责释放」——`MultiMesh` 被释放时它会释放自己的 RID。

### 2.5 材质共享与状态切换

GPU 侧的「状态」包括：着色器管线、混合模式、深度状态、绑定组……
每切换一次状态，驱动就要重新绑定，代价固定。

**Godot 4 里最常见的状态切换来源**：

| 来源 | 表现 | 对策 |
|------|------|------|
| 每个物体一份材质副本 | 材质参数略有不同就各切一次管线 | 共享材质；差异用**实例数据**或**全局 uniform** 表达 |
| `material_override` 到处用 | 每个 override 都是一个独立材质 | 同一批物体用同一个 override |
| 不透明 / 半透明交替 | 队列切换（不透明队列 → 透明队列） | 把半透明物体集中摆放，减少队列交替 |
| 纹理不同 | 绑定组切换 | 用**纹理图集**把多张贴图合并成一张 |

**关键认知**：共享材质的收益不在「Draw Call 变少」（Draw Call 数不变），
而在**「状态切换变少」**——帧时间会降，但 `RENDER_TOTAL_DRAW_CALLS_IN_FRAME` 不变。
**只看 Draw Call 数字会误判优化效果。**

```gdscript
# 反例：每个实例一份材质（编辑器里右键 "Make Unique" 就会这样）
for i in range(200):
	var m := StandardMaterial3D.new()      # ← 200 个不同的材质资源
	m.albedo_color = Color(1, 0, 0)
	mesh_instance.material_override = m

# 正例：一份材质 + 逐实例颜色
var shared := StandardMaterial3D.new()
shared.vertex_color_use_as_albedo = true
var mm := MultiMesh.new()
mm.use_colors = true
mm.instance_count = 200
mm.mesh = quad_mesh
for i in range(200):
	mm.set_instance_color(i, Color.from_hsv(randf(), 0.6, 0.9))
```

### 2.6 离线合面

静态、材质相同、永远一起出现的小物件，可以在**离线阶段**合成一个大网格：

```gdscript
# 用 SurfaceTool 把若干个小方块合成一个网格
var st := SurfaceTool.new()
st.begin(Mesh.PRIMITIVE_TRIANGLES)
for cell in cells:
	var box := BoxMesh.new()
	box.size = Vector3(1, 1, 1)
	# get_mesh_arrays() 返回按 Mesh.ARRAY_VERTEX / ARRAY_NORMAL / ARRAY_TEX_UV 顺序组织的数组组
	var arrays := box.get_mesh_arrays()
	st.append_from(arrays, 0, Transform3D(Basis(), Vector3(cell.x, 0, cell.y)))
var combined := st.commit()
```

> ⚠️ `SurfaceTool.append_from()` 的第一个参数是**一整组表面数组**（不是单个顶点数组），
> 第二个参数是取第几个表面。写错的话会得到空网格或者索引越界。
> 实际工程里更常见的做法是**在建模软件里合并**，或用编辑器的网格合并工具，而不是在运行时拼。

> 💡 合面的代价：**失去逐物体剔除能力**。合在一起的大网格只要有一部分在视锥里，整个网格都要画。
> 所以「一棵树的 5000 个叶子」适合合，「散落全图的 5000 块石头」不该合。

### 2.7 什么时候**不要**用 `MultiMesh`

| 场景 | 为什么不适合 |
|------|--------------|
| 每个实例需要不同的网格 | `MultiMesh` 只有一个 `mesh` |
| 需要逐实例的视锥剔除 | 整个 `MultiMesh` 作为一个整体参与剔除 |
| 需要逐实例的阴影剔除 | 同上，阴影也按整体处理 |
| 需要逐实例的碰撞 | `MultiMesh` 没有碰撞体，要另外用 `StaticBody3D` + `CollisionShape3D` |
| 非均匀缩放 + 需要正确法线 | 缩放矩阵会影响法线变换，需要在着色器里小心处理 |
| 数量很少（< 50） | 收益抵不上复杂度，直接用 `MeshInstance3D` |

### 2.8 实战：一个可运行的植被系统

把前面的知识点串起来，下面这段脚本生成一片按区块分组的植被：

```gdscript
# 植被系统：每 32×32 米一个区块，每区块一个 MultiMeshInstance3D
extends Node3D

const CHUNK_SIZE := 32.0
const GRID := 24
const TREE_MESH := preload("res://meshes/tree.tscn")

var _chunks: Dictionary = {}

func _build() -> void:
	for gx in range(GRID):
		for gz in range(GRID):
			var chunk := _make_chunk(gx, gz)
			if chunk != null:
				add_child(chunk)

func _make_chunk(gx: int, gz: int) -> Node:
	var mm := MultiMesh.new()
	mm.transform_format = MultiMesh.TRANSFORM_3D
	mm.use_colors = true
	mm.instance_count = 64
	mm.mesh = TREE_MESH

	var count := 0
	var origin := Vector3(gx * CHUNK_SIZE, 0.0, gz * CHUNK_SIZE)
	for i in range(64):
		var offset := Vector3(randf() * CHUNK_SIZE, 0.0, randf() * CHUNK_SIZE)
		var basis := Basis.from_euler(Vector3(0.0, randf() * TAU, 0.0))
		mm.set_instance_transform(i, Transform3D(basis, origin + offset))
		# 逐实例颜色：让同一片林子有深浅变化
		var tint := Color.from_hsv(randf_range(0.25, 0.35), 0.6, randf_range(0.7, 1.0))
		mm.set_instance_color(i, tint)
		count += 1

	if count == 0:
		return null

	var mmi := MultiMeshInstance3D.new()
	mmi.multimesh = mm
	# 远处整块不画（配合可见性范围做粗粒度 LOD）
	mmi.visibility_range_end = 160.0
	mmi.visibility_range_end_margin = 20.0
	mmi.visibility_range_fade_mode = GeometryInstance3D.VISIBILITY_RANGE_FADE_SELF
	return mmi
```

> 📌 **注意这个例子的粒度取舍**：分块（chunk）是为了让「可见性范围」有作用——
> 一整片林子做成一个 `MultiMesh`，远处的整片林子会一起消失；
> 分成 32 米见方的小块后，只有远处的小块消失，近处的仍然存在。
> **MultiMesh 的粒度决定了你能做多细的剔除。**

> ⚠️ `TREE_MESH` 用 `preload` 加载的是一个 `PackedScene`，不是 `Mesh`。
> 要把它塞进 `MultiMesh.mesh`，得先拿到场景里的 `MeshInstance3D.mesh`；
> 更好的做法是直接 `preload` 一个 `.res` 格式的 `Mesh` 资源。

### 2.9 2D 的 `MultiMesh`

2D 版本的数据模型一致，差异在绘制方式：

| 维度 | 3D | 2D |
|------|----|----|
| 节点 | `MultiMeshInstance3D` | `MultiMeshInstance2D` |
| 变换格式 | `MultiMesh.TRANSFORM_3D` | `MultiMesh.TRANSFORM_2D` |
| 绘制内容 | 网格 + 材质 | `texture` 贴图 |
| 逐实例数据 | 颜色 / `INSTANCE_CUSTOM` | 颜色 / 逐实例自定义数据 |

> 📌 2D **同样没有自动合批器**（见第 18 篇）：`renderer_canvas_cull.cpp` 与 `renderer_canvas_render_rd.cpp` 里 "batch" 命中数为 0。
> 2D 想减少提交，同样靠 `MultiMesh`（尤其是大量重复的子弹、树叶、雨滴）。

---

## 三、可见性剔除与距离 LOD

### 3.1 三层剔除

| 层 | 判据 | 谁负责 | 开销 |
|----|------|--------|------|
| **视锥剔除** | 物体包围盒是否与相机视锥相交 | 引擎自动，每个 `VisualInstance3D` 都做 | 极低 |
| **距离剔除** | 物体与相机的距离是否在 `visibility_range_*` 之外 | `GeometryInstance3D` 属性 | 极低 |
| **遮挡剔除** | 物体是否被不透明物体挡住 | `OccluderInstance3D` + **Embree** | **中**（CPU 侧） |

### 3.2 距离 LOD：`visibility_range_*`

> **Godot 4.3 没有 `LOD3D` 节点**：`doc/classes/LOD3D.xml` 返回 404，`scene/register_scene_types.cpp` 里检索 "LOD" 命中数为 0。LOD 由 **`GeometryInstance3D` 的可见性范围（`visibility_range_*`）+ 网格自带的 LOD 层级（`lod_bias`）** 实现。

```gdscript
# 近处：高模，30 米以外隐藏
var near_lod := MeshInstance3D.new()
near_lod.mesh = high_poly_mesh
near_lod.visibility_range_end = 30.0          # 超过 30 米就不再绘制
near_lod.visibility_range_fade_mode = GeometryInstance3D.VISIBILITY_RANGE_FADE_SELF

# 远处：低模，30 米以外才出现
var far_lod := MeshInstance3D.new()
far_lod.mesh = low_poly_mesh
far_lod.visibility_range_begin = 30.0         # 0 = 不限制（不隐藏）
far_lod.visibility_range_fade_mode = GeometryInstance3D.VISIBILITY_RANGE_FADE_SELF

# 网格自身携带的 LOD 层级（导入时生成的 LOD）由 lod_bias 控制切换快慢
near_lod.lod_bias = 1.0
```

> `visibility_range_begin` / `visibility_range_end` 的默认值 `0.0` 表示**不启用**该方向的检查。淡出模式 `VISIBILITY_RANGE_FADE_SELF` 需要配合 `visibility_range_begin_margin` / `visibility_range_end_margin` 才有明显的过渡宽度，并且只在 Forward+ 下生效。

完整属性表：

| 属性 | 默认 | 含义 |
|------|------|------|
| `visibility_range_begin` | 0.0 | 小于这个距离**不绘制**（0 = 不限制） |
| `visibility_range_end` | 0.0 | 大于这个距离**不绘制**（0 = 不限制） |
| `visibility_range_begin_margin` | 0.0 | 起始端的淡出宽度 |
| `visibility_range_end_margin` | 0.0 | 结束端的淡出宽度 |
| `visibility_range_fade_mode` | `VISIBILITY_RANGE_FADE_DISABLED` | `DISABLED` / `SELF` / `DEPENDENCIES` |

**用法要点**：

- `begin` 与 `end` 之间是**可见区间**；两者都为 0 表示永远可见；
- 淡出只在 **Forward+** 下生效（Compatibility / Mobile 不支持）；
- `VISIBILITY_RANGE_FADE_DEPENDENCIES` 会连带影响依赖该物体的子节点；
- **可见性范围是「物体级」的**：`MultiMeshInstance3D` 上设置的是整个多网格的范围，
  不是单个实例——所以「远处的树少画几棵」不能靠它实现，得用 `visible_instance_count` 或 `amount_ratio` 那种思路。

### 3.3 网格 LOD 与 `lod_bias`

Godot 4 的网格 LOD 层级在**导入阶段**生成（导入器的 Mesh 高级选项里可以配置 LOD 数量与简化比例），
运行时由 `lod_bias` 控制「什么时候切到低模」：

- `lod_bias` 越大 → 越早切到低模（省几何，费画质）；
- `lod_bias` 越小 → 越晚切（保画质，费几何）；
- `1.0` 是「按屏幕占比的默认阈值切换」。

网格层级也可以在运行时生成：

```gdscript
# SurfaceTool 可以直接生成 LOD 层级
var st := SurfaceTool.new()
st.begin(Mesh.PRIMITIVE_TRIANGLES)
st.set_normal(Vector3.UP)
st.set_uv(Vector2(0, 0))
st.add_vertex(Vector3(0, 0, 0))
st.add_vertex(Vector3(1, 0, 0))
st.add_vertex(Vector3(0, 1, 0))
st.generate_lod(0.5, 0.8)      # 生成简化层级
var mesh_with_lod := st.commit()
```

> 📌 `lod_bias` 也会作用在**反射探针**上：`ReflectionProbe.mesh_lod_threshold` 单独控制反射里用的 LOD 阈值。
> `Viewport.mesh_lod_threshold` 则是整个视口的全局阈值。
> 这三个阈值叠在一起时，**关卡里某个物体「怎么换视角就糊」**，通常就是它们在打架。

**一套典型的距离分级参考**：

> ⚠️ 下表为示意数据（未附测试环境），实际收益取决于材质数量、
> Draw Call 与过度绘制占比，请在目标平台实测。

| 距离 | 多边形数 | 预期收益 |
|------|---------|---------|
| 0-10m | 10000 | - |
| 10-30m | 5000 | 显著下降 |
| 30+m | 1000 | 接近消除几何开销 |

### 3.4 遮挡剔除：基于 **Embree** 的实现

> Godot 4 **有**遮挡剔除：4.3 内置基于 **Embree** 的实现，但它**默认关闭**，必须显式打开全局开关。

```gdscript
# 遮挡剔除的正确做法：
# 1) 全局开关（项目设置，默认 false）
#    Project Settings → Rendering → Occlusion Culling → Use Occlusion Culling
#    即 rendering/occlusion_culling/use_occlusion_culling = true
#    自定义 Viewport 还要额外设 Viewport.use_occlusion_culling = true
# 2) 在场景中放置 OccluderInstance3D，把大块墙体/地板标记为遮挡体
# 3) 在编辑器里点 "Bake Occluders" 烘焙出遮挡网格（只统计不透明材质）
var occluder := OccluderInstance3D.new()
occluder.occluder = BoxOccluder3D.new()   # 也可用 QuadOccluder3D / SphereOccluder3D / PolygonOccluder3D
add_child(occluder)
```

> - 遮挡剔除在 **CPU 侧**用 Embree 渲染遮挡体到一张低分辨率缓冲，再据此逐个剔除 3D 节点，因此**有 CPU 开销**。
> - 大型开放场景几乎没有收益；这类场景用**网格 LOD + 可见性范围**更划算。
> - Web 导出模板出于内存限制**默认不支持**遮挡剔除，需要用 `module_raycast_enabled=yes` 自行编译模板。
> - 遮挡体被移动或隐藏会触发后台重算，可能掉帧几帧。

遮挡体的四种形状：

| 遮挡体 | 属性 | 适用 |
|--------|------|------|
| `BoxOccluder3D` | `size` | 房间、箱子、整块墙体 |
| `QuadOccluder3D` | `size` | 薄板（隔断、单面墙） |
| `SphereOccluder3D` | `radius` | 球形掩体 |
| `PolygonOccluder3D` | `polygon` | 任意凸多边形 |

`OccluderInstance3D` 自己的两个属性：

| 属性 | 说明 |
|------|------|
| `bake_mask` | 烘焙时按材质分组，**不同组的遮挡体互不遮挡**（避免"墙 A 被墙 B 挡住"的错误剔除） |
| `bake_simplification_distance` | 烘焙时的简化距离：距离越远简化越狠，遮挡网格越小 |

> 📌 **遮挡剔除的收益模型**：它省的是「被挡住物体的顶点 + 像素」，
> 但付出的是「每帧在 CPU 上重建遮挡体缓冲 + 逐节点查询」。
> 所以它只在**「相机背后有大量物体」**的室内场景才划算；
> 开阔场景里被遮挡的物体本来就少，开了纯亏。

> ⚠️ 遮挡剔除需要 **Embree** 支持。Web 导出模板默认不包含（见上面那条），移动端也不建议开。

### 3.5 包围盒与剔除裕量

| 属性 | 作用 |
|------|------|
| `GeometryInstance3D.custom_aabb` | 手动指定包围盒，替代引擎自动计算 |
| `GeometryInstance3D.extra_cull_margin` | 给包围盒加一圈「保险」，防止边缘物体被误剔除 |
| `MultiMesh.custom_aabb` | 多网格的整体包围盒 |
| `VisualInstance3D.sorting_use_aabb_center` | 透明排序用 AABB 中心而不是物体原点 |

**什么时候需要手动指定 `custom_aabb`**：

- 顶点动画（CPU 侧改顶点）：引擎算的 AABB 不含动画位移 → 物体被提前剔除；
- 骨骼动画的极端姿势超出静态包围盒；
- 粒子系统、程序化生成的网格。

**什么时候需要 `extra_cull_margin`**：任何「包围盒会变化」的物体，
给 0.1~0.5 的余量通常就能消除「走到边缘突然消失」的现象。

### 3.6 常见误用

| 误用 | 后果 | 正解 |
|------|------|------|
| 给需要远处可见的物体设 `visibility_range_end` | 远处凭空消失 | 先确认设计意图；用淡出模式 |
| 以为淡出在所有后端都生效 | Compatibility / Mobile 里硬切 | 淡出只在 Forward+ 生效，重要物体别依赖它 |
| 在 `MultiMeshInstance3D` 上设可见性范围以为能逐实例剔除 | 整批一起消失 | 多网格只能整体剔除 |
| 遮挡体用了半透明材质 | 烘焙不出遮挡网格 | 遮挡体必须不透明 |
| 遮挡体到处乱放 | CPU 开销吃掉收益 | 只在真正的「房间」放 |
| 不动的东西设了 `extra_cull_margin` 很大 | 视锥剔除形同虚设 | 裕量按实际动画幅度给 |

---

### 3.7 渲染层掩码：比剔除更「粗」但更便宜

视锥剔除解决不了「物体在视野里但我不想画它」的场景（比如小地图上的标记、UI 用的 3D 头像）。
这时用**渲染层**：

| 属性 | 作用 |
|------|------|
| `VisualInstance3D.layers` | 这个物体属于哪些渲染层（位掩码） |
| `Camera3D.cull_mask` | 这个相机渲染哪些层（位掩码） |
| `VisualInstance3D.set_layer_mask_value()` / `get_layer_mask_value()` | 按位设置 / 读取 |

```gdscript
# 约定：层 1 = 主场景，层 2 = 特效与 UI 辅助物
var marker := MeshInstance3D.new()
marker.layers = 2                       # 只在「特效相机」里可见

var main_camera := Camera3D.new()
main_camera.cull_mask = 1               # 主相机只渲染主场景层
```

> ⚠️ **渲染层和物理层是两回事**：`VisualInstance3D.layers` 只影响渲染，
> 物理碰撞看的是 `CollisionObject3D.collision_layer` / `collision_mask`。
> 调层的时候别把两者搞混——「物体穿模了」十有八九是物理层没设对，不是渲染层。

> 💡 渲染层最省的一个用法：**把粒子、飘字、辅助线放到单独一层**，
> 这样在「录制演示视频」或者「做性能对比基线」时可以一键关掉它们。

---

## 四、GPU 侧优化

### 4.0 技巧速查

| 技巧 | 说明 |
|------|------|
| **减少纹理大小** | 使用压缩纹理 |
| **减少着色器复杂度** | 简化计算 |
| **使用 Instancing** | GPU 实例化 |
| **减少 Overdraw** | 排序优化 |

### 4.1 纹理压缩

> ⚠️ 下表为示意数据（未附测试环境）。压缩比与平台、贴图内容强相关，请在目标平台上实测。

| 格式 | 平台 | 压缩比 |
|------|------|--------|
| **BPTC** | PC | 4:1 |
| **ETC2** | Android | 4:1 |
| **PVRTC** | iOS | 4:1 |
| **S3TC** | 通用 | 4:1 |

对应到引擎里的格式常量：

| 常量 | 格式 | 典型用途 |
|------|------|----------|
| `Image.COMPRESS_BPTC` | BC7 | PC 通用，带 alpha 质量好 |
| `Image.COMPRESS_S3TC` | DXT1/3/5 | 老 PC / 通用 |
| `Image.COMPRESS_ETC2` | ETC2 | Android 主流 |
| `Image.COMPRESS_ASTC` | ASTC 4x4 / 8x8 | 移动端高质量 |

```gdscript
# 运行时压缩一张贴图（一般用不到，导入期压缩更好）
var img := Image.create_empty(512, 512, false, Image.FORMAT_RGBA8)
img.compress(Image.COMPRESS_BPTC, 0.9)
```

> 📌 **压缩贴图必须在导入期做**（Project Settings → Import → 纹理 → Compress Mode），
> 运行时的 `Image.compress()` 会吃掉 CPU 时间，收益只在「运行时下载的资源」这类场景成立。
> 另外：**法线贴图、遮罩贴图（ORM）不能当普通颜色贴图压**，要选对应的压缩模式，否则光照会出错。

### 4.2 过度绘制与透明

过度绘制（overdraw）是 GPU 侧最常见的瓶颈：

| 症状 | 检查方法 | 对策 |
|------|----------|------|
| 半透明物体大量重叠 | `Viewport.debug_draw = Viewport.DEBUG_DRAW_OVERDRAW` | 减少重叠、缩小面积、改混合模式 |
| 粒子铺满屏幕 | 同上 | 降粒子数、降屏幕覆盖、减通道 |
| UI 大量叠层 | 2D 的 overdraw | 合并 UI 层、减少全屏半透明遮罩 |

> 调试方法见第 22 篇《渲染调试工具》（`Viewport.DebugDraw` 全 27 项）。

### 4.3 后处理

| 后处理 | 成本 | 降本手段 |
|--------|------|----------|
| Glow / Bloom | 多级模糊 pass | 降低 glow levels 数、缩小辉光缓冲 |
| DOF | 依赖深度缓冲 | 用 `CameraAttributesPractical` 的低质量档 |
| SSR | 屏幕空间追踪 | 降步数、只在关键区域开 |
| SSAO / SSIL | 依赖深度+法线 | 降质量档、关掉不必要的 |
| 体积雾 | 3D 纹理 + 光照 | 降分辨率 |

> 📌 后处理在 Compatibility 后端支持最少（很多直接不支持），
> 「两个后端表现一致」的项目要特别小心这一块。

---

## 五、统一性能数字口径与测试条件模板

### 5.1 为什么必须带测试条件

同一句「优化后帧率从 45 提到 60」，在不同条件下可以是完全相反的结论：

- 1080p 还是 4K？→ 填充率差 4 倍；
- RTX 3060 还是核显？→ 结论可能反转；
- 场景里有 10 万个三角形还是 1000 万个？→ CPU 瓶颈变 GPU 瓶颈；
- 采样 1 帧还是 600 帧？→ 1 帧的数字是噪声。

**本节的规则**（本书统一口径）：

1. 任何性能数字，必须能回答「在什么条件下测的」；
2. 条件至少包括：**引擎版本 / 渲染后端 / GPU / 分辨率 / 场景规模 / 采样方式**；
3. 拿不到测试条件时，数字必须标注为「⚠️ 示意数据（未附测试环境）」；
4. 横向比较只在**同一组条件**内有效，跨条件比较无效。

### 5.2 测试条件模板

复制下面这张表，每个性能数字旁边都放一份：

```text
【测试条件】
引擎版本：Godot 4.3.stable.official（Forward+ 渲染器）
GPU：NVIDIA GeForce RTX 3060 12GB（驱动 551.23）
CPU：Intel Core i5-12400F
内存：32 GB DDR4-3200
分辨率：1920×1080，窗口模式，全屏 VSync 关闭
场景规模：约 1,200 个 MeshInstance3D / 86 万三角形 / 24 个材质 / 41 MB 贴图
采样方式：预热 120 帧后连续采样 600 帧，取平均值与 P95 帧时间
工具：引擎内 Performance 监视器 + 调试构建
备注：所有数值取自单次连续运行，未跨机器复测
```

### 5.3 采样方法（别只取一帧）

| 指标 | 建议 |
|------|------|
| 预热 | 至少 2 秒 / 120 帧（着色器编译、纹理上传都在前几帧） |
| 采样长度 | ≥ 10 秒 / 600 帧 |
| 平均帧时间 | `sum(frame_time) / frames` |
| P95 / P99 | 用来发现「偶发卡顿」，只看平均值会漏掉尖刺 |
| 抖动 | 帧时间的标准差，比平均帧时间更能反映手感 |
| 重复 | 同一条件至少跑 3 次，取中位数 |

### 5.4 复现步骤（写进报告里）

```text
1. 用 4.3.stable 官方版打开项目，确认渲染后端为 Forward+；
2. 关闭 VSync，固定窗口分辨率 1920×1080；
3. 导出调试构建（debug build），或用编辑器运行并勾上「仅调试构建」相关选项；
4. 固定相机路径（录制一段固定轨迹回放），避免手动操作造成波动；
5. 预热 120 帧，采样 600 帧，导出数据；
6. 重复 3 次，取中位数。
```

> 📌 相机轨迹固定是**最容易被忽略、影响最大**的一条：手动飞行时镜头朝向的细微差别，
> 会让视锥剔除的结果差几个百分点，足以掩盖真实优化效果。

### 5.5 自动采集环境信息

把测试条件模板里「手填」的部分自动化，避免事后补：

```gdscript
# 性能报告生成器：把环境信息与渲染统计一起写进文本
extends Node

const SAMPLE_FRAMES := 600

var _frames: int = 0
var _total_time: float = 0.0
var _report: Array = []

func _ready() -> void:
	_report.append("【测试条件】")
	_report.append("引擎版本：%s" % str(Engine.get_version_info()))
	_report.append("GPU：%s" % RenderingServer.get_video_adapter_name())
	_report.append("GPU 厂商：%s" % RenderingServer.get_video_adapter_vendor())
	_report.append("CPU：%s（%d 核）" % [OS.get_processor_name(), OS.get_processor_count()])
	_report.append("分辨率：%s" % str(DisplayServer.window_get_size()))
	_report.append("采样方式：预热 120 帧后连续采样 %d 帧" % SAMPLE_FRAMES)

func _process(delta: float) -> void:
	_frames += 1
	if _frames <= 120:
		return
	_total_time += delta
	if _frames < 120 + SAMPLE_FRAMES:
		return
	_write_report()

func _write_report() -> void:
	var used := _frames - 120
	_report.append("【结果】")
	_report.append("平均帧时间：%.2f ms" % (_total_time * 1000.0 / used))
	_report.append("平均 FPS：%.1f" % (used / _total_time))
	_report.append("绘制调用：%d" % int(Performance.get_monitor(Performance.RENDER_TOTAL_DRAW_CALLS_IN_FRAME)))
	_report.append("渲染对象：%d" % int(Performance.get_monitor(Performance.RENDER_TOTAL_OBJECTS_IN_FRAME)))
	_report.append("三角形：%d" % int(Performance.get_monitor(Performance.RENDER_TOTAL_PRIMITIVES_IN_FRAME)))
	var f := FileAccess.open("user://perf_report.txt", FileAccess.WRITE)
	if f != null:
		f.store_string("\n".join(_report))
		f.close()
```

> ⚠️ `Engine.get_version_info()` 返回的是字典，直接 `str()` 打印可读性一般，
> 正式报告里建议取其中的 `string` 字段。上面这段是为了「零依赖先把环境记下来」。
> 另外 `FileAccess` 写入 `user://` 目录，不同平台的实际路径不同（用 `OS.get_user_data_dir()` 可以拿到）。

### 5.6 性能报告模板

```text
【结论】把 1,200 个石头实例合并成 3 个 MultiMesh 后，CPU 帧时间下降 2.1 ms。

【测试条件】
（照抄 5.2 的模板）

【改动】
1. 石头：1,200 个 MeshInstance3D → 3 个 MultiMeshInstance3D（按区域分块）
2. 材质：4 份材质副本 → 1 份共享材质 + 逐实例颜色
3. 阴影：远处的小物件关闭投影

【结果】
| 指标 | 改前 | 改后 | 变化 |
|------|------|------|------|
| 平均帧时间 | 22.4 ms | 20.3 ms | -2.1 ms |
| 绘制调用 | 1,247 | 89 | -93% |
| 阴影绘制调用 | 1,190 | 12 | -99% |
| 三角形 | 862,000 | 851,000 | -1.3% |

【结论有效性】
只在本测试条件下成立；移动端与 Compatibility 后端未复测。
```

### 5.7 本篇性能表的口径声明

本章出现的所有带「效果百分比」的表格，**统一按「⚠️ 示意数据（未附测试环境）」处理**，
只用于说明**相对关系**（例如「MultiMesh 的 draw call 降幅大于共享材质」），
**不可作为选型依据**。要给出真实数字，请按 5.2 的模板自己测一遍。

### 5.8 常见性能目标值

> ⚠️ 下表目标值为**示意数据**（未附测试环境），请按自己的项目预算调整。

> ⚠️ 下表为示意数据（未附测试环境），仅用于建立数量级概念。实际开销取决于场景规模与目标硬件，请在目标平台实测。

| 指标 | 目标 |
|------|------|
| **帧率** | 60 FPS |
| **DrawCall** | <500 |
| **GPU 占用** | <80% |
| **显存占用** | <2GB |

> ⚠️ 这四个数字是**预算**，不是实测值。预算的意义在于「超出就要有人负责优化」，
> 而不是「达到就一定流畅」。定预算时请按第 5.2 节的模板补上测试条件。

### 5.9 六种「优化无效」的情形

| 现象 | 真实原因 | 下一步 |
|------|----------|--------|
| Draw Call 砍了 90%，帧率纹丝不动 | 瓶颈在 GPU 填充率或 CPU 逻辑 | 换测量维度（见第 22 篇） |
| 帧率上去了，但 GPU 时间没降 | 省下的是 CPU 侧提交时间 | 这也是优化，别追求 GPU 数字 |
| 合并了 1000 个物体，阴影 pass 反而更贵 | 合面后整体投影面积变大 | 关小物件投影或用 `SHADOW_CASTING_SETTING_OFF` |
| 编辑器里很流畅，导出版很卡 | 编辑器用的是不同的渲染路径（兼容模式、调试绘制） | 用导出构建复测 |
| 帧时间很稳但「感觉卡」 | 可能是输入延迟或 VSync 造成的 | 关 VSync 测真实帧时间 |
| 只在一个视角测，转个视角就崩 | 换了可见物体集合 | 固定相机轨迹，多视角采样 |

> 📌 **最后一条最容易被忽略**：绝大多数性能问题都藏在「另一个视角」里。
> 固定轨迹回放不是形式主义，是让数据可比较的前提。

### 5.10 什么时候**不要**优化

| 情况 | 理由 |
|------|------|
| 目标设备本身就弱，但玩家机型更弱 | 先定目标机型再定预算 |
| 效果只在过场出现一次 | 过场可以加载慢一点 |
| 优化会牺牲可维护性且收益 < 5% | 不划算 |
| 问题其实是**逻辑 bug**（每帧 `get_node`、字符串拼接） | 那是脚本问题，不是渲染问题 |

> 💡 性能优化的最大浪费是「优化了没人看的地方」。
> 先用第 22 篇的工具确认问题真实存在，再动手。

---

## 六、把优化排进迭代流程

### 6.1 优化的四个阶段

```
1. 测量：先有数据（用第 22 篇的工具链）
    ↓
2. 定位：CPU 忙还是 GPU 忙？填充率还是几何量？
    ↓
3. 改动：一次只动一个变量，改完立刻复测
    ↓
4. 固化：把测试条件写进报告，把预算写进团队规范
```

### 6.2 每类问题的第一选择

| 症状 | 第一选择 | 备选 |
|------|----------|------|
| Draw Call 极高 | `MultiMesh` 合并同类物体 | 离线合面 |
| 状态切换多 | 共享材质 | 纹理图集 |
| 阴影 pass 极高 | 关小物件投影 | 缩小阴影视图 |
| 填充率爆 | 降分辨率 / 关后处理 | 减少屏幕覆盖 |
| 几何量爆 | 网格 LOD + `lod_bias` | `visibility_range` |
| 相机背后物体多 | 遮挡剔除（**Embree**） | 先用可见性范围顶一顶 |

### 6.3 性能预算

给每个项目定三条线，比事后优化省力得多：

| 预算 | 典型值（⚠️ 示意数据） | 说明 |
|------|------------------------|------|
| 绘制调用上限 | < 500 / 帧 | 超过说明场景组织失控 |
| 三角形上限 | < 100 万 / 帧 | 移动端要更严 |
| 帧时间预算 | 16.6 ms（60 FPS） | 其中 GPU 侧建议 < 10 ms |

> ⚠️ 上表是**示意数据（未附测试环境）**，仅用于建立数量级概念。
> 预算值必须按自己的项目与目标平台重新定，并写进团队规范。

### 6.4 把结论固化成规范

优化做多了以后，应该把结论沉淀成「规范」，而不是每次重新讨论：

| 规范条目 | 写法示例 |
|----------|----------|
| 静态场景的 Draw Call 预算 | 单个室内场景 ≤ 300 |
| 材质复用规则 | 同一类物件必须共享材质，差异用逐实例颜色表达 |
| LOD 强制项 | 导入网格必须生成 2 级 LOD，`lod_bias` 默认 1.0 |
| 遮挡剔除使用范围 | 仅室内场景开启，开关由场景负责人决定 |
| 性能报告格式 | 用 5.6 的模板，缺测试条件的数据不予采信 |

> 💡 **规范的价值在于「默认值就正确」**：把「共享材质」「生成 LOD」做成导入与提交的默认行为，
> 比开十次评审会都管用。

---

## 核心要点

1. **没有自动合批**：Godot 4 的 3D 渲染器没有通用合批器（"batch" 命中数为 0），等价手段是 `MultiMesh`、材质共享与可见性范围。
2. **MultiMesh** 是 Godot 4 的实例化方案：数据在 buffer 里而不是节点里，支持逐实例变换、颜色与自定义数据（着色器里读 `INSTANCE_CUSTOM`）。
3. **状态切换**与 Draw Call 是两回事：共享材质降的是状态切换，Draw Call 数字不变——只看数字会误判效果。
4. **LOD 没有 `LOD3D` 节点**：距离 LOD 靠 `visibility_range_begin/end` + `visibility_range_fade_mode`，网格层级靠 `lod_bias`。
5. **遮挡剔除**4.3 确有基于 **Embree** 的实现，但默认关闭，需打开 `rendering/occlusion_culling/use_occlusion_culling` 并放置 `OccluderInstance3D`；它在 CPU 侧有开销，只在封闭室内场景划算。
6. **包围盒**要跟上动画：`custom_aabb` 与 `extra_cull_margin` 能消除「走到边缘凭空消失」。
7. **性能数字必须带测试条件**：引擎版本、渲染后端、GPU、分辨率、场景规模、采样方式六项缺一不可；拿不到就标「⚠️ 示意数据」。
8. **采样纪律**：预热 120 帧、采样 ≥ 600 帧、固定相机轨迹、重复 3 次取中位数，再看 P95 尖刺。

---

## 🔗 延伸阅读

- **官方文档**: [可见性范围（Visibility ranges / HLOD）](https://docs.godotengine.org/en/stable/tutorials/3d/visibility_ranges.html)、[遮挡剔除（Occlusion culling）](https://docs.godotengine.org/en/stable/tutorials/3d/occlusion_culling.html)、[使用服务器优化（Optimization using Servers）](https://docs.godotengine.org/en/stable/tutorials/performance/using_servers.html)、[多网格（MultiMesh）](https://docs.godotengine.org/en/stable/tutorials/performance/using_servers.html)
- **类参考**: [MultiMesh](https://docs.godotengine.org/en/stable/classes/class_multimesh.html)、[MultiMeshInstance3D](https://docs.godotengine.org/en/stable/classes/class_multimeshinstance3d.html)、[GeometryInstance3D](https://docs.godotengine.org/en/stable/classes/class_geometryinstance3d.html)、[OccluderInstance3D](https://docs.godotengine.org/en/stable/classes/class_occluderinstance3d.html)、[Performance](https://docs.godotengine.org/en/stable/classes/class_performance.html)
- **源码位置**: `servers/rendering_server.h`（`multimesh_*`）、`scene/3d/mesh_instance_3d.h`、`scene/3d/geometry_instance_3d.h`、`servers/rendering/renderer_scene_cull.cpp`、`servers/rendering/renderer_scene_occlusion_cull.cpp`

---

## 📋 下一章预告

**第 22 篇：渲染调试工具**

- 渲染 Debug 开关：碰撞体、导航网格
- Viewport 可视化：`Viewport.DebugDraw` 全 27 项
- 性能监控：Performance 监视器与渲染统计
- Vulkan 验证层与 GPU 帧分析（RenderDoc / apitrace / Nsight）

---

**作者**: wangshucheng
**首发平台**: 微信公众号  
**写作时间**: 2026 年 3 月  
**Godot 版本**: 4.x（基线 4.3；本文涉及的 4.4+ 差异已在行内标注）

---

**上一篇**: [第 20 篇：粒子渲染](/articles/20-particle-rendering.md)
**下一篇**: [第 22 篇：渲染调试工具](/articles/22-rendering-debug-tools.md)

---

*如果你觉得文章有帮助，欢迎转发给更多开发者！*
