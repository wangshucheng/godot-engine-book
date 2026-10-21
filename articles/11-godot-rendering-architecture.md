# 第 11 篇：Godot 渲染架构概述

> **本章导读**：Godot 4.x 的渲染系统由「场景端 + RenderingServer + 图形抽象层」三层组成，本章把这三层拆开讲清楚：谁在主线程、谁在渲染线程、一帧里到底发生了什么。  
> 同时给出三种渲染器（Forward+ / Mobile / Compatibility）在**机制**层面的差异 —— 簇分配、逐对象光照、GLES3 通路 —— 以及各自的能力边界。读完本章，你能读懂 `servers/rendering/` 的目录结构，能按目标平台与画质需求选渲染器，也能用 `RenderingServer` 的同步接口安全地与渲染线程交互。  
> **前置知识**：第一卷《引擎核心架构》（已完成）；了解 RID 资源句柄的基本概念。  
> **难度**：⭐⭐⭐⭐ 高级  
> **本卷定位**：第二卷 渲染系统（12 篇）

---

## 📖 本章导读

渲染系统是游戏引擎的"脸面"，决定了玩家看到的一切视觉效果。Godot 4.x 的渲染架构经历了重大重构，从 Godot 3.x 的 GLES2/GLES3 迁移到基于 **Vulkan** 的现代渲染后端。

本章将深入剖析 Godot 渲染系统的整体架构，理解其设计哲学、核心组件和工作流程，为后续深入各个渲染子系统打下坚实基础。

---

## 🎯 学习目标

- 理解 Godot 渲染系统的整体架构和设计哲学
- 掌握三种渲染器的特点和适用场景
- 了解 Vulkan 后端的核心优势
- 熟悉渲染系统的关键组件和它们之间的关系
- 能够根据项目需求选择合适的渲染器

---

## 1. Godot 渲染系统演进

### 1.1 Godot 3.x vs Godot 4.x

| 特性 | Godot 3.x | Godot 4.x |
|------|-----------|-----------|
| **图形 API** | GLES2 / GLES3 | Vulkan, OpenGL ES 3, OpenGL 3 |
| **渲染器** | 单一渲染器 | 3 种独立渲染器 |
| **光照模型** | 传统 Forward | Clustered Forward（Forward+）/ 逐对象光照（Mobile） |
| **SDFGI** | ❌ 不支持 | ✅ 实时全局光照 |
| **体积雾** | 有限支持 | 完整支持 |
| **GPU 粒子** | 基础支持 | 完整 GPU 粒子系统 |

### 1.2 为什么选择 Vulkan？

Vulkan 是 Khronos Group 推出的现代图形 API，相比 OpenGL 有以下优势：

```
┌─────────────────────────────────────────────────────────┐
│                  Vulkan 核心优势                        │
├─────────────────────────────────────────────────────────┤
│  ✅ 显式控制：更细粒度的 GPU 资源管理                    │
│  ✅ 多线程友好：命令缓冲可并行录制                       │
│  ✅ 跨平台：Windows, Linux, macOS, Android, Web         │
│  ✅ 低开销：减少驱动层开销，提升 CPU-GPU 通信效率        │
│  ✅ 现代特性：原生支持计算着色器、光线追踪等             │
└─────────────────────────────────────────────────────────┘
```

> **注意**：Godot 4.x 没有 WebGPU 后端。Web 平台走 **WebGL 2**（OpenGL ES 3.0），对应 **Compatibility 渲染器**；桌面与移动平台走 Vulkan（Windows 还可回退到 Direct3D 12）。

---

## 2. 三种渲染器详解

Godot 4.x 提供了三种渲染器，每种针对不同的使用场景：

### 2.1 Clustered Forward Renderer（集群前向渲染器）

**适用场景**: 桌面平台、高质量 3D 游戏

```
特点:
├── 用 3D 网格（cluster）把视锥切成空间簇，光源按"影响到哪些簇"动态收集
├── 支持 SDFGI（符号距离场全局光照）
├── 支持体积雾和 Volumetric Fog
├── 支持屏幕空间反射 (SSR)
├── 支持 SSIL（屏幕空间间接光）
└── 需要 RenderingDevice 后端（Vulkan / Direct3D 12）
```

> **关于"8 盏灯"**：这个数字限制的是**单个物体可同时受影响的光源数**（per-object 上限，Mobile 渲染器源码中为 `MAX_RDL_CULL = 8`），**不是"每个簇 8 盏"**。Forward+ 的簇是三维网格单元，簇本身不设固定灯数上限——光照数据按"簇 → 光源列表"组织，着色器再对每个像素取其所在簇的光源列表。

**性能特征**:
- ✅ 高质量光照和阴影
- ✅ 适合复杂 3D 场景
- ⚠️ 对 GPU 要求较高
- ⚠️ 不支持低端移动设备

### 2.2 Mobile Renderer（移动渲染器）

**适用场景**: 移动设备、Web、低端硬件

```
特点:
├── 优化的移动设备性能
├── 支持大多数 3D 特性
├── 不支持 SDFGI
├── 简化的光照模型
├── 支持 Vulkan 和 OpenGL ES 3
└── 电池友好型设计
```

**性能特征**:
- ✅ 低功耗、高能效
- ✅ 兼容移动 GPU
- ⚠️ 视觉效果有所妥协
- ⚠️ 不支持高级光照特性

### 2.3 Compatibility Renderer（兼容渲染器）

**适用场景**: 老旧设备、WebGL 2、最大兼容性

```
特点:
├── 基于 OpenGL 3 / OpenGL ES 3
├── 最大设备兼容性
├── 不支持 Vulkan 特性
├── 基础 3D 渲染能力
└── 适合 2D 游戏和简单 3D
```

**性能特征**:
- ✅ 最广泛的设备支持
- ✅ WebGL 2 兼容
- ⚠️ 功能最有限
- ⚠️ 不适合复杂 3D 场景

---

## 3. 渲染架构核心组件

### 3.1 架构图

```
┌─────────────────────────────────────────────────────────────┐
│                      Godot 渲染架构                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐     │
│  │  场景树     │    │   资源系统   │    │   渲染服务器  │     │
│  │  (Scene)    │───▶│ (Resources) │───▶│  (RS)       │     │
│  └─────────────┘    └─────────────┘    └──────┬──────┘     │
│                                               │             │
│                    ┌──────────────────────────┼──┐          │
│                    │                          │  │          │
│           ┌────────▼────────┐        ┌────────▼──▼────┐    │
│           │  Forward+       │        │   Mobile       │    │
│           │  Renderer       │        │   Renderer     │    │
│           │  (桌面高质量)    │        │   (移动优化)    │    │
│           └────────┬────────┘        └────────┬───────┘    │
│                    │                          │             │
│           ┌────────▼──────────────────────────▼───────┐    │
│           │          Vulkan / OpenGL Backend          │    │
│           │          (图形 API 抽象层)                 │    │
│           └─────────────────────┬─────────────────────┘    │
│                                 │                           │
│                    ┌────────────▼────────────┐             │
│                    │      GPU Driver         │             │
│                    │      (显卡驱动)          │             │
│                    └─────────────────────────┘             │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 关键组件说明

#### RenderingServer (RS)

渲染服务器是 Godot 渲染系统的核心接口，所有渲染操作都通过它进行：

```gdscript
# GDScript 示例：通过 RenderingServer 创建网格
# 真实签名（servers/rendering_server.h）：
#   mesh_add_surface_from_arrays(mesh: RID, primitive: int, arrays: Array,
#                               blend_shapes: Array = [], lods: Dictionary = {},
#                               compress_format: int = 0)
# 注意：primitive 是必填的第 2 个参数，arrays 传的是顶点数组，不是 ArrayMesh 资源。
var mesh_rid := RenderingServer.mesh_create()
var arrays := []   # 依次填入 Mesh.ARRAY_VERTEX / ARRAY_NORMAL / ARRAY_TEX_UV / ARRAY_INDEX
RenderingServer.mesh_add_surface_from_arrays(
	mesh_rid,
	Mesh.PRIMITIVE_TRIANGLES,
	arrays
)
```

> `ArrayMesh.add_surface_from_arrays(primitive, arrays, blend_shapes, lods, compress_format)` 与它是同一套参数；日常开发用 `ArrayMesh` 即可，只有需要绕过场景树做批处理/流式加载时才直接调用 `RenderingServer`。

**主要职责**:
- 管理所有渲染资源（网格、材质、纹理、灯光等）
- 提供低级渲染 API
- 处理渲染状态和命令

#### Renderer 类

每种渲染器都是 `RendererSceneRender` 抽象基类的具体实现（4.3 真实继承链）：

```cpp
// Godot 4.3 源码 - servers/rendering/renderer_scene_render.h:43
class RendererSceneRender {          // 普通抽象基类，不是 Singleton
public:
    virtual void render_scene(const Ref<RenderSceneBuffers> &p_render_buffers,
                              const CameraData *p_camera_data,
                              const CameraData *p_prev_camera_data,
                              const PagedArray<RenderGeometryInstance *> &p_instances,
                              const PagedArray<RID> &p_lights, /* ... */) = 0;
    virtual void update() = 0;
};

// servers/rendering/renderer_rd/renderer_scene_render_rd.h
class RendererSceneRenderRD : public RendererSceneRender { /* 公共 RD 实现 */ };

// servers/rendering/renderer_rd/forward_clustered/render_forward_clustered.h
class RenderForwardClustered : public RendererSceneRenderRD { /* Forward+ */ };

// servers/rendering/renderer_rd/forward_mobile/render_forward_mobile.h
class RenderForwardMobile : public RendererSceneRenderRD { /* Mobile */ };
```

> 兼容渲染器（Compatibility）不经过 `RenderingDevice`，走的是 OpenGL 3.3 / OpenGL ES 3.0 / WebGL 2 这条独立通路。

#### Rasterizer (光栅化器)

负责将几何体转换为像素：

```
光栅化流程:
顶点着色器 → 图元装配 → 光栅化 → 片段着色器 → 测试与混合 → 帧缓冲
```

---

## 4. 渲染管线概览

### 4.1 单帧渲染流程

```
┌──────────────────────────────────────────────────────────────┐
│                    单帧渲染流程                              │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  1. 输入处理                                                  │
│     └─▶ 处理玩家输入、更新游戏状态                           │
│                                                              │
│  2. 场景更新                                                  │
│     └─▶ 更新节点变换、动画、物理                             │
│                                                              │
│  3. 可见性确定                                                │
│     └─▶ 视锥体剔除、遮挡剔除                                 │
│                                                              │
│  4. 阴影映射                                                  │
│     └─▶ 从光源视角渲染深度图                                 │
│                                                              │
│  5. 几何体渲染                                                │
│     └─▶ 渲染不透明物体（从前往后）                           │
│                                                              │
│  6. 透明物体渲染                                              │
│     └─▶ 渲染透明物体（从后往前）                             │
│                                                              │
│  7. 后处理                                                    │
│     └─▶ SSAO、Bloom、色调映射等                              │
│                                                              │
│  8. 呈现                                                      │
│     └─▶ 交换缓冲、显示到屏幕                                 │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### 4.2 Clustered Forward 光照计算

Clustered Forward 的核心思想是将屏幕分割成多个簇（Cluster），每个簇独立计算光照：

```
屏幕分割示例 (8x4 簇):
┌───┬───┬───┬───┬───┬───┬───┬───┐
│ C0│ C1│ C2│ C3│ C4│ C5│ C6│ C7│  ← 每个簇包含一组光源
├───┼───┼───┼───┼───┼───┼───┼───┤
│ 只计算影响该簇的光源，大幅提升性能         │
└───┴───┴───┴───┴───┴───┴───┴───┘
```

**优势**:
- 避免传统 Forward 渲染中 per-pixel 光照的开销
- 支持大量动态光源
- 保持 Forward 渲染的透明物体处理优势

---

## 5. 渲染器选择指南

### 5.1 决策树

```
你的目标平台是什么？
│
├── 桌面 (Windows/Mac/Linux)
│   └── 需要高质量 3D 吗？
│       ├── 是 → Clustered Forward + Vulkan
│       └── 否 → Compatibility Renderer
│
├── 移动 (iOS/Android)
│   └── 目标设备性能？
│       ├── 高端 → Mobile Renderer (Vulkan)
│       └── 中低端 → Mobile Renderer (GLES3)
│
└── Web (WebGL)
    └── Compatibility Renderer (唯一选择)
```

### 5.2 项目类型推荐

| 项目类型 | 推荐渲染器 | 理由 |
|----------|------------|------|
| AAA 级 3D 游戏 | Clustered Forward | 最高画质、完整特性 |
| 独立 3D 游戏 | Clustered Forward / Mobile | 平衡画质与性能 |
| 2D 游戏 | Compatibility | 2D 不需要高级 3D 特性 |
| 移动休闲游戏 | Mobile | 功耗优化、兼容性好 |
| WebGL 游戏 | Compatibility | 浏览器兼容性要求 |
| VR/AR 应用 | Clustered Forward | 高帧率、低延迟 |

---

## 6. 实践：切换渲染器

### 6.1 项目设置中切换

```
项目 → 项目设置 → 渲染 → 渲染器

可选值:
- Forward+ (Clustered Forward)
- Mobile
- Compatibility
```

### 6.2 代码中检测当前渲染器

```gdscript
# 获取当前渲染方法（渲染器在启动时确定，运行时改需要重启进程）
var rendering_method := ProjectSettings.get_setting("rendering/renderer/rendering_method", "forward_plus")
print("当前渲染器：", rendering_method)

# 移动端 / Web 平台可以用项目设置里的覆盖项切换
var platform_method := ProjectSettings.get_setting("rendering/renderer/rendering_method.mobile", "mobile")
print("移动端默认渲染器：", platform_method)

# GPU 适配器名称（不是渲染方法！）
print("GPU 适配器：", RenderingServer.get_video_adapter_name())
```

> **不要用 `RenderingServer.supports_feature()`**：4.3 里 `RenderingServer.Features` 枚举只剩 `FEATURE_SHADERS` 与 `FEATURE_MULTITHREADED` 两个常量，且被 `#ifndef DISABLE_DEPRECATED` 包裹、官方注释为 "Never actually used"、文档里标注 `deprecated="This constant has not been used since Godot 3.0."`；对应的方法名是 `has_feature()`，不是 `supports_feature()`，且未导出为脚本方法。判断能力请直接读项目设置或查询具体类属性。

### 6.3 运行时适配

```gdscript
# 根据硬件能力动态调整画质
# 注意：ProjectSettings 只有 set_setting()，没有 set()。
#      ProjectSettings.set(a, b) 会落到 Object.set(property, value)，
#      把"设置键"当成属性名，结果是设置不生效。
func adapt_graphics_quality():
    var adapter_name = RenderingServer.get_video_adapter_name().lower()

    # 检测是否为集成显卡
    if "intel" in adapter_name and "iris" not in adapter_name:
        # 降低画质设置（抗锯齿是项目设置，改动需要重启才生效）
        ProjectSettings.set_setting("rendering/anti_aliasing/quality/msaa_3d", 0)

        # SDFGI / SSAO 不在项目设置里开关，而是挂在 Environment 资源上
        if environment != null:
            environment.sdfgi_enabled = false
            environment.ssao_enabled = false

    # 移动设备优化
    if OS.get_name() in ["Android", "iOS"]:
        if environment != null:
            environment.sdfgi_enabled = false
            environment.ssao_enabled = false
```

> `rendering/renderer/rendering_method` 是**启动时**读取的设置：运行时用 `set_setting()` 改它不会切换渲染器，必须重启进程（或重启编辑器）才生效。

---

## 7. 性能考量

### 7.1 渲染器性能对比

> ⚠️ 下表为示意数据（未附测试环境），仅用于建立数量级概念。
> 实际数值取决于场景规模、光源数量、阴影贴图分辨率与目标硬件，请在目标平台实测。

| 渲染器 | 绘制调用 | 单物体受影响光源上限 | 内存占用 | 推荐分辨率 |
|--------|----------|----------|----------|------------|
| Clustered Forward | 中等 | 8（per-object，非 per-cluster） | 高 | 1080p+ |
| Mobile | 低 | 8（per-object） | 中 | 720p-1080p |
| Compatibility | 最低 | 很少 | 低 | 720p 以下 |

### 7.2 优化建议

**Clustered Forward 优化**:
```
✅ 合理使用 SDFGI（性能开销大）
✅ 使用光照探针替代部分动态光
✅ 合并静态网格减少绘制调用
❌ 避免过多动态光源
❌ 避免过度使用透明材质
```

**Mobile 优化**:
```
✅ 使用烘焙光照
✅ 减少实时阴影
✅ 简化材质着色器
❌ 避免复杂后处理
❌ 避免高分辨率阴影图
```

---

## 8. 渲染线程模型与帧管线

前 7 节回答的是"渲染器是什么、怎么选"。这一节补上渲染卷里一直缺席的一层：**一帧里，到底是谁、在哪个线程上、做了什么**。第 14 篇（场景渲染流程）、第 21 篇（性能优化）都会回头引用这一节的术语（"帧管线""渲染线程""提交"），先把定义钉死。

### 8.1 三个角色：场景端、RenderingServer、渲染线程

一次 3D 绘制在 Godot 4.3 里被切成三层职责：

| 角色 | 载体（源码路径） | 线程 | 职责 |
|------|------|------|------|
| **场景端** | `RendererSceneCull`（`servers/rendering/renderer_scene_cull.h/.cpp`） | 主线程 | 遍历场景中的几何体 / 灯光 / 贴花，执行视锥与遮挡剔除，排序，产出 `RenderGeometryInstance*` 列表 |
| **引擎渲染子系统** | `RendererSceneRender` → `RendererSceneRenderRD` → `RenderForwardClustered` / `RenderForwardMobile` | 渲染线程（可与主线程同线程） | 消费剔除后的列表，构建渲染列表、录制 RD 命令、提交 GPU |
| **图形抽象层** | `RenderingDevice` → `RenderingDeviceDriver` → `RenderingDeviceDriverVulkan` | 渲染线程 | 真正的 Vulkan / D3D12 / Metal 调用 |

数据流是单向的一次性交接：

```
主线程                                             渲染线程
--------------------------------------------------------------------------
RendererViewport::_draw_3d()          renderer_viewport.cpp:248
   └─ RSG::scene->render_camera()
        └─ RendererSceneCull::render_camera()      renderer_scene_cull.cpp:2549
             ├─ _visibility_cull()   ← 视锥 / 遮挡 / visibility_range
             ├─ _scene_cull()        ← 灯光、探针、贴花、雾体
             └─ _render_scene()                       renderer_scene_cull.cpp:3028
                  └─ scene_render->render_scene(     renderer_scene_cull.cpp:3414
                        scene_cull_result.{geometry_instances, light_instances,
                          reflections, voxel_gi_instances, decals, lightmaps, fog_volumes} ...
                        │
                        ▼
                   RendererSceneRender::render_scene()      renderer_scene_render.h
                        ▼
                   RendererSceneRenderRD::render_scene()    renderer_scene_render_rd.cpp:1108
                        ▼
                   RenderForwardClustered::_render_scene()
                        forward_clustered/render_forward_clustered.cpp:1570
                        ▼
                   RenderingDevice 录制命令 → 提交 Vulkan
```

> ⚠️ **路径更正（3.x → 4.x）**：Godot 3.x 的场景端剔除代码放在 `scene/renderer/` 目录（`scene/renderer/scene_renderer.cpp` 一类文件）。**Godot 4.3 没有这个目录** —— 对 4.3 分支请求 `scene/renderer/scene_renderer.h` 返回 404。4.x 把这一层搬到了 `servers/rendering/renderer_scene_cull.h/.cpp`，类名也从 3.x 的 `SceneRenderer` 变成了 `RendererSceneCull`。

### 8.2 `render_scene()` 的参数就是"剔除结果"的完整清单

`RendererSceneRender::render_scene()` 的签名（`servers/rendering/renderer_scene_render.h`）是理解整条数据流的关键：它接收的**不是场景树**，而是一批**已经剔除、已经排序好的扁平列表**。

```cpp
// Godot 4.3 源码 - servers/rendering/renderer_scene_render.h
virtual void render_scene(const Ref<RenderSceneBuffers> &p_render_buffers,
						  const CameraData *p_camera_data,
						  const CameraData *p_prev_camera_data,
						  const PagedArray<RenderGeometryInstance *> &p_instances,   // ← 已剔除的几何体
						  const PagedArray<RID> &p_lights,                             // ← 已剔除的灯光
						  const PagedArray<RID> &p_fog_volumes,
						  /* ... 与探针 / 贴花 / 雾体 / 阴影等 ... */) = 0;
```

三点值得注意：

1. **`p_instances` 是 `PagedArray<RenderGeometryInstance *>`** —— 裸指针数组，每个元素是一个"已经完成变换、材质、可见性判定"的渲染实例。渲染器在这之后**不再回头访问场景树**。
2. **剔除与排序发生在主线程**（`_visibility_cull()` / `_scene_cull()` / `_render_scene()`，见上表路径；内部可用 `WorkerThreadPool` 并行，如 `_visibility_cull_threaded()`），因此 CPU 侧的剔除开销会**直接计入主线程帧时间**。
3. **渲染线程不碰场景树**。这意味着渲染线程里没有 `Node`、没有 `ObjectID` 解引用，也就没有"游戏逻辑改了 transform，渲染线程读到一半"的竞态 —— 状态在交接点被快照了。

### 8.3 渲染线程模型：三种 `RenderThreadMode`

Godot 4.3 把"渲染要不要独立线程"做成了**项目设置**，取值来自 `OS::RenderThreadMode`：

```cpp
// Godot 4.3 源码 - core/os/os.h:94
enum RenderThreadMode {
	RENDER_THREAD_UNSAFE,   // 0
	RENDER_THREAD_SAFE,     // 1
	RENDER_SEPARATE_THREAD  // 2
};
```

对应的项目设置是 `rendering/driver/threads/thread_model`（整数，默认 `OS::RENDER_THREAD_SAFE`）：

```cpp
// Godot 4.3 源码 - main/main.cpp:2314
// 默认 RENDER_THREAD_SAFE；编辑器与无线程构建被强制为 SAFE。
if (rtm == -1) {
	rtm = GLOBAL_DEF("rendering/driver/threads/thread_model", OS::RENDER_THREAD_SAFE);
}

if (rtm >= 0 && rtm < 3) {
	if (editor || project_manager) {
		// Editor and project manager cannot run with rendering in a separate thread (they will crash on startup).
		rtm = OS::RENDER_THREAD_SAFE;
	}
#if !defined(THREADS_ENABLED)
	rtm = OS::RENDER_THREAD_SAFE;
#endif
	OS::get_singleton()->_render_thread_mode = OS::RenderThreadMode(rtm);
}
```

**只有 `RENDER_SEPARATE_THREAD` 才会真的开一个渲染线程**（main/main.cpp:2866）：

```cpp
rendering_server = memnew(RenderingServerDefault(
		OS::get_singleton()->get_render_thread_mode() == OS::RENDER_SEPARATE_THREAD));
```

| 模式 | 取值 | 渲染跑在哪 | 说明 |
|------|------|------------|------|
| `RENDER_THREAD_UNSAFE` | 0 | 主线程 | 渲染与游戏逻辑同线程；对应"驱动允许非线程安全调用"的档位 |
| `RENDER_THREAD_SAFE` | 1 | 主线程 | 同样不建独立线程，但走线程安全档位；**4.3 的默认值**，也是编辑器/无线程构建的强制值 |
| `RENDER_SEPARATE_THREAD` | 2 | 独立渲染线程 | 渲染逻辑搬到 `WorkerThreadPool` 的专用任务上，与主线程通过命令队列通信 |

> ⚠️ 三个名字最容易读错：**只有第 3 种才是"独立渲染线程"**。`SAFE` 与 `UNSAFE` 的差别在 RD 驱动层的线程安全档位（资源创建 / 上传与命令录制能否并发），而不是"有没有第二个线程"。这一档位在不同图形后端上的具体影响由驱动实现决定，官方文档未逐条展开，**以引擎源码与目标平台实测为准**。

### 8.4 独立渲染线程是怎么跑起来的

`RenderingServerDefault` 用一条 `CommandQueueMT` 把主线程的请求排队给渲染线程：

```cpp
// Godot 4.3 源码 - servers/rendering/rendering_server_default.cpp:248 / :371
void RenderingServerDefault::init() {
	if (create_thread) {
		print_verbose("RenderingServerWrapMT: Starting render thread");
		DisplayServer::get_singleton()->release_rendering_thread();
		WorkerThreadPool::TaskID tid = WorkerThreadPool::get_singleton()->add_task(
				callable_mp(this, &RenderingServerDefault::_thread_loop), true);
		command_queue.set_pump_task_id(tid);
		command_queue.push_and_sync(this, &RenderingServerDefault::_init);
	}
}

// 渲染线程的任务体 _thread_loop() 在自己的循环里不断 flush_all()。
```

要点：

- 渲染线程是 **`WorkerThreadPool` 的一个常驻任务**，不是裸 `Thread`。
- `DisplayServer` 会把图形上下文的"当前线程"**移交**给渲染线程（`release_rendering_thread()` / `gl_window_make_current()`），这是 Vulkan / OpenGL 上下文必须在创建它的线程上使用的硬性要求。
- 渲染线程在自己的循环里不断 `flush_all()`，把命令队列里积压的请求执行掉。

### 8.5 一帧的完整时序

```
┌────────────────────────────────────────────────────────────────────┐
│                          一帧的时序                                │
├────────────────────────────────────────────────────────────────────┤
│  【主线程】                                                        │
│    1. 输入事件 → 传播到场景树                                      │
│    2. Main::iteration() 推进帧时钟（main/main.cpp）                │
│    3. 物理帧：PhysicsServer3D::step() × N                          │
│    4. _process()：脚本逻辑、动画、变换更新                         │
│    5. RenderingServer::draw() → 把 draw 请求入队                   │
│         （独立线程模式下这里【不等待 GPU】）                       │
│    6. 继续下一帧的主循环                                           │
│                                                                    │
│  【渲染线程】（RENDER_SEPARATE_THREAD 时独立存在）                 │
│    7. RendererViewport::_draw_3d()                                 │
│    8. RendererSceneCull::render_camera()                           │
│         ├─ _visibility_cull()  视锥 / 遮挡 / visibility_range      │
│         ├─ _scene_cull()       灯光 / 探针 / 贴花 / 雾体           │
│         └─ _render_scene()     排序，产出剔除后的列表              │
│    9. scene_render->render_scene(...)                              │
│   10. RendererSceneRenderRD::render_scene() → _render_scene()      │
│   11. RenderForwardClustered::_render_scene()                      │
│         深度预通道 → 阴影 → 不透明 → 天空 → 透明 → 后处理 …        │
│   12. RenderingDevice 录制命令 → 提交队列 → GPU                    │
│                                                                    │
│  【GPU】                                                           │
│   13. 执行已提交的命令；呈现到交换链                               │
└────────────────────────────────────────────────────────────────────┘
```

> 第 11 步的详细 pass 顺序见**第 14 篇《场景渲染流程》**的"深度预通道、OIT 与真实 Pass 顺序"一章；第 9～10 步的渲染线程版本与 `RenderForwardMobile`（无深度预通道）的差异也在那里逐条对照。

### 8.6 主线程与渲染线程之间的同步点

| API | 作用 | 代价 |
|-----|------|------|
| `RenderingServer.sync()` | 把命令队列里的请求**同步执行完**（独立线程下是 `command_queue.sync()`，非独立线程下是 `flush_all()`） | 阻塞主线程，可能等待渲染线程 |
| `RenderingServer.call_on_render_thread(callable)` | 把一个 `Callable` **投递到渲染线程**执行；已经在渲染线程上时直接调用 | 需要等待渲染线程轮到它 |
| `RenderingServer.is_on_render_thread()` | 判断当前代码是否跑在渲染线程上 | 无 |
| `RenderingServer.draw()` | 提交一帧绘制 | 独立线程模式下**立即返回**，不等待 GPU |

```cpp
// Godot 4.3 源码 - servers/rendering/rendering_server_default.cpp:394
void RenderingServerDefault::sync() {
	if (create_thread) {
		command_queue.sync();
	} else {
		command_queue.flush_all(); // Flush all pending from other threads.
	}
}
```

`call_on_render_thread()` 的官方说明（`doc/classes/RenderingServer.xml`）：

> As the RenderingServer actual logic may run on an separate thread, accessing its internals from the main (or any other) thread will result in errors. To make it easier to run code that can safely access the rendering internals (such as [RenderingDevice] and similar RD classes), push a callable via this function so it will be executed on the render thread.

```gdscript
# 在渲染线程上安全地操作 RD 资源
RenderingServer.call_on_render_thread(func():
	var rd := RenderingServer.get_rendering_device()
	# 这里可以安全地创建/更新 RD 资源
	print("当前线程是渲染线程吗？", RenderingServer.is_on_render_thread())
)
```

> ⚠️ **Godot 4.3 的 `RenderingServer` 没有 `force_sync()` 方法**。`servers/rendering_server.h` 里与同步相关的公开虚函数只有 `virtual void sync() = 0;`（第 1658 行）、`virtual bool has_changed() const = 0;` 与 `virtual void draw(bool p_swap_buffers = true, double frame_step = 0.0) = 0;`。需要"强制等待 GPU"的场景请用 `RenderingDevice.sync()`（**仅本地 RD 可用**，见第 12 篇），并注意它有明确的性能代价。
>
> 📌 **勘误（脚本层补充）**：上面说的是 **C++ 头文件里的虚函数**。在 **4.3 的脚本类参考**里，`RenderingServer.force_sync()` 仍然作为 **deprecated** 方法存在（官方标注为"不做任何事"），所以在 GDScript 里调用它不会报错，但也不会产生同步效果。**结论不变**：真正能同步的是 `sync()`；需要等 GPU 请用 `RenderingDevice.sync()`（仅本地 RD 可用）。

### 8.7 帧率与 VSync 属于哪一层

VSync 属于**显示层**，不属于渲染线程模型：

```cpp
// Godot 4.3 源码 - servers/display_server.h:71
// Keep the VSyncMode enum values in sync with the `display/window/vsync/vsync_mode`
// project setting hint.
enum VSyncMode {
	VSYNC_DISABLED,
	VSYNC_ENABLED,
	VSYNC_ADAPTIVE,
	VSYNC_MAILBOX
};
```

| 项目设置 / API | 取值 | 作用 |
|----------------|------|------|
| `display/window/vsync/vsync_mode` | `Disabled` / `Enabled` / `Adaptive` / `Mailbox` | 传给 `DisplayServer`，最终由 `RenderingContextDriver::surface_set_vsync_mode()` 落到具体图形 API（Vulkan 的 present mode、OpenGL 的交换间隔） |
| `RenderingDevice.get_frame_delay()` | 整数 | 图形 API 保留的帧数；主 RD 在三缓冲 VSync 下通常是 3，本地 RD 只有 1 |

> `RenderingDevice.get_frame_delay()` 的官方描述（`doc/classes/RenderingDevice.xml`）："Returns the frame count kept by the graphics API. Higher values result in higher input lag, but with more consistent throughput. For the main [RenderingDevice], frames are cycled (usually 3 with triple-buffered V-Sync enabled). However, local [RenderingDevice]s only have 1 frame."

### 8.8 `Performance.TIME_PROCESS` 到底测了什么

这是最容易被误读的一组指标。官方类参考（`doc/classes/Performance.xml`）的原文是：

| 常量 | 官方描述 |
|------|----------|
| `Performance.TIME_PROCESS` | "Time it took to complete one frame, in seconds." |
| `Performance.TIME_PHYSICS_PROCESS` | "Time it took to complete one physics frame, in seconds." |
| `Performance.TIME_NAVIGATION_PROCESS` | "Time it took to complete a navigation step, in seconds. This includes navigation map updates as well as agent avoidance calculations." |

**口径要点**：

1. `TIME_PROCESS` 是**主循环一帧**的耗时，**不包含**渲染线程的工作，更**不包含** GPU 执行时间。在 `RENDER_SEPARATE_THREAD` 下，主线程的 `RenderingServer::draw()` 只是入队就返回，所以这段时间被完整地排除在 `TIME_PROCESS` 之外。
2. `TIME_PHYSICS_PROCESS` 是**一个物理帧**的耗时（不是一帧里的物理步数总和的墙钟时间口径之外的另一种定义），与 `TIME_PROCESS` 不是同一个量纲。
3. `TIME_PROCESS` 与 `TIME_FPS` 的关系是**倒数关系但不是严格互推**：`TIME_FPS` "is only updated once per second, even if queried more often"。

**为什么还需要 GPU 侧的数据**：因为 `TIME_PROCESS` 看不见 GPU。要看 GPU 侧每一步的耗时，4.3 的路径是：

| 手段 | 层级 | 说明 |
|------|------|------|
| 编辑器 **Visual Profiler** | 编辑器 | 逐 pass 显示 GPU 耗时，底层读的是 `RenderingServer::get_frame_profile()` |
| `RenderingServer.get_frame_profile()` | C++ | `servers/rendering_server.h` 的虚函数，返回 `Vector<FrameProfileArea>` |
| `RenderingServer::FrameProfileArea` | C++ | 结构体只有三个字段：`String name; double gpu_msec; double cpu_msec;` |
| `RenderingServer.get_rendering_info()` / `viewport_get_render_info()` | GDScript | 拿 draw call、对象数等**统计量**（不是耗时） |

> ⚠️ **`get_frame_profile()` 在 Godot 4.3 里没有导出为 GDScript 方法**。`doc/classes/RenderingServer.xml` 里搜不到 `get_frame_profile`、`FrameProfileArea`、`set_frame_profiling_enabled` 中的任何一个——它只在 C++ 层存在（`servers/rendering_server.h:1681-1689`），编辑器 Visual Profiler 是它的主要消费者。想在脚本里拿 GPU 侧数据，4.3 的公开入口是 `get_rendering_info()` / `viewport_get_render_info()` 这类统计接口。

### 8.9 相关项目设置速查

| 项目设置 | 类型 / 取值 | 默认 | 作用 |
|----------|-------------|------|------|
| `rendering/driver/threads/thread_model` | 整数（`OS::RenderThreadMode`） | `1`（`RENDER_THREAD_SAFE`） | 是否把渲染放到独立线程；仅 `2` 会创建渲染线程 |
| `display/window/vsync/vsync_mode` | `Disabled` / `Enabled` / `Adaptive` / `Mailbox` | `Enabled` | 垂直同步模式，最终落到图形 API 的 present 策略 |
| `rendering/occlusion_culling/use_occlusion_culling` | bool | `false` | 启用遮挡剔除（`RendererSceneOcclusionCull`）。根视口走这个项目设置；普通 `Viewport` 用节点属性 `Viewport.use_occlusion_culling`（默认 `false`） |
| `rendering/occlusion_culling/occlusion_rays_per_thread` | int | — | 每个线程的遮挡探测射线数（`RendererViewport` 构造时读取） |

### 8.10 常见误区

| 误区 | 事实 |
|------|------|
| "渲染永远在另一个线程上" | 默认是 `RENDER_THREAD_SAFE`，渲染与主线程同线程；只有显式切到 `RENDER_SEPARATE_THREAD` 才会多一个线程 |
| "`Performance.TIME_PROCESS` 包含 GPU 时间" | 不包含。它测的是主循环一帧，渲染线程与 GPU 都在其外 |
| "调用 `RenderingServer.draw()` 会等这一帧画完" | 独立线程模式下只是入队（`command_queue.push(this, &RenderingServerDefault::_draw, ...)`），立即返回 |
| "把 `thread_model` 改成 `UNSAFE` 帧率就更快" | `UNSAFE` 并不创建独立线程；它改变的是驱动层的线程安全档位，性能收益需实测，不能预设 |
| "剔除是渲染线程做的" | 剔除与排序在**主线程**的 `RendererSceneCull` 里完成，渲染线程拿到的是已经筛好的列表 |
| "`RenderingServer.force_sync()` 可以强制同步" | C++ 头文件里没有这个虚函数；4.3 的脚本类参考里它是 **deprecated 的空方法**，真正能同步的只有 `sync()` |

### 8.11 场景端剔除的并行边界

上一节说"剔除与排序发生在主线程"，这句话容易被误读成"剔除是单线程的"。需要再拆细一层。

| 阶段 | 发生在哪 | 能否并行 | 产物 |
|------|----------|----------|------|
| 场景树同步（`Node` 变换、可见性、`NOTIFICATION_TRANSFORM_CHANGED`） | 主线程 | ❌ 场景树本身是单线程的 | 待剔除的实例列表 |
| 视锥剔除（实例 AABB vs 相机视锥） | 主线程的 `RendererSceneCull` | ✅ 引擎提供并行能力，可交给 `WorkerThreadPool` | 可见实例列表 |
| 遮挡剔除（`RendererSceneOcclusionCull`） | 主线程 | ✅ 探测射线按线程配额分配 | 遮挡后的可见列表 |
| 排序（材质键 / 深度 / 优先级） | 主线程 | ⚠️ 比较器是确定性的，但排序本身通常不是瓶颈 | 渲染列表 |
| 渲染列表构建 + 命令录制 | 渲染线程 | ⚠️ 录制阶段是串行的 | GPU 命令 |

> ⚠️ 表中"能否并行"描述的是**架构上的可能性**，不是"某条路径一定并行了"。可以确定的是三件事：① 场景树只在主线程被访问；② 剔除与排序的**汇合点在主线程**；③ 渲染线程拿到的永远是合并后的完整列表。
>
> **因此剔除开销一定计入主线程帧时间。** 这一条在做性能预算时经常被忽略：玩家抱怨"掉帧"时，如果 `Performance.TIME_PROCESS` 明显偏高但 GPU 很闲，瓶颈大概率在剔除/排序，而不是着色。

**能真正减少剔除成本的三条路**（而不是" hoping 剔除器更快"）：

| 手段 | 作用点 | 做法 |
|------|--------|------|
| `GeometryInstance3D.visibility_range_begin` / `_end` | 减少**进入剔除的实例数** | 超出距离范围的实例不参与视锥与遮挡剔除 |
| `GeometryInstance3D.lod_bias` | 提前切换更远的 LOD | 配合 `visibility_range` 使用，避免远处实例仍在做高精度渲染 |
| `GeometryInstance3D.gi_mode` | 关闭不需要 GI 的实例的 GI 通道 | `GI_MODE_DISABLED` 让该实例不参与 GI 计算 |

> `GeometryInstance3D.visibility_range_begin` / `visibility_range_end` 与 `lod_bias` 的完整用法见**第 21 篇《渲染性能优化》**；本节只强调它们在**剔除入口**就减负，因此收益比"在着色端省算力"更直接。

### 8.12 RID：谁拥有渲染资源

RID 是渲染服务器内部的整数句柄。它不是 `Object`，没有脚本可见的方法，也不能 `await`、不能 `connect` 信号 —— 它只有一个作用：**标识一份由 `RenderingServer` 托管的渲染资源**。

```gdscript
# 创建一份网格资源，返回 RID
var mesh_rid: RID = RenderingServer.mesh_create()

# 场景节点（MeshInstance3D 等）在自己被销毁时释放所持有的 RID；
# 如果你手动创建了 RID，就必须自己调用 free_rid()。
RenderingServer.free_rid(mesh_rid)
```

三个必须记住的规则：

| 规则 | 说明 | 踩坑后果 |
|------|------|----------|
| **RID 不共享所有权** | `RefCounted` 引用计数归零就自动释放；RID 没有这层保护，谁创建谁负责 `free_rid()` | 忘记释放 → 显存/内存泄漏，且 `free_rid()` 之后继续使用该 RID → 未定义行为 |
| **创建与释放必须走主线程** | RID 的创建/释放是 `RenderingServer` 的命令，会被投递到渲染线程 | 在渲染线程里直接 `free_rid()` 会与命令队列竞争 |
| **跨线程"使用"可以，"创建"要小心** | 渲染线程里用 RID 做渲染是设计内的；创建新 RID 请用 `RenderingServer.call_on_render_thread()` | 主线程创建、渲染线程立刻使用，中间没有同步点 |

**显存与资源的观测口径**（脚本可见的三个计数器）：

| 计数器 | 含义 |
|--------|------|
| `Performance.RENDER_VIDEO_MEM_USED` | 显存占用总量（含纹理与缓冲） |
| `Performance.RENDER_TEXTURE_MEM_USED` | 纹理占用 |
| `Performance.RENDER_BUFFER_MEM_USED` | 缓冲占用 |

```gdscript
# 观测显存占用（单位：字节）
print("显存：", Performance.RENDER_VIDEO_MEM_USED / 1024.0 / 1024.0, " MB")
print("纹理：", Performance.RENDER_TEXTURE_MEM_USED / 1024.0 / 1024.0, " MB")
print("缓冲：", Performance.RENDER_BUFFER_MEM_USED / 1024.0 / 1024.0, " MB")
```

> ⚠️ 这三个是**当前值**（占用），不是**速率**（每帧增长）。要抓"是不是在泄漏"，正确做法是隔一段时间采样一次做差值，而不是盯着一帧的绝对值看。

### 8.13 帧分析的三层接口

想知道"这一帧到底花在哪"，4.3 提供了三个层次的能力，粒度和可及性差别很大。

**第 1 层：脚本可见的计数器**（能拿到数字，拿不到耗时）

| 接口 | 给出什么 | 典型用途 |
|------|----------|----------|
| `Performance.get_monitor(Performance.TIME_PROCESS)` | 主循环一帧耗时（秒） | 判断"是不是主线程慢" |
| `Performance.RENDER_TOTAL_DRAW_CALLS_IN_FRAME` | 本帧绘制调用数 | 判断"是不是 draw call 太多" |
| `Performance.RENDER_TOTAL_OBJECTS_IN_FRAME` | 本帧渲染对象数 | 判断"是不是剔除没减负" |
| `Performance.RENDER_TOTAL_PRIMITIVES_IN_FRAME` | 本帧图元数 | 判断"是不是面数太高" |
| `RenderingServer.get_rendering_info()` | 引擎侧各项统计 | 取渲染器内部计数 |
| `RenderingServer.viewport_get_render_info(viewport, info)` | 指定视口的统计 | 取某个子视口的 draw call / 物体数 |

**第 2 层：C++ 层的逐 pass 耗时**（`FrameProfileArea`）

```cpp
// Godot 4.3 源码 - servers/rendering_server.h
// 结构体只有三个字段：一个显示名、GPU 耗时（毫秒）、CPU 耗时（毫秒）。
struct FrameProfileArea {
    String name;
    double gpu_msec;
    double cpu_msec;
};

// 取当前帧的逐区域耗时
virtual Vector<FrameProfileArea> get_frame_profile() const = 0;
```

> ⚠️ **`get_frame_profile()` 在 Godot 4.3 里没有导出为 GDScript 方法**（`doc/classes/RenderingServer.xml` 里搜不到它）。它在 C++ 层存在，**编辑器 Visual Profiler 是它的主要消费者**。想在脚本里拿 GPU 侧数据，4.3 的公开入口只有第 1 层那些计数器。

**第 3 层：编辑器可视化开关**（`Viewport.debug_draw`）

`Viewport.DebugDraw` 在 4.3 共有 **27 项**，常用的几项：

| 枚举值 | 看什么 |
|--------|--------|
| `DEBUG_DRAW_LIGHTING` | 只画光照贡献 |
| `DEBUG_DRAW_OVERDRAW` | 过绘区域（同一像素被画了几次） |
| `DEBUG_DRAW_WIREFRAME` | 线框 |
| `DEBUG_DRAW_NORMAL_BUFFER` | 法线缓冲 |
| `DEBUG_DRAW_SHADOW_ATLAS` | 阴影图集 |
| `DEBUG_DRAW_PSSM_SPLITS` | 平行光级联分割 |
| `DEBUG_DRAW_OCCLUDERS` | 遮挡体 |
| `DEBUG_DRAW_INTERNAL_BUFFER` | 引擎内部缓冲 |

> 第 4 层是**外部工具**：RenderDoc、apitrace 这类抓帧工具能给出完整的命令流与 GPU 时间线。详见**第 22 篇《渲染调试工具》**。

---

## 九、三种渲染器的机制差异

前八节回答了"渲染器是什么、怎么选、谁在干活"。这一章把"机制差异"摊开讲：三种渲染器**在实现层面**究竟差在哪，为什么同样的场景在不同渲染器上表现会差一个量级。第 13 篇会把这些差异整理成与 Unity 的对照矩阵，本章负责把**机制本身**讲透。

### 9.1 三种渲染器落在哪一层

```
┌──────────────────────────────────────────────────────────────────┐
│                       场景端（主线程）                            │
│            RendererSceneCull：剔除 + 排序 → 渲染列表               │
└───────────────────────────┬──────────────────────────────────────┘
                            │  渲染列表（已剔除、已排序）
                            ▼
┌──────────────────────────────────────────────────────────────────┐
│                     渲染器实现（渲染线程）                        │
├──────────────────┬──────────────────┬────────────────────────────┤
│  Forward+        │  Mobile          │  Compatibility            │
│  RenderForward   │  RenderForward   │  GLES3 场景渲染器         │
│  Clustered       │  Mobile          │  （不走 RD）              │
├──────────────────┴──────────────────┴────────────────────────────┤
│         图形抽象层                                               │
│  Forward+/Mobile：RenderingDevice → RenderingDeviceDriver        │
│  Compatibility  ：OpenGL 3.3 / GLES 3.0 / WebGL 2（**不经过 RD**） │
└──────────────────────────────────────────────────────────────────┘
```

| 渲染器 | 图形后端 | 是否经过 `RenderingDevice` | 场景端渲染实现 | 源码目录 |
|--------|----------|---------------------------|----------------|----------|
| Forward+ | Vulkan / D3D12 / Metal | ✅ | `RenderForwardClustered` | `servers/rendering/renderer_rd/forward_clustered/` |
| Mobile | Vulkan / D3D12 / Metal | ✅ | `RenderForwardMobile` | `servers/rendering/renderer_rd/forward_mobile/` |
| Compatibility | OpenGL 3.3 / GLES 3.0 / WebGL 2 | ❌ | GLES3 场景渲染器（`drivers/gles3/rasterizer_scene_gles3.h`） | `drivers/gles3/` |

> 三种渲染器**共用同一套场景端**（`RendererSceneCull`）与**同一套 `RenderingServer` 接口**。差别只发生在"渲染器实现 → 图形 API"这一段。这也是为什么换渲染器时，场景、材质、`.gdshader` 都不用改 —— 改的是这一段。

### 9.2 机制差异总矩阵

| 机制维度 | Forward+ | Mobile | Compatibility |
|----------|----------|--------|---------------|
| 图形后端 | Vulkan / D3D12 / Metal | Vulkan / D3D12 / Metal | OpenGL 3.3 / GLES 3.0 / WebGL 2 |
| 是否经过 `RenderingDevice` | ✅ | ✅ | ❌ |
| 光照剔除方式 | **簇分配**（视锥切成 3D 网格） | **逐对象**（per-object） | **逐对象**（per-object） |
| 单个物体可受影响的光源数 | 不设硬上限（按所属簇取） | 8（`MAX_RDL_CULL`） | 8（`rendering/limits/opengl/max_lights_per_object`） |
| 深度预通道 | ✅ | ❌ | ❌ |
| 阴影图管理 | Shadow Atlas + PSSM 级联 | Shadow Atlas | Shadow Atlas |
| 全局光照 | SDFGI / LightmapGI / VoxelGI / LightmapProbe | LightmapGI / VoxelGI / LightmapProbe | LightmapGI / VoxelGI |
| 屏幕空间反射（`ssr_enabled`） | ✅ | ❌ | ❌ |
| 屏幕空间间接光（`ssil_enabled`） | ✅ | ❌ | ❌ |
| 环境光遮蔽（`ssao_enabled`） | ✅ | ✅ | ❌ |
| 体积雾（`volumetric_fog_enabled`） | ✅ | ❌ | ❌ |
| Compute shader | ✅ | ✅ | ❌ |
| 自定义后处理（`CompositorEffect`） | ✅ | ✅ | ❌（依赖 `RenderingDevice`） |
| GPU 粒子 | ✅ | ✅ | ❌（回退为 CPU 粒子） |
| 目标平台 | 桌面 / 高端主机 | 移动 / 中端桌面 | Web / 老旧设备 |

> ⚠️ 这张表的"支持"指的是**4.3 引擎自身提供了该特性的实现**。个别特性（尤其是屏幕空间效果）的 Compatibility 支持状态在不同 4.x 小版本间有变化，上线前请以目标版本源码与目标平台实测为准。表中"全局光照"一行指的是**可用的 GI 手段集合**，不表示各手段在每种渲染器下的行为完全一致。

> 💡 **从这张表能直接读出的三条结论**：
> 1. **Mobile 砍掉的是"屏幕空间 + 体积"这一类依赖视差与历史帧的特效**，不是砍掉阴影或烘焙光照 —— 所以 Mobile 上的画面差异主要在"远处的空气感"，几何与直接光基本一致。
> 2. **Compatibility 砍掉的是"整条 RD 通路"** —— compute、存储缓冲、自定义后处理一起消失，这是架构性的，不是开关。
> 3. **Forward+ 相对 Mobile 的核心增量就是"簇"**：把"灯数"从 per-object 维度解放到 per-pixel 维度。

### 9.3 Forward+：簇分配（cluster allocation）

传统前向渲染的成本是"**每个像素 × 场景里所有灯**"。簇方案把成本改成"**每个像素 × 真正照到它的灯**"。

```
视锥被切成 3D 网格（cluster）：

            深度方向（若干层，近处密、远处疏）
              │
    ┌─────────┼─────────┬─────────┐
    │  簇     │  簇     │  簇     │  ← 屏幕横向切片
    ├─────────┼─────────┼─────────┤
    │  簇     │  簇     │  簇     │  ← 屏幕纵向切片
    └─────────┴─────────┴─────────┘
              │
              ▼
   每帧构建「簇 → 光源列表」
```

**每帧发生三件事**：

| 步骤 | 做什么 | 在哪 |
|------|--------|------|
| ① 划分 | 把视锥按屏幕 x/y 切片 × 深度切片切成三维网格 | 渲染线程 |
| ② 收集 | 遍历可见灯，把每盏灯的**影响范围**（omni/spot 的作用半径、方向光的整个视锥）投影到网格上，记录"哪些簇被这盏灯影响" | 渲染线程 |
| ③ 查表 | 片元着色器用（屏幕坐标，深度）定位像素所在簇 → 取该簇的光源列表 → 逐灯计算 | GPU |

**为什么有效**：光源数不再受"场景总灯数"限制，成本变成"这一小块空间里有多少灯"。同一盏灯照亮 100 个簇和 10000 个簇，着色成本完全不同。

**代价**（也要讲清楚）：

| 代价 | 说明 |
|------|------|
| CPU 侧每帧构建 | 遍历所有可见灯做投影与分桶，是实打实的 CPU 开销 |
| 数据上传 | 簇 → 光源列表要作为存储缓冲上传到 GPU |
| 簇内列表有容量 | 单个簇能记录的光源数有上限，超出部分按距离/能量裁剪 —— 极端密集布光时仍会"丢灯" |
| 深度切片的分布 | 近处切得密、远处切得疏是这类方案的标准做法；具体层数与分布曲线由 `cluster_builder_rd.h` 的实现决定（以 4.3 源码为准） |

**源码锚点**：

```cpp
// Godot 4.3 源码 - servers/rendering/renderer_rd/forward_clustered/render_forward_clustered.h
class RenderForwardClustered : public RendererSceneRenderRD {
	// 簇（光源集合）的构建器
	ClusterBuilderRD *cluster_builder = nullptr;
	// ...
};
```

簇构建器本体在 `servers/rendering/renderer_rd/cluster_builder_rd.h` / `.cpp`。

**可以直接看到的证据**：编辑器的 `Viewport.DebugDraw` 里有一组**只在簇路径下才有意义**的项 —— `DEBUG_DRAW_CLUSTER_OMNI_LIGHTS`、`DEBUG_DRAW_CLUSTER_SPOT_LIGHTS`、`DEBUG_DRAW_CLUSTER_DECALS`、`DEBUG_DRAW_CLUSTER_REFLECTION_PROBES`。打开它们，屏幕上会画出每个簇里装了哪些灯。Mobile 与 Compatibility 没有簇，因此也没有这几项可视化。

> ⚠️ 再强调一次 §2.1 那条注记：**"每物体 8 盏灯"是 Mobile 的 per-object 上限（`MAX_RDL_CULL`），不是 Forward+ 的簇容量。** Forward+ 的簇本身不设"每个簇 8 盏"的硬上限（虽然每簇的列表容量有限，但那是溢出裁剪，不是固定配额）。

### 9.4 Mobile：逐对象光照

Mobile 渲染器**不建簇**。它对**每一个可见几何实例**单独收集"影响它的"灯：

| 步骤 | 做什么 |
|------|--------|
| ① 逐实例收集 | 对每个可见实例，按它的包围盒收集范围内的 omni / spot 灯、反射探针、贴花 |
| ② 截断 | 数量超过上限就裁掉 —— 上限是 `MAX_RDL_CULL = 8`（`forward_mobile/render_forward_mobile.h`） |
| ③ 写表 | 结果写进该实例的"光源索引表"，片元着色器按对象取列表 |

**与簇的差别，一句话讲清**：

| | Forward+（簇） | Mobile（逐对象） |
|---|---|---|
| 分桶依据 | **空间**（这块三维空间里有哪些灯） | **物体**（这个物体被哪些灯照到） |
| 光源上限 | 受簇列表容量限制，但与物体大小无关 | 硬上限 8，与物体大小无关 |
| 小物体远处 | 只要它所在簇有灯就能被照到 | 同样最多 8 盏，但**可能挤不进前 8** |
| 灯少而集中 | 成本按簇计，簇多 → 列表长 | 每个物体只算 1~2 盏，**更省** |
| 灯多而分散 | 簇各管一段，总成本可控 | 触顶，**远处物体丢灯** |

> 💡 **实践结论**：Mobile 场景的关键不是"总灯数"，而是"**同时影响同一个物体的灯数**"。如果你的场景是"一盏主光 + 几十盏装饰小灯均匀铺开"，逐对象方案会稳定在每物体 1~2 盏，很划算；如果是"一盏主光 + 一圈同处一室的强光"，很容易触顶 8 盏并出现"部分物体没被照到"的观感问题。

Mobile 的另一个取舍是**不做深度预通道**（第 14 篇会给出 Forward+ 与 Mobile 的 pass 序列表）。少一个 pass 省带宽，代价是透明物体后面的像素会被重复着色。

### 9.5 Compatibility：GLES3 通路

Compatibility 渲染器**完全绕开 `RenderingDevice`**：

| 层面 | Forward+ / Mobile | Compatibility |
|------|-------------------|---------------|
| 图形 API 抽象 | `RenderingDevice` → `RenderingDeviceDriver` → Vulkan 驱动 | 直接调 OpenGL |
| 场景端渲染实现 | `RenderForwardClustered` / `RenderForwardMobile` | GLES3 场景渲染器（`drivers/gles3/rasterizer_scene_gles3.h`） |
| 资源管理 | RD 资源（buffer / texture / sampler / uniform set） | GL 侧资源（`drivers/gles3/storage/`） |
| 上下文 | `RenderingContextDriverVulkan` 等 RD 上下文驱动 | GLES3 自己的上下文驱动（`drivers/gles3/`） |
| 着色器 | SPIR-V → RD shader module | GLSL ES → GL program |

**为什么它必须另开一条路**：Web 平台只提供 WebGL 2（OpenGL ES 3.0），没有 Vulkan，也没有 compute。`RenderingDevice` 的官方类参考写得很直白 —— **在 headless 模式或使用 Compatibility 渲染方法时，`RenderingDevice` 不可用**。所以 Compatibility 不是"Forward+ 的降级开关"，而是**另一套实现**。

**光照模型**：同样是**逐对象**，且同样有 8 盏的硬上限，只是这个上限由项目设置控制：

| 项目设置 | 类型 | 默认 | 作用 |
|----------|------|------|------|
| `rendering/limits/opengl/max_lights_per_object` | int | 8 | 单个物体可同时受影响的灯数上限（Compatibility 通路） |

> 想在 Compatibility 下验证"是不是触顶了 8 盏"，最简单的办法是把这个值临时调高，看画面是否变亮/变完整 —— 如果变了，说明之前确实被截断了。

### 9.6 Compatibility 的能力边界清单

| 能力 | Compatibility | 原因 |
|------|---------------|------|
| `RenderingDevice` | ❌ 不可用 | 不经过 RD 通路（官方类参考 Note） |
| Compute shader（`shader_type compute`） | ❌ 不可用 | GLES 3.0 无 compute |
| 存储缓冲 / UBO 的自定义布局 | ❌ 不可用 | 依赖 RD |
| `CompositorEffect`（自定义后处理） | ❌ 不可用 | 依赖 `RenderingDevice` |
| GPU 粒子（`GPUParticles3D` / `GPUParticles2D`） | ❌ 回退为 CPU 粒子 | 依赖 compute |
| SDFGI（`Environment.sdfgi_enabled`） | ❌ 不可用 | Forward+ 专属 |
| SSR（`Environment.ssr_enabled`） | ❌ 不可用 | RD 路径专属 |
| SSIL（`Environment.ssil_enabled`） | ❌ 不可用 | RD 路径专属 |
| 体积雾（`Environment.volumetric_fog_enabled`） | ❌ 不可用 | RD 路径专属 |
| 光照贴图烘焙（`LightmapGI`） | ✅ 可用 | 烘焙在 CPU 侧完成，与渲染器无关 |
| 体素 GI（`VoxelGI`） | ✅ 可用 | 同上 |
| 阴影（`DirectionalLight3D` 等） | ✅ 可用 | 走 GL 阴影贴图 |
| 泛光（`Environment.glow_enabled`） | ✅ 可用 | 走 GL 后处理 |
| 深度雾 / 高度雾 | ✅ 可用 | 走 GL 雾 |

> 💡 **一条实用的判断法**：凡是**需要读回上一帧或深度缓冲做屏幕空间计算**的特性（SSR / SSIL / SSAO / 体积雾），在 Compatibility 下基本都没有对应实现；凡是**在 CPU 侧或单次绘制内就能算完**的特性（阴影、烘焙光照、雾、泛光），都还在。迁移到 Web 时，按这条线评估工作量最快。

### 9.7 换渲染器时，哪些东西会变

| 项目 | 换渲染器后 | 说明 |
|------|-----------|------|
| 场景结构 | ❌ 不变 | 节点与资源完全复用 |
| `StandardMaterial3D` | ❌ 不变 | 材质不绑定渲染管线（见第 13 篇 2.4） |
| `.gdshader`（`shader_type spatial`） | ❌ 不变 | 同一套着色器语义 |
| `Environment` 上的 RD 专属开关 | ⚠️ **被忽略** | `sdfgi_enabled` / `ssr_enabled` / `ssil_enabled` / `volumetric_fog_enabled` 在 Compatibility 下不生效，且**不会报错** |
| `CompositorEffect` | ⚠️ **不执行** | 依赖 RD |
| GPU 粒子 | ⚠️ **回退** | 引擎改用 CPU 粒子实现 |
| `shader_type compute` | ⚠️ **加载失败** | 需要在导出前就分流 |
| 光照数量 | ⚠️ **可能触顶** | Compatibility 的 per-object 上限同样是 8 |
| 阴影质量 | ⚠️ 有差异 | 各渲染器的阴影实现细节不同（贴图尺寸、过滤方式） |

```gdscript
# 在运行时给出提示：当前渲染方法下哪些特性不可用
func warn_unsupported_features() -> void:
    var method: String = ProjectSettings.get_setting(
        "rendering/renderer/rendering_method", "forward_plus")
    if method == "compatibility":
        push_warning("当前为 Compatibility 渲染器：SDFGI / SSR / SSIL / 体积雾 / " +
            "CompositorEffect / compute shader 均不可用；GPU 粒子会回退为 CPU 粒子。")
```

> ⚠️ `rendering/renderer/rendering_method` 是**启动时读取**的设置，运行时改它不会切换渲染器。上面的代码只用于"启动后告知玩家当前处于哪种模式"，不能用来做运行时切换。

### 9.8 三种渲染器各自的调试入口

| 想要看什么 | Forward+ | Mobile | Compatibility |
|------------|----------|--------|---------------|
| 簇里装了哪些灯 | `Viewport.DebugDraw` 的簇相关项 | 无（没有簇） | 无（没有簇） |
| 光照结果 | `DEBUG_DRAW_LIGHTING` | `DEBUG_DRAW_LIGHTING` | `DEBUG_DRAW_LIGHTING` |
| 过绘 | `DEBUG_DRAW_OVERDRAW` | `DEBUG_DRAW_OVERDRAW` | `DEBUG_DRAW_OVERDRAW` |
| 阴影图集 | `DEBUG_DRAW_SHADOW_ATLAS` | `DEBUG_DRAW_SHADOW_ATLAS` | `DEBUG_DRAW_SHADOW_ATLAS` |
| 平行光级联 | `DEBUG_DRAW_PSSM_SPLITS` | `DEBUG_DRAW_PSSM_SPLITS` | `DEBUG_DRAW_PSSM_SPLITS` |
| SDFGI | `DEBUG_DRAW_SDFGI` / `DEBUG_DRAW_SDFGI_PROBES` | 无 | 无 |
| 逐 pass 耗时 | 编辑器 Visual Profiler（数据来自 C++ 层 `get_frame_profile()`） | 同左 | 同左 |
| 命令流 | RenderDoc / apitrace（Vulkan 下直接可用） | 同左 | 需 OpenGL 抓帧工具 |

> 抓帧工具的选择见**第 22 篇《渲染调试工具》**。这里只强调一条：**Visual Profiler 与 `Viewport.DebugDraw` 组合使用效率最高** —— 前者告诉你"哪一步慢"，后者告诉你"这一步算出来对不对"。

---

## 📝 本章总结

### 关键术语

| 术语 | 解释 |
|------|------|
| Vulkan | 现代跨平台图形 API，低开销、显式控制 |
| Clustered Forward | 集群前向渲染，高效处理多光源 |
| SDFGI | 符号距离场全局光照，实时 GI 解决方案 |
| RenderingServer | Godot 渲染系统的核心接口 |
| 绘制调用 (Draw Call) | CPU 向 GPU 发送的渲染命令 |

## 核心要点

1. **Godot 4.x 的渲染架构是三层**：场景端（主线程，剔除与排序）+ `RenderingServer`（常驻服务）+ 图形抽象层（`RenderingDevice` → `RenderingDeviceDriver` → 具体后端）。
2. **只有 `RENDER_SEPARATE_THREAD` 才真的开渲染线程**；4.3 的默认是 `RENDER_THREAD_SAFE`，渲染与主线程同线程。
3. **剔除与排序在主线程完成**，渲染线程拿到的是已经筛好的扁平列表，因此剔除开销一定计入主线程帧时间。
4. **`RenderingServer.get_frame_profile()` 在 4.3 未导出为脚本方法**，逐 pass 耗时要看编辑器 Visual Profiler；脚本侧只能拿计数器。
5. **Forward+ 用簇分配、Mobile 用逐对象光照、Compatibility 也是逐对象** —— 这是三种渲染器最本质的机制差异。
6. **"每物体 8 盏灯"是 Mobile 与 Compatibility 的 per-object 上限**，不是 Forward+ 的簇容量。
7. **Compatibility 是另一套实现而不是降级开关**：不经过 `RenderingDevice`，因此 compute、`CompositorEffect`、GPU 粒子、SSR / SSIL / 体积雾全部不可用。
8. **换渲染器时场景与材质不用动**，但 `Environment` 上的 RD 专属开关会被静默忽略，迁移前要逐项核对。

---

## 🔗 延伸阅读

- **官方文档**: [渲染器总览（Renderers）](https://docs.godotengine.org/en/stable/tutorials/rendering/renderers.html)
- **类参考**: [RenderingServer](https://docs.godotengine.org/en/stable/classes/class_renderingserver.html)、[RenderingDevice](https://docs.godotengine.org/en/stable/classes/class_renderingdevice.html)、[Environment](https://docs.godotengine.org/en/stable/classes/class_environment.html)、[ProjectSettings](https://docs.godotengine.org/en/stable/classes/class_projectsettings.html)
- **Vulkan 规范**: [Khronos Vulkan Specification](https://www.khronos.org/vulkan/)
- **源码位置**: `servers/rendering/`、`servers/rendering/renderer_rd/`、`servers/rendering/renderer_rd/cluster_builder_rd.h`（簇构建）、`drivers/gles3/`（Compatibility 通路）
- **技术博客**: [Godot 4.0 Rendering Deep Dive](https://godotengine.org/article/godot-4-0-rendering-deep-dive/)

---

## 📋 下一章预告

**第 12 篇：Vulkan 渲染后端深度解析**

- Vulkan 驱动在 4.3 的两个类：上下文侧与设备侧
- `RenderingDevice` / `RenderingDeviceDriver` 抽象与 RD 实战
- 命令队列、命令池与"屏障自动插入"
- uniform set 资源布局、纹理格式与用法位、显存与堆
- 从 SPIR-V 到一次 compute 派发的完整路径

---

*写作时间：2026-03-20*  
*字数：约 3,300 字（不含代码块）（不含代码块）*  
*状态：✅ 完成*

**Godot 版本**: 4.x（基线 4.3；本文涉及的 4.4+ 差异已在行内标注）

---

**上一篇**: [第 53 篇：输入系统](/articles/53-input-system.md)
**下一篇**: [第 12 篇：Vulkan 渲染后端深度解析](/articles/12-vulkan-backend.md)
