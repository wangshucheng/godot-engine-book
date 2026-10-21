# 第 14 篇：场景渲染流程

> **本章导读**：本章把"场景渲染流程"从概念图换成源码级事实。
> 读完后你能：（1）在编辑器 Visual Profiler 里对号入座每一个时间条；（2）说清深度预通道、阴影、GI、SDFGI、体积雾、透明各自落在哪个 pass；（3）遇到排序 / 深度 / 覆盖类问题时，知道该翻源码的哪个函数；（4）分清 Godot 4 有与没有的能力边界。
> **前置知识**：第 11 篇《Godot 渲染架构总览》第 8 章「渲染线程模型与帧管线」。
> **难度**：进阶。

> **摘要**：场景渲染是 Godot 渲染系统的核心。本文将深入分析场景渲染流程、剔除、排序、合批。

---

## 一、场景渲染流程

### 1.1 渲染流程概述

```
1. 场景更新
   ↓
2. 可见性剔除
   ↓
3. 渲染排序（按材质键 / 深度 / 优先级）
   ↓
4. 生成渲染列表（不透明 / 透明 / 阴影）
   ↓
5. 生成渲染指令
   ↓
6. 提交 GPU
   ↓
7. 显示
```

> 📌 上面的流程图是**概念示意**（只说明"哪些步骤先做、哪些步骤可以并行"）。**Godot 4.7.2 的真实 pass 顺序**（准备场景 → SDFGI → 深度预通道 → 阴影 / GI → SSAO / SSIL / SSR → 体积雾 → 不透明 → 天空 → 透明 → 后处理链 → 色调映射 → 抗锯齿 → 输出，每一步都标注了源码函数与 Visual Profiler 里的时间条）见 **第五章「深度预通道、OIT 与真实 Pass 顺序」**。

> Godot 4.x **没有** Godot 3.x 那种"自动合批器"：渲染列表里每个可见表面各自提交一次绘制，Draw Call 的削减靠"共享材质 + MultiMesh 实例化 + 可见性范围"在**场景组织**层面完成，而不是渲染器在运行时帮你把物体合并。

### 1.2 源码位置

**源码位置**：`servers/rendering/renderer_scene_render.h`（抽象基类）与 `servers/rendering/renderer_scene_render.cpp`；具体实现在 `servers/rendering/renderer_rd/` 下。

```cpp
// Godot 4.7.2 源码 - servers/rendering/renderer_scene_render.h:41
class RendererSceneRender {
private:
	RendererEnvironmentStorage environment_storage;
	RendererCompositorStorage compositor_storage;

public:
	enum {
		MAX_DIRECTIONAL_LIGHTS = 8,
		MAX_DIRECTIONAL_LIGHT_CASCADES = 4,
		MAX_RENDER_VIEWS = 2
	};

	// 真正的场景渲染入口：渲染线程每帧调用一次
	virtual void render_scene(const Ref<RenderSceneBuffers> &p_render_buffers,
							  const CameraData *p_camera_data,
							  const CameraData *p_prev_camera_data,
							  const PagedArray<RenderGeometryInstance *> &p_instances,
							  const PagedArray<RID> &p_lights,
							  const PagedArray<RID> &p_reflection_probes,
							  const PagedArray<RID> &p_voxel_gi_instances,
							  const PagedArray<RID> &p_decals,
							  const PagedArray<RID> &p_lightmaps,
							  const PagedArray<RID> &p_fog_volumes,
							  RID p_environment, RID p_camera_attributes, RID p_compositor,
							  RID p_shadow_atlas, RID p_occluder_debug_tex, RID p_reflection_atlas,
							  /* ... */ ) = 0;

	virtual void update() = 0;
	virtual ~RendererSceneRender() {}
};
```

> ⚠️ 4.3 里**不存在** `class RendererSceneRender : public Singleton`，也不存在 `_render_scene` / `_cull_objects` / `_sort_objects` / `_batch_objects` 这四个虚函数——它们在 `renderer_scene_render.h/.cpp` 中命中数为 0。剔除、排序、渲染列表的组装都由 `RendererSceneRenderRD` 及其子类（`RenderForwardClustered` / `RenderForwardMobile`）在 `renderer_rd/` 目录中实现。

### 1.3 一帧被切成三段：谁在哪个线程上做什么

第 11 篇第 8 章已经给过完整的线程模型，这里只把它压缩成一条**可操作的路径**——排错时顺着这条链往下走，就能知道问题出在"没进渲染列表"还是"进了但画错了"。

| 阶段 | 源码入口 | 线程 | 产出 |
|------|----------|------|------|
| **剔除 + 排序** | `RendererSceneCull::render_camera()`（`servers/rendering/renderer_scene_cull.cpp:2549`） | 主线程 | `PagedArray<RenderGeometryInstance *>` 等扁平列表 |
| **渲染列表 + 录制** | `RendererSceneRenderRD::render_scene()`（`servers/rendering/renderer_rd/renderer_scene_render_rd.cpp:1359`） | 渲染线程 | `RenderingDevice` 命令缓冲 |
| **GPU 提交** | `RenderingDevice` → `RenderingDeviceDriver` | 渲染线程 | Vulkan / D3D12 / Metal 命令 |

场景端这一侧再细分是三个连续调用：

```cpp
// Godot 4.7.2 源码 - servers/rendering/renderer_scene_cull.cpp
// :2670  render_camera()：一帧一次的入口
// :3297  _render_scene()：把剔除结果组装成渲染器要的列表
// :3706  scene_render->render_scene(...)：交给渲染器
```

渲染器这一侧的落点是：

```cpp
// Godot 4.7.2 源码 - servers/rendering/renderer_rd/forward_clustered/render_forward_clustered.cpp:1704
void RenderForwardClustered::_render_scene(RenderDataRD *p_render_data, const Color &p_default_bg_color) {
	// 第五节表里的大部分标记在这个函数体里；
	// 阴影 / GI / SSAO / SSIL / SSR / 体积雾那一组在 _pre_opaque_render()（:1517）里
}
```

**排错时的用法**：

- 物体**完全没画出来** → 先怀疑剔除（第二章）：是不是被视锥剔了、被 `visibility_range` 剔了、被遮挡剔了。
- 物体**画出来了但位置/层级不对** → 怀疑排序（第三章）：透明物体的 `render_priority`、不透明物体的材质键。
- 物体**颜色不对 / 缺光照 / 被别的物体盖住** → 怀疑 pass 顺序（第五章）：深度预通道、阴影、天空、透明的相对次序。

### 1.4 "渲染列表"不是一个东西，是好几个

`RenderForwardClustered` 内部维护的是**多份**渲染列表，而不是一份：

| 列表 | 用途 | 排序依据 |
|------|------|----------|
| `opaque_render_list` | 不透明表面 | 材质键（`sort_key1` / `sort_key2`） |
| `transparent_render_list` | 透明表面 | 优先级 + 反向深度 |
| `shadow_render_list` | 阴影投射体 | 与不透明类似的材质键 |
| `cull_mask` 相关的分组 | 按 `light_cull_mask` / `visibility_layer` 分组 | 分组键优先 |

**它们不共享一个排序**。这是排错时最常见的误解：把透明物体的 `render_priority` 调很大，并不会让它画到不透明物体**之前**——官方文档在 `Material.render_priority` 的说明里写得很清楚：

> This will not impact how transparent objects are sorted relative to opaque objects or how dynamic meshes will be sorted relative to other opaque meshes. This is because all transparent objects are drawn after all opaque objects and all dynamic opaque meshes are drawn before other opaque meshes.

---

## 二、可见性剔除

### 2.1 剔除类型

| 类型 | 说明 |
|------|------|
| **Frustum Culling** | 视锥体剔除 |
| **Occlusion Culling** | 遮挡剔除 |
| **Distance Culling** | 距离剔除 |
| **Backface Culling** | 背面剔除 |

### 2.2 剔除流程

```
遍历场景对象
    ↓
检查是否在视锥体内
    ↓
检查是否被遮挡
    ↓
检查距离
    ↓
添加到渲染列表
```

### 2.3 剔除其实分三层，每层都能单独关

Godot 4.3 的剔除不是"一个开关"，而是**三个互相独立的层**。搞清楚是哪一层剔掉的，才能对症下药。

| 层 | 谁在管 | 关掉它的方法 | 副作用 |
|----|--------|-------------|--------|
| **视锥剔除** | 场景端 `RendererSceneCull`，用相机的 `frustum` 判包围盒 | 基本无法关（除非把 `GeometryInstance3D` 的 `visibility_range` 拉大） | 无 |
| **遮挡剔除** | 场景端，用 `OccluderInstance3D` 提供的遮挡体做深度测试 | 项目设置 `rendering/occlusion_culling/use_occlusion_culling = false` | 遮挡体不再生效，CPU 侧剔除开销下降 |
| **距离 / 可见性范围剔除** | 场景端，比较相机距离与 `visibility_range_begin/end` | 把 `visibility_range_end` 调大，或把 `visibility_range_fade_mode` 设为禁用 | 远处物体不再自动消失 |

对应的属性全在 `GeometryInstance3D` 上：

| 属性 | 类型 | 作用 |
|------|------|------|
| `GeometryInstance3D.visibility_range_begin` | float | 可见性范围的**起点**距离 |
| `GeometryInstance3D.visibility_range_end` | float | 可见性范围的**终点**距离 |
| `GeometryInstance3D.visibility_range_begin_margin` | float | 起点的过渡余量 |
| `GeometryInstance3D.visibility_range_end_margin` | float | 终点的过渡余量 |
| `GeometryInstance3D.visibility_range_fade_mode` | `VISIBILITY_RANGE_FADE_DISABLED` / `VISIBILITY_RANGE_FADE_SELF` / `VISIBILITY_RANGE_FADE_DEPENDENCIES` | 淡出是只作用于自身，还是连带子节点 |
| `GeometryInstance3D.lod_bias` | float | LOD 层级偏置，越小越早切低模 |
| `GeometryInstance3D.ignore_occlusion_culling` | bool | 这个实例**不参与**遮挡剔除 |
| `GeometryInstance3D.extra_cull_margin` | float | 额外扩大剔除包围盒，防边缘抖动 |
| `GeometryInstance3D.cast_shadow` | `SHADOW_CASTING_SETTING_OFF` / `SHADOW_CASTING_SETTING_ON` / `SHADOW_CASTING_SETTING_DOUBLE_SIDED` / `SHADOW_CASTING_SETTING_SHADOWS_ONLY` | 是否进入阴影 pass 的渲染列表 |

> 💡 `visibility_range_fade_mode` 里的 `VISIBILITY_RANGE_FADE_DEPENDENCIES` 是个容易忽略的坑：勾上之后，**依赖这个节点的子节点也会一起淡出**。做 UI 叠加层或挂载特效时经常误伤。

### 2.4 剔除与排序是两件事，别混

| | 剔除 | 排序 |
|---|------|------|
| 回答的问题 | "它这次**要不要**画？" | "它**排第几**画？" |
| 发生位置 | 主线程，场景端 | 主线程（排序键在剔除时算好）+ 渲染线程（按键分组） |
| 失败表现 | 物体**消失** | 物体**重叠 / 穿插** |
| 调参入口 | `visibility_range_*`、遮挡剔除开关 | `Material.render_priority`、材质键 |

一个物体被剔掉了，你在材质上调一百次 `render_priority` 都没用；反过来，两个透明面穿插了，把 `visibility_range` 调小只会让它们一起消失。

### 2.5 剔除是并行的，但开销算在主线程上

场景端的剔除在 4.3 里是可以并行的：`RendererSceneCull` 会用 `WorkerThreadPool` 把可见性判定拆给多个工作线程（内部函数 `_visibility_cull_threaded()`）。

但要注意两点：

1. **并行的是"判定"，不是"整帧"**。剔除结果最终要汇总成有序列表交给渲染线程，汇总这一步是串行的。
2. **CPU 侧的剔除开销会计入主线程帧时间**。主线程同时还要跑游戏逻辑，所以"主线程 16 ms 里渲染占了 8 ms"是常见现象——这 8 ms 里既有剔除，也有第 21 篇讲的物理、脚本、AI。

> 💡 实测建议：把「调试 → 显示性能」里的 **FPS** 与 **Process** / **Physics Process** 时间一起看。如果 Process 时间远大于渲染时间，去查脚本；如果两者都高，场景端剔除（对象数量太多、层级太深）是常见元凶。

---

## 三、渲染排序

### 3.1 排序规则

| 规则 | 说明 |
|------|------|
| **材质键排序** | 把使用同一材质（同一 uniform set）的表面排到一起，减少 GPU 状态切换 |
| **深度排序** | 阴影 pass 用正序、不透明 pass 用材质键优先 |
| **透明度排序** | 透明物体按"优先级 + 反向深度"排序，避免相互穿插 |
| **优先级** | `material.render_priority` 高的先绘制 |

> 排序的目的**不是**把物体合并成一个 Draw Call（Godot 4 没有这个能力），而是让**状态切换最少**——连续使用同一材质的表面可以复用已绑定的 uniform set。

### 3.2 排序实现

排序发生在 `RenderForwardClustered::RenderList` 里（`servers/rendering/renderer_rd/forward_clustered/render_forward_clustered.h`），用两个 64 位排序键打包成 `sort_key1` / `sort_key2`：

```cpp
// Godot 4.7.2 源码 - render_forward_clustered.h
struct SortByKey {
	_FORCE_INLINE_ bool operator()(const GeometryInstanceSurfaceDataCache *A,
									const GeometryInstanceSurfaceDataCache *B) const {
		return (A->sort.sort_key2 == B->sort.sort_key2)
				? (A->sort.sort_key1 < B->sort.sort_key1)
				: (A->sort.sort_key2 < B->sort.sort_key2);
	}
};

struct SortByReverseDepthAndPriority {   // 透明物体
	_FORCE_INLINE_ bool operator()(const GeometryInstanceSurfaceDataCache *A,
									const GeometryInstanceSurfaceDataCache *B) const {
		return (A->sort.priority == B->sort.priority)
				? (A->owner->depth > B->owner->depth)
				: (A->sort.priority < B->sort.priority);
	}
};
```

### 3.3 排序键里装了什么

`sort_key1` / `sort_key2` 是**两个 64 位整数**，渲染器把多个维度打包进去，拆成"高位在前、低位在后"的比较顺序。理解打包顺序，就知道"两个物体为什么挨在一起却不是同一个材质"。

| 维度 | 大致作用 | 排在前面的含义 |
|------|----------|----------------|
| 渲染 pass / 队列号 | 同一 pass 的物体排在一起 | 相同 pass 的连续绘制，减少状态切换 |
| 材质 RID（uniform set 的身份） | 同一材质的表面排在一起 | 复用已绑定的 uniform set，跳过重新绑定 |
| 表面序号 | 同一网格的多个 surface | 保持网格内表面顺序稳定 |
| 网格 / 实例 RID | 同一网格的多个实例 | 让同网格实例共享顶点缓冲绑定 |

**读法**：两个物体的键"前几位相同、后几位不同"，说明它们**共享了同一个 pass 与同一个材质**，只是表面或实例不同；键的**高位**（pass / 材质）不同，就意味着**要切换 uniform set**——这才是 GPU 状态切换的真正来源。

### 3.4 不透明与透明用的是两套比较器

同一个 **RenderList** 里同时装着两套排序规则：

| 渲染列表 | 比较器 | 关键差异 |
|----------|--------|----------|
| 不透明 | **SortByKey** | 先看 pass / 材质键，**完全不看深度** |
| 透明 | **SortByReverseDepthAndPriority** | 先看 `render_priority`，同优先级比**反向深度**（远的先画） |

为什么不透明不按深度排序？因为不透明物体靠深度测试决定谁挡谁，顺序不影响最终像素；但**按材质键排能让 GPU 少切换状态**，这在实践中比省掉一点深度写入更划算。

透明则相反：透明物体靠混合叠加，顺序**直接决定最终颜色**，所以必须按深度排；代价是"两个半透明面互相穿插"时排序瑕疵无法避免。

### 3.5 排序优先级的边界

`Material.render_priority` 的取值范围由 `Material.RENDER_PRIORITY_MIN = -128` 与 `Material.RENDER_PRIORITY_MAX = 127` 界定。

| 误用 | 后果 |
|------|------|
| 把透明物体的 `render_priority` 设成很大的正数，想让它"浮到最上面" | 它仍然在**所有不透明物体之后**绘制，只是提前到透明队列内部 |
| 用 `render_priority` 解决"透明面被不透明面挡住" | 无效。不透明面在透明 pass 之前就已经写好了深度 |
| 靠 `render_priority` 修"两个透明面穿插" | 只能修**这一对**的关系，修不了它与第三个透明面之间的矛盾 |

---

## 四、减少 Draw Call 的手段

> Godot 4.x 的渲染器**没有**运行时合批器（Godot 3.x 的 batcher 已移除）。`servers/rendering/renderer_canvas_cull.cpp`、`renderer_canvas_render_rd.cpp`、`renderer_scene_render_rd.cpp` 与 `servers/rendering/rendering_server.h` 中 "batch" 的命中数**全部为 0**。Draw Call 的削减要在**场景组织**层面完成。

### 4.1 Godot 4 的等价手段

| 手段 | 说明 |
|------|------|
| **MultiMesh / MultiMeshInstance3D** | 同一网格的 N 个实例合并成 1 次实例化绘制，Transform 存在 GPU 缓冲区里 |
| **共享材质** | 多个 MeshInstance3D 引用同一个 `StandardMaterial3D` 资源，渲染器才能复用 uniform set、减少状态切换 |
| **SurfaceTool / ArrayMesh 合面** | 把静态小物件在**离线阶段**合并成一个大网格（这才是真正的"合批"，但要你自己做） |
| **可见性范围（visibility_range）** | `GeometryInstance3D.visibility_range_begin/end` 让远处的物体整体不可见，从源头减少绘制 |
| **LOD** | `GeometryInstance3D.lod_bias` + 网格自带的 LOD 层级，远处换低模 |

### 4.2 实例化示例

```gdscript
# 用 MultiMesh 把 1000 个相同网格合并成 1 次实例化绘制
var mm := MultiMesh.new()
mm.transform_format = MultiMesh.TRANSFORM_3D
mm.use_colors = true          # 每个实例可带颜色
mm.mesh = BoxMesh.new()      # 任何 Mesh 资源都可以

mm.instance_count = 1000
for i in mm.instance_count:
    var xform := Transform3D(Basis(), Vector3(i * 2.0, 0, 0))
    mm.set_instance_transform(i, xform)
    mm.set_instance_color(i, Color.WHITE)

var mmi := MultiMeshInstance3D.new()
mmi.multimesh = mm
add_child(mmi)
```

### 4.3 效果

> ⚠️ 下表为示意数据（未附测试环境），仅用于建立数量级概念。
> 实际 Draw Call 数取决于场景拆分方式、材质共享程度与可见性范围设置，请在目标平台实测。

| 场景 | 改造前 DrawCall | 改造后 DrawCall | 说明 |
|------|--------|--------|------|
| **简单** | 100 | ~20 | 100 个静态小物件合并为 1 个 MultiMesh |
| **中等** | 500 | ~100 | 静态物件合面 + 共享材质 + 远景 visibility_range |
| **复杂** | 2000 | ~400 | 逐场景定制，收益上限取决于物件能否真正同质化 |

### 4.4 状态切换才是真正的开销

**Draw Call 数量不是唯一指标**，GPU 上真正贵的是每次"换一套渲染状态"：

| 状态 | 什么时候变 | 影响 |
|------|------------|------|
| Uniform set | 材质 / 材质参数变了 | 重新绑定一组 buffer，Godot 内部会缓存并复用 |
| 顶点缓冲 | 网格变了 | 重新绑定 |
| 着色器管线 | 着色器或变体变了 | 切换 pipeline，可能触发驱动侧重编译 |
| 混合 / 深度状态 | 透明与不透明之间切换 | 管线状态变更 |

排序键把"同一个材质的表面排在一起"，收益就来自这里：**连续绘制同一材质时，渲染器可以跳过 uniform set 的重新绑定**。所以"共享材质"这条优化建议，在 GPU 侧的价值往往比"减少物体数"更大。

### 4.5 怎么验证自己的改动有效

不要靠感觉，用引擎自带的读数：

```gdscript
# 运行期读引擎的渲染统计（数值含义见 Performance 类参考）
print("draw call: ", Performance.get_monitor(Performance.RENDER_TOTAL_DRAW_CALLS_IN_FRAME))
print("objects   : ", Performance.get_monitor(Performance.RENDER_TOTAL_OBJECTS_IN_FRAME))
print("primitives: ", Performance.get_monitor(Performance.RENDER_TOTAL_PRIMITIVES_IN_FRAME))
```

> ⚠️ 上面三个常量名里，带 `_IN_FRAME` 后缀的那个是 4.3 的**正确**写法。少了这个后缀的旧名在 4.3 **不存在**，照抄会报 "Invalid access to property or key"：

```text
# 4.7.2 里同样不存在的写法（仅作反例）：
Performance.RENDER_TOTAL_DRAW_CALLS
```

编辑器里的对应入口是「调试 → 显示性能」或渲染器底部的统计面板；逐 pass 的耗时则看第 22 篇讲的 Visual Profiler。

### 4.6 共享材质到底共享了什么

"共享材质"听起来只是省内存，但它在渲染侧还共享了另外三样东西：

| 共享的东西 | 共享后的效果 | 不共享的后果 |
|------------|--------------|--------------|
| **Uniform set** | 渲染器缓存并复用已绑定的 uniform buffer 绑定 | 每个表面都要重新绑定一组 buffer |
| **着色器管线** | 同一材质变体共享同一个 pipeline | 换材质 = 换 pipeline，驱动侧可能重编译 |
| **纹理绑定** | 纹理只在第一次使用时绑定 | 重复绑定 |

反过来，**每次 `duplicate()` 一个材质都会打破这层共享**——虽然 `duplicate()` 出来的材质参数相同，但它们是**不同的 `Material` 资源**，渲染器会为它们各建一份 uniform set。

```gdscript
# 不好：循环里 duplicate，每个实例一份独立资源
for i in 100:
    var m := base_material.duplicate()   # ← 100 份 uniform set
    m.albedo_color = Color.from_hsv(i / 100.0, 1.0, 1.0)
    $MeshInstance3D.set_surface_override_material(0, m)

# 更好：共享同一个材质，靠 MultiMesh 的实例颜色区分
var mm := MultiMesh.new()
mm.transform_format = MultiMesh.TRANSFORM_3D
mm.use_colors = true
mm.mesh = BoxMesh.new()
mm.instance_count = 100
# … 逐个 set_instance_transform / set_instance_color
```

> 💡 如果确实需要"同一形状、不同颜色"的多个实例，**优先考虑 `MultiMesh` 的实例颜色**（`MultiMesh.use_colors` + `set_instance_color()`），而不是复制材质。

---

## 五、深度预通道、OIT 与真实 Pass 顺序

第 1 节那张"1. 场景更新 → 2. 可见性剔除 → …→ 7. 显示"的流程图，是通用引擎的**概念示意**，不是 Godot 的实现。本章把它换成以 **Godot 4.7.2 源码为锚**的真实顺序。

本章的顺序不是推演出来的，而是直接来自源码里的 `RENDER_TIMESTAMP()` 标记 —— 这些标记正是编辑器 **Visual Profiler** 里显示的条目名。所以下面每一行你都能在 Profiler 里找到同名的时间条。

### 5.1 深度预通道（Depth Pre-Pass）为什么存在

**一句话：先用最便宜的深度-only 着色把"哪些像素会被覆盖"确定下来，再跑完整着色，从而减少 overdraw。**

在 Forward+ 里，深度预通道是一个**独立于不透明 pass 的完整几何 pass**：

```
┌──────────────────────────────────────────────────────────────────────┐
│                    Forward+ 的深度预通道                             │
├──────────────────────────────────────────────────────────────────────┤
│  1. 用最简材质跑一遍全部几何体，只写深度（color 写入被丢弃）         │
│  2. 得到"每个像素最靠前的表面是谁"                                   │
│  3. 不透明 pass 复用它：深度测试变 EQUAL，被遮挡的片元直接剔         │
└──────────────────────────────────────────────────────────────────────┘
```

它在源码里的落点非常清楚：

```cpp
// Godot 4.7.2 源码 - servers/rendering/renderer_rd/forward_clustered/render_forward_clustered.cpp:2123
RENDER_TIMESTAMP("GI + Render Depth Pre-Pass (Parallel)");   // 与 GI 更新并行
...
RENDER_TIMESTAMP("Render Depth Pre-Pass");                   // :2125
...
RENDER_TIMESTAMP("Resolve Depth Pre-Pass (MSAA)");           // :2146 多重采样下做 resolve
```

它解决的问题可以用一句话概括：**没有深度预通道时，一层楼板后面的一百个室内物件会各自跑一遍完整 PBR 着色，然后被楼板全部覆盖——这些着色全部是浪费的。** 深度预通道把"被覆盖"这件事提前到最廉价的阶段判定。

**哪些材质会进深度预通道？** 由 `SceneShaderForwardClustered` 的 `ShaderData` 决定：

```cpp
// Godot 4.7.2 源码 - servers/rendering/renderer_rd/forward_clustered/scene_shader_forward_clustered.cpp:66
uses_depth_prepass_alpha = false;
...
// :130  把着色器里的 render_mode 开关映射到材质标志
actions.render_mode_flags["depth_prepass_alpha"] = &uses_depth_prepass_alpha;
...
// :868  对应的 shader 宏
actions.render_mode_defines["depth_prepass_alpha"] = "#define USE_OPAQUE_PREPASS\n";
...
// :259  最终判定：这个材质要不要进深度预通道
return !has_alpha || (uses_depth_prepass_alpha && !(depth_draw == DEPTH_DRAW_DISABLED || depth_test == DEPTH_TEST_DISABLED));
```

读这段代码可以得到三条结论：

1. **完全不透明的材质一定进预通道**（`!has_alpha`）。
2. **带 alpha 的材质只有开了 `depth_prepass_alpha` 才进**，而且不能同时关掉深度写入或深度测试。
3. 着色器层面的开关就是 `render_mode depth_prepass_alpha;`；材质层面的对应项是 `BaseMaterial3D.transparency = TRANSPARENCY_ALPHA_DEPTH_PRE_PASS`。

`CompositorEffect.needs_normal_roughness` 的官方文档也印证了这一点：

> This triggers normal and roughness data to be output during our depth pre-pass, only applicable for the Forward+ renderer.

> ⚠️ **Mobile 渲染器没有深度预通道。** `RenderForwardMobile::_render_scene()`（`forward_mobile/render_forward_mobile.cpp:644`）里**不存在** `Render Depth Pre-Pass` 这个时间戳 —— 移动端的做法是"直接渲染不透明物体"，用更少的 pass 换更低的开销。

#### 5.1.1 预通道里到底写了什么

"深度预通道"不是"不画"，而是**画得很便宜**：

| 项目 | 预通道 | 不透明 pass |
|------|--------|------------|
| 深度缓冲 | ✅ 写 | ✅ 写（深度测试变 EQUAL） |
| 颜色缓冲 | ❌ 不写（写入被丢弃） | ✅ 写 |
| 光照计算 | ❌ 不做 | ✅ 做 |
| 纹理采样 | 只采深度预通道需要的（如 alpha、normal/roughness） | 全量 |

`CompositorEffect.needs_normal_roughness` 之所以能"在深度预通道里输出法线与粗糙度"，正是因为预通道里**本来就要跑一遍材质的顶点/片元着色**，只是把光照部分关掉、只保留需要的输出。

#### 5.1.2 预通道的收益从哪来，什么时候不值得

预通道是**用一遍几何遍历换一遍光照计算**。所以：

- 场景**overdraw 严重**（室内、密堆小物件、粒子）→ 收益大。
- 场景**几乎不重叠**（开阔地形、稀疏摆放）→ 预通道纯粹多跑一遍几何，收益接近 0 甚至略负。

这就是为什么它只在 Forward+ 里默认开启，而 Mobile 直接不做。

### 5.2 不透明 → 天空 → 透明：为什么是这个顺序

Forward+ 的主 pass 顺序（源码锚定，见 5.8 的完整表）里，三个关键节点是：

| 顺序 | 源码标记 | 含义 |
|------|----------|------|
| 1 | `Render Opaque Pass` | 不透明物体写深度、写颜色 |
| 2 | `Render Sky` | 天空盒。天空**在透明之前**渲染，且通常只填充"还没有被几何体覆盖"的像素 |
| 3 | `Render 3D Transparent Pass` | 透明物体，靠混合叠加在已有颜色上 |

为什么天空排在透明之前？因为**透明物体需要"透过"看到后面的东西**。如果天空晚于透明渲染，玻璃后面的天空就会被透明物体挡住，产生错误的结果。

#### 5.2.1 天空只填"没人占的像素"

天空不是简单地"画一张全屏图"，而是：

1. 天空盒（`Sky` 资源，`sky_material`）按 `Environment.background_mode` 决定要不要画；
2. 天空**在深度测试下**渲染 —— 已经被不透明物体写进深度缓冲的像素被剔除，天空只补剩下的。

这带来两个可观察的现象：

- 室内场景里，如果天空没画对，通常是 `Environment.background_mode` 选了 `BG_CLEAR_COLOR` 之类，而不是天空本身出错。
- `Environment.background_camera_feed_id` 存在时，后台画面会代替天空进入颜色缓冲。

天空资源本身的参数在 `Sky` 上：

| 属性 | 说明 |
|------|------|
| `Sky.sky_material` | 天空材质（`ProceduralSkyMaterial` / `PanoramaSkyMaterial` 一类） |
| `Sky.process_mode` | `PROCESS_MODE_AUTOMATIC` / `PROCESS_MODE_QUALITY` / `PROCESS_MODE_INCREMENTAL` / `PROCESS_MODE_REALTIME`，决定天空的更新频率 |
| `Sky.radiance_size` | 辐射贴图边长（`RADIANCE_SIZE_32` ~ `RADIANCE_SIZE_2048`），影响 IBL 与反射质量 |

> 💡 `Sky.process_mode` 与 `Environment.sdfgi_read_sky_light` 是配合关系：SDFGI 要读天空光做间接光，如果天空自己还在"增量更新"，SDFGI 读到的就是**旧值**，画面会有一帧延迟的间接光。

### 5.3 透明物体怎么排序：不是 OIT

> **Godot 4.7.2 仍没有 OIT（Order-Independent Transparency，加权混合无序透明）。**
> 在 `servers/rendering/renderer_rd/` 的全部源文件里检索 `weighted_blend` / `oit` / `order_independent` **命中数为 0**。Godot 的透明处理是**经典的按深度排序 + alpha 混合**，不是无序混合。

排序规则是**先优先级、再反向深度**：

```cpp
// Godot 4.7.2 源码 - servers/rendering/renderer_rd/forward_clustered/render_forward_clustered.h
struct SortByReverseDepthAndPriority {   // 透明物体
	_FORCE_INLINE_ bool operator()(const GeometryInstanceSurfaceDataCache *A,
									const GeometryInstanceSurfaceDataCache *B) const {
		return (A->sort.priority == B->sort.priority)
				? (A->owner->depth > B->owner->depth)   // 同优先级：远的先画
				: (A->sort.priority < B->sort.priority);  // 优先级小的先画
	}
};
```

这解释了两个常见现象：

- **两个半透明物体重叠时会出现排序瑕疵**：因为排序只看"到相机的深度"，不解析几何体的真实遮挡关系 —— 这正是 OIT 要解决的问题，而 Godot 4.7.2 仍没有做。
- **`render_priority` 能救场**：把该物体排到前面或后面即可。

`Material.render_priority` 的官方描述（`doc/classes/Material.xml`）：

> Sets the render priority for objects in 3D scenes. Higher priority objects will be sorted in front of lower priority objects. In other words, all objects with [member render_priority] [code]1[/code] will render before all objects with [member render_priority] [code]0[/code].
> [b]Note:[/b] This will not impact how transparent objects are sorted relative to opaque objects or how dynamic meshes will be sorted relative to other opaque meshes. This is because all transparent objects are drawn after all opaque objects and all dynamic opaque meshes are drawn before other opaque meshes.

取值范围由 `Material.RENDER_PRIORITY_MIN = -128` 与 `Material.RENDER_PRIORITY_MAX = 127` 界定。

#### 5.3.1 透明排序的三个失效场景

| 场景 | 原因 | 缓解手段 |
|------|------|----------|
| 两个**互相穿插**的半透明面 | 排序只看中心深度，交错部分无法定序 | `render_priority` 手工定序，或改成 alpha 裁剪（`TRANSPARENCY_ALPHA_SCISSOR`） |
| 一个**很大的**半透明面（玻璃幕墙）罩住许多小物体 | 大面中心深度可能比小物体**更近**，先画大面 → 小物体被它盖住 | 改用 `TRANSPARENCY_ALPHA_DEPTH_PRE_PASS`，让大面先写深度再画小物体 |
| 透明物体**与不透明物体**穿插 | 不透明永远先画，透明永远后画 | 无解，只能改设计（把半透明部分拆成独立物体） |

#### 5.3.2 为什么 Godot 4.3 不做 OIT

OIT 需要额外的渲染目标（累积加权的颜色 + 累积权重）、额外的 resolve pass，以及对"半透明层数"的额外限制。在 Forward+ 的移动端变体上，这些额外 pass 的代价大于它解决的排序瑕疵。Godot 的选择是：**提供 `render_priority` 这个人工干预的出口**，把排序瑕疵的控制权交给作者。

### 5.4 材质侧的真实开关

| 属性 | 类型 / 取值 | 真实语义 |
|------|------------|----------|
| `BaseMaterial3D.transparency` | `TRANSPARENCY_DISABLED(0)` / `TRANSPARENCY_ALPHA(1)` / `TRANSPARENCY_ALPHA_SCISSOR(2)` / `TRANSPARENCY_ALPHA_HASH(3)` / `TRANSPARENCY_ALPHA_DEPTH_PRE_PASS(4)` | 决定材质走不走混合，以及**要不要进深度预通道** |
| `BaseMaterial3D.alpha_scissor_threshold` | float（默认 0.0） | alpha 裁剪阈值：低于它的片元被 `discard` 掉 |
| `BaseMaterial3D.depth_draw_mode` | `DEPTH_DRAW_OPAQUE_ONLY(0)` / `DEPTH_DRAW_ALWAYS(1)` / `DEPTH_DRAW_DISABLED(2)` | 什么时候写深度 |
| `Material.render_priority` | int，`-128` ~ `127` | 同一渲染列表内的排序优先级 |

三者的分工，用官方描述说最清楚：

- `TRANSPARENCY_ALPHA_SCISSOR`（别名 `TRANSPARENCY_ALPHA_TEST`）：
  > The material will cut off all values below a threshold, the rest will remain opaque. **The opaque portions will be rendered in the depth prepass.** This is faster to render than alpha blending, but slower than opaque rendering. This also supports casting shadows.
- `TRANSPARENCY_ALPHA_DEPTH_PRE_PASS`：
  > The material will use the texture's alpha value for transparency, but will discard fragments with an alpha of less than **0.99** during the depth prepass and fragments with an alpha less than **0.1** during the shadow pass. This also supports casting shadows.

- `depth_draw_mode`：
  > `DEPTH_DRAW_OPAQUE_ONLY` — Depth is drawn only for opaque objects during the opaque prepass (if any) and during the opaque pass.
  > `DEPTH_DRAW_ALWAYS` — Objects will write to depth during the opaque and the transparent passes.
  > `DEPTH_DRAW_DISABLED` — Objects will not write their depth to the depth buffer, even during the depth prepass (if enabled).
  > [b]Note:[/b] This does not influence whether transparent objects are included in the depth prepass or not. **For that, see [enum Transparency].**

> 💡 **最容易踩的一条**：`depth_draw_mode` **不决定**透明物是否进深度预通道，那是 `transparency` 的事。两个属性名字相近、管的是不同开关。

### 5.5 阴影 pass：为什么排在不透明之前

阴影不是"不透明 pass 的一部分"，它是**独立的一整轮几何渲染**，在 Forward+ 的顺序里出现在不透明 pass 之前：

| 顺序 | 源码标记 | 源码位置 | 说明 |
|------|----------|----------|------|
| 1 | `Render OmniLight Shadows` | `forward_clustered/render_forward_clustered.cpp:1410` | 点光 / 聚光的阴影（立方体 / 双抛物面） |
| 2 | `Render GI + Render Shadows (Parallel)` | :1430 | 阴影与 GI **并行**执行 |
| 3 | `Render Shadows` | :1432 | 只有阴影（GI 不需要时） |
| 4 | `Render GI` | :1434 | 只有 GI（阴影不需要时） |

三点结论：

1. **阴影必须先于不透明 pass**：不透明 pass 采样阴影贴图，贴图还没画完就没得采。
2. **阴影与 GI 是并行分支**：两者之间没有数据依赖，引擎用两条渲染通道并行跑以填满 GPU。
3. **阴影 pass 走的是自己的渲染列表**（`shadow_render_list`），成员由 `GeometryInstance3D.cast_shadow` 决定，`SHADOW_CASTING_SETTING_OFF` 的实例根本不进这个列表。

进入阴影 pass 的几何体，跑的是**深度-only 的着色器**（只写深度，不写颜色），并且用 `Light3D.shadow_transmittance_bias` / `shadow_normal_bias` / `shadow_bias` 控制偏移。偏移是"为了不让阴影出现自阴影条纹（shadow acne）而故意把阴影贴图往外推"，代价是阴影与物体接触处会**轻微脱离**（peter-panning）。

| 偏移参数 | 作用方向 | 典型症状 |
|----------|----------|----------|
| `Light3D.shadow_bias` | 沿光线方向的深度偏移 | 阴影出现条纹 / 摩尔纹 |
| `Light3D.shadow_normal_bias` | 沿法线方向偏移 | 阴影与物体脱离、悬空 |
| `Light3D.shadow_transmittance_bias` | 透射阴影的偏移 | 半透明物体的阴影形状不对 |
| `Light3D.shadow_reverse_cull_face` | 反转剔除面 | 单面片物体的阴影消失 |

> 💡 平行光的阴影**级联**参数（`directional_shadow_*` 系列）也在这里起作用：级联把相机视锥切成几段，每段用自己的正交范围渲染一张阴影贴图。详见第 15 篇《光照系统》第 2 章。

### 5.6 体积雾：FogVolume 与 Environment 的两套参数

Godot 4.3 里有**两套互不相干**的雾参数，初学者最容易混：

| | 深度雾 | 体积雾 |
|---|--------|--------|
| 开关 | `Environment.fog_enabled` | `Environment.volumetric_fog_enabled` |
| 模型 | 基于相机距离的解析雾（2D 叠加） | 真正的三维介质，参与光照散射 |
| 有节点吗 | ❌ 没有 | ✅ 有：`FogVolume` 节点 |
| 影响实时光照 | ❌ | ✅（散射、遮挡） |
| 影响 GI | ❌ | ✅（`volumetric_fog_gi_inject`） |
| 支持后端 | 全部 | Forward+（Mobile 不支持） |

**深度雾**（`fog_*`）是一组"按距离叠加"的解析雾：

| 属性 | 说明 |
|------|------|
| `Environment.fog_enabled` | 总开关 |
| `Environment.fog_mode` | `FOG_MODE_EXPONENTIAL`（指数）/ `FOG_MODE_DEPTH`（深度曲线） |
| `Environment.fog_light_color` / `fog_light_energy` | 雾的颜色与强度 |
| `Environment.fog_sun_scatter` | 太阳方向的散射强度 |
| `Environment.fog_density` | 指数雾密度 |
| `Environment.fog_depth_begin` / `fog_depth_end` / `fog_depth_curve` | 深度雾的起止距离与曲线 |
| `Environment.fog_height` / `fog_height_density` | 高度雾 |
| `Environment.fog_aerial_perspective` | 空气透视强度 |
| `Environment.fog_sky_affect` | 天空受雾影响的程度 |

**体积雾**（`volumetric_fog_*`）是真正的三维雾，需要 `FogVolume` 节点提供"介质在哪里"：

| 属性 | 说明 |
|------|------|
| `Environment.volumetric_fog_enabled` | 总开关 |
| `Environment.volumetric_fog_density` | 雾的密度（越大越浓） |
| `Environment.volumetric_fog_albedo` | 雾的散射颜色 |
| `Environment.volumetric_fog_length` | 采样步进长度（越大越省，但细节越少） |
| `Environment.volumetric_fog_detail_spread` | 细节噪声的扩散范围 |
| `Environment.volumetric_fog_anisotropy` | 各向异性（0 = 各向同性，接近 1 = 强前向散射） |
| `Environment.volumetric_fog_emission` / `volumetric_fog_emission_energy` | 雾的自发光（用于"发光的雾"） |
| `Environment.volumetric_fog_ambient_inject` | 注入多少环境光 |
| `Environment.volumetric_fog_gi_inject` | 注入多少进 GI 缓冲 |
| `Environment.volumetric_fog_sky_affect` | 天空受雾影响的程度 |
| `Environment.volumetric_fog_temporal_reprojection_enabled` | 时间重投影（用上一帧结果平滑） |
| `Environment.volumetric_fog_temporal_reprojection_amount` | 重投影混合系数 |
| `FogVolume.material` | 雾体使用的材质（决定雾的形状与自定义效果） |
| `FogVolume.size` | 雾体的作用范围 |

`FogVolume` 继承自 `VisualInstance3D`，也就是说它**在场景树里是一个可见实例**，会被视锥剔除；把它放在 `WorldEnvironment` 附近或场景中心是常规做法。

> ⚠️ **体积雾在 Mobile 渲染器上不可用。** `RenderForwardMobile::_render_scene()` 里没有体积雾的时间戳，Mobile 走的是深度雾那条路。需要在移动端也有雾感时，用 `Environment.fog_enabled` 这一组深度雾属性，而不是 `volumetric_fog_enabled` 那一组体积雾属性。

**体积雾与光源的交互**：光源对体积雾的贡献由 `Light3D.light_volumetric_fog_energy` 控制——它是一个**乘数**，把光源能量按比例转成雾中的散射。默认值让雾看起来比较"实"，如果你觉得灯在雾里不够亮，调这个属性比调 `light_energy` 更合适（后者会连带着把物体表面的照明一起调亮）。

**体积雾在 pass 顺序里的位置**：

| 顺序 | 源码标记 | 源码位置 | 说明 |
|------|----------|----------|------|
| 1 | `Render SDFGI` | `forward_clustered/render_forward_clustered.cpp:1139`（`_update_sdfgi`，:1128） | SDFGI 探针更新 |
| 2 | `Update Volumetric Fog` | :1517（`_update_volumetric_fog`，:1187） | 体积雾缓冲更新 |

体积雾缓冲的更新排在**最前面**，早于阴影、早于不透明 pass。原因是体积雾的散射要用到**光源的阴影**——如果雾是"阳光穿过缝隙的光柱"，那它必须知道哪些地方被阴影挡住了。

### 5.7 SDFGI：级联、探针与更新时机

SDFGI（Software Dynamic Global Illumination）是 Godot 4.3 里**唯一完全实时的 GI 方案**，它用符号距离场（Signed Distance Field）表示场景遮挡，用一套 GPU 探针在运行时求解间接光。

它的全部参数都在 `Environment` 上：

| 属性 | 类型 | 说明 |
|------|------|------|
| `Environment.sdfgi_enabled` | bool | 总开关 |
| `Environment.sdfgi_cascades` | int | 级联数量（越多越远越准，代价越高） |
| `Environment.sdfgi_cascade0_distance` | float | 第一级级联的起始距离 |
| `Environment.sdfgi_max_distance` | float | 最远一级级联覆盖的距离 |
| `Environment.sdfgi_min_cell_size` | float | 最小体素尺寸（越小越精细，显存与时间越高） |
| `Environment.sdfgi_y_scale` | int（枚举） | Y 轴压缩比例：`SDFGI_Y_SCALE_50_PERCENT` / `SDFGI_Y_SCALE_75_PERCENT` / `SDFGI_Y_SCALE_100_PERCENT` |
| `Environment.sdfgi_energy` | float | 间接光能量倍率 |
| `Environment.sdfgi_bounce_feedback` | float | 一次反弹的反馈比例（模拟多次反弹） |
| `Environment.sdfgi_read_sky_light` | bool | 是否把天空光算进 GI |
| `Environment.sdfgi_use_occlusion` | bool | 是否用遮挡信息做遮挡判定 |
| `Environment.sdfgi_normal_bias` | float | 法线方向偏移（减少自遮挡噪点） |
| `Environment.sdfgi_probe_bias` | float | 探针位置偏移（减少漏光） |

> ⚠️ `sdfgi_y_scale` 是**枚举**不是浮点数。写成 `env.sdfgi_y_scale = 1.0` 会报类型错误；正确写法是 `env.sdfgi_y_scale = Environment.SDFGI_Y_SCALE_75_PERCENT`。

#### 5.7.1 级联是怎么分的

SDFGI 把可视范围切成若干个**级联（cascade）**，每个级联有自己的体素网格：

```
相机
 ├── 级联 0：sdfgi_cascade0_distance 之内，格子最细（sdfgi_min_cell_size）
 ├── 级联 1：更远，格子按 2 倍递增
 ├── 级联 2：更远，再 2 倍
 └── 级联 N-1：最远，上限 sdfgi_max_distance
```

格子尺寸每级翻倍，是 SDFGI 能在"覆盖几百米"的同时保持可接受开销的关键。代价是**远处的间接光精度低、细节少**——这是所有距离场 GI 的共性。

#### 5.7.2 探针与更新时机

SDFGI 在场景中布置一批探针，每个探针记录周围若干个方向上的间接光。探针的更新是 Forward+ 每帧的**第二个**标记（紧跟在 `Prepare 3D Scene` 之后）：

| 顺序 | 源码标记 | 源码位置 |
|------|----------|----------|
| 2 | `Render SDFGI` | `forward_clustered/render_forward_clustered.cpp:1266`，由 `_update_sdfgi()`（:1255）调用 |

`_update_sdfgi()` 的输入是**上一帧结束时的场景状态**——因为 SDFGI 依赖的遮挡信息（哪些地方被挡住了）要到不透明 pass 画完才知道。这意味着：

- SDFGI 的结果**天然有一帧延迟**。相机快速移动时，间接光"跟不上"是正常现象，不是 bug。
- SDFGI 的结果**依赖上一帧的可见性**：被上一帧剔掉的物体不会贡献遮挡。

> 💡 想缓解延迟，可以把 `sdfgi_cascades` 调小、`sdfgi_min_cell_size` 调大，让更新本身更快。

#### 5.7.3 SDFGI 的能力边界

| 能力 | SDFGI | 说明 |
|------|-------|------|
| 后端支持 | **仅 Forward+** | Mobile 与 Compatibility 都不支持 |
| 动态物体 | ✅ | 物体移动后，下一帧的 SDFGI 就会更新 |
| 动态光源 | ✅ | 光源变化会被计入下一次探针更新 |
| 精度 | 低于烘焙 GI | 体素化必然带来误差 |
| 内存 | 随场景体积线性增长 | 大场景 + 小格子 = 大显存 |
| 与 LightmapGI 共存 | ❌ 互斥 | 同一场景里通常只用其中一种 |

### 5.8 Forward+ 的真实 Pass 顺序（源码锚定）

下表按**运行时顺序**列出 `RenderForwardClustered` 每一帧的 `RENDER_TIMESTAMP` 标记。左列是 Profiler 里看到的名字，右列是源码位置。

| # | Profiler 里的条目名 | 源码位置（`forward_clustered/render_forward_clustered.cpp`，除注明外） | 说明 |
|---|-------------------|--------------------------------------------------------------|------|
| 1 | `Prepare 3D Scene` | :1726（`_render_scene`，:1704） | 准备场景 |
| 2 | `Render SDFGI` | :1266（`_update_sdfgi`，:1255） | SDFGI 探针更新 |
| 3 | `Setup 3D Scene` | :1778 | 构建渲染列表、簇数据 |
| 4 | `Setup Sky` | :2071 | 准备天空 |
| 5 | `GI + Render Depth Pre-Pass (Parallel)` | :2123 | 深度预通道与 GI 并行 |
| 6 | **`Render Depth Pre-Pass`** | :2125 | 深度预通道 |
| 7 | `Resolve Depth Pre-Pass (MSAA)` | :2146 | MSAA 下的深度 resolve |
| 8 | `Process Pre Opaque Compositor Effects` | :2172 | Compositor 回调点 1 |
| 9 | `Setup Shadows` | :1530（`_pre_opaque_render`，:1517） | 准备阴影贴图 |
| 10 | `Render OmniLight Shadows` | :1562 | 全向光阴影 |
| 11 | `Render GI + Render Directional/SpotLight Shadows (Parallel)` | :1583 | 阴影与 GI 可并行 |
| 12 | `Render Directional/SpotLight Shadows` | :1585 | 平行光 / 聚光阴影 |
| 13 | `Render GI` | :1587 | 实时光照探针 |
| 14 | `Prepare Depth for SSAO/SSIL` | :1624 | 为 SSAO/SSIL 准备深度 |
| 15 | `Process SSAO` | :1430（`_process_ssao`，:1422） | 屏幕空间环境光遮蔽 |
| 16 | `Process SSIL` | :1456（`_process_ssil`，:1448） | 屏幕空间间接光 |
| 17 | `Process SSR` | :1490（`_process_ssr`，:1483） | 屏幕空间反射 |
| 18 | `Pre Opaque Render` | :1644 | 不透明前处理收尾 |
| 19 | `Update Volumetric Fog` | :1678（`_update_volumetric_fog`，:1317） | 体积雾缓冲更新 |
| 20 | **`Render Opaque Pass`** | :2188 | 不透明 pass |
| 21 | `Render Motion Pass` | :2245 | 运动矢量（需要时） |
| 22 | `Process Post Opaque Compositor Effects` | :2269 | Compositor 回调点 2 |
| 23 | **`Render Sky`** | :2297 | 天空 |
| 24 | `Resolve MSAA` | :2309 | 颜色 resolve |
| 25 | `Process Post Sky Compositor Effects` | :2330 | Compositor 回调点 3 |
| 26 | `Sub-Surface Scattering` | :2337（`_process_sss`，:1684） | 次表面散射 |
| 27 | `Merge Specular` | :2345 | 合并高光（分离高光缓冲） |
| 28 | `Clear Separate Specular (Canvas Background Mode)` | :2353 | 画布背景模式下的清理 |
| 29 | `Copy Screen Texture` / `Copy Depth Texture` | :2367 / :2378 | 拷贝屏幕/深度纹理 |
| 30 | `Process Pre Transparent Compositor Effects` | :2407 | Compositor 回调点 4 |
| 31 | **`Render 3D Transparent Pass`** | :2411 | 透明 pass |
| 32 | `Resolve` | :2431 | 解析 |
| 33 | `Copy Final Framebuffer (SSIL/SSR)` | :2451 | 拷贝最终帧缓冲供后处理用 |
| 34 | `Process Post Transparent Compositor Effects` | :2457 | Compositor 回调点 5 |
| 35 | `FSR2` / `TAA` | :2471 / :2539 | 抗锯齿 / 时间累积 |
| 36 | `Tonemap` | :2548 → 调用 `_render_buffers_post_process_and_tonemap()` | 进入后处理链 |

> 📌 **4.7.2 相对 4.3 的顺序变化**：屏幕空间效果（SSAO / SSIL / SSR）现在与阴影、GI 一起落在 `_pre_opaque_render()`（:1517）里，**排在深度预通道之后、不透明 pass 之前**；`Process SSR` 是 4.7.2 的标记名（4.3 叫 `Screen-Space Reflections`）。另外 4.7.2 新增了 `Setup Shadows`（:1530）、`GI + Render Depth Pre-Pass (Parallel)`（:2123）与 `Copy Final Framebuffer (SSIL/SSR)`（:2451）三个标记。

`_render_buffers_post_process_and_tonemap()`（`renderer_scene_render_rd.cpp:412`）内部的顺序是：

| 顺序 | Profiler 条目 | 源码位置（`renderer_scene_render_rd.cpp`） |
|------|--------------|--------------------------------------|
| 1 | `Depth of Field` | :439（景深） |
| 2 | `Auto exposure` | :492（自动曝光） |
| 3 | `Glow` | :518（泛光） |
| 4 | `Tonemap` | :570（色调映射） |

> ⚠️ 注意两个细节：**景深在自动曝光之前**（不是"曝光 → 景深"）；而**色调映射永远在最后**，它之后的输出已经在显示空间里。

#### 5.8.1 读这张表的三个用法

1. **定位性能瓶颈**：Visual Profiler 里哪根时间条最长，就去优化哪个 pass。"Render Opaque Pass" 长 → 减面 / 减材质复杂度 / 减光源；"Render Depth Pre-Pass" 长 → overdraw 太严重。
2. **定位"效果没出来"**：开了 SSAO 但画面没变化 → 看 `Process SSAO` 有没有出现；开了 SDFGI 但没间接光 → 看 `Render SDFGI` 有没有出现（可能后端是 Mobile）。
3. **定位"效果延迟一帧"**：SDFGI、体积雾都是**读上一帧状态**的，天然有延迟。

### 5.9 Mobile 的真实 Pass 顺序（对比）

`RenderForwardMobile::_render_scene()`（`forward_mobile/render_forward_mobile.cpp:644`）的标记少得多：

| # | Profiler 条目名 | 源码行号 | 与 Forward+ 的差异 |
|---|----------------|---------|-------------------|
| 1 | `Render Shadows` | :808（`_pre_opaque_render`，:767） | 同样先出阴影，但没有 GI 并行分支 |
| 2 | `Prepare 3D Scene` | :844 | — |
| 3 | `Setup 3D Scene` | :852 | — |
| 4 | `Setup Sky` | :1127 | — |
| 5 | `Render Opaque` | :1229 | **没有深度预通道** |
| 6 | `Render Transparent` | :1357 | 直接接在不透明之后 |
| 7 | `Tonemap` | :1385 | 没有独立的 DOF / Auto exposure / Glow 时间条 |

差异总结成一张表：

| 能力 | Forward+ | Mobile |
|------|-----------|--------|
| 深度预通道 | ✅ | ❌ |
| 阴影 + GI 并行 | ✅ | ❌（无实时 GI） |
| SSAO / SSIL | ✅ | ❌ |
| SSR | ✅ | ❌ |
| 次表面散射 | ✅ | ❌ |
| 独立的高光缓冲（Merge Specular） | ✅ | ❌ |
| 分离的 DOF / 自动曝光 / Glow 时间条 | ✅ | 部分（合并在 Tonemap 前后） |
| SDFGI | ✅ | ❌ |
| 体积雾 | ✅ | ❌ |
| 簇化光照（cluster） | ✅ | ❌（逐对象光照） |

> 💡 **一句话总结后两行**：Mobile 渲染器是"把 Forward+ 的每一项高级特性砍掉，用更少的 pass 换更低的开销"。你如果发现某个效果在移动端不见了，先查这张表，而不是查代码 bug。

### 5.10 自定义后处理：Compositor / CompositorEffect

如果要在 Godot 4.3 里插入自己的后处理 pass，官方入口是 **`Compositor` 资源 + `CompositorEffect`**。

**挂载方式**：

```gdscript
# CompositorEffect 是抽象基类，必须继承并实现 _render_callback
extends CompositorEffect

func _render_callback(effect_callback_type: int, render_data: RenderData) -> void:
    # effect_callback_type 一定等于你在 effect_callback_type 里指定的那个
    var rsb := render_data.get_render_scene_buffers()
    var color := rsb.get_texture("render_buffers", "color")
    # …在这里用 RenderingDevice 录制你自己的 pass

# 挂到环境上
var compositor := Compositor.new()
compositor.compositor_effects = [my_effect]
environment.compositor = compositor
```

**五个回调点**（`CompositorEffect.EffectCallbackType`，与 `RenderingServer.CompositorEffectCallbackType` 一一对应）：

| 值 | 枚举名 | 官方描述 |
|----|--------|----------|
| 0 | `EFFECT_CALLBACK_TYPE_PRE_OPAQUE` | 在不透明 pass **之前**、深度预通道（如果有）**之后**被调用 |
| 1 | `EFFECT_CALLBACK_TYPE_POST_OPAQUE` | 在不透明 pass **之后**、天空渲染**之前**被调用 |
| 2 | `EFFECT_CALLBACK_TYPE_POST_SKY` | 在天空渲染**之后**、后缓冲创建**之前**被调用（如果启用，也会在次表面散射 / SSR 之前） |
| 3 | `EFFECT_CALLBACK_TYPE_PRE_TRANSPARENT` | 在透明 pass **之前**、天空渲染之后、后缓冲创建之后被调用 |
| 4 | `EFFECT_CALLBACK_TYPE_POST_TRANSPARENT` | 在透明 pass **之后**、任何内建后处理与输出到渲染目标**之前**被调用 |

C++ 侧的枚举定义（`servers/rendering/rendering_server.h:1089`）：

```cpp
enum CompositorEffectCallbackType {   // servers/rendering/rendering_server.h:1089
	COMPOSITOR_EFFECT_CALLBACK_TYPE_PRE_OPAQUE, POST_OPAQUE, POST_SKY,
	COMPOSITOR_EFFECT_CALLBACK_TYPE_PRE_TRANSPARENT, POST_TRANSPARENT,
	COMPOSITOR_EFFECT_CALLBACK_TYPE_MAX, COMPOSITOR_EFFECT_CALLBACK_TYPE_ANY = -1,
};
```

**声明你需要的资源**（`CompositorEffect` 的成员属性 → `RenderingServer::CompositorEffectFlags`）：

| 属性 | 标志 | 效果 |
|------|------|------|
| `access_resolved_color` | `COMPOSITOR_EFFECT_FLAG_ACCESS_RESOLVED_COLOR = 1` | MSAA 开启时，先做一次颜色 resolve |
| `access_resolved_depth` | `COMPOSITOR_EFFECT_FLAG_ACCESS_RESOLVED_DEPTH = 2` | 同上，针对深度 |
| `needs_motion_vectors` | `COMPOSITOR_EFFECT_FLAG_NEEDS_MOTION_VECTORS = 4` | 在不透明 pass 中额外输出运动矢量 |
| `needs_normal_roughness` | `COMPOSITOR_EFFECT_FLAG_NEEDS_ROUGHNESS = 8` | 在**深度预通道**中输出法线与粗糙度（仅 Forward+） |
| `needs_separate_specular` | `COMPOSITOR_EFFECT_FLAG_NEEDS_SEPARATE_SPECULAR = 16` | 高光写入独立缓冲，效果之后再合并（仅 Forward+） |

> ⚠️ **`CompositorEffect` 在 4.3 是 `experimental` 类**（类参考里标注 "The implementation may change as more of the rendering internals are exposed over time."）。另外它的回调**运行在渲染线程上** —— 里面可以直接用 `RenderingDevice`，但不要碰场景树。

#### 5.10.1 选哪个回调点

| 你要做的事 | 选哪个回调点 | 理由 |
|------------|--------------|------|
| 改写不透明物体的最终颜色（描边、风格化后处理） | `EFFECT_CALLBACK_TYPE_POST_OPAQUE` | 此时不透明物体已写入颜色缓冲，天还没画 |
| 天空之后、SSR 之前做全局光照相关处理 | `EFFECT_CALLBACK_TYPE_POST_SKY` | 天空已就位，屏幕缓冲还没建 |
| 需要屏幕上的**透明物体**参与（如屏幕空间扭曲） | `EFFECT_CALLBACK_TYPE_PRE_TRANSPARENT` | 透明 pass 还没画，扭曲不会作用到透明物 |
| 内建后处理（景深 / 泛光 / 色调映射）之前插一手 | `EFFECT_CALLBACK_TYPE_POST_TRANSPARENT` | 所有几何都已完成 |

> 第 19 篇《后处理效果》会完整讲 `Compositor` / `CompositorEffect` 的用法；这里只强调一点：**它运行在渲染线程**，回调里不要访问场景树。

### 5.11 走一遍：一个带玻璃幕墙的室内场景

把前面所有 pass 串起来，看一个具体场景在各 pass 里发生了什么。

**场景设定**：一栋办公楼，一层有 200 个室内家具（桌子、椅子、柜子），正面是一整面玻璃幕墙，室外有一棵大树（动态投影），室内开了 3 盏点光源。

| pass | 场景里发生了什么 | 关注点 |
|------|------------------|--------|
| `Render SDFGI` | 上一帧的场景被体素化，探针重算间接光 | 玻璃幕墙后是**明亮的室外**，间接光会从窗口"漏"进来 |
| `Update Volumetric Fog` | 若开了体积雾，采样阴影贴图做散射 | 依赖阴影已经画好，所以体积雾更新排在阴影之前的那一轮缓冲里 |
| `Render OmniLight Shadows` | 3 盏点光的立方体阴影贴图 | 点光阴影在 Shadow Atlas 里各占一块 |
| `Render Shadows` | 平行光（大树 + 室内）的级联阴影 | 4 段级联，室内被家具遮挡 → 阴影级联浪费 |
| `Render Depth Pre-Pass` | 200 个家具 + 地板 + 玻璃幕墙各跑一遍 | 玻璃幕墙用的是 `TRANSPARENCY_ALPHA_DEPTH_PRE_PASS`，**会**进预通道 |
| `Render Opaque Pass` | 家具、地板着色 | 玻璃幕墙的不透明部分（alpha ≥ 0.99）在这里写深度 |
| `Render Sky` | 天空填满没被覆盖的像素 | 玻璃后面看到的天空已经在颜色缓冲里了 |
| `Render 3D Transparent Pass` | 玻璃的半透明部分混合 | 深度测试用的是预通道写下的深度，所以玻璃不会盖住室内家具 |
| `Tonemap` → `Glow` → `DOF` | 后处理链 | 顺序见 5.8 |

**这个场景暴露的三个设计点**：

1. **玻璃用 `TRANSPARENCY_ALPHA_DEPTH_PRE_PASS` 而不是 `TRANSPARENCY_ALPHA`**，就是为了进深度预通道——否则玻璃会挡住室内家具的深度，导致室内家具的透明物体排序全乱。
2. **室内开点光 + 平行光双重阴影**是浪费。平行光的级联已经把室内照暗了，点光阴影主要贡献接触阴影，但代价是 3 块 Shadow Atlas 区域 + 3 轮几何渲染。
3. **SDFGI 的间接光会穿过窗口**。如果发现室内过亮、边缘发灰，通常是 `sdfgi_energy` 偏高或 `sdfgi_cascade0_distance` 太大（把室外也纳入了计算范围）。

> 📌 这张表也是"为什么本节要按源码顺序讲"的最好理由：**同一个场景，改一个材质开关，动的不是一个 pass，而是整条链上的好几环。**

---

## 📝 本章总结

渲染一帧，本质上是"**先决定画什么，再决定按什么顺序画，最后决定每一遍画到哪个 pass 里**"。Godot 4.3 把这三件事分别放在三个地方：剔除与排序在主线程的 `RendererSceneCull`，渲染列表与 pass 录制在渲染线程的 `RenderForwardClustered`，GPU 提交在 `RenderingDevice`。

本章最重要的一条认知是：**Godot 4 没有运行时合批器**。Draw Call 的削减不是渲染器的工作，而是你在场景组织层（共享材质、MultiMesh、可见性范围）就已经决定的结果。

---

## 核心要点

1. **一帧三段**：主线程剔除排序（`renderer_scene_cull.cpp:2549`）→ 渲染线程录制（`renderer_scene_render_rd.cpp:1108`）→ `RenderingDevice` 提交。
2. **剔除与排序是两件事**：剔除决定"画不画"，排序决定"排第几"；调错地方会白费功夫。
3. **Godot 4 没有运行时合批器**：Draw Call 靠 MultiMesh / 共享材质 / 可见性范围在场景组织层解决，排序的目的是减少 GPU 状态切换。
4. **深度预通道**只在 Forward+ 存在，材质是否进通道由 `BaseMaterial3D.transparency` 决定，**不是** `depth_draw_mode`。
5. **透明不是 OIT**：按 `render_priority` + 反向深度排序，排序瑕疵要用 `render_priority` 人工修。
6. **阴影与 GI 是并行分支**，都排在不透明 pass 之前；SDFGI 与体积雾排在最前面，且都读上一帧状态，天然有一帧延迟。
7. **真实 pass 顺序**以 `RENDER_TIMESTAMP()` 标记为准，见 5.8 的 30 行表；Mobile 的差异见 5.9。

---

## 🔗 延伸阅读

- **官方文档**: [可见性范围（Visibility ranges / HLOD）](https://docs.godotengine.org/en/stable/tutorials/3d/visibility_ranges.html)、[使用 Lightmap 全局光照](https://docs.godotengine.org/en/stable/tutorials/3d/global_illumination/using_lightmap_gi.html)
- **类参考**: [RenderingServer](https://docs.godotengine.org/en/stable/classes/class_renderingserver.html)、[GeometryInstance3D](https://docs.godotengine.org/en/stable/classes/class_geometryinstance3d.html)、[MultiMeshInstance3D](https://docs.godotengine.org/en/stable/classes/class_multimeshinstance3d.html)、[CompositorEffect](https://docs.godotengine.org/en/stable/classes/class_compositoreffect.html)
- **源码位置**: `servers/rendering/renderer_scene_render.h`、`servers/rendering/renderer_rd/forward_clustered/render_forward_clustered.h`、`servers/rendering/renderer_rd/forward_clustered/scene_shader_forward_clustered.cpp`、`servers/rendering/renderer_rd/forward_mobile/render_forward_mobile.cpp`、`servers/rendering/renderer_rd/environment/`、`servers/rendering/renderer_rd/effects/`

---

## 📋 下一章预告

**第 15 篇：光照系统**

- DirectionalLight3D / OmniLight3D / SpotLight3D 的参数
- 阴影：PSSM 级联、软阴影与阴影偏移
- 全局光照：LightmapGI、VoxelGI、LightmapProbe、SDFGI
- 光照烘焙的编辑器流程

---

**作者**: wangshucheng
**首发平台**: 微信公众号  
**写作时间**: 2026 年 3 月  
**Godot 版本**: 4.x（基线 4.7.2；本文涉及的版本差异已在行内标注）

---

**上一篇**: [第 13 篇：Godot vs Unity 渲染对比](/articles/13-godot-vs-unity-rendering.md)
**下一篇**: [第 15 篇：光照系统](/articles/15-lighting-system.md)

---

*如果你觉得这篇文章有帮助，欢迎转发给更多开发者！*
