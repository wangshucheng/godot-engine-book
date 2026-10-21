#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""verify_book.py —— 《深入理解 Godot 引擎》书稿自动门禁

用法:
    python tools/verify_book.py                # 跑全部规则
    python tools/verify_book.py --rules api    # 只跑 API 存在性
    python tools/verify_book.py --selftest     # 跑判据自检（阳性对照）
    python tools/verify_book.py --report out.txt

规则组:
    structure  围栏闭合 / 表格列数 / 内部链接 / 行尾 / 篇末四件套
    api        代码块与正文里的 Godot API 是否真实存在（比对基线版本的官方类参考）
    stats      README / 封面的统计读数是否与书稿实测一致
    perf       性能数字是否带测试条件或「示意数据」标注

退出码: 0 = 全通过；1 = 有 error 级问题；2 = 门禁自身出错。
"""
from __future__ import annotations

import argparse
import io
import json
import os
import re
import sys
from dataclasses import dataclass, field

sys.stdout.reconfigure(encoding="utf-8")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARTICLES = os.path.join(ROOT, "articles")
INDEX_PATH = os.path.join(ROOT, "tools", "godot_api_index.json")
ALLOW_PATH = os.path.join(ROOT, "tools", "api_allowlist.txt")

FENCE_RE = re.compile(r"^```([A-Za-z0-9_+#.-]*)\s*$", re.M)
INLINE_RE = re.compile(r"`([^`\n]{1,80})`")
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
CLASS_TOKEN_RE = re.compile(r"^[A-Z][A-Za-z0-9]*$")
UPPER_CONST_RE = re.compile(r"^[A-Z][A-Z0-9_]*$")

# 工作区行尾约定：仓库内是 LF（git 规范化），Windows 检出时是 CRLF（core.autocrlf=true）。
# 「必须 CRLF」只对 Windows 本地有意义；在 Linux CI 上检出的是 LF，不该判错。
# 可用环境变量 GODOT_BOOK_CRLF=on|off 显式覆盖（默认按平台自动判断）。
_crlf_mode = os.environ.get("GODOT_BOOK_CRLF", "").strip().lower()
if _crlf_mode in ("0", "off", "false", "no"):
    REQUIRE_CRLF = False
elif _crlf_mode in ("1", "on", "true", "yes"):
    REQUIRE_CRLF = True
else:
    REQUIRE_CRLF = os.name == "nt"

# GDScript 语言层内建函数（不在官方类参考的 @GlobalScope 里）
LANG_BUILTINS = set(
    """
    assert bool dict float int len load preload range str type
    """.split()
)

# GDScript 关键字（不是调用）
GDSCRIPT_KEYWORDS = set(
    """
    if elif else for while match when break continue pass return await
    and or not in is as self super class class_name extends signal enum
    func static const var export onready tool rpc rpc_id annotation
    abstract breakpoint preload
    """.split()
)

# GDScript 注解（`@export_group(...)` 之类，不是方法调用）
GDSCRIPT_ANNOTATIONS = set(
    """
    export export_category export_group export_subgroup export_range export_file
    export_enum export_flags export_flags_2d_navigation export_storage
    export_custom onready tool icon rpc rpc_id static_unload warning_ignore
    abstract noshadows
    """.split()
)

# Unity 侧 API：书稿里用于对比，不是 Godot 类
UNITY_API = {
    "MonoBehaviour", "GameObject", "Transform", "Vector3", "Vector2", "Quaternion",
    "Awake", "Start", "Update", "FixedUpdate", "LateUpdate", "OnDestroy",
    "OnEnable", "OnDisable", "SceneManager", "DontDestroyOnLoad", "Resources",
    "Destroy", "Instantiate", "Set", "Get", "GetComponent", "AddComponent",
    "Find", "FindObjectOfType", "Camera", "Light", "Renderer", "Material",
    "Shader", "Texture2D", "Animator", "Animation", "Coroutine", "WaitForSeconds",
    "Debug", "Time", "Input", "PlayerPrefs", "Application", "Object", "Component",
    "ScriptableObject", "SerializeField", "RequireComponent", "ExecuteInEditMode",
    "LayerMask", "Physics", "Rigidbody", "Collider", "MeshRenderer",
    "MeshFilter", "BoxCollider", "SphereCollider", "Rigidbody2D",
    "BoxCollider2D", "SpriteRenderer", "Sprite", "AudioSource", "AudioClip",
    "Canvas", "CanvasGroup", "Image", "Text", "Button", "Toggle", "Slider",
    "InputField", "ScrollRect", "AnimationClip", "QualitySettings",
    "Screen", "UnityEngine", "System", "Mathf", "Editor", "MenuItem",
    "SerializeReference", "Header", "Tooltip", "Space", "Range", "ContextMenu",
    "RuntimeInitializeOnLoadMethod", "Scene", "BuildPipeline", "PlayerSettings",
    "EditorUtility", "AssetDatabase", "Prefab", "Mesh", "Renderer2D",
}

# 看起来像文件名/路径的词尾
FILE_EXTS = {
    "xml", "gd", "tscn", "scn", "res", "tres", "cs", "cpp", "h", "hpp", "json",
    "yml", "yaml", "ini", "cfg", "conf", "txt", "md", "png", "jpg", "svg", "webp",
    "wav", "ogg", "mp3", "pck", "so", "dll", "gdextension", "import", "godot",
    "shader", "gdshader", "glsl", "hlsl", "bat", "ps1", "zip", "sub",
    "plist", "framework", "dylib", "bundle", "app", "xcconfig", "pbxproj",
    "entitlements", "a", "lib", "exe", "apk", "aab", "ipa", "wasm",
}

BUILTIN_TYPE_NAMES = {
    "Variant", "Nil", "bool", "int", "float", "String", "StringName", "NodePath",
    "Object", "Callable", "Signal", "RID", "Array", "Dictionary", "PackedByteArray",
    "PackedInt32Array", "PackedInt64Array", "PackedFloat32Array",
    "PackedFloat64Array", "PackedStringArray", "PackedVector2Array",
    "PackedVector3Array", "PackedColorArray", "PackedVector4Array",
    "Error", "Dictionary", "PackedStringArray",
}

# 裸属性访问只校验这一组高频属性，避免把局部变量误判成引擎成员
COMMON_PROPERTIES = {
    "position", "global_position", "rotation", "rotation_degrees", "scale",
    "visible", "hidden", "name", "owner", "modulate", "self_modulate",
    "z_index", "texture", "size", "global_rotation", "global_scale",
    "process_mode", "material_override", "mesh", "skeleton", "animation",
    "autoplay", "volume_db", "pitch_scale", "loop", "playing", "energy",
    "shadow_enabled", "light_energy", "light_color", "text", "pressed",
    "disabled", "min_value", "max_value", "step", "albedo", "roughness",
    "metallic", "emission_enabled", "emission", "cull_mask", "cast_shadow",
    "light_size", "omni_range", "spot_range", "spot_angle", "shadow_bias",
    "shadow_normal_bias", "light_bake_mode", "gi_mode", "texture_normal",
    "texture_albedo", "distance_fade_enabled",
}


# --------------------------------------------------------------------------- #
# 基础工具
# --------------------------------------------------------------------------- #
def strip_comment(line: str) -> str:
    out = []
    in_str = False
    quote = ""
    for ch in line:
        if in_str:
            out.append(ch)
            if ch == quote:
                in_str = False
            continue
        if ch in "\"'":
            in_str = True
            quote = ch
            out.append(ch)
            continue
        if ch == "#":
            break
        out.append(ch)
    return "".join(out)


def strip_strings(line: str) -> str:
    out = []
    in_str = False
    quote = ""
    for ch in line:
        if in_str:
            if ch == quote:
                in_str = False
                out.append(ch)
            else:
                out.append(" ")
            continue
        if ch in "\"'":
            in_str = True
            quote = ch
            out.append(ch)
            continue
        out.append(ch)
    return "".join(out)


def strip_code(code: str) -> str:
    """整块地去掉**注释内容**与**字符串内容**，保留行数与列宽。

    必须单遍扫描：注释与字符串会互相干扰（`#` 在字符串里不是注释，
    而注释里的引号又不该开启字符串状态）。同时支持三引号多行串
    （书稿里常见 `var t := ...` 的代码模板）。
    """
    out = []
    i = 0
    n = len(code)
    state = None  # None | '"' | "'" | '"""' | "'''"
    while i < n:
        ch = code[i]
        if state is None:
            if code.startswith('"""', i) or code.startswith("'''", i):
                state = code[i:i + 3]
                out.append("   ")
                i += 3
                continue
            if ch in "\"'":
                state = ch
                out.append(" ")
                i += 1
                continue
            if ch == "#":
                j = code.find("\n", i)
                if j < 0:
                    j = n
                out.append(" " * (j - i))
                i = j
                continue
            out.append(ch)
            i += 1
            continue
        if len(state) == 3:
            if code.startswith(state, i):
                out.append("   ")
                i += 3
                state = None
                continue
        else:
            if ch == "\\":
                nxt = code[i + 1:i + 2]
                out.append("\n" if nxt == "\n" else " ")
                out.append("\n" if nxt == "\n" else " ")
                i += 2
                continue
            if ch == state:
                out.append(" ")
                i += 1
                state = None
                continue
        out.append("\n" if ch == "\n" else " ")
        i += 1
    return "".join(out)


def strip_strings_and_comments(line: str) -> str:
    return strip_strings(strip_comment(line))


@dataclass
class Finding:
    rule: str
    severity: str
    file: str
    line: int
    message: str
    token: str = ""

    def key(self) -> str:
        return f"{self.rule}|{self.token}"


@dataclass
class Book:
    finding_list: list = field(default_factory=list)

    def add(self, rule, severity, file, line, message, token=""):
        self.finding_list.append(
            Finding(rule, severity, file, line, message, token)
        )


# --------------------------------------------------------------------------- #
# 索引
# --------------------------------------------------------------------------- #
class ApiIndex:
    def __init__(self, path: str):
        with io.open(path, encoding="utf-8") as f:
            raw = json.load(f)
        self.version = raw.get("version", "?")
        self.classes = raw["classes"]
        self.global_members = set(raw.get("global", {}).get("m", "").split())
        self.global_constants = set(raw.get("global", {}).get("c", "").split())
        self.singletons = raw.get("singletons", {})
        self._cache: dict = {}
        # 语言层内建 ∪ 官方 @GlobalScope 方法
        self.builtins = LANG_BUILTINS | self.global_members

    def has_class(self, name: str) -> bool:
        return name in self.classes or name in self.singletons

    def chain(self, name: str) -> list:
        out = []
        cur = self.singletons.get(name, name)
        guard = 0
        while cur and guard < 32:
            guard += 1
            e = self.classes.get(cur)
            if e is None:
                break
            out.append(cur)
            cur = e.get("inherits") or ""
        return out

    def _members(self, cls: str, key: str) -> set:
        acc = set()
        for c in self.chain(cls):
            e = self.classes.get(c)
            if not e:
                continue
            acc.update(e.get(key, "").split())
        return acc

    def methods(self, cls: str) -> set:
        return self._members(cls, "m")

    def properties(self, cls: str) -> set:
        return self._members(cls, "p")

    def signals(self, cls: str) -> set:
        return self._members(cls, "s")

    def constants(self, cls: str) -> set:
        acc = set()
        for c in self.chain(cls):
            e = self.classes.get(c)
            if not e:
                continue
            acc.update(e.get("c", "").split())
            for part in e.get("e", "").split(";"):
                if not part:
                    continue
                _, _, vals = part.partition(":")
                acc.update(vals.split())
        return acc

    def enum_names(self, cls: str) -> set:
        acc = set()
        for c in self.chain(cls):
            e = self.classes.get(c)
            if not e:
                continue
            for part in e.get("e", "").split(";"):
                if not part:
                    continue
                name, _, _ = part.partition(":")
                acc.add(name)
        return acc

    def has_member(self, cls: str, name: str) -> bool:
        return (
            name in self.methods(cls)
            or name in self.properties(cls)
            or name in self.signals(cls)
            or name in self.constants(cls)
            or name in self.enum_names(cls)
        )

    def property_types(self, cls: str) -> dict:
        acc = {}
        for c in self.chain(cls):
            e = self.classes.get(c)
            if not e:
                continue
            for pair in e.get("t", "").split():
                if ":" in pair:
                    k, _, v = pair.partition(":")
                    acc[k] = v
        return acc

    def is_object_type(self, typename: str) -> bool:
        if not typename or typename in BUILTIN_TYPE_NAMES:
            return False
        return typename in self.classes


class Allowlist:
    """每行: rule|token|说明（# 开头为注释）。token 可带 @file 前缀限定。"""

    def __init__(self, path: str):
        self.entries: dict = {}
        if not os.path.exists(path):
            return
        with io.open(path, encoding="utf-8") as f:
            for raw in f:
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split("|", 2)
                if len(parts) < 2:
                    continue
                rule = parts[0].strip()
                token = parts[1].strip()
                reason = parts[2].strip() if len(parts) > 2 else ""
                self.entries[f"{rule}|{token}"] = reason

    def allows(self, rule: str, token: str, filename: str = "") -> bool:
        if f"{rule}|{token}" in self.entries:
            return True
        if f"{rule}|{token}@{filename}" in self.entries:
            return True
        # 成员级条目允许只写成员名：`Node.foo` 也能命中 `unknown_member|foo`
        if rule == "unknown_member" and "." in token:
            base = token.rsplit(".", 1)[-1]
            if f"{rule}|{base}" in self.entries:
                return True
        return False


# --------------------------------------------------------------------------- #
# 读取书稿
# --------------------------------------------------------------------------- #
def read_articles(folder: str):
    out = []
    for name in sorted(os.listdir(folder)):
        if not name.endswith(".md"):
            continue
        path = os.path.join(folder, name)
        with io.open(path, encoding="utf-8", newline="") as f:
            text = f.read()
        out.append((name, text))
    return out


def split_blocks(text: str):
    """返回 (lang, code, start_line) 列表；start_line 为代码块首行的 1-based 行号。"""
    lines = text.split("\n")
    blocks = []
    i = 0
    while i < len(lines):
        line = lines[i].rstrip("\r")
        m = re.match(r"^```([A-Za-z0-9_+#.-]*)\s*$", line)
        if m:
            lang = m.group(1)
            start = i + 1
            j = i + 1
            body = []
            while j < len(lines):
                if re.match(r"^```\s*$", lines[j].rstrip("\r")):
                    break
                body.append(lines[j].rstrip("\r"))
                j += 1
            blocks.append((lang, "\n".join(body), start))
            i = j + 1
        else:
            i += 1
    return blocks


def strip_fenced(text: str) -> str:
    lines = text.split("\n")
    out = []
    inside = False
    for line in lines:
        s = line.rstrip("\r")
        if re.match(r"^```", s):
            inside = not inside
            out.append("")
            continue
        out.append("" if inside else s)
    return "\n".join(out)


# --------------------------------------------------------------------------- #
# 文件作用域
# --------------------------------------------------------------------------- #
@dataclass
class Scope:
    """一个 .md 文件里所有代码块的符号汇总——书稿常把同一个脚本拆成多个围栏，
    跨围栏定义的函数/枚举必须能被识别，否则会误报「该类没有这个方法」。"""
    classes: set = field(default_factory=set)
    enums: set = field(default_factory=set)
    enum_members: set = field(default_factory=set)
    funcs: set = field(default_factory=set)
    declared: set = field(default_factory=set)


FUNC_RE = re.compile(r"^\s*(?:@\w+\s+)*(?:static\s+)?func\s+([A-Za-z_]\w*)\s*\(", re.M)
FUNC_FULL_RE = re.compile(r"\bfunc\s+([A-Za-z_]\w*)\s*\(([^)]*)\)", re.S)
ENUM_RE = re.compile(r"^\s*enum\s+([A-Za-z_]\w*)\s*\{([^}]*)\}", re.M)
CLASS_RE = re.compile(r"^\s*(?:class_name\s+|class\s+)([A-Za-z_]\w*)", re.M)
VAR_RE = re.compile(r"^\s*(?:@\w+\s+)*var\s+([A-Za-z_]\w*)", re.M)
CONST_RE = re.compile(r"^\s*const\s+([A-Za-z_]\w*)", re.M)
FOR_RE = re.compile(r"^\s*for\s+([A-Za-z_]\w*)\s+in\b", re.M)


def build_scope(code_blocks) -> Scope:
    sc = Scope()
    for _, code, _ in code_blocks:
        for m in CLASS_RE.finditer(code):
            sc.classes.add(m.group(1))
        for m in ENUM_RE.finditer(code):
            sc.enums.add(m.group(1))
            for member in m.group(2).split(","):
                member = member.split("#")[0].strip()
                if member:
                    sc.enum_members.add(member)
        for m in FUNC_RE.finditer(code):
            sc.funcs.add(m.group(1))
        for m in FUNC_FULL_RE.finditer(code):
            sc.funcs.add(m.group(1))
            for raw_param in m.group(2).split(","):
                raw_param = raw_param.split("=")[0]
                part = raw_param.split(":")[0].strip()
                if part and re.match(r"^[A-Za-z_]\w*$", part):
                    sc.declared.add(part)
        for rx in (VAR_RE, CONST_RE, FOR_RE):
            for m in rx.finditer(code):
                sc.declared.add(m.group(1))
    return sc


# --------------------------------------------------------------------------- #
# 规则一：结构
# --------------------------------------------------------------------------- #
def check_local_links(book: Book, filename: str, text: str, base_dir: str = ""):
    """校验一个文件里的内部链接目标是否存在（外部 http(s) 链接跳过）。

    注意：必须先去掉代码围栏再扫链接——否则 GDScript 的数组类型转换
    `float[MAX_STEPS](0.125)` 会被当成 markdown 链接 `[MAX_STEPS](0.125)`。
    """
    rel_base = os.path.join(base_dir, filename) if base_dir else filename
    prose = strip_fenced(text)
    for m in LINK_RE.finditer(prose):
        target = m.group(1)
        if target.startswith(("http://", "https://", "#", "mailto:", "tel:")):
            continue
        path = target.split("#")[0].split("?")[0]
        if not path:
            continue
        if path.startswith("/"):
            resolved = os.path.join(ROOT, path.lstrip("/").replace("/", os.sep))
        else:
            resolved = os.path.normpath(
                os.path.join(os.path.dirname(os.path.join(ROOT, rel_base)),
                             path.replace("/", os.sep)))
        if not os.path.exists(resolved):
            line_no = prose[: m.start()].count("\n") + 1
            book.add("structure", "error", filename, line_no,
                     f"内部链接目标不存在：{target}")


def rule_structure(book: Book, articles):
    # 根目录文件（README / 封面 / 首页）的内部链接也要校验——
    # 它们同样会发布出去，死链不会被「文章级」检查发现。
    for root_file in ("README.md", "_cover.md", "index.html"):
        path = os.path.join(ROOT, root_file)
        if not os.path.exists(path):
            continue
        text = io.open(path, encoding="utf-8", newline="").read()
        check_local_links(book, root_file, text)

    for name, text in articles:
        # 1) 围栏闭合：所有 ``` 标记的总数必须是偶数，且逐行走一遍确认能配平
        markers = len(re.findall(r"^```", text, re.M))
        if markers % 2:
            book.add("structure", "error", name, 1,
                     f"代码围栏不闭合：` ``` ` 标记 {markers} 个（奇数）")
        else:
            inside = False
            for idx, ln in enumerate(text.split("\n"), 1):
                if re.match(r"^```", ln.rstrip("\r")):
                    inside = not inside
            if inside:
                book.add("structure", "error", name, 1,
                         "代码围栏不闭合：存在未闭合的 ``` 起始标记")
        # 表格列数一致
        lines = text.split("\n")
        block = []
        for idx, ln in enumerate(lines, 1):
            s = ln.strip()
            if s.startswith("|") and s.endswith("|") and s.count("|") >= 2:
                block.append((idx, s.count("|")))
            else:
                if len(block) >= 2:
                    counts = {c for _, c in block}
                    if len(counts) > 1:
                        bad = [i for i, c in block if c != block[0][1]]
                        book.add("structure", "error", name, bad[0],
                                 f"表格列数不一致：期望 {block[0][1]-1} 列，"
                                 f"第 {bad[0]} 行起有 {len(bad)} 行列数不同")
                block = []
        # 内部链接
        check_local_links(book, name, text)
        # 行尾
        #   仓库里存的是 **LF**（git 在 core.autocrlf=true 下入库时规范化），
        #   Windows 工作区检出时才是 CRLF。所以：
        #     · 「混用」在任何平台都是错 → error
        #     · 「必须 CRLF」只是 **Windows 工作区约定** → 仅在 Windows 上查
        #   否则 Linux CI 检出的全是 LF，会把每个文件都误判成错。
        crlf = text.count("\r\n")
        lone_lf = text.count("\n") - crlf
        lone_cr = text.count("\r") - crlf
        if lone_cr:
            book.add("structure", "error", name, 1,
                     f"存在单独的 CR（老 Mac 换行），共 {lone_cr} 处")
        elif crlf and lone_lf:
            book.add("structure", "error", name, 1,
                     f"行尾混用：CRLF {crlf} 处、LF {lone_lf} 处")
        elif REQUIRE_CRLF and lone_lf:
            book.add("structure", "error", name, 1,
                     f"文件未使用 CRLF 行尾（Windows 工作区约定，仓库内仍是 LF）"
                     f"：有 {lone_lf} 处 LF")
        # 篇末四件套（取最后 300 行；附录本来就以清单结尾，不要求篇末导航）
        if not name.startswith("appendix-"):
            tail = "\n".join(text.split("\n")[-300:])
            for req in ("延伸阅读", "上一篇", "下一篇"):
                # 第 01 篇是第一篇，没有「上一篇」是正常的
                if req == "上一篇" and name.startswith("01-"):
                    continue
                if req not in tail:
                    book.add("structure", "error", name, 1, f"篇末缺少「{req}」块")
            if "Godot 版本" not in tail:
                book.add("structure", "error", name, 1, "篇末缺少「Godot 版本」尾注")


# --------------------------------------------------------------------------- #
# 规则二：API 存在性
# --------------------------------------------------------------------------- #
class ApiChecker:
    def __init__(self, index: ApiIndex, allow: Allowlist, book: Book):
        self.ix = index
        self.allow = allow
        self.book = book
        self.user_classes: set = set()
        self.scene_names: set = set()
        self.user_funcs: set = set()

    # -- 全书预扫描 -------------------------------------------------------- #
    def prepass(self, articles):
        for _, text in articles:
            for m in re.finditer(r"\bclass_name\s+([A-Z][A-Za-z0-9]*)", text):
                self.user_classes.add(m.group(1))
            for m in re.finditer(r"\bclass\s+([A-Z][A-Za-z0-9]*)", text):
                self.user_classes.add(m.group(1))
        # 全书出现过的自定义函数/信号名（不是引擎 API 的）——这些不是「不存在的 API」
        engine_names = set()
        for cls in self.ix.classes.values():
            engine_names.update(cls.get("m", "").split())
            engine_names.update(cls.get("s", "").split())
        engine_names.update(self.ix.global_members)
        for _, text in articles:
            for m in re.finditer(r"^\s*(?:@\w+\s+)*(?:static\s+)?func\s+([A-Za-z_]\w*)",
                                 text, re.M):
                if m.group(1) not in engine_names:
                    self.user_funcs.add(m.group(1))
            for m in re.finditer(r"^\s*signal\s+([A-Za-z_]\w*)", text, re.M):
                if m.group(1) not in engine_names:
                    self.user_funcs.add(m.group(1))

    def file_scene_names(self, text: str) -> set:
        """本文件里出现在**引号字符串**中的 PascalCase 词（场景节点名、文件基名等）。

        必须按文件作用域取：若做成全局，某个文件里 `get_node("RenderingServer")`
        就会让全书所有 `RenderingServer.xxx` 的正文检查失效——门禁会被悄悄削弱。
        """
        out = set()
        for m in re.finditer(r"\"([^\"\n]*)\"|'([^'\n]*)'", text):
            raw = m.group(1) if m.group(1) is not None else m.group(2)
            for tok in re.findall(r"\b([A-Z][A-Za-z0-9]+)\b", raw or ""):
                out.add(tok)
        return out

    def report(self, rule, name, line, message, token):
        if self.allow.allows(rule, token, name):
            return
        self.book.add(rule, "error", name, line, message, token)

    # -- GDScript ----------------------------------------------------------- #
    def check_gdscript(self, name, code, start_line, scope: Scope):
        local_classes = set(scope.classes)
        local_funcs = set(scope.funcs)
        local_enums = set(scope.enums)
        declared = set(scope.declared)
        extends = None
        for raw in code.split("\n"):
            line = strip_comment(raw).strip()
            m = re.match(r"^extends\s+([A-Za-z_]\w*)", line)
            if m:
                extends = m.group(1)
                break
        var_types = self.infer_var_types(code, local_classes)
        self.check_assignment_types(name, code, start_line, var_types,
                                    extends, local_classes)

        for offset, raw in enumerate(code.split("\n")):
            line_no = start_line + 1 + offset
            line = strip_strings_and_comments(raw)
            if not line.strip():
                continue
            # extends
            m = re.search(r"\bextends\s+([A-Za-z_]\w*)", line)
            if m:
                cls = m.group(1)
                if (cls not in local_classes and cls not in self.user_classes
                        and not self.ix.has_class(cls)):
                    self.report("unknown_class", name, line_no,
                                f"`extends {cls}`：{self.ix.version} 官方类参考中没有这个类",
                                f"extends:{cls}")
            # class_name 撞引擎类
            m = re.search(r"\bclass_name\s+([A-Za-z_]\w*)", line)
            if m and self.ix.has_class(m.group(1)):
                self.report("shadowed_class", name, line_no,
                            f"`class_name {m.group(1)}` 与引擎类同名，会遮蔽引擎 API",
                            m.group(1))
            # 静态调用 / 常量 / 枚举：PascalCase 接收者
            for m in re.finditer(
                    r"(?<![$@\"'/.\w])([A-Z][A-Za-z0-9]*)\s*\.\s*([A-Za-z_][A-Za-z0-9_]*)",
                    line):
                recv, attr = m.group(1), m.group(2)
                if recv in local_classes or recv in local_enums:
                    continue
                if recv in BUILTIN_TYPE_NAMES:
                    continue
                if recv in self.user_classes or recv in self.scene_names:
                    continue
                if recv in UNITY_API:
                    continue
                if not self.ix.has_class(recv):
                    self.report("unknown_class", name, line_no,
                                f"`{recv}`：{self.ix.version} 官方类参考里没有这个类", recv)
                    continue
                if attr in local_funcs or attr == "new":
                    continue
                if not self.ix.has_member(recv, attr):
                    kind = "常量/枚举" if UPPER_CONST_RE.match(attr) else "成员"
                    self.report("unknown_member", name, line_no,
                                f"`{recv}.{attr}`：{recv} 上没有这个{kind}",
                                f"{recv}.{attr}")
            # 实例成员：已知类型的变量（self 走 extends 类）
            for m in re.finditer(
                    r"(?<![$@\"'/.\w])([a-z_][a-z0-9_]*)\s*\.\s*([A-Za-z_][A-Za-z0-9_]*)",
                    line):
                var, attr = m.group(1), m.group(2)
                cls = extends if var == "self" else var_types.get(var)
                if not cls or cls in local_classes:
                    continue
                if attr in local_funcs or attr in self.user_funcs:
                    continue
                if attr in scope.declared:
                    continue
                if not self.ix.has_member(cls, attr):
                    self.report("unknown_member", name, line_no,
                                f"`{var}.{attr}`：{cls} 上没有这个成员",
                                f"{cls}.{attr}")
            # 裸方法调用（self 方法）
            for m in re.finditer(r"(?<![.\w])([a-z_][a-z0-9_]*)\s*\(", line):
                fn = m.group(1)
                if fn in local_funcs or fn in self.ix.builtins:
                    continue
                if fn in GDSCRIPT_KEYWORDS or fn in declared:
                    continue
                if fn in self.user_funcs:
                    continue
                if fn in GDSCRIPT_ANNOTATIONS:
                    continue
                if not extends or extends in local_classes:
                    continue
                if not self.ix.has_class(extends):
                    continue
                if fn not in self.ix.methods(extends):
                    self.report("unknown_member", name, line_no,
                                f"`{fn}()`：{extends} 上没有这个方法",
                                f"{extends}.{fn}")
            # 裸属性访问：只校验高频属性
            for m in re.finditer(r"(?<![.\w\"'])([a-z_][a-z0-9_]*)(?!\s*\()", line):
                prop = m.group(1)
                if prop not in COMMON_PROPERTIES:
                    continue
                if prop in declared or prop in local_funcs:
                    continue
                if not extends or extends in local_classes:
                    continue
                if not self.ix.has_class(extends):
                    continue
                if not self.ix.has_member(extends, prop):
                    self.report("unknown_member", name, line_no,
                                f"`{prop}`：{extends} 上没有这个属性",
                                f"{extends}.{prop}")

    def infer_var_types(self, code, local_classes):
        """只推断「块顶层」的 var，且只对已知引擎类建表——未知类（如示例里的自定义类）
        一旦建表，后续 `obj.member` 就会被误判成「该类没有这个成员」。"""
        out = {}
        for raw in code.split("\n"):
            if not raw.strip() or raw[:1].isspace():
                continue
            line = re.sub(r"^@\w+\s+", "", strip_comment(raw).strip())
            m = re.match(r"^var\s+([a-z_]\w*)\s*:\s*:\s*([A-Z][A-Za-z0-9]*)", line)
            if m:
                self._put_type(out, local_classes, m.group(1), m.group(2))
                continue
            m = re.match(r"^var\s+([a-z_]\w*)\s*:\s*([A-Z][A-Za-z0-9]*)", line)
            if m:
                self._put_type(out, local_classes, m.group(1), m.group(2))
                continue
            m = re.match(r"^var\s+([a-z_]\w*)\s*:?=\s*([A-Z][A-Za-z0-9]*)\s*\.\s*new\s*\(", line)
            if m:
                self._put_type(out, local_classes, m.group(1), m.group(2))
                continue
            m = re.match(r"^const\s+([a-z_]\w*)\s*:?=\s*([A-Z][A-Za-z0-9]*)\s*\.\s*new\s*\(", line)
            if m:
                self._put_type(out, local_classes, m.group(1), m.group(2))
        return out

    def _put_type(self, out, local_classes, var, cls):
        if cls in local_classes or cls in BUILTIN_TYPE_NAMES:
            return
        if not self.ix.has_class(cls):
            return
        out[var] = cls

    # -- 赋值类型规则 ------------------------------------------------------- #
    def literal_kind(self, value: str):
        v = value.strip()
        if not v or v == "null":
            return None
        if v[0] in "\"'":
            return "String"
        if v[0] == "[":
            return "Array"
        if v[0] == "{":
            return "Dictionary"
        if v in ("true", "false"):
            return "bool"
        if re.match(r"^-?\d+$", v):
            return "int"
        if re.match(r"^-?\d*\.\d+$", v):
            return "float"
        return None

    def type_conflict(self, declared: str, vkind: str) -> bool:
        if declared in ("Variant", "StringName", "NodePath"):
            return False
        if declared == "String":
            return vkind != "String"
        if declared in ("int", "float"):
            return vkind in ("String", "Array", "Dictionary")
        if declared == "bool":
            return vkind in ("String", "Array", "Dictionary")
        if declared.startswith("Packed"):
            return vkind == "Array"
        if declared in ("Array", "Dictionary"):
            return vkind != declared
        if self.ix.is_object_type(declared):
            return vkind in ("String", "Array", "Dictionary", "bool", "int", "float")
        return False

    def check_assignment_types(self, name, code, start_line, var_types,
                               extends, local_classes):
        for offset, raw in enumerate(code.split("\n")):
            line_no = start_line + 1 + offset
            line = strip_strings_and_comments(raw)
            if not line.strip():
                continue
            m = re.match(
                r"^\s*([A-Za-z_]\w*)\s*\.\s*([A-Za-z_]\w*)\s*=\s*([^=].*?)\s*$", line)
            if m:
                var, prop, value = m.group(1), m.group(2), m.group(3)
                cls = extends if var == "self" else var_types.get(var)
                if cls and cls not in local_classes:
                    t = self.ix.property_types(cls).get(prop)
                    vkind = self.literal_kind(value)
                    if t and vkind and self.type_conflict(t, vkind):
                        self.report("type_mismatch", name, line_no,
                                    f"`{var}.{prop}` 的声明类型是 {t}，"
                                    f"不能直接赋 {vkind} 字面量",
                                    f"{cls}.{prop}")
            m = re.match(
                r"^\s*var\s+([A-Za-z_]\w*)\s*:\s*([A-Z][A-Za-z0-9]*)\s*=\s*([^=].*?)\s*$",
                line)
            if m:
                declared, value = m.group(2), m.group(3)
                if declared in local_classes:
                    continue
                vkind = self.literal_kind(value)
                if vkind and self.type_conflict(declared, vkind):
                    self.report("type_mismatch", name, line_no,
                                f"变量声明类型是 {declared}，不能直接赋 {vkind} 字面量",
                                f"var:{declared}")

    # -- C# / C++ ----------------------------------------------------------- #
    def check_csharp(self, name, code, start_line, scope: Scope):
        for offset, raw in enumerate(code.split("\n")):
            line_no = start_line + 1 + offset
            line = strip_strings_and_comments(raw)
            for m in re.finditer(r"\bGodot\.([A-Z][A-Za-z0-9]*)", line):
                cls = m.group(1)
                if not self.ix.has_class(cls):
                    self.report("unknown_class", name, line_no,
                                f"`Godot.{cls}`：{self.ix.version} 官方类参考里没有这个类", cls)
            for m in re.finditer(r"class\s+\w+\s*:\s*([A-Z][A-Za-z0-9]*)", line):
                base = m.group(1)
                if base in ("Exception", "Object", "Reference", "RefCounted"):
                    continue
                if base in UNITY_API or base in scope.classes:
                    continue
                if not self.ix.has_class(base):
                    self.report("unknown_class", name, line_no,
                                f"C# 基类 `{base}` 不存在于 {self.ix.version} 类参考", base)

    def check_cpp(self, name, code, start_line, scope: Scope):
        for offset, raw in enumerate(code.split("\n")):
            line_no = start_line + 1 + offset
            line = strip_strings_and_comments(raw)
            for m in re.finditer(r"\bgodot::([A-Z][A-Za-z0-9]*)", line):
                cls = m.group(1)
                if not self.ix.has_class(cls):
                    self.report("unknown_class", name, line_no,
                                f"`godot::{cls}`：{self.ix.version} 官方类参考里没有这个类", cls)
            for m in re.finditer(r"\bmemnew\(\s*([A-Z][A-Za-z0-9]*)", line):
                cls = m.group(1)
                if not self.ix.has_class(cls):
                    self.report("unknown_class", name, line_no,
                                f"`memnew({cls})`：{self.ix.version} 官方类参考里没有这个类", cls)

    # -- 正文里的行内代码 ---------------------------------------------------- #
    def check_prose(self, name, text, scope: Scope):
        prose = strip_fenced(text)
        scene_names = self.file_scene_names(text)
        for m in INLINE_RE.finditer(prose):
            token = m.group(1).strip()
            if not token or " " in token:
                continue
            base = token.split("(")[0].strip()
            if not base:
                continue
            parts = base.split(".")
            head = parts[0]
            if not CLASS_TOKEN_RE.match(head) or head.isupper():
                continue
            if head in UNITY_API or head in self.user_classes or head in scene_names:
                continue
            if head in BUILTIN_TYPE_NAMES:
                continue
            if len(parts) == 1:
                # 独立出现的词：只有「类名形态」（含内部大写，如 LODLevel / ORMMaterial）
                # 才可能是类名；Enabled / Pass / Position 这类普通词一律放过。
                if not re.search(r"[a-z][A-Z]", head):
                    continue
            if head in scope.classes or head in scope.enums:
                continue
            if len(parts) > 1 and parts[-1].lower() in FILE_EXTS:
                continue
            if len(parts) == 1 and head.lower() in FILE_EXTS:
                continue
            line_no = prose[: m.start()].count("\n") + 1
            if len(parts) == 1:
                if not self.ix.has_class(head):
                    self.report("unknown_class", name, line_no,
                                f"正文提到的 `{head}` 不在 {self.ix.version} 官方类参考中", head)
            else:
                attr = parts[1]
                if attr == "new":
                    continue
                if not self.ix.has_class(head):
                    self.report("unknown_class", name, line_no,
                                f"正文提到的 `{head}` 不在 {self.ix.version} 官方类参考中", head)
                    continue
                if not self.ix.has_member(head, attr):
                    self.report("unknown_member", name, line_no,
                                f"正文提到的 `{head}.{attr}` 在 {self.ix.version} 中不存在",
                                f"{head}.{attr}")

    # -- 入口 --------------------------------------------------------------- #
    def check_file(self, name, text):
        blocks = split_blocks(text)
        scope = build_scope([b for b in blocks if b[0] == "gdscript"])
        for lang, code, start in blocks:
            if lang == "gdscript":
                self.check_gdscript(name, code, start, scope)
            elif lang == "csharp":
                self.check_csharp(name, code, start, scope)
            elif lang == "cpp":
                self.check_cpp(name, code, start, scope)
        self.check_prose(name, text, scope)


# --------------------------------------------------------------------------- #
# 规则组：syntax —— GDScript 解析期错误（不需要 Godot 可执行文件）
# --------------------------------------------------------------------------- #
GDSCRIPT_KEYWORDS_STMT = {
    "if", "elif", "else", "for", "while", "match", "when", "break", "continue",
    "pass", "return", "await", "assert", "class", "class_name", "extends",
    "signal", "enum", "const", "var", "func", "static", "export", "onready",
    "tool", "rpc", "abstract",
}
IDENT_START = re.compile(r"^[A-Za-z_]\w*$")


def _strip_blanks(code: str):
    """返回去掉注释与空行后的 (行号, 文本) 序列（行号为 1-based，块内相对行）。"""
    out = []
    for i, raw in enumerate(code.split("\n"), 1):
        line = strip_comment(raw).rstrip()
        if not line.strip():
            continue
        out.append((i, line.strip()))
    return out


def rule_syntax(book: Book, articles, index):
    """抓 GDScript 常见的**解析期**错误（脚本根本加载不了的那一类）。

    覆盖：
      ① 脚本级 extends 不是第一条语句 / 出现多次
      ② 同一段完整脚本里 func 重名（只在「自称是完整脚本」时才报）
      ③ 子类成员遮蔽父类属性（脚本会报 "Member xxx already exists in parent class"）
      ④ 括号 / 方括号 / 花括号不配对
      ⑤ 同一行缩进里 tab 与空格混用（GDScript 只认一种）

    注意：书里的代码块多数是**教学片段**，所以判定必须按「列」区分作用域——
    缩进的 `extends` 属于内层类，不算脚本级 extends；没有脚本级 extends 的块
    视作片段，不做重复函数这类「整脚本级」判定。
    """
    for name, text in articles:
        file_funcs = {}
        for lang, code, start in split_blocks(text):
            if lang != "gdscript":
                continue
            # 先把注释与字符串（含三引号多行串）内容清空，再做语法判定
            code_nostr = strip_code(code)
            raw_lines = code_nostr.split("\n")
            base = start + 1  # 块内行号 → 文件行号

            # 收集「语句级」信息：{行号: (缩进, 文本)}
            stmts = []
            for i, raw in enumerate(raw_lines, 1):
                line = raw.rstrip()
                if not line.strip():
                    continue
                indent = len(raw) - len(raw.lstrip())
                stmts.append((i, indent, line.strip()))

            # 脚本级 extends = 缩进为 0 的 extends
            ext = [(i, l) for i, ind, l in stmts if ind == 0 and re.match(r"^extends\s+\w", l)]
            if len(ext) > 1:
                book.add("syntax", "warning", name, base + ext[1][0] - 1,
                         f"同一代码块出现 {len(ext)} 条脚本级 extends——"
                         f"若这些是备选模板可忽略，若当同一脚本则只能有一条")
            if ext:
                ext_idx, ext_line = ext[0]
                for i, ind, l in stmts:
                    if i >= ext_idx:
                        break
                    if l.startswith("class_name ") or l.startswith("@"):
                        continue
                    book.add("syntax", "warning", name, base + i - 1,
                             f"extends 后面跟的类声明之前还有语句（{l[:40]}）——"
                             f"若这是一份完整脚本，extends 必须是第一条语句")
                    break
                ext_cls = re.match(r"^extends\s+(\w+)", ext_line).group(1)
            else:
                ext_cls = None

            # 顶层 func 重名（只在自称完整脚本的块里报）
            if ext:
                seen_func = {}
                for i, ind, l in stmts:
                    if ind != 0:
                        continue
                    m = re.match(r"^(?:static\s+)?func\s+([A-Za-z_]\w*)\s*\(", l)
                    if not m:
                        continue
                    fn = m.group(1)
                    if fn in seen_func:
                        book.add("syntax", "warning", name, base + i - 1,
                                 f"函数 `{fn}` 在同一段脚本里定义了两次"
                                 f"（首次在第 {base + seen_func[fn] - 1} 行）")
                    else:
                        seen_func[fn] = i
                    file_funcs.setdefault(fn, []).append(i)

            # ③ 成员遮蔽父类属性
            #   注意作用域：只有**类成员**（类体里的 var）才会让脚本加载失败；
            #   函数内的局部变量与同名成员只是 GDScript 的 shadowed_variable 警告。
            #   所以要先算出每条 var 声明「属于哪个作用域」。
            openers = []  # [(header_indent, kind, base_class)]，kind ∈ {"class","func"}
            if ext_cls:
                openers.append((-1, "class", ext_cls))
            for i, ind, l in stmts:
                m = re.match(r"^class\s+([A-Za-z_]\w*)\s*(?:extends\s+(\w+))?", l)
                if m:
                    openers.append((ind, "class", m.group(2)))
                    continue
                m = re.match(r"^(?:static\s+)?func\s+([A-Za-z_]\w*)\s*\(", l)
                if m:
                    openers.append((ind, "func", None))
                    continue
                m = re.match(r"^(?:@export[^ ]*\s+)*var\s+([A-Za-z_]\w*)", l)
                if not m:
                    continue
                # 所属作用域 = 最近一个 header_indent < ind 的开启者
                owner = None
                for h_ind, kind, owner_base in reversed(openers):
                    if h_ind < ind:
                        owner = (kind, owner_base)
                        break
                if owner is None or owner[0] != "class":
                    continue  # 函数内的局部变量：只是 shadowed_variable 警告
                base_cls = owner[1]
                if not base_cls or not index.has_class(base_cls):
                    continue
                parent_props = index.property_types(base_cls)
                vname = m.group(1)
                if vname in parent_props:
                    book.add("syntax", "error", name, base + i - 1,
                             f"`var {vname}` 遮蔽了父类 {base_cls} 的同名属性"
                             f"（声明类型 {parent_props[vname]}）——"
                             f"脚本会报 \"Member {vname} already exists "
                             f"in parent class\" 而加载失败")

            # ④ 括号配对（注释与字符串都已清空，不会误判）
            depth = {"(": 0, "[": 0, "{": 0}
            pairs = {")": "(", "]": "[", "}": "{"}
            orig_lines = code.split("\n")
            for i, (raw_orig, raw) in enumerate(zip(orig_lines, raw_lines), 1):
                s = raw
                for ch in s:
                    if ch in depth:
                        depth[ch] += 1
                    elif ch in pairs:
                        depth[pairs[ch]] -= 1
                        if depth[pairs[ch]] < 0:
                            book.add("syntax", "error", name, base + i - 1,
                                     f"括号不配对：多余的 `{ch}`")
                            depth[pairs[ch]] = 0
                # 缩进要看**原始行**：清空后的行里注释内容已变成空格，会误判成混用
                indent = raw_orig[: len(raw_orig) - len(raw_orig.lstrip())]
                if "\t" in indent and " " in indent:
                    book.add("syntax", "error", name, base + i - 1,
                             "缩进里 tab 与空格混用（GDScript 只认一种）")
            for ch, n in depth.items():
                if n > 0:
                    book.add("syntax", "error", name, base,
                             f"括号不配对：`{ch}` 多出 {n} 个")


# --------------------------------------------------------------------------- #
# 规则三：统计读数
# --------------------------------------------------------------------------- #
def rule_stats(book: Book, articles):
    """统计口径（与 README / 封面一致）：
       - 正文中文字 = 剔除代码围栏后的 CJK 汉字数（U+4E00–U+9FFF）
       - 代码行   = **带语言标记**的代码块内的非空行数（不含围栏本身）
       - 围栏     = 所有 ``` 代码块的数量（其中带语言标记的另计）
       - 表格     = 连续的、以 | 开头且以 | 结尾的行构成的表格块
       - 示意图   = 含制表符画框线（+ - | 等）的非表格行
    """
    code_lines = 0
    cjk = 0
    fences = 0
    fences_lang = 0
    boxes = 0
    tables = 0
    for _, text in articles:
        prose = strip_fenced(text)
        cjk += sum(1 for ch in prose if "\u4e00" <= ch <= "\u9fff")
        for lang, code, _ in split_blocks(text):
            fences += 1
            if lang:
                fences_lang += 1
                code_lines += sum(1 for ln in code.split("\n") if ln.strip())
        in_table = False
        box_run = 0
        # ASCII 图示通常写在代码围栏里，所以示意图按**原文**统计；
        # 表格在正文里，所以表格按**去围栏正文**统计。
        for ln in text.split("\n"):
            s = ln.strip().rstrip("\r")
            is_box = bool(re.search(r"[─-╿┌-┿╭-╯▏▕]", s)) or (
                s.startswith("+") and "-" in s)
            if is_box:
                box_run += 1
            else:
                if box_run >= 3:
                    boxes += 1
                box_run = 0
        if box_run >= 3:
            boxes += 1
        for ln in prose.split("\n"):
            s = ln.strip()
            is_table = s.startswith("|") and s.endswith("|") and s.count("|") >= 3
            if is_table:
                if not in_table:
                    tables += 1
                    in_table = True
                continue
            in_table = False
    st = {
        "articles": len(articles),
        "cjk": cjk,
        "code_lines": code_lines,
        "blocks": fences,
        "blocks_lang": fences_lang,
        "ascii_box": boxes,
        "tables": tables,
    }
    for fname in ("README.md", "_cover.md"):
        path = os.path.join(ROOT, fname)
        if not os.path.exists(path):
            continue
        text = io.open(path, encoding="utf-8").read()

        def expect_int(desc, needle_re, actual):
            m = re.search(needle_re, text)
            if not m:
                return False
            got = int(m.group(1).replace(",", "").replace("，", ""))
            if got != actual:
                book.add("stats", "error", fname, 1,
                         f"{desc} 读数漂移：文中 {got}，实测 {actual}", desc)
            return True

        def expect_wan(desc, needle_re, actual):
            m = re.search(needle_re, text)
            if not m:
                return False
            got = float(m.group(1))
            if abs(got - actual) > 0.06:
                book.add("stats", "error", fname, 1,
                         f"{desc} 读数漂移：文中 {got} 万字，实测 "
                         f"{round(actual, 1)} 万字", desc)
            return True

        expect_int("篇数", r"(\d+)\s*篇", st["articles"])
        expect_int("代码行", r"代码[^\n]{0,20}?(\d[\d,]*)\s*行", st["code_lines"])
        expect_int("代码行", r"(\d[\d,]*)\s*行[^\n]{0,12}?代码", st["code_lines"])
        # 「约 14.6 万字」与「145,900 字」两种写法，二选一命中即可
        if not expect_wan("正文中文字", r"约\s*([\d.]+)\s*万字", st["cjk"] / 10000):
            expect_int("正文中文字", r"正文中文字[^\n]{0,16}?(\d[\d,]*)\s*字", st["cjk"])
            expect_int("正文中文字", r"([\d,]+)\s*字", st["cjk"])
        expect_int("示意图", r"(\d+)\s*张\s*ASCII", st["ascii_box"])
        expect_int("表格", r"(\d+)\s*张表格", st["tables"])
        expect_int("表格", r"(\d+)\s*/\s*\d+\s*张表格", st["tables"])
    return st


# --------------------------------------------------------------------------- #
# 规则四：性能数字标注
# --------------------------------------------------------------------------- #
PERF_RE = re.compile(r"\d+(?:\.\d+)?\s*(?:FPS|fps|ms|毫秒|帧/秒|MB|GB)")
PERF_MARK_RE = re.compile(r"示意数据|测试条件|测试环境|实测|基准|Benchmark", re.I)


def rule_perf(book: Book, articles):
    for name, text in articles:
        prose = strip_fenced(text)
        lines = prose.split("\n")
        for i, ln in enumerate(lines, 1):
            s = ln.strip()
            if not s or s.startswith("#"):
                continue  # 标题里的 "FPS 游戏" 不是性能读数
            if not PERF_RE.search(s):
                continue
            # 表格行：看该表表头之前有没有标注；非表格行：看上下各 8 行
            if s.startswith("|"):
                j = i - 1
                while j > 0 and lines[j - 1].strip().startswith("|"):
                    j -= 1
                window = "\n".join(lines[max(0, j - 6): i + 1])
            else:
                window = "\n".join(lines[max(0, i - 9): i + 8])
            if PERF_MARK_RE.search(window):
                continue
            book.add("perf", "warning", name, i,
                     f"性能读数未见测试条件/示意数据标注：{s[:60]}")


# --------------------------------------------------------------------------- #
# 自检（阳性对照）：判据必须能抓到已知的历史 P0，且不能对正确写法误报
# --------------------------------------------------------------------------- #
SELFTEST_CASES = [
    ("unknown_class", "extends LOD3D\n", "LOD3D 在基线官方类参考中不存在", True),
    ("unknown_member", "var light = DirectionalLight3D.new()\nlight.shadow_max_distance = 100\n",
     "DirectionalLight3D 没有 shadow_max_distance", True),
    ("unknown_member", "var light = DirectionalLight3D.new()\nlight.shadow_orthogonal_size = 10\n",
     "DirectionalLight3D 没有 shadow_orthogonal_size", True),
    ("unknown_member", "var gi = LightmapGI.new()\ngi.bake_mode = 1\n",
     "LightmapGI 没有 bake_mode", True),
    ("type_mismatch", "var gi = LightmapGI.new()\ngi.light_data = \"res://x.gi\"\n",
     "light_data 是 LightmapGIData，不能赋字符串", True),
    ("unknown_class", "var x = EditorResourceImporter.new()\n",
     "EditorResourceImporter 在基线官方类参考中不存在", True),
    ("unknown_member", "print(Performance.RENDER_TOTAL_DRAW_CALLS)\n",
     "Performance 常量名错", True),
    ("unknown_member", "var rs = ResourceSaver.new()\nrs.save_to_buffer(x)\n",
     "ResourceSaver.save_to_buffer 不存在", True),
    ("syntax", "extends Node\n\n@export var name: StringName = &\"x\"\n",
     "成员 var name 遮蔽父类 Node.name（脚本加载失败）", True),
    ("syntax", "extends Node\n\nfunc _ready():\n\tvar name = get_name()\n\tprint(name)\n",
     "函数内局部变量 name 遮蔽成员（只是 warning，不算错）", False),
    ("syntax", "extends Area3D\n\n@export var gravity_direction: Vector3 = Vector3.DOWN\n",
     "成员 var gravity_direction 遮蔽父类 Area3D 同名属性", True),
    ("syntax", "extends Node\n\nfunc a():\n\tprint(1)\n",
     "正常脚本（阳性对照，应通过）", False),
    ("unknown_member", "var l = DirectionalLight3D.new()\nl.directional_shadow_mode = DirectionalLight3D.SHADOW_PARALLEL_4_SPLITS\n",
     "directional_shadow_mode 存在（阳性对照，应通过）", False),
    ("unknown_member", "print(Performance.RENDER_TOTAL_DRAW_CALLS_IN_FRAME)\n",
     "Performance.RENDER_TOTAL_DRAW_CALLS_IN_FRAME 存在（阳性对照，应通过）", False),
    ("type_mismatch", "var l = DirectionalLight3D.new()\nl.light_color = \"warm\"\n",
     "light_color 是 Color，不能赋字符串", True),
    ("type_mismatch", "var l = DirectionalLight3D.new()\nl.light_color = Color(1, 0.9, 0.8)\n",
     "light_color = Color(...) 合法（阳性对照，应通过）", False),
    ("unknown_member", "extends Node\nfunc _ready():\n\tvar v = Vector2.ZERO\n\tprint(v)\n",
     "块顶层 var + 内建常量合法（阳性对照，应通过）", False),
]


def run_selftest(index: ApiIndex, allow: Allowlist) -> int:
    """自检用**空白名单**：这里验证的是判据本身的能力，
    而不是在书稿语境下某个符号该不该被放行。
    （若用真白名单，正例里的 EditorResourceImporter / ResourceSaver.save_to_buffer
      会被放行，导致判据看起来「没牙」。）"""
    empty_allow = Allowlist(os.devnull)
    book = Book()
    checker = ApiChecker(index, empty_allow, book)
    failures = 0
    for rule, code, desc, expect_hit in SELFTEST_CASES:
        book.finding_list = []
        scope = build_scope([("gdscript", code, 1)])
        checker.check_gdscript("selftest.md", code, 1, scope)
        if rule == "syntax":
            # 语法规则走独立的 rule_syntax（按整篇文件的代码块扫描）
            rule_syntax(book, [("selftest.md", "```gdscript\n" + code + "```")], index)
        hits = [f for f in book.finding_list if f.rule == rule]
        if expect_hit and not hits:
            print(f"[FAIL] 判据无牙：{desc} —— 没报出 {rule}")
            failures += 1
        elif not expect_hit and hits:
            print(f"[FAIL] 假阳性：{desc} —— 报了 {hits[0].message}")
            failures += 1
        else:
            print(f"[ ok ] {desc}")
    print(f"\n自检: {len(SELFTEST_CASES) - failures}/{len(SELFTEST_CASES)} 通过")
    return 1 if failures else 0


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rules", default="all",
                    help="逗号分隔: structure,syntax,api,stats,perf")
    ap.add_argument("--selftest", action="store_true", help="只跑判据自检")
    ap.add_argument("--report", default="", help="把结果写入文件")
    ap.add_argument("--strict", action="store_true", help="warning 也算失败")
    args = ap.parse_args()

    if not os.path.exists(INDEX_PATH):
        print(f"缺少类参考索引: {INDEX_PATH}", file=sys.stderr)
        return 2
    index = ApiIndex(INDEX_PATH)
    allow = Allowlist(ALLOW_PATH)

    if args.selftest:
        return run_selftest(index, allow)

    rules = {"structure", "syntax", "api", "stats", "perf"} if args.rules == "all" else set(
        r.strip() for r in args.rules.split(",")
    )
    articles = read_articles(ARTICLES)
    book = Book()
    stats = None

    if "structure" in rules:
        rule_structure(book, articles)
    if "syntax" in rules:
        rule_syntax(book, articles, index)
    if "api" in rules:
        checker = ApiChecker(index, allow, book)
        checker.prepass(articles)
        for name, text in articles:
            checker.check_file(name, text)
    if "stats" in rules:
        stats = rule_stats(book, articles)
    if "perf" in rules:
        rule_perf(book, articles)

    errors = [f for f in book.finding_list if f.severity == "error"]
    warnings = [f for f in book.finding_list if f.severity == "warning"]

    lines = []
    lines.append("=" * 68)
    lines.append(f"书稿门禁报告  (Godot 类参考基线 {index.version})")
    lines.append("=" * 68)
    if stats:
        lines.append(
            f"实测: {stats['articles']} 篇 / 正文 {stats['cjk']} 汉字 / "
            f"代码 {stats['code_lines']} 行 / 围栏 {stats['blocks']} 个 / "
            f"框图 {stats['ascii_box']} / 表格 {stats['tables']}"
        )
    lines.append(f"结果: error {len(errors)} 条, warning {len(warnings)} 条")
    lines.append("")
    for sev, items in (("ERROR", errors), ("WARN", warnings)):
        if not items:
            continue
        lines.append(f"--- {sev} ({len(items)}) ---")
        by_file = {}
        for f in items:
            by_file.setdefault(f.file, []).append(f)
        for fname in sorted(by_file):
            lines.append(f"  {fname}")
            for f in by_file[fname][:60]:
                lines.append(f"    L{f.line:<5} [{f.rule}] {f.message}")
            if len(by_file[fname]) > 60:
                lines.append(f"    ... 其余 {len(by_file[fname])-60} 条省略")
    out = "\n".join(lines)
    print(out)
    if args.report:
        with io.open(args.report, "w", encoding="utf-8", newline="\n") as f:
            f.write(out + "\n")

    if errors:
        return 1
    if args.strict and warnings:
        return 1
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        sys.exit(2)
