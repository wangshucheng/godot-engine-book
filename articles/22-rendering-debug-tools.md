# 深入理解 Godot 引擎 #22 | 渲染调试工具

> **摘要**：Godot 提供多种渲染调试工具。本文将分析 Debug 模式、可视化器、性能监控。

---

## 一、Debug 模式

### 1.1 渲染 Debug

```gdscript
# 启用渲染 Debug
ProjectSettings.set("debug/settings/visible_collision_shapes", true)
ProjectSettings.set("debug/settings/visible_navigation", true)

# 渲染统计
var stats = Performance.get_monitor(Performance.RENDER_TOTAL_OBJECTS_IN_FRAME)
print("渲染对象数：", stats)
```

### 1.2 Debug 选项

| 选项 | 说明 |
|------|------|
| **Collision Shapes** | 显示碰撞体 |
| **Navigation** | 显示导航网格 |
| **LOD** | 显示 LOD 层级 |
| **Wireframe** | 线框模式 |

---

## 二、可视化器

### 2.1 渲染可视化

```gdscript
# 线框模式
get_viewport().debug_draw = Viewport.DEBUG_DRAW_WIREFRAME

# 无光照模式
get_viewport().debug_draw = Viewport.DEBUG_DRAW_UNSHADED

# 光照模式
get_viewport().debug_draw = Viewport.DEBUG_DRAW_LIGHTING
```

### 2.2 可视化类型

| 类型 | 说明 |
|------|------|
| **Wireframe** | 线框显示 |
| **Unshaded** | 无光照 |
| **Lighting** | 光照显示 |
| **Overdraw** | 过度绘制 |

---

## 三、性能监控

### 3.1 性能监控器

```gdscript
# 获取性能数据
var fps = Performance.get_monitor(Performance.TIME_FPS)
var draw_calls = Performance.get_monitor(Performance.RENDER_TOTAL_DRAW_CALLS)
var objects = Performance.get_monitor(Performance.RENDER_TOTAL_OBJECTS_IN_FRAME)

print("FPS: ", fps)
print("Draw Calls: ", draw_calls)
print("Objects: ", objects)
```

### 3.2 性能指标

| 指标 | 说明 | 目标 |
|------|------|------|
| **FPS** | 帧率 | 60 |
| **Draw Calls** | 绘制调用 | <500 |
| **Objects** | 渲染对象 | <2000 |
| **Video Mem** | 显存占用 | <2GB |

---

## 四、Vulkan 调试层

### 4.1 启用 Vulkan 调试

```gdscript
# 启用 Vulkan 验证层
ProjectSettings.set("rendering/vulkan/debug_layers", true)

# 启用 Vulkan 同步
ProjectSettings.set("rendering/vulkan/sync_mode", 1)
```

### 4.2 调试输出

```
Vulkan Validation Layer:
- 检查 API 使用错误
- 检查资源泄漏
- 检查性能问题
```

---

## 五、第二卷总结

### 5.1 已完成内容

✅ 11: Godot 渲染架构概述  
✅ 12: Vulkan 渲染后端  
✅ 13: Godot vs Unity 渲染对比  
✅ 14: 场景渲染流程  
✅ 15: 光照系统  
✅ 16: 材质系统  
✅ 17: GDShader 语言  
✅ 18: 2D 渲染  
✅ 19: 后处理效果  
✅ 20: 粒子渲染  
✅ 21: 性能优化  
✅ 22: 渲染调试工具  

### 5.2 核心知识点

| 主题 | 核心概念 |
|------|---------|
| **架构** | RenderingServer、Vulkan |
| **光照** | 光源类型、阴影、SDFGI |
| **材质** | StandardMaterial3D、PBR |
| **Shader** | GDShader、Spatial、CanvasItem |
| **2D** | CanvasItem、合批 |
| **后处理** | Bloom、DOF、SSAO |
| **粒子** | GPU 粒子、发射器 |
| **优化** | DrawCall、LOD、遮挡剔除 |
| **调试** | Profiler、可视化器 |

---

## 六、总结

### 核心要点

1. **Debug 模式**：碰撞、导航、LOD
2. **可视化器**：线框、光照、Overdraw
3. **性能监控**：FPS、DrawCall、Objects
4. **Vulkan 调试**：验证层、同步模式

### 下一卷

**第三卷**: 脚本与虚拟机（8 篇）

---

**作者**: 王飞书  
**首发平台**: 微信公众号  
**写作时间**: 2026 年 3 月  
**Godot 版本**: 4.3（最新稳定版）

---

**上一篇**: [深入理解 Godot 引擎 #21 | 性能优化](#)  
**下一篇**: [深入理解 Godot 引擎 #23 | GDScript 虚拟机](#)

---

**第二卷 完**

*如果你觉得这篇文章有帮助，欢迎转发给更多开发者！*
