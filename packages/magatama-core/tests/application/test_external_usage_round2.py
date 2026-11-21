"""外部パッケージの利用の地図: 契約 第2版(R1〜R10)のテスト。

契約: external_usage_usecase.py の冒頭の「契約 第2版」。レビューで見つかった見逃しを塞ぐ。
設計役(MAGATAMA Advisor 側)が持ち主のテストで、実装役は変更しない。
"""

from __future__ import annotations

from pathlib import Path

import pytest

from magatama_core.application.usecases.external_usage_usecase import (
    ExternalUsageUseCase,
    FileUsage,
    analyze_source,
    language_for,
)


def tops(usage: FileUsage) -> set[str]:
    return {i.top for i in usage.imports}


def contexts(usage: FileUsage) -> set[tuple[str, str]]:
    return {(i.top, i.context) for i in usage.imports}


def gap_kinds(usage: FileUsage) -> list[str]:
    return [g.kind for g in usage.gaps]


def covered(usage: FileUsage, name: str) -> bool:
    """name を読み込みとして出したか、決まらない動的な読み込みとして gap に出したか。"""
    return name in tops(usage) or any(
        g.kind == "dynamic_import" and g.candidates is None for g in usage.gaps
    )


def write(root: Path, rel: str, content: str) -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


# ---------------------------------------------------------------- R1 ファイルのシンボリックリンク


def test_r1_link_to_unscanned_target_is_analyzed(tmp_path: Path) -> None:
    root = tmp_path / "x"
    target = write(
        root, "bin/tool", "import hidden_dep\n"
    )  # 拡張子も shebang もない → それ自体は走査されない
    (root / "tool.py").symlink_to(target)
    excluded = write(root, "node_modules/pkg/real.py", "import nm_dep\n")
    (root / "nm.py").symlink_to(excluded)
    result = ExternalUsageUseCase().execute(root)
    assert {(i.top, i.file) for i in result.imports} == {
        ("hidden_dep", "tool.py"),
        ("nm_dep", "nm.py"),
    }
    assert result.files_scanned["python"] == 2


# ---------------------------------------------------------------- R2 相対名と package


@pytest.mark.parametrize(
    "source",
    [
        "import importlib\nimportlib.import_module('.sub', package='ext')\n",
        "import importlib\nimportlib.import_module('.sub', 'ext')\n",
        "from importlib import import_module\nimport_module('..a.b', package='ext.inner')\n",
    ],
)
def test_r2_relative_name_with_literal_package(source: str) -> None:
    usage = analyze_source("python", "m.py", source)
    assert ("ext", "dynamic") in contexts(usage)


def test_r2_relative_name_with_unknown_package_is_a_gap() -> None:
    source = "import importlib\ndef f(p):\n    return importlib.import_module('.sub', package=p)\n"
    usage = analyze_source("python", "m.py", source)
    assert gap_kinds(usage).count("dynamic_import") == 1


# ---------------------------------------------------------------- R3 require の別名と AMD


@pytest.mark.parametrize(
    ("source", "name"),
    [
        (
            'import { createRequire } from "module";\nconst req = createRequire(import.meta.url);\nreq("x1");\n',
            "x1",
        ),
        (
            'const { createRequire } = require("node:module");\nconst rq = createRequire(__filename);\nrq("x1b");\n',
            "x1b",
        ),
        ('const r = require;\nr("x2");\n', "x2"),
        ('module.require("x4");\n', "x4"),
        ('define(["x3"], function (x) {});\n', "x3"),
        ('define("my-mod", ["x3b"], function (x) {});\n', "x3b"),
        ('require(["x3c"], function (x) {});\n', "x3c"),
    ],
)
def test_r3_require_aliases_and_amd(source: str, name: str) -> None:
    usage = analyze_source("javascript", "m.js", source)
    assert name in tops(usage)


@pytest.mark.parametrize(
    "source",
    [
        'require.call(null, "x");\n',
        'require.apply(null, ["x"]);\n',
        "define(deps, function () {});\n",
    ],
)
def test_r3_indirect_require_calls_are_gaps(source: str) -> None:
    usage = analyze_source("javascript", "m.js", source)
    assert "dynamic_import" in gap_kinds(usage)


# ---------------------------------------------------------------- R4 npm: の指定子


@pytest.mark.parametrize(
    ("source", "module", "top"),
    [
        ('import a from "npm:x9@1";\n', "npm:x9@1", "x9"),
        ('import b from "npm:@s/p@2/sub";\n', "npm:@s/p@2/sub", "@s/p"),
        ('import c from "npm:plain";\n', "npm:plain", "plain"),
    ],
)
def test_r4_npm_specifier(source: str, module: str, top: str) -> None:
    usage = analyze_source("typescript", "m.ts", source)
    assert [(i.module, i.top) for i in usage.imports] == [(module, top)]


# ---------------------------------------------------------------- R5 対象のファイル


def test_r5_pyw_is_python() -> None:
    assert language_for("gui.pyw") == "python"


def test_r5_shebang_scripts_and_unsupported_extensions(tmp_path: Path) -> None:
    root = tmp_path / "x"
    write(root, "bin/script", "#!/usr/bin/env python3\nimport shebang_dep\n")
    write(root, "bin/cli", '#!/usr/bin/env node\nrequire("node_shebang_dep");\n')
    write(root, "LICENSE", "import not_code\n")
    write(root, "ext/fast.pyx", "import cython_dep\n")
    write(root, "ext/fast.pxd", "cdef int x\n")
    write(root, "docs/page.mdx", 'import Box from "mdx-dep";\n')
    result = ExternalUsageUseCase().execute(root)
    assert {(i.top, i.file, i.language) for i in result.imports} == {
        ("shebang_dep", "bin/script", "python"),
        ("node_shebang_dep", "bin/cli", "javascript"),
    }
    assert sorted((g.kind, g.language, g.file) for g in result.gaps) == [
        ("unsupported_file", "javascript", "docs/page.mdx"),
        ("unsupported_file", "python", "ext/fast.pxd"),
        ("unsupported_file", "python", "ext/fast.pyx"),
    ]
    assert result.files_scanned == {"python": 1, "javascript": 1, "typescript": 0}


# ---------------------------------------------------------------- R6 Python のほかの読み込み


def test_r6_runpy_run_module_literal() -> None:
    usage = analyze_source("python", "m.py", "import runpy\nrunpy.run_module('x5')\n")
    assert ("x5", "dynamic") in contexts(usage)


@pytest.mark.parametrize(
    "source",
    [
        "import runpy\ndef f(n):\n    runpy.run_module(n)\n",
        "import importlib\ngetattr(importlib, 'import_module')('x6')\n",
        "m = getattr(__builtins__, '__import__')('x6')\n",
        "__builtins__.__import__('x6')\n",
        "import builtins\nbuiltins.__import__('x6')\n",
    ],
)
def test_r6_indirect_python_imports_are_covered(source: str) -> None:
    usage = analyze_source("python", "m.py", source)
    assert covered(usage, "x6") or "dynamic_import" in gap_kinds(usage)


# ---------------------------------------------------------------- R7 文字列のコードの実行


@pytest.mark.parametrize(
    "source",
    [
        "(0, eval)(s);\n",
        "const e = eval;\ne(s);\n",
        'const vm = require("vm");\nconst sc = new vm.Script(code);\n',
        'const vm = require("vm");\nvm.compileFunction(code);\n',
        'setTimeout("doIt()", 10);\n',
        "setInterval(`tick()`, 10);\n",
    ],
)
def test_r7_js_eval_forms_are_gaps(source: str) -> None:
    usage = analyze_source("javascript", "m.js", source)
    assert "dynamic_eval" in gap_kinds(usage)


@pytest.mark.parametrize(
    "source",
    [
        "setTimeout(fn, 10);\n",
        "setTimeout(() => go(), 10);\n",
        "const o = { eval: 1 };\nconsole.log(o.eval);\n",
    ],
)
def test_r7_js_non_eval_forms_are_not_gaps(source: str) -> None:
    usage = analyze_source("javascript", "m.js", source)
    assert "dynamic_eval" not in gap_kinds(usage)


@pytest.mark.parametrize(
    "source",
    ["e = eval\ne(s)\n", "run = exec\n", "fs = [compile]\n"],
)
def test_r7_python_eval_references_are_gaps(source: str) -> None:
    usage = analyze_source("python", "m.py", source)
    assert "dynamic_eval" in gap_kinds(usage)


# ---------------------------------------------------------------- R8 一覧が書き換えられうる場合


@pytest.mark.parametrize(
    ("language", "source"),
    [
        ("javascript", 'const m = ["a"];\nconst n = m;\nn.push(v);\nrequire(m[0]);\n'),
        ("javascript", 'const m = ["a"];\nadd(m);\nrequire(m[0]);\n'),
        (
            "python",
            "import importlib\nM = ['a']\nm = M\nm.append(x)\nimportlib.import_module(M[0])\n",
        ),
        ("python", "import importlib\nM = ['a']\nextend(M)\nimportlib.import_module(M[0])\n"),
        (
            "python",
            "import importlib\nfrom cfg import *\nNAME = 'a'\nimportlib.import_module(NAME)\n",
        ),
    ],
)
def test_r8_escaping_lists_are_not_resolved(language: str, source: str) -> None:
    usage = analyze_source(language, "m." + ("js" if language == "javascript" else "py"), source)
    assert "dynamic_import" in gap_kinds(usage)


def test_r8_plain_iteration_and_subscript_still_resolve() -> None:
    source = (
        "import importlib\nMODS = ['a', 'b']\n"
        "def f():\n    for n in MODS:\n        importlib.import_module(n)\n"
        "    return importlib.import_module(MODS[0])\n"
    )
    usage = analyze_source("python", "m.py", source)
    assert {"a", "b"} <= tops(usage)
    assert "dynamic_import" not in gap_kinds(usage)


# ---------------------------------------------------------------- R9 TYPE_CHECKING


@pytest.mark.parametrize(
    ("source", "name", "context"),
    [
        ("TYPE_CHECKING = True\nif TYPE_CHECKING:\n    import x7\n", "x7", "conditional"),
        ("import foo\nif foo.TYPE_CHECKING:\n    import x8\n", "x8", "conditional"),
        ("import typing as t\nif t.TYPE_CHECKING:\n    import x9\n", "x9", "type_only"),
        (
            "from typing_extensions import TYPE_CHECKING as TC\nif TC:\n    import x10\n",
            "x10",
            "type_only",
        ),
    ],
)
def test_r9_type_checking_must_come_from_typing(source: str, name: str, context: str) -> None:
    usage = analyze_source("python", "m.py", source)
    assert (name, context) in contexts(usage)


# ---------------------------------------------------------------- 名前が出てくるだけでは読み込みにしない


def test_name_in_comment_or_string_is_not_an_import(tmp_path: Path) -> None:
    root = tmp_path / "x"
    write(root, "a.py", '# import requests\nDOC = "use requests later"\nimport yaml\n')
    write(root, "b.js", '// require("minimist")\nconst s = "minimist";\n')
    result = ExternalUsageUseCase().execute(root)
    assert {i.top for i in result.imports} == {"yaml"}
    assert result.gaps == []
