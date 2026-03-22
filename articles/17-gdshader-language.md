# 深入理解 Godot 引擎 #17 | GDShader 语言

> **摘要**：GDShader 是 Godot 的 Shader 语言。本文将深入分析 Shader 类型、语法、编写技巧。

---

## 一、Shader 类型

### 1.1 Shader 类型

| 类型 | 说明 | 使用场景 |
|------|------|---------|
| **Spatial** | 3D Shader | 3D 模型、地形 |
| **CanvasItem** | 2D Shader | 2D 精灵、UI |
| **Particles** | 粒子 Shader | 粒子系统 |

### 1.2 Shader 结构

```glsl
shader_type spatial;
render_mode unshaded;

uniform vec4 albedo : source_color;
uniform float metallic;
uniform float roughness;

void vertex() {
    // 顶点处理
}

void fragment() {
    // 片元处理
    COLOR = albedo;
}
```

---

## 二、Shader 语法

### 2.1 变量类型

```glsl
// 基本类型
float value;
vec2 uv;
vec3 color;
vec4 position;

//  uniform 变量
uniform float speed;
uniform vec3 light_color;
uniform sampler2D texture;

// 内置变量
varying vec2 v_uv;
varying vec3 v_normal;
```

### 2.2 内置函数

```glsl
// 数学函数
float result = sin(value);
vec3 normalized = normalize(vector);
float dot_product = dot(a, b);

// 纹理采样
vec4 color = texture(albedo_texture, UV);
vec4 normal = texture(normal_texture, UV);
```

---

## 三、Shader 示例

### 3.1 水波效果

```glsl
shader_type spatial;

uniform float wave_speed = 1.0;
uniform float wave_height = 0.5;

void vertex() {
    float wave = sin(VERTEX.x * 2.0 + TIME * wave_speed) * wave_height;
    VERTEX.y += wave;
}

void fragment() {
    ALBEDO = vec3(0.0, 0.5, 1.0);
}
```

### 3.2 溶解效果

```glsl
shader_type spatial;

uniform sampler2D noise_texture;
uniform float dissolve_amount : hint_range(0, 1);

void fragment() {
    float noise = texture(noise_texture, UV).r;
    if (noise < dissolve_amount) {
        discard;
    }
    ALBEDO = vec3(1.0, 0.0, 0.0);
}
```

---

## 四、Shader 优化

### 4.1 优化技巧

| 技巧 | 说明 |
|------|------|
| **减少纹理采样** | 合并纹理通道 |
| **简化计算** | 使用近似函数 |
| **LOD** | 远距离简化 Shader |
| **Instancing** | GPU 实例化 |

### 4.2 性能对比

| Shader 复杂度 | GPU 占用 | 帧率 |
|------------|---------|------|
| 简单 | 10% | 120 FPS |
| 中等 | 30% | 60 FPS |
| 复杂 | 80% | 30 FPS |

---

## 五、总结

### 核心要点

1. **Shader 类型**：Spatial、CanvasItem、Particles
2. **语法**：uniform、varying、内置函数
3. **示例**：水波、溶解效果
4. **优化**：减少采样、简化计算

### 下一篇

**下一篇**: 2D 渲染

---

**作者**: 王飞书  
**首发平台**: 微信公众号  
**写作时间**: 2026 年 3 月  
**Godot 版本**: 4.3（最新稳定版）

---

**上一篇**: [深入理解 Godot 引擎 #16 | 材质系统](#)  
**下一篇**: [深入理解 Godot 引擎 #18 | 2D 渲染](#)

---

*如果你觉得这篇文章有帮助，欢迎转发给更多开发者！*
