# 深入理解 Godot 引擎 #14 | 场景渲染流程

> **摘要**：场景渲染是 Godot 渲染系统的核心。本文将深入分析场景渲染流程、剔除、排序、合批。

---

## 一、场景渲染流程

### 1.1 渲染流程概述

```
1. 场景更新
   ↓
2. 可见性剔除
   ↓
3. 渲染排序
   ↓
4. 合批处理
   ↓
5. 生成渲染指令
   ↓
6. 提交 GPU
   ↓
7. 显示
```

### 1.2 源码位置

**源码位置**: `servers/rendering/renderer_scene_render.cpp`

```cpp
// Godot 源码 - renderer_scene_render.cpp
class RendererSceneRender : public Singleton {
    // 渲染场景
    virtual void _render_scene() = 0;
    
    // 剔除
    virtual void _cull_objects() = 0;
    
    // 排序
    virtual void _sort_objects() = 0;
    
    // 合批
    virtual void _batch_objects() = 0;
};
```

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

---

## 三、渲染排序

### 3.1 排序规则

| 规则 | 说明 |
|------|------|
| **材质排序** | 相同材质合并 |
| **深度排序** | 从前到后/从后到前 |
| **透明度排序** | 透明物体特殊处理 |

### 3.2 排序优化

```cpp
// 材质批次排序
sort(render_list, [](a, b) {
    if (a.material != b.material) {
        return a.material < b.material;  // 材质优先
    }
    return a.depth < b.depth;  // 深度次之
});
```

---

## 四、合批处理

### 4.1 合批类型

| 类型 | 说明 |
|------|------|
| **静态合批** | 静态物体合并 |
| **动态合批** | 动态物体合并 |
| **GPU 合批** | GPU Instancing |
| **材质合批** | 相同材质合并 |

### 4.2 合批效果

| 场景 | 合批前 | 合批后 | 优化 |
|------|--------|--------|------|
| **简单** | 100 DrawCall | 20 DrawCall | 80% |
| **中等** | 500 DrawCall | 100 DrawCall | 80% |
| **复杂** | 2000 DrawCall | 400 DrawCall | 80% |

---

## 五、总结

### 核心要点

1. **渲染流程**：剔除→排序→合批→渲染
2. **剔除优化**：减少渲染对象
3. **排序优化**：减少状态切换
4. **合批优化**：减少 DrawCall

### 下一篇

**下一篇**: 光照系统

---

**作者**: 王飞书  
**首发平台**: 微信公众号  
**写作时间**: 2026 年 3 月  
**Godot 版本**: 4.3（最新稳定版）

---

**上一篇**: [深入理解 Godot 引擎 #13 | Godot vs Unity 渲染对比](#)  
**下一篇**: [深入理解 Godot 引擎 #15 | 光照系统](#)

---

*如果你觉得这篇文章有帮助，欢迎转发给更多开发者！*
