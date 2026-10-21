# 第 18 篇：2D 渲染

> **本章导读**：
> 这一章把 Godot 的 2D 渲染路径拆开讲：谁在裁剪、谁在排序、绘制命令怎么进内存、`_draw()` 与 `queue_redraw()` 的生命周期怎么走。
> 随后逐个交代 CanvasItem 的材质、混合模式、可见性与裁剪、多分辨率与 `canvas_transform`、2D 光照这几组最容易踩坑的 API。
> 最关键的一节在第七章：**Godot 4 没有 2D 合批器**——这不是"性能不够好"，而是 Godot 3 的 batcher 已经被移除，源码里连 "batch" 这个词都没有。
> 读完你应该能自己判断"我这个 2D 场景到底慢在哪一环"，而不是盲目套用 3.x 时代的经验。

> **前置知识**：第 17 篇《GDShader 语言》
> **难度**：进阶

---

## 一、2D 渲染架构

### 1.1 原生 2D

Godot 使用原生 2D 渲染，而非 3D 模拟：

| 特性 | Godot | Unity |
|------|-------|-------|
| **2D 坐标** | 像素坐标 | 3D 投影 |
| **渲染器** | CanvasItem | 3D 管线 |
| **批处理** | 无自动合批器，靠 MultiMesh / 共享材质 | SRP Batcher / GPU Instancing |
| **性能** | 优秀 | 良好 |

### 1.2 CanvasItem

```gdscript
# CanvasItem 是所有 2D 节点的基类
# Node2D
#   ├── Sprite2D
#   ├── Polygon2D
#   └── TileMapLayer
# Control
#   ├── Label
#   ├── Button
#   └── Panel
```

`CanvasItem` 是 2D 渲染的**最小单元**。它做三件事：

1. 持有一串**绘制命令**（`draw_rect` / `draw_texture` / …）；
2. 持有一份**变换**（`Node2D` 上的 `position` / `rotation` / `scale`）；
3. 参与**可见性、裁剪、排序、材质**的决策。

节点树如下（`Control` 也继承自 `CanvasItem`）：

```
CanvasItem (Node)
├── Node2D
│   ├── Sprite2D
│   ├── Polygon2D
│   ├── TileMapLayer
│   ├── MultiMeshInstance2D
│   ├── Camera2D
│   ├── PointLight2D
│   └── LightOccluder2D
└── Control
    ├── Label
    ├── Button
    └── Panel
```

### 1.3 渲染路径：cull → render

2D 渲染在 4.x 拆成两个 C++ 模块，源码都在 `servers/rendering/` 下：

| 模块（C++ 类名） | 源文件 | 职责 |
|---|---|---|
| RendererCanvasCull | `servers/rendering/renderer_canvas_cull.cpp`（约 93 KB）、`renderer_canvas_cull.h` | **剔除与排序**：遍历画布树、算裁剪矩形、算 modulate、按 z 排序 |
| RendererCanvasRender（抽象基类）/ RendererCanvasRenderRD（RD 实现） | `servers/rendering/renderer_canvas_render.h`、`servers/rendering/renderer_rd/renderer_canvas_render_rd.cpp`（约 113 KB） | **命令提交**：把绘制命令翻译成后端（RD / GLES3）的渲染调用 |

> 上面两个是 **C++ 内部类**，不是 Godot 的脚本 API——它们不出现在官方类参考里，也没有任何 `ClassDB` 绑定。引用它们只能用源码路径，不能在 GDScript 里 `new` 出来。脚本侧的对应物是 `RenderingServer` 的 `canvas_item_add_*` / `canvas_item_set_*` 系列。

剔除与排序模块的核心是两个私有函数（源码签名）：

```cpp
void _render_canvas_item_tree(RID p_to_render_target, Canvas::ChildItem *p_child_items,
        int p_child_item_count, const Transform2D &p_transform, const Rect2 &p_clip_rect,
        const Color &p_modulate, RendererCanvasRender::Light *p_lights,
        RendererCanvasRender::Light *p_directional_lights,
        RS::CanvasItemTextureFilter p_default_filter, RS::CanvasItemTextureRepeat p_default_repeat,
        bool p_snap_2d_vertices_to_pixel, uint32_t p_canvas_cull_mask,
        RenderingMethod::RenderInfo *r_render_info = nullptr);

void _cull_canvas_item(Item *p_canvas_item, const Transform2D &p_parent_xform,
        const Rect2 &p_clip_rect, const Color &p_modulate, int p_z,
        RendererCanvasRender::Item **r_z_list, RendererCanvasRender::Item **r_z_last_list,
        Item *p_canvas_clip, Item *p_material_owner, bool p_allow_y_sort,
        uint32_t p_canvas_cull_mask, const Point2 &p_repeat_size, int p_repeat_times);
```

也就是说，一帧 2D 渲染的顺序是：

```
World2D / CanvasLayer
        │
        ▼
RendererCanvasCull::_render_canvas_item_tree()
        │  遍历画布的子项
        ▼
RendererCanvasCull::_cull_canvas_item()   ← 递归
        │  · 累乘父级 transform
        │  · 累乘 modulate / self_modulate
        │  · 叠加父级 clip_rect
        │  · 按 z_index 分桶（z_list / z_last_list）
        │  · 处理 y_sort
        ▼
RendererCanvasRender::canvas_render_items()
        │  按 z 顺序遍历，调用后端
        ▼
RendererCanvasRenderRD（RD 后端）/ RasterizerCanvasGLES3（兼容后端）
```

剔除与排序模块的 Item 结构继承自渲染模块的 Item 结构，额外带着 `z_index`、`z_relative`、`sort_y`、`modulate`、`self_modulate`、`use_parent_material`、`visibility_layer`、`ysort_*` 这些剔除阶段需要的信息。

### 1.4 绘制命令在内存里长什么样

渲染模块的 `Item` 里存的是一条**命令链表**（`Command *commands`），不是"渲染结果"。每个 `Command` 有一个类型标签，枚举定义在 `servers/rendering/renderer_canvas_render.h`：

```cpp
struct Command {
    enum Type {
        TYPE_RECT,
        TYPE_NINEPATCH,
        TYPE_POLYGON,
        TYPE_PRIMITIVE,
        TYPE_MESH,
        TYPE_MULTIMESH,
        TYPE_PARTICLES,
        TYPE_TRANSFORM,
        TYPE_CLIP_IGNORE,
        TYPE_ANIMATION_SLICE,
    };
    Command *next = nullptr;
    Type type;
};
```

对照到脚本侧的绘制命令：

| `Command::Type` | 对应的绘制命令 | 承载数据的 C++ 结构 |
|---|---|---|
| `TYPE_RECT` | `draw_rect` / `draw_texture_rect` / `draw_texture_rect_region` | CommandRect |
| `TYPE_NINEPATCH` | 九宫格绘制 | CommandNinePatch |
| `TYPE_POLYGON` | `draw_polygon` / `draw_colored_polygon` | CommandPolygon |
| `TYPE_PRIMITIVE` | `draw_primitive` | CommandPrimitive |
| `TYPE_MESH` | `draw_mesh` | CommandMesh |
| `TYPE_MULTIMESH` | `draw_multimesh` | CommandMultiMesh |
| `TYPE_PARTICLES` | 粒子绘制 | CommandParticles |
| `TYPE_TRANSFORM` | `draw_set_transform` | CommandTransform |
| `TYPE_CLIP_IGNORE` | 临时关闭裁剪 | CommandClipIgnore |
| `TYPE_ANIMATION_SLICE` | `draw_animation_slice` | CommandAnimationSlice |

> 右列的 C++ 结构名同样是**引擎内部类型**，只在源码里出现，脚本侧不可见。脚本能看到的只有中间那列——`CanvasItem` 的绘制方法。

命令是**一次性生成、长期缓存**的：`draw_animation_slice` 这类命令存在的意义，就是让一条命令只画一次，而不是每帧重画。

内存分配上有个值得知道的细节：命令**按 4 KB 一块**分配（`CommandBlock::MAX_SIZE = 4096`），第一条命令单独 `memnew`，其余塞进块里；块只增不减，且在 CanvasItem 被删除前不会释放。这样做是为了让命令链表在内存里**连续**，提高缓存命中率。

> 推论：频繁 `queue_redraw()` 会不断往链表尾部追加新命令。旧命令的清理发生在 CanvasItem 重新绘制时（`canvas_item_clear` 语义）。如果每帧都重绘一个有几万条命令的 CanvasItem，内存与遍历开销都会明显上升——这是 2D 性能问题里最容易被忽略的一类。

### 1.5 z 排序与 y_sort

剔除与排序模块用两个数组做 z 分桶：

- `z_list`：普通项，按 `z_index` 从小到大排；
- `z_last_list`：需要"最后画"的项（比如带混合的顶层 UI）。

z 值的范围由 `z_range = RS::CANVAS_ITEM_Z_MAX - RS::CANVAS_ITEM_Z_MIN + 1` 决定；`z_index` 越大越靠前。`z_as_relative` 为 `true`（默认）时，z 值相对**父节点**累加；设为 `false` 则相对根节点。

`y_sort_enabled` 打开后，同一个父节点下的子项按 **Y 坐标**排序（源码里的 ItemPtrSort 比较器：先比 `ysort_pos.y`，相等时比 `ysort_index`）。这让 2D 角色能正确地按脚底 Y 排序遮挡，而不用手写 `z_index`。

> `y_sort_enabled` 的排序只发生在**同一个父节点**的子项之间。要跨父节点排序，得把相关节点放在同一个父节点下（或用 `YSort` 容器节点）。

### 1.6 脚本侧的等价入口：RenderingServer 的 canvas_item API

上面讲的都是 C++ 内部实现。脚本侧真正能碰到的是 `RenderingServer` 的 `canvas_item_*` 系列——它是 CanvasItem 在渲染服务器一侧的**低层镜像**：

| 分类 | 方法 |
|---|---|
| 创建与销毁 | `RenderingServer.canvas_item_create()`、`RenderingServer.canvas_item_clear()` |
| 追加命令 | `RenderingServer.canvas_item_add_rect()`、`canvas_item_add_circle()`、`canvas_item_add_line()`、`canvas_item_add_polyline()`、`canvas_item_add_polygon()`、`canvas_item_add_primitive()`、`canvas_item_add_texture_rect()`、`canvas_item_add_texture_rect_region()`、`canvas_item_add_nine_patch()`、`canvas_item_add_multiline()`、`canvas_item_add_mesh()`、`canvas_item_add_multimesh()`、`canvas_item_add_particles()`、`canvas_item_add_set_transform()`、`canvas_item_add_clip_ignore()`、`canvas_item_add_animation_slice()` |
| 状态 | `RenderingServer.canvas_item_set_transform()`、`canvas_item_set_material()`、`canvas_item_set_modulate()`、`canvas_item_set_self_modulate()`、`canvas_item_set_visible()`、`canvas_item_set_z_index()`、`canvas_item_set_z_as_relative_to_parent()`、`canvas_item_set_visibility_layer()`、`canvas_item_set_light_mask()`、`canvas_item_set_clip()`、`canvas_item_set_parent()`、`canvas_item_set_use_parent_material()`、`canvas_item_set_draw_behind_parent()`、`canvas_item_set_sort_children_by_y()`、`canvas_item_set_default_texture_filter()`、`canvas_item_set_default_texture_repeat()`、`canvas_item_set_canvas_group_mode()` |

对应的**节点侧**入口是 `CanvasItem.get_canvas_item()`——它返回该节点在渲染服务器里的 CanvasItem RID：

```gdscript
var rid := $Sprite2D.get_canvas_item()
RenderingServer.canvas_item_set_z_index(rid, 10)
```

> 绝大多数情况直接用 `CanvasItem` / `Node2D` 的属性就够了（`z_index`、`modulate`、`visible` 内部就是在调这些接口）。只有在做**自定义 2D 渲染器**、或者需要绕过节点树直接提交命令时，才值得直接用 `RenderingServer`。
>
> 另外注意 `canvas_item_add_triangle_array()` 这个入口：它对应的是内部命令类型 `TYPE_RECT` 的三角形变体，脚本侧的 `CanvasItem` 并没有公开对应的 `draw_triangle_array()` 方法——想画三角形要么用 `draw_polygon()`，要么用 `draw_primitive()`。

---

## 二、CanvasItem 的绘制命令

### 2.1 `_draw()` 与 `queue_redraw()`

`CanvasItem` 的自定义绘制发生在 `_draw()` 虚函数里。生命周期是：

1. 你调用 `queue_redraw()`，把该 CanvasItem 标记为"需要重绘"；
2. 空闲期（idle time）引擎检查这个标记；
3. 如果该 CanvasItem **可见**，引擎发出 `CanvasItem.NOTIFICATION_DRAW` 通知并调用 `_draw()`；
4. `_draw()` 里调用的 `draw_*` 系列把命令追加到该 CanvasItem 的命令链表。

关键点：

- `_draw()` **每帧最多被调用一次**（无论你调多少次 `queue_redraw()`）；
- 不可见时不会调用 `_draw()`；
- `_draw()` 里**不要**做与绘制无关的事（不要在里面改节点状态、不要在里面 `add_child`），因为它处在渲染状态同步的中途。

```gdscript
extends Node2D

var _radius := 20.0
var _progress := 0.0

func _process(delta: float) -> void:
    _progress += delta
    if _progress >= 1.0:
        _progress = 0.0
        queue_redraw()      # 请求重绘

func _draw() -> void:
    # 每次 _draw() 都会把上一帧的命令清掉，重新追加
    draw_circle(Vector2.ZERO, _radius, Color(0.2, 0.8, 0.4))
    draw_arc(Vector2.ZERO, _radius + 6.0, 0.0, TAU * _progress, 32, Color(1, 1, 1), 3.0)
```

> 若只是改一个**已有**命令的参数（比如材质颜色、贴图），不需要 `queue_redraw()`——直接改属性即可。只有**命令列表本身**变了（数量、几何、类型）才需要重绘。
>
> 用 `draw_set_transform()` 之后的命令也会随 `_draw()` 一起被清空。

### 2.2 绘制命令全表

`CanvasItem` 的绘制方法分三组。

#### 2.2.1 几何图形

| 方法 | 说明 |
|---|---|
| `draw_rect(rect, color, filled, width, antialiased)` | 矩形；`filled` 为 `false` 时画边框 |
| `draw_circle(position, radius, color, filled, width, antialiased)` | 圆；填充时忽略 `width` |
| `draw_arc(center, radius, start_angle, end_angle, point_count, color, width, antialiased)` | 圆弧 |
| `draw_line(from, to, color, width, antialiased)` | 直线；`width` 为负时是两点矩形 |
| `draw_dashed_line(from, to, color, width, dash, aligned, antialiased)` | 虚线 |
| `draw_polyline(points, color, width, antialiased)` | 折线（不闭合） |
| `draw_polyline_colors(points, colors, width, antialiased)` | 逐点着色的折线 |
| `draw_multiline(points, color, width, antialiased)` | 多段不相连的线 |
| `draw_multiline_colors(points, colors, width, antialiased)` | 逐段着色的多段线 |

#### 2.2.2 多边形与图元

| 方法 | 说明 |
|---|---|
| `draw_polygon(points, colors, uvs, texture)` | 实心多边形，每个点可单独着色 |
| `draw_colored_polygon(points, color, uvs, texture)` | 实心多边形，整体单色 |
| `draw_primitive(points, colors, uvs, texture)` | 自定义图元：1 点=点，2 点=线，3 点=三角形，4 点=四边形；0 点或多于 4 点不绘制 |

#### 2.2.3 纹理、网格与文本

| 方法 | 说明 |
|---|---|
| `draw_texture(texture, position, modulate, transpose)` | 贴图 |
| `draw_texture_rect(texture, rect, tile, modulate, transpose)` | 贴图矩形（`tile` 为真则平铺） |
| `draw_texture_rect_region(texture, rect, src_rect, modulate, transpose)` | 贴图的指定区域 |
| `draw_mesh(mesh, texture)` | 在 2D 里画 `Mesh` |
| `draw_multimesh(multimesh, texture)` | 在 2D 里画 `MultiMesh` |
| `draw_string(font, pos, text, alignment, width, font_size, modulate)` | 画文本（`pos` 是基线左下角） |
| `draw_string_outline(...)` | 带描边的文本 |
| `draw_multiline_string(font, pos, text, alignment, width, font_size, max_lines, modulate)` | 多行文本 |
| `draw_multiline_string_outline(...)` | 多行文本（带描边） |
| `draw_char(font, pos, char, font_size, modulate)` | 单个字符 |
| `draw_char_outline(...)` | 单个字符（带描边） |
| `draw_style_box(style_box, rect)` | 画一个 `StyleBox` |
| `draw_lcd_texture_rect_region(...)` | 字体图集的 LCD 子像素抗锯齿区域 |
| `draw_msdf_texture_rect_region(...)` | MSDF 字体图集区域 |

#### 2.2.4 状态控制

| 方法 | 说明 |
|---|---|
| `draw_set_transform(position, rotation, scale)` | 设置后续命令的变换 |
| `draw_set_transform_matrix(transform)` | 用 `Transform2D` 设置后续命令的变换 |
| `draw_animation_slice(animation_length, slice_begin, slice_end, offset)` | 之后的命令只在动画切片内可见 |
| `draw_end_animation()` | 结束动画切片，恢复全部可见 |

> `draw_set_transform()` **只影响其后追加的命令**，且这个变换会随命令一起被缓存——它是命令链表里的一条 `TYPE_TRANSFORM` 命令，不是全局状态。

### 2.3 一个完整的绘制例子

```gdscript
extends Node2D

func _draw() -> void:
    # 1) 先设变换，后面所有命令都在这个局部坐标系里
    draw_set_transform(Vector2(100, 100), deg_to_rad(15.0), Vector2(1.0, 1.0))

    # 2) 几何
    draw_rect(Rect2(-40, -40, 80, 80), Color(0.2, 0.4, 0.8), true)
    draw_rect(Rect2(-40, -40, 80, 80), Color(1, 1, 1), false, 2.0)

    # 3) 多边形（逐点着色）
    var pts := PackedVector2Array([Vector2(0, -60), Vector2(50, 0), Vector2(0, 60), Vector2(-50, 0)])
    var cols := PackedColorArray([Color.RED, Color.GREEN, Color.BLUE, Color.YELLOW])
    draw_polygon(pts, cols)

    # 4) 变换不影响之前追加的命令
    draw_set_transform(Vector2.ZERO, 0.0, Vector2.ONE)
    draw_circle(Vector2(120, 0), 16.0, Color(1, 0.5, 0))
```

---

## 三、材质与混合模式

### 3.1 CanvasItemMaterial 的真实成员

`CanvasItemMaterial` 在 4.3 的成员**只有三组**：

| 属性 | 类型 | 说明 |
|---|---|---|
| `blend_mode` | `int`（枚举 `CanvasItemMaterial.BlendMode`） | 混合方式 |
| `light_mode` | `int`（枚举 `CanvasItemMaterial.LightMode`） | 与 2D 光照的关系 |
| `particles_animation` | `bool` | 开启 2D 粒子的雪碧图动画 |
| `particles_anim_h_frames` | `int` | 雪碧图列数 |
| `particles_anim_v_frames` | `int` | 雪碧图行数 |
| `particles_anim_loop` | `bool` | 动画是否循环 |

> ⚠️ **`CanvasItemMaterial` 没有 `normal_map`。** 4.3 的 `canvas_item_material.h` 里检索 "normal_map" 命中数为 **0**。写 `material.normal_map = load(...)` 会报 `Invalid set index 'normal_map'`。2D 法线贴图请走 6.3 节的两条正路。

**`blend_mode` 的 5 个取值**：

| 常量 | 值 | 说明 |
|---|---|---|
| `CanvasItemMaterial.BLEND_MODE_MIX` | 0 | 正常混合，颜色与 alpha 独立 |
| `CanvasItemMaterial.BLEND_MODE_ADD` | 1 | 加法混合 |
| `CanvasItemMaterial.BLEND_MODE_SUB` | 2 | 减法混合 |
| `CanvasItemMaterial.BLEND_MODE_MUL` | 3 | 乘法混合 |
| `CanvasItemMaterial.BLEND_MODE_PREMULT_ALPHA` | 4 | 预乘 alpha 混合 |

**`light_mode` 的 3 个取值**：

| 常量 | 值 | 说明 |
|---|---|---|
| `CanvasItemMaterial.LIGHT_MODE_NORMAL` | 0 | 正常参与 2D 光照 |
| `CanvasItemMaterial.LIGHT_MODE_UNSHADED` | 1 | 完全不受光照影响 |
| `CanvasItemMaterial.LIGHT_MODE_LIGHT_ONLY` | 2 | 只在光照 pass 绘制 |

```gdscript
var mat := CanvasItemMaterial.new()
mat.blend_mode = CanvasItemMaterial.BLEND_MODE_ADD
mat.light_mode = CanvasItemMaterial.LIGHT_MODE_UNSHADED
$Sprite2D.material = mat
```

### 3.2 CanvasTexture

想在 2D 里用高光 / 法线而不写着色器，可以用 `CanvasTexture`——它是 `Texture2D` 的子类，可以把漫反射、法线、高光三张图打包成一张"复合贴图"：

| 属性 | 说明 |
|---|---|
| `CanvasTexture.diffuse_texture` | 漫反射贴图 |
| `CanvasTexture.normal_texture` | 法线贴图 |
| `CanvasTexture.specular_texture` | 高光贴图 |
| `CanvasTexture.specular_color` | 高光颜色 |
| `CanvasTexture.specular_shininess` | 高光锐度 |

```gdscript
var ct := CanvasTexture.new()
ct.diffuse_texture = load("res://albedo.png")
ct.normal_texture = load("res://normal.png")
$Sprite2D.texture = ct
```

### 3.3 ShaderMaterial 与 render_mode

用 `ShaderMaterial` 可以在 2D 里做任意效果。材质面板上 `CanvasItemMaterial` 提供的那些选项，本质上就是给 canvas_item 着色器拼 `render_mode` 行：

| 材质面板选项 | 对应的 `render_mode` |
|---|---|
| Blend Mode = Add | `blend_add` |
| Blend Mode = Sub | `blend_sub` |
| Blend Mode = Mul | `blend_mul` |
| Blend Mode = Premul Alpha | `blend_premul_alpha` |
| Light Mode = Unshaded | `unshaded` |
| Light Mode = Light Only | `light_only` |
| Disable Vertex Transform | `skip_vertex_transform` |

```glsl
shader_type canvas_item;
render_mode blend_add, unshaded;

uniform float intensity : hint_range(0.0, 4.0) = 1.0;

void fragment() {
    COLOR = texture(TEXTURE, UV) * intensity;
}
```

```gdscript
var mat := ShaderMaterial.new()
mat.shader = preload("res://shaders/glow_add.gdshader")
mat.set_shader_parameter("intensity", 2.0)
$Sprite2D.material = mat
```

### 3.4 混合模式对照

| 混合 | `blend_mode` | `render_mode` | 典型用途 |
|---|---|---|---|
| 正常 | `BLEND_MODE_MIX` | `blend_mix` | 默认 |
| 相加 | `BLEND_MODE_ADD` | `blend_add` | 火焰、辉光、光束 |
| 相减 | `BLEND_MODE_SUB` | `blend_sub` | 暗角、负片 |
| 相乘 | `BLEND_MODE_MUL` | `blend_mul` | 阴影贴花、染色 |
| 预乘 alpha | `BLEND_MODE_PREMULT_ALPHA` | `blend_premul_alpha` | 自己管理 alpha 的特效 |

> 混合同样可以逐 CanvasItem 覆盖：`CanvasItem.material` 是**实例**材质，`CanvasItem.use_parent_material` 为 `true` 时则继承父节点的材质（少一次材质切换）。`CanvasItem.material_override` 属于 3D 的 `GeometryInstance3D`，2D 侧没有这个属性。

---

## 四、可见性、裁剪与分层

### 4.1 可见性与可见层

| 属性 | 说明 |
|---|---|
| `CanvasItem.visible` | 本节点是否可见 |
| `CanvasItem.is_visible_in_tree()` | 自身 + 全部祖先都可见时才为 `true` |
| `CanvasItem.visibility_layer` | 可见层（位掩码，20 位） |
| `CanvasItem.get_visibility_layer_bit(bit)` | 读单个位 |
| `CanvasItem.set_visibility_layer_bit(bit, enabled)` | 写单个位 |
| `CanvasItem.light_mask` | 参与哪些 2D 灯光的位掩码 |

> `visible = false` 的节点**不会**触发 `_draw()`，它的命令也不会被提交。所以用 `visible` 切换比"画了但设为透明"便宜得多。

`visibility_layer` 与 `Viewport.canvas_cull_mask` 配合：视口的 `canvas_cull_mask` 决定这个视口"看"哪些层。典型用法是同一场景里放两个 `Camera2D` + 两个 `SubViewport`，一个渲染 UI 层，一个渲染游戏层。

### 4.2 clip_children：四种取值

`CanvasItem.clip_children` 决定**子节点是否被本节点的绘制范围裁剪**：

| 常量 | 值 | 行为 |
|---|---|---|
| `CanvasItem.CLIP_CHILDREN_DISABLED` | 0 | 不裁剪（默认） |
| `CanvasItem.CLIP_CHILDREN_ONLY` | 1 | 只裁剪子节点，**本节点自己照常绘制** |
| `CanvasItem.CLIP_CHILDREN_AND_DRAW` | 2 | 子节点被裁剪，**本节点自己也只画在裁剪区内** |
| `CanvasItem.CLIP_CHILDREN_MAX` | 3 | 枚举上界 |

> `CLIP_CHILDREN_ONLY` 与 `CLIP_CHILDREN_AND_DRAW` 的区别是**本节点自己**是否也被裁掉。做"血条裁剪"（本体的血条要溢出）用 `ONLY`；做"圆形头像裁剪"（本体和子节点都裁）用 `AND_DRAW`。

裁剪矩形来自节点自身绘制内容的包围盒（`get_rect()`），不是它的 `size`——`Node2D` 没有 `size` 属性。

### 4.3 CanvasLayer 与 z_index

`CanvasLayer` 是独立于 2D 世界坐标的"画布层"，用来做 UI、背景层等：

| 属性 | 说明 |
|---|---|
| `CanvasLayer.layer` | 层号，数值越大越靠前 |
| `CanvasLayer.offset` / `rotation` / `scale` / `transform` | 层的变换 |
| `CanvasLayer.visible` | 整层可见性 |
| `CanvasLayer.follow_viewport_enabled` | 跟随视口变换（用于视差） |
| `CanvasLayer.follow_viewport_scale` | 跟随的缩放比例 |
| `CanvasLayer.custom_viewport` | 指定渲染到哪个视口 |
| `CanvasLayer.get_canvas()` | 取得该层的画布 RID |
| `CanvasLayer.get_final_transform()` | 该层的最终变换 |

`CanvasItem.z_index` 决定同一层内的前后顺序；`z_as_relative` 为 `true` 时相对父节点。

### 4.4 屏幕外剔除

`VisibleOnScreenNotifier2D` 会在节点进出屏幕时发出信号：

| API | 说明 |
|---|---|
| `VisibleOnScreenNotifier2D.rect` | 判定用的矩形（本地坐标） |
| `VisibleOnScreenNotifier2D.is_on_screen()` | 当前是否在屏幕内 |
| 信号 `screen_entered` | 进入屏幕 |
| 信号 `screen_exited` | 离开屏幕 |

```gdscript
func _on_screen_exited() -> void:
    $Enemy.visible = false
    $Enemy.set_process(false)
```

> 注意：`VisibleOnScreenNotifier2D` **只是通知**，它本身不会阻止渲染。要真正省掉绘制开销，仍要自己把内容 `visible = false`、或者减少节点数量。

### 4.5 CanvasGroup：把子树压成一张贴图

`CanvasGroup` 是 2D 里少数几个"真的能减少提交量"的节点——它把整棵子树先渲染到一张离屏贴图上，再当作**一个** CanvasItem 提交。

| 属性 | 说明 |
|---|---|
| `CanvasGroup.use_mipmaps` | 为生成的贴图生成 mipmap（缩小时更平滑） |
| `CanvasGroup.fit_margin` | 画布组的边距（像素），给子节点超出部分留出空间；默认 10 |
| `CanvasGroup.clear_margin` | 画布组的边距（像素），上一帧多清理出去一圈，避免拖影 |

典型用法是"整组一起动"的面板：一堆子节点各自带渐变、描边、遮罩，父节点上挂 `CanvasGroup`，然后只移动这个父节点。

```gdscript
var group := CanvasGroup.new()
group.use_mipmaps = true
group.fit_margin = 8.0
add_child(group)

for i in 20:
    var s := Sprite2D.new()
    s.texture = load("res://dot.png")
    s.position = Vector2(i * 12, 0)
    group.add_child(s)
```

> 代价是**多一次离屏渲染 + 一次贴图采样**。如果子树本身就是 1~3 个简单精灵，用 `CanvasGroup` 反而更慢。它的收益要在"子树复杂 + 整体频繁移动/缩放"时才明显。

---

## 五、多分辨率与 canvas_transform

### 5.1 两条变换

2D 里有两条不同的变换，混用是 2D 坐标问题的主要来源：

| API | 含义 |
|---|---|
| `CanvasItem.get_global_transform()` | 从本节点局部坐标 → **画布**坐标（不含视口变换） |
| `CanvasItem.get_global_transform_with_canvas()` | 从本节点局部坐标 → **视口**坐标 |
| `CanvasItem.get_canvas_transform()` | 从画布坐标 → 视口坐标 |
| `CanvasItem.get_viewport_transform()` | 从画布坐标 → 视口**嵌入区域**坐标 |
| `CanvasItem.get_screen_transform()` | 本节点在**屏幕**坐标下的变换（编辑器插件用） |
| `Viewport.canvas_transform` | 视口对**整个画布**的变换（世界 → 视口） |
| `Viewport.global_canvas_transform` | 全局画布变换（世界 → 视口，含额外视差层） |

> 一句话记忆：**`global_transform` 是"我在画布哪儿"，`global_transform_with_canvas` 是"我在屏幕哪儿"。** 点击检测用前者，摆 UI 用后者。

### 5.2 Camera2D

`Camera2D` 通过 `canvas_transform` 间接影响整张画布：

| 属性 | 说明 |
|---|---|
| `Camera2D.zoom` | 缩放（`Vector2`，**大于 1 是放大**） |
| `Camera2D.position_smoothing_enabled` | 平滑跟随 |
| `Camera2D.position_smoothing_speed` | 平滑速度 |
| `Camera2D.limit_left` / `limit_top` / `limit_right` / `limit_bottom` | 边界限制 |
| `Camera2D.ignore_rotation` | 忽略父节点旋转 |
| `Camera2D.anchor_mode` | 锚定模式（拖拽居中 / 固定左上） |
| `Camera2D.make_current()` | 设为当前相机 |
| `Camera2D.force_update_scroll()` | 立刻应用滚动位置（不等平滑） |

```gdscript
var cam := Camera2D.new()
cam.zoom = Vector2(2.0, 2.0)
cam.position_smoothing_enabled = true
cam.position_smoothing_speed = 8.0
add_child(cam)
cam.make_current()
```

### 5.3 SubViewport 与 2D 缩放

`SubViewport` 用来做分屏、小地图、UI 叠加：

| 属性 | 说明 |
|---|---|
| `SubViewport.size` | 视口尺寸 |
| `SubViewport.size_2d_override` | **2D 缩放**：在 2D 层面放大/缩小内容，3D 不受影响 |
| `SubViewport.size_2d_override_stretch` | 缩放模式（是否拉伸） |
| `SubViewport.render_target_update_mode` | 更新策略 |
| `SubViewport.render_target_clear_mode` | 清理策略 |

`render_target_update_mode` 的取值：

| 常量 | 说明 |
|---|---|
| `SubViewport.UPDATE_DISABLED` | 完全不更新 |
| `SubViewport.UPDATE_ONCE` | 只更新一次 |
| `SubViewport.UPDATE_WHEN_VISIBLE` | 可见时更新 |
| `SubViewport.UPDATE_WHEN_PARENT_VISIBLE` | 父级可见时更新 |
| `SubViewport.UPDATE_ALWAYS` | 每帧更新 |

> `size_2d_override` 是 **SubViewport 独有**的属性。普通的 `Viewport`（含根视口）**没有** `size_2d_override`，在它上面写这个属性会报 `Invalid set index 'size_2d_override'`。

### 5.4 视口级的 2D 开关

| 属性 | 说明 |
|---|---|
| `Viewport.canvas_cull_mask` | 该视口渲染哪些可见层 |
| `Viewport.snap_2d_transforms_to_pixel` | 变换吸附到整像素（避免抖动） |
| `Viewport.use_hdr_2d` | 2D 走 HDR 管线 |
| `Viewport.msaa_2d` | 2D 的 MSAA 采样数 |
| `Viewport.canvas_item_default_texture_filter` | 默认纹理过滤 |
| `Viewport.canvas_item_default_texture_repeat` | 默认寻址模式 |
| `Viewport.sdf_oversize` / `Viewport.sdf_scale` | SDF 字体渲染的过采样与缩放 |

### 5.5 视差

4.3 推荐用 `Parallax2D` 节点（取代老的 `ParallaxBackground`）：

| 属性 | 说明 |
|---|---|
| `Parallax2D.scroll_scale` | 滚动比例（`0` = 完全跟随相机） |
| `Parallax2D.repeat_size` | 重复尺寸 |
| `Parallax2D.repeat_times` | 重复次数 |
| `Parallax2D.autoscroll` | 自动滚动 |
| `Parallax2D.follow_viewport` | 是否跟随视口 |
| `Parallax2D.screen_offset` | 屏幕偏移 |

---

## 六、2D 光照

### 6.1 2D 光源

2D 光照是**逐像素**的：光源在 2D 平面上有一个位置和半径（或一个方向），配合遮挡体产生阴影。

`Light2D` 的全部成员：

| 属性 | 说明 |
|---|---|
| `Light2D.energy` | 强度 |
| `Light2D.color` | 颜色 |
| `Light2D.enabled` | 是否启用 |
| `Light2D.blend_mode` | 混合模式（`BLEND_MODE_ADD` / `SUB` / `MIX`） |
| `Light2D.shadow_enabled` | 是否投射阴影 |
| `Light2D.shadow_color` | 阴影颜色 |
| `Light2D.shadow_filter` | 阴影过滤（`SHADOW_FILTER_NONE` / `PCF5` / `PCF13`） |
| `Light2D.shadow_filter_smooth` | 阴影边缘平滑度 |
| `Light2D.range_layer_min` / `range_layer_max` | 影响的可见层范围 |
| `Light2D.range_item_cull_mask` | 影响的 `light_mask` 范围 |
| `Light2D.shadow_item_cull_mask` | 阴影影响的 `light_mask` 范围 |
| `Light2D.range_z_min` / `range_z_max` | 影响的 Z 范围 |
| `Light2D.editor_only` | 仅编辑器可见 |

两个具体光源：

| 节点 | 特有属性 |
|---|---|
| `PointLight2D` | `texture`、`texture_scale`、`offset`、`height` |
| `DirectionalLight2D` | `max_distance`、`height` |

```gdscript
# 2D 光源
var light = PointLight2D.new()
light.color = Color.YELLOW
light.energy = 2.0
light.shadow_enabled = true

# 2D 阴影
var shadow = LightOccluder2D.new()
shadow.occluder = occluder_resource
```

> 4.3 的 `Light2D` **没有** `range_min` / `range_max`（那是 Godot 3.x 的属性），也没有 `texture_scale`——`texture_scale` 在 `PointLight2D` 上。4.x 用 `range_layer_min` / `range_layer_max` / `range_z_min` / `range_z_max` 控制影响范围。

### 6.2 2D 阴影与遮挡体

```gdscript
# 遮挡体多边形（资源）
var poly := OccluderPolygon2D.new()
poly.polygon = PackedVector2Array([Vector2(0, 0), Vector2(32, 0), Vector2(32, 32), Vector2(0, 32)])
poly.closed = true

# 挂到场景里
var occluder := LightOccluder2D.new()
occluder.occluder = poly
add_child(occluder)
```

| 属性 | 说明 |
|---|---|
| `OccluderPolygon2D.polygon` | 多边形顶点 |
| `OccluderPolygon2D.closed` | 是否闭合 |
| `OccluderPolygon2D.cull_mode` | 剔除方向（`CULL_DISABLED` / `CULL_CLOCKWISE` / `CULL_COUNTER_CLOCKWISE`） |
| `LightOccluder2D.occluder` | 绑定的 `OccluderPolygon2D` |
| `LightOccluder2D.occluder_light_mask` | 哪些光源的阴影会被它挡住 |
| `LightOccluder2D.sdf_collision` | 用物理碰撞生成遮挡形状（4.x 新增） |

### 6.3 2D 法线贴图

`CanvasItemMaterial` 在 4.3 只有 `blend_mode` / `light_mode` / `particles_anim_*` 三组属性，**没有** `normal_map`（写 `material.normal_map = ...` 会报 `Invalid set index 'normal_map'`）。2D 法线贴图有两条正路：

**方案 A：内置的 `CanvasTexture`（不写着色器）**

```gdscript
var ct := CanvasTexture.new()
ct.diffuse_texture = load("res://albedo.png")
ct.normal_texture = load("res://normal.png")   # CanvasTexture 有 normal_texture 成员
$sprite.texture = ct
```

**方案 B：自定义 `canvas_item` 着色器**

```glsl
// res://shaders/2d_normal.gdshader
shader_type canvas_item;

uniform sampler2D normal_texture : hint_normal;

void fragment() {
    vec4 n = texture(normal_texture, UV);
    NORMAL = n.rgb;              // 2D 着色器的法线输出（inout）
    COLOR = texture(TEXTURE, UV);
}
```

```gdscript
var mat := ShaderMaterial.new()
mat.shader = preload("res://shaders/2d_normal.gdshader")
mat.set_shader_parameter("normal_texture", load("res://normal.png"))
$sprite.material = mat
```

> 两种方案都需要场景里有 2D 光源（`PointLight2D` / `DirectionalLight2D`）才会生效；`CanvasItemMaterial.light_mode = CanvasItemMaterial.LIGHT_MODE_UNSHADED` 会让该 CanvasItem 完全不参与 2D 光照。

---

## 七、2D 批量提交：Godot 4 没有 2D 合批器

### 7.1 没有自动合批器

Godot 3.x 的 2D batcher 在 Godot 4 中**已被移除**：`servers/rendering/renderer_canvas_cull.cpp`（93 KB）与 `servers/rendering/renderer_canvas_render_rd.cpp`（113 KB）中 "batch" 的命中数都是 **0**。Godot 4 的 2D 渲染器是"一个 CanvasItem 一批绘制命令"，不会在运行时把相同纹理的 Sprite2D 合并成一次 Draw Call。

```
多个 Sprite2D
    ↓
各自提交自己的绘制命令
    ↓
GPU 逐个绘制
```

> 也就是说，"相同纹理自动合批"是 Godot 3.x 的行为，在 Godot 4 里不成立。真正能减少 2D Draw Call 的做法见下表。

这个结论不是"读文档读来的"，而是可以直接量出来的：

| 观察点 | 4.3 的事实 |
|---|---|
| `renderer_canvas_cull.cpp` 中 "batch" 命中 | 0 |
| `renderer_canvas_render_rd.cpp` 中 "batch" 命中 | 0 |
| `renderer_canvas_render.h` 中 "batch" 命中 | 0 |
| 同一纹理的不同 `Sprite2D` | 各自一条 `TYPE_RECT` 命令，互不合并 |
| `RenderingServer` 2D 侧 API | 只有 `canvas_item_add_*` / `canvas_item_set_*`，没有"合并请求"入口 |

2D 的"优化"因此不是调一个开关，而是**改结构**：让同类内容用**更少的 CanvasItem** 表达。

### 7.2 减少 2D Draw Call 的手段

| 技巧 | 效果 | 说明 |
|------|------|------|
| **MultiMeshInstance2D** | N 个精灵 → 1 次实例化绘制 | 静态或规则排列的大量同类精灵首选 |
| **共享纹理与材质** | 减少状态切换 | 多个 CanvasItem 引用同一个 `CanvasItemMaterial` 资源 |
| **TileMapLayer** | 图块按图集批量提交 | 每个 TileMapLayer 维护自己的图集批次 |
| **合并到父节点** | 减少 CanvasItem 数量 | 用 `Node2D` 承载静态装饰，或用 `MultiMesh` |
| **VisibleOnScreenNotifier2D** | 屏幕外不绘制 | 配合 `visibility_range` 思路做 2D 版本 |
| **一张大图集** | 减少纹理绑定 | 手动打图集比指望引擎合批更现实 |
| **`CanvasGroup`** | 把子树渲染成一张贴图 | 适合"整组一起动"的 UI 面板 |

`MultiMeshInstance2D` 的用法：

```gdscript
var mm := MultiMesh.new()
mm.transform_format = MultiMesh.TRANSFORM_2D
mm.use_colors = true
mm.instance_count = 1000

for i in mm.instance_count:
    mm.set_instance_transform_2d(i, Transform2D(0.0, Vector2(i * 8, 0)))
    mm.set_instance_color(i, Color(1, 1, 1, 1))

var mmi := MultiMeshInstance2D.new()
mmi.multimesh = mm
mmi.texture = load("res://bullet.png")
add_child(mmi)
```

| `MultiMesh` 成员 | 说明 |
|---|---|
| `MultiMesh.instance_count` | 实例数 |
| `MultiMesh.transform_format` | `TRANSFORM_2D` 或 `TRANSFORM_3D` |
| `MultiMesh.transform_2d_array` | 批量读写变换 |
| `MultiMesh.set_instance_transform_2d()` | 写单个实例变换 |
| `MultiMesh.get_instance_transform_2d()` | 读单个实例变换 |
| `MultiMesh.use_colors` | 是否使用实例颜色 |
| `MultiMesh.visible_instance_count` | 实际绘制的实例数（小于 `instance_count` 时省开销） |
| `MultiMesh.mesh` | 3D 版的网格 |

> `MultiMeshInstance2D.texture` 是它**自带**的贴图（2D 的 MultiMesh 不走 `MultiMesh.mesh`）。这和 3D 的 `MultiMeshInstance3D` 不一样。

`TileMapLayer` 的分块提交参数：

| 属性 | 说明 |
|---|---|
| `TileMapLayer.tile_set` | 图块集 |
| `TileMapLayer.enabled` | 是否参与渲染 |
| `TileMapLayer.rendering_quadrant_size` | 按象限分块渲染的粒度（默认 16） |
| `TileMapLayer.set_cell()` | 写格子 |
| `TileMapLayer.get_used_cells()` | 列出用到的格子 |
| `TileMapLayer.get_used_rect()` | 用到的矩形范围 |

### 7.3 怎么自己验证「Godot 4 没有 2D 合批器」

不要只信结论。下面三步可以在自己的项目里当场复核：

**第一步：数一数同纹理的精灵带来了多少 Draw Call。**

```gdscript
# 放进场景，运行几秒后看输出
func _ready() -> void:
    await get_tree().create_timer(1.0).timeout
    print("draw calls  = ", Performance.RENDER_TOTAL_DRAW_CALLS_IN_FRAME)
    print("objects     = ", Performance.RENDER_TOTAL_OBJECTS_IN_FRAME)
```

在一个放了 200 个同贴图 `Sprite2D` 的场景里，2D 的 draw call 会随精灵数**近似线性**增长——如果引擎在做运行时合批，这条曲线应该是平的。

**第二步：直接检索引擎源码。**

| 检索对象 | 4.3 的命中数 |
|---|---|
| `servers/rendering/renderer_canvas_cull.cpp` 中 "batch" | **0** |
| `servers/rendering/renderer_canvas_render_rd.cpp` 中 "batch" | **0** |
| `servers/rendering/renderer_canvas_render.h` 中 "batch" | **0** |
| `servers/rendering/renderer_scene_render_rd.cpp` 中 "batch" | **0** |

> 最后一行同样重要：3D 侧也没有"通用合批器"。Godot 4 的 3D 走的是 MultiMesh / 实例化 + 材质共享，**不是**把不同 MeshInstance 合并成一次 Draw Call。

**第三步：看 `RenderingServer` 有没有"请求合并"的入口。**

`RenderingServer` 的 2D 侧只有 `canvas_item_add_*`（追加命令）与 `canvas_item_set_*`（设状态）两族方法，**没有任何"把这些 item 合并"的接口**。对比 3.x 时代存在的 batcher 配置项（`rendering/2d/batching` 一类的项目设置），4.3 的项目设置里也**没有**对应项。

### 7.4 2D 场景自检清单

| 检查项 | 怎么查 | 目标 |
|---|---|---|
| 场景里有多少个 CanvasItem | 编辑器大纲里数，或运行时遍历 | 越少越好 |
| 同贴图的精灵有多少 | 按 `texture` 分组统计 | 合并成 MultiMesh |
| 有没有每帧 `queue_redraw()` | 搜 `_process` 里的 `queue_redraw` | 只在真的变了时调 |
| 一个 CanvasItem 里有几条命令 | 拆成多个 `_draw()` 调用计数 | 拆成多个 CanvasItem 或改用静态内容 |
| 屏幕外的东西还在画吗 | 挂 `VisibleOnScreenNotifier2D` | 关掉 `visible` |
| 材质是不是共享的 | 看每个 Sprite 的 `material` 槽 | 指向同一个资源 |
| 滤镜开销 | `texture_filter` 是不是 `TEXTURE_FILTER_NEAREST` | 像素画关掉线性过滤 |

---

## 八、2D 优化

### 8.1 优化技巧

| 技巧 | 说明 |
|------|------|
| **纹理图集** | 合并纹理，减少绑定切换 |
| **TileMapLayer** | 图块按图集批量提交 |
| **可见性** | 关闭屏幕外渲染（`VisibleOnScreenNotifier2D`） |
| **MultiMesh** | 大量同类精灵合并成一次实例化绘制 |
| **少画命令** | 一个 CanvasItem 里画完所有内容，而不是每帧 `queue_redraw()` 重建上千条命令 |
| **关掉不需要的滤镜** | `texture_filter` 设成 `TEXTURE_FILTER_NEAREST` 能省掉线性过滤开销 |

### 8.2 性能对比

> ⚠️ 下表为示意数据（未附测试环境），仅用于建立数量级概念。
> 实际 Draw Call 数与帧率取决于场景构成与目标硬件，请在目标平台实测。

| 优化前 | 优化后 | 提升 |
|--------|--------|------|
| 100 DrawCall | 20 DrawCall | 80% |
| 60 FPS | 120 FPS | 100% |

### 8.3 怎么量自己的 2D 场景

| 指标 | 取法 |
|---|---|
| 每帧 2D Draw Call | `Performance.RENDER_TOTAL_DRAW_CALLS_IN_FRAME` |
| 每帧渲染对象数 | `Performance.RENDER_TOTAL_OBJECTS_IN_FRAME` |
| 视口内细分统计 | `Viewport.get_render_info(Viewport.RENDER_INFO_DRAW_CALLS_IN_FRAME, ...)`，配合 `Viewport.RENDER_INFO_TYPE_CANVAS` / `RENDER_INFO_TYPE_VISIBLE` / `RENDER_INFO_TYPE_SHADOW` |
| 单个视口的 2D 统计 | `Viewport.get_render_info()` 的 `RENDER_INFO_*` 系列 |

```gdscript
func _report_2d() -> void:
    var draw_calls := Performance.RENDER_TOTAL_DRAW_CALLS_IN_FRAME
    var objects := Performance.RENDER_TOTAL_OBJECTS_IN_FRAME
    print("2D/3D 总计 draw calls = ", draw_calls, "，对象数 = ", objects)
```

---

## 核心要点

1. **2D 渲染分两段**：剔除与排序模块（`renderer_canvas_cull.cpp`）负责裁剪与 z 排序，命令提交模块（`renderer_canvas_render_rd.cpp`）负责把命令交给 GPU；两者的边界就是 `canvas_render_items()`。
2. **`_draw()` 每帧最多调一次**，必须先 `queue_redraw()`；不可见时根本不调用，所以用 `visible` 切换比画透明更省。
3. **绘制命令是缓存下来的链表**，按 4 KB 一块分配；频繁重绘会不断追加命令，命令一多就是明显的性能坑。
4. **`CanvasItemMaterial` 在 4.3 只有** `blend_mode` / `light_mode` / `particles_animation` / `particles_anim_h_frames` / `particles_anim_v_frames` / `particles_anim_loop`，**没有 `normal_map`**。
5. **2D 法线贴图走 `CanvasTexture` 或自定义 canvas_item 着色器**，两条路都成立。
6. **`clip_children` 有三种行为**（`DISABLED` / `ONLY` / `AND_DRAW`），`ONLY` 与 `AND_DRAW` 的差别是本节点自己是否也被裁。
7. **坐标换算要分清**：`get_global_transform()` 到画布，`get_global_transform_with_canvas()` 到视口，`Viewport.canvas_transform` 是世界 → 视口的那一层。
8. **Godot 4 没有 2D 合批器**——"batch" 在三个 2D 渲染源文件里命中数都是 0；减少 Draw Call 只能靠 MultiMesh、图集、合并节点、减少 CanvasItem 数量。

---

## 🔗 延伸阅读

- **官方文档**: [2D 精灵动画](https://docs.godotengine.org/en/stable/tutorials/2d/2d_sprite_animation.html)、[使用 TileMap](https://docs.godotengine.org/en/stable/tutorials/2d/using_tilemaps.html)、[CanvasItem 教程](https://docs.godotengine.org/en/stable/tutorials/2d/canvas_item.html)
- **类参考**: [CanvasItem](https://docs.godotengine.org/en/stable/classes/class_canvasitem.html)、[CanvasItemMaterial](https://docs.godotengine.org/en/stable/classes/class_canvasitemmaterial.html)、[CanvasTexture](https://docs.godotengine.org/en/stable/classes/class_canvastexture.html)、[MultiMeshInstance2D](https://docs.godotengine.org/en/stable/classes/class_multimeshinstance2d.html)、[Light2D](https://docs.godotengine.org/en/stable/classes/class_light2d.html)
- **源码位置**: `servers/rendering/renderer_canvas_cull.cpp`、`servers/rendering/renderer_canvas_cull.h`、`servers/rendering/renderer_canvas_render.h`、`servers/rendering/renderer_rd/renderer_canvas_render_rd.cpp`、`scene/main/canvas_item.cpp`、`scene/resources/canvas_item_material.cpp`

---

## 📋 下一章预告

**第 19 篇：后处理效果**

- 后处理管线与 WorldEnvironment
- 色调映射、泛光、SSAO、SSR、景深
- 色彩校正与 LUT
- **自定义后处理：Compositor / CompositorEffect**——5 个回调点、4.3 的限制，以及为什么 `canvas_item` 贴图**不是**后处理

---

**作者**: wangshucheng
**首发平台**: 微信公众号
**写作时间**: 2026 年 3 月
**Godot 版本**: 4.x（基线 4.3；本文涉及的 4.4+ 差异已在行内标注）

---

**上一篇**: [第 17 篇：GDShader 语言](/articles/17-gdshader-language.md)
**下一篇**: [第 19 篇：后处理效果](/articles/19-post-processing-effects.md)

---

*如果你觉得这篇文章有帮助，欢迎转发给更多开发者！*
