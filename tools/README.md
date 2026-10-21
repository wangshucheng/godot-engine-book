# 书稿自动门禁

本书是**纯内容仓库**（docsify），没有构建也没有测试。`tools/` 下的工具把评审报告 §6.3
建议的 5 条门禁固化成了可重复执行的脚本：

| 规则组 | 抓什么 | 对应报告条目 |
|---|---|---|
| `structure` | 代码围栏不闭合 / 表格列数不一致 / 内部链接断链（含 README、封面、首页）/ 裸 LF 行尾 / 篇末四件套缺失 | §6.3「链接与围栏检查」 |
| `syntax` | GDScript **解析期**错误：`extends` 位置与条数、重复 `func`、**成员遮蔽父类属性**、括号不配对、tab 与空格混用 | §6.3「GDScript 片段语法检查」 |
| `api` | 代码块与正文里引用的 Godot 类 / 方法 / 属性 / 常量 / 枚举是否真实存在于基线版本的官方类参考 | §6.3「API 存在性检查」 |
| `stats` | README 与封面的统计读数是否与书稿实测一致 | §6.3「统计读数校验」 |
| `perf` | 性能读数是否带测试条件或「示意数据」标注 | §6.3「性能数字标注检查」 |

## 快速使用

```bash
python tools/verify_book.py                # 跑全部规则（CI 里跑的就是这条）
python tools/verify_book.py --rules api    # 只跑 API 存在性
python tools/verify_book.py --rules structure
python tools/verify_book.py --selftest     # 判据自检（阳性对照）
python tools/verify_book.py --report out.txt
```

退出码：`0` 全通过；`1` 有 error；`2` 门禁自身出错（缺索引等）。

## 文件

| 文件 | 作用 |
|---|---|
| `tools/verify_book.py` | 门禁本体 |
| `tools/godot_api_index.json` | Godot **4.7.2** 官方类参考索引（由 `doc/classes/*.xml` + `modules/*/doc_classes/*.xml` + `platform/*/doc_classes/*.xml` 派生；4.7.2 起 `editor/doc_classes/` 已并入 `doc/classes/`） |
| `tools/fetch_godot_api.py` | 重新抓取官方类参考并重建索引（换版本 / 升基线时用） |
| `tools/api_allowlist.txt` | 白名单：书里**有意提及**的、不存在于基线版本的符号（按 4.7.2 对账，符号进基线就必须删条目） |
| `tools/check_gdscript_syntax.py` | 把「自称是完整脚本」的 GDScript 块喂给 `godot --headless --check-only`（咨询性，见下） |

## `syntax` 规则组抓什么

GDScript **解析期**错误——脚本根本加载不了的那一类：

| # | 规则 | 备注 |
|---|---|---|
| ① | `extends` 不是脚本第一条语句 / 出现多条 | 只认**列 0** 的 `extends`（缩进的属内层类） |
| ② | 同一段完整脚本里 `func` 重名 | 只在「自称完整脚本」（有脚本级 extends）的块里报 |
| ③ | **成员遮蔽父类属性** | `extends X` 的类体里 `var name` 与 `X` 的属性同名 → 脚本报 "Member xxx already exists in parent class" 而**加载失败** |
| ④ | 括号 / 方括号 / 花括号不配对 | 注释与字符串（含三引号多行串）先清空再统计 |
| ⑤ | 缩进里 tab 与空格混用 | GDScript 只认一种缩进 |

> 作用域要分清：**类成员**遮蔽父类属性是错误；**函数内的局部变量**遮蔽成员只是
> `shadowed_variable` 警告，不算错。规则按「作用域开启者」栈判定。

### 行尾规则为什么分平台

仓库里存的是 **LF**（git 在 `core.autocrlf=true` 下入库时规范化），**Windows 检出时才是 CRLF**。
所以 `structure` 规则这样分：

- **任何平台都是错**：行尾**混用**（一部分 CRLF 一部分 LF）、单独的 CR；
- **仅 Windows 本地查**：文件必须是 CRLF（工作区约定）。Linux CI 检出的是 LF，不该判错。

用环境变量 `GODOT_BOOK_CRLF=on|off` 可显式覆盖（默认按平台自动判断）。

## Godot 语法级检查（咨询性）

```bash
python tools/check_gdscript_syntax.py                  # 只报告，不检查
python tools/check_gdscript_syntax.py --godot /path/to/godot
GODOT_BIN=/path/to/godot python tools/check_gdscript_syntax.py
```

**如实说明覆盖范围**：全书 978 个 ```gdscript 块里，只有 **27** 个首行是 `extends` / `class_name`，
其余是**教学片段**（缺上下文、缺父类、甚至缺 `extends`），
`--check-only` 要求完整脚本，对它们**不适用**——强行检查只会得到满屏误报。

所以 CI 里它是**手动触发**（`workflow_dispatch` 的 `godot_check` 输入）且 `continue-on-error`，
**不阻断合并**；能跑的那 27 个块里，报 "Identifier not found" 往往是因为它引用了本篇其它
代码块的定义，也不一定是真错误。


## 索引从哪来

`tools/godot_api_index.json` 由 `tools/fetch_godot_api.py` 生成，流程是：

1. 列出 `godotengine/godot@4.7.2-stable` 下的全部类参考 XML（1078 个：`doc/classes/` 810 + `modules/*/doc_classes/` 261 + `platform/*/doc_classes/` 7）；
2. 并行下载（优先 `cdn.jsdelivr.net`，回落 `github.com/raw`；
   `raw.githubusercontent.com` 在部分网络下不可达，别用它）。
   **实测可达性会变**：曾遇到 `cdn.jsdelivr.net` 也不通、但 `gcore.jsdelivr.net` 正常
   （约 1–2s/文件）；`fastly.jsdelivr.net` 可用但慢（约 20s/文件）。
   抓取脚本已内建回落分支，遇到超时先重跑一次通常即可；
3. 解析成紧凑索引：每个类一行，记方法 / 属性 / 信号 / 常量 / 枚举 / 属性类型。

> **抓完必须与官方源逐字节比对**再拿去当判据底座——本轮用 `git clone --depth 1 --filter=blob:none --sparse`
> 取到同一 tag 提交（`ed1daf0`）的官方 blob，与 CDN 路径下载的 **120 个重叠文件逐字节全部一致**（0 处不一致）。
>
> **GitHub 代码搜索不能当「不存在」的证据**：它对 `group_uniforms` 返回 0 命中，
> 而该关键字在基线版本里确实存在。「不存在」的结论要以**本地下载的源码全文检索**为准。


> **坑点提醒**：Godot 4.7.2 的类 XML **仍然没有 `<enums>` 段**——枚举成员写在 `<constants>` 里，
> 用 `enum="枚举名"` 属性标注所属枚举。只解析 `<enums>` 会导致所有枚举**类型名**
> （如 `DirectionalLight3D.ShadowMode`、`Viewport.DebugDraw`）查不到。
> 解析器保留了 `<enums>` 分支只是为了向前兼容，但它不是当前格式。

重建索引：

```bash
python tools/fetch_godot_api.py                  # 4.7.2-stable（默认）
python tools/fetch_godot_api.py --tag 4.6-stable  # 换基线
python tools/fetch_godot_api.py --index-only      # 只重建，不重下
```

## 判据必须自证有牙

`--selftest` 用一组**已知的历史 P0** 做阳性对照：

- `extends LOD3D`（基线版本无此类）
- `DirectionalLight3D.shadow_max_distance` / `shadow_orthogonal_size`（不存在）
- `LightmapGI.bake_mode`（不存在）
- `LightmapGI.light_data = "res://x.gi"`（类型错，属性是 `LightmapGIData` 资源）
- `EditorResourceImporter.new()`（不存在）
- `Performance.RENDER_TOTAL_DRAW_CALLS`（常量名错）
- `ResourceSaver.save_to_buffer()`（4.3 到 4.7.2 全都没有）
- 以及 3 个**阳性对照**（`directional_shadow_mode`、`Performance.RENDER_TOTAL_DRAW_CALLS_IN_FRAME`、
  `light_color = Color(...)` 必须**不报**）

判据本身出问题时，`--selftest` 会先红。

## 白名单纪律

`tools/api_allowlist.txt` 只允许收「书里有意提及」的符号，每条必须写明依据：

| 类别 | 例子 |
|---|---|
| C++ 引擎内部类型 | `ObjectID`、`MethodBind`、`RendererSceneCull`、`SCsub` |
| 书里写明「基线里没有」的反例 | `ResourceLoader.unload`、`AudioServer.set_hrtf_enabled`、`use_1d_color_correction` |
| 3.x 已移除（迁移对照） | `ParticleShape3D`、`KinematicBody`、`WebSocketServer` |
| Unity 侧 API | `MonoBehaviour`、`ScriptableRenderPipeline` |
| 书里写「4.x 没有这个 API」的反例 | `ResourceLoader.unload`、`AudioServer.set_hrtf_enabled` |
| 书稿示例里的自定义方法/信号 | `_get_or_create_metrics`、`peer_connected` |

⚠️ **把真实缺陷放进白名单等于关掉门禁**。新增条目前请先确认它确实是「有意提及」，
而不是「写错了」。

## 换基线的实际流程（4.3 → 4.7.2 这一轮踩过的坑）

1. **先看 tag 存不存在**：`https://api.github.com/repos/godotengine/godot/tags` 能一次列全。
   `4.7.2-stable` 是 tag 名，版本号 `4.7.2` 才是书里写的基线号。
2. **缓存必须按 tag 隔离**：`.audit-tmp/classxml/<tag>/`。老版本只按「路径」命名缓存时，
   换基线会把旧 XML 当成 `cached` 直接命中，两个版本的类参考混进同一个索引——判据底座静默失真。
3. **类参考清单不要只靠 tree API**：它的递归响应有 1MB+，本机链路会在传输中途断流
   （`http.client.IncompleteRead`）。清单落盘到 `.audit-tmp/classxml/<tag>.paths.json` 并带重试；
   兜底可用 contents API 逐目录列举（注意 `modules/*/doc_classes/` 有个别模块会漏，
   最终以 `git ls-tree` 的 1078 条为准）。
4. **镜像要轮转**：`raw.githubusercontent.com` 常超时，`cdn.jsdelivr.net` 时通时不通；
   脚本内置 `github.com/.../raw` → `gcore.jsdelivr.net` → `fastly.jsdelivr.net` → `cdn.jsdelivr.net` 逐个回落。
5. **网络实在拉不动时用 git**：`git clone --depth 1 --filter=blob:none --sparse --branch <tag>`
   再 `git sparse-checkout set --no-cone '/doc/classes/*' '/modules/*/doc_classes/*' ...`，
   一次 pack 传输比上千个 HTTP 请求稳；然后**必须与 CDN 版逐字节比对**再当判据底座。
6. **换完基线先跑 `--selftest`**：阳性对照必须在新基线下**依然成立**，
   否则说明判据本身失效了（而不是书稿错了）。
7. **白名单要重新对账**：符号一旦进入基线，对应条目必须删除——
   否则就等于给「门禁不再检查这个符号」留了后门。
8. **书稿里每条「某版本没有 X」都要重判**：基线一换，这些断言的真值会变。
   判据是本地官方 XML + 官方源码，不是记忆。

## 统计口径

`--rules stats` 的口径（README / 封面必须与之一致）：

- **正文中文字** = 剔除代码围栏后的 CJK 汉字（U+4E00–U+9FFF）
- **代码行** = **带语言标记**的代码块内的非空行（不含围栏本身）
- **代码块** = 全部 ``` 围栏（另计带语言标记的个数）
- **示意图** = 含制表符画框线的图示块（≥3 行连续）
- **表格** = 正文中的 Markdown 表格块

## CI

`.github/workflows/book-check.yml` 在 push / PR 时自动跑：

1. `--selftest`（判据自检）
2. 全量门禁，并上传报告工件

> 仓库 `core.autocrlf=true` 且没有 `.gitattributes`，工作区约定 **CRLF**。
> 改稿后请确认行尾没被写成 LF（`structure` 规则会判红）。
