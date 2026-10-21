#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把书稿里「自称是完整脚本」的 GDScript 代码块喂给 `godot --headless --check-only`。

⚠️ 覆盖范围有限，如实说明：
  · 全书 978 个 ```gdscript 块里，只有约 27 个首行是 `extends` / `class_name`，
    其余是**教学片段**（缺上下文、缺父类、甚至缺 `extends`），
    `--check-only` 要求完整脚本，对它们**不适用**——强行检查只会得到满屏误报。
  · 即便那 27 个，也可能引用本篇其它代码块里才定义的类/变量，
    所以本脚本是**咨询性（advisory）**的：它报告结果，不作为门禁的失败条件。

用法:
    python tools/check_gdscript_syntax.py                      # 只报告，不检查
    python tools/check_gdscript_syntax.py --godot /path/to/godot
    GODOT_BIN=/path/to/godot python tools/check_gdscript_syntax.py
"""
import argparse
import io
import os
import re
import shutil
import subprocess
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ART = os.path.join(ROOT, "articles")

BLOCK_RE = re.compile(r"```gdscript\n(.*?)```", re.S)
COMPLETE_RE = re.compile(r"^(extends\s+\w|class_name\s+\w)")


def collect():
    """返回 [(文件, 块序号, 代码)]，只含首行是 extends / class_name 的块。"""
    out = []
    for fn in sorted(os.listdir(ART)):
        if not fn.endswith(".md"):
            continue
        text = io.open(os.path.join(ART, fn), encoding="utf-8", newline="").read()
        text = text.replace("\r\n", "\n")
        for i, m in enumerate(BLOCK_RE.finditer(text), 1):
            code = m.group(1)
            first = next((l for l in code.split("\n") if l.strip()), "")
            if COMPLETE_RE.match(first):
                line = text[: m.start()].count("\n") + 1
                out.append((fn, line, code))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--godot", default=os.environ.get("GODOT_BIN", ""),
                    help="godot 可执行文件路径（默认取环境变量 GODOT_BIN）")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    blocks = collect()
    print(f"书稿中可当完整脚本检查的 GDScript 块：{len(blocks)} 个")
    if not blocks:
        return 0

    godot = args.godot
    if not godot:
        found = shutil.which("godot") or shutil.which("godot4")
        godot = found or ""
    if not godot or not os.path.exists(godot):
        print("未找到 Godot 可执行文件 —— 跳过实际检查。")
        print("  本机可执行：godot --version 后把路径传给 --godot，或设 GODOT_BIN 环境变量。")
        print("  CI 里用 workflow_dispatch 的 godot_check 输入开启（会下载 Godot 4.3 headless）。")
        return 0

    tmp = tempfile.mkdtemp(prefix="gdscript_check_")
    failures = []
    for n, (fn, line, code) in enumerate(blocks, 1):
        path = os.path.join(tmp, f"block_{n:03d}.gd")
        io.open(path, "w", encoding="utf-8", newline="\n").write(code)
        try:
            r = subprocess.run([godot, "--headless", "--check-only", "--script", path],
                               capture_output=True, text=True, timeout=60)
        except subprocess.TimeoutExpired:
            failures.append((fn, line, "超时"))
            continue
        if r.returncode != 0:
            out = (r.stdout or "") + (r.stderr or "")
            failures.append((fn, line, out.strip()[:400]))

    print(f"实际检查：{len(blocks)} 个块，失败 {len(failures)} 个")
    for fn, line, msg in failures:
        print("-" * 60)
        print(f"{fn}:{line}")
        print(msg)
    if args.verbose:
        print("\n注：失败的块里，报「Identifier not found」通常是因为它引用了本篇其它代码块的定义，")
        print("    不一定是真错误——本脚本是咨询性的。")
    return 0  # 咨询性：不作为门禁失败条件


if __name__ == "__main__":
    sys.exit(main())
