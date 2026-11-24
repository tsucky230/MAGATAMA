"""外部パッケージの利用の地図: 契約 第3版(部品の中の読み込み `internal_imports`)のテスト。

契約: KAGAMI の docs/contracts/magatama-external-usage.md の「第3版」(実装のときに external_usage_usecase.py の冒頭へ写す)。
設計役(KAGAMI 側)が持ち主のテストで、実装役は変更しない。

- analyze_source の結果(FileUsage)は internal_imports を持つ。各要素は language・specifier・kind・names・file・line・col・context
  (names は Python の from import なら ImportName の tuple、JS/TS は None)
- execute(..., include_internal=True) のときだけ to_dict() に "internal_imports" を足す。ほかの鍵は指定の有無で同じ
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from magatama_core.application.usecases.external_usage_usecase import (
    ExternalUsageUseCase,
    FileUsage,
    analyze_source,
)


def internal(usage: FileUsage) -> set[tuple[str, str, str]]:
    return {(i.specifier, i.kind, i.context) for i in usage.internal_imports}


def tops(usage: FileUsage) -> set[str]:
    return {i.top for i in usage.imports}


def gap_kinds(usage: FileUsage) -> list[str]:
    return [g.kind for g in usage.gaps]


def write(root: Path, rel: str, content: str) -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


# ---------------------------------------------------------------- A17 JS/TS の全形式


@pytest.mark.parametrize(
    ("language", "source", "expected"),
    [
        ("javascript", 'import a from "./a";\n', {("./a", "import", "module")}),
        ("javascript", 'import "./side";\n', {("./side", "import", "module")}),
        ("javascript", 'export { x } from "../x";\n', {("../x", "export_from", "module")}),
        ("javascript", 'export * from "./all";\n', {("./all", "export_from", "module")}),
        ("javascript", 'const b = require("./b");\n', {("./b", "require", "module")}),
        ("javascript", 'function f() {\n  return require("./c");\n}\n', {("./c", "require", "function")}),
        (
            "javascript",
            'const { createRequire } = require("module");\nconst r2 = createRequire(__filename);\nr2("./d");\n',
            {("./d", "require", "module")},
        ),
        ("javascript", 'const r = require;\nr("./e");\n', {("./e", "require", "module")}),
        ("javascript", 'define(["./f", "lodash"], function (f, _) {});\n', {("./f", "amd", "module")}),
        ("javascript", 'require(["./g"], function (g) {});\n', {("./g", "amd", "module")}),
        ("javascript", 'async function f() {\n  await import("./h");\n}\n', {("./h", "dynamic_import", "function")}),
        ("javascript", "const i = require(`./i`);\n", {("./i", "require", "module")}),
        ("javascript", 'import y from "#internal/y";\n', {("#internal/y", "import", "module")}),
        ("javascript", 'importScripts("./worker-lib.js");\n', {("./worker-lib.js", "import_scripts", "module")}),
        ("javascript", 'const m = require("/abs/m");\n', {("/abs/m", "require", "module")}),
        ("typescript", 'import type { T } from "./types";\n', {("./types", "import", "type_only")}),
        ("javascript", 'const M = "./j";\nrequire(M);\n', {("./j", "require", "dynamic")}),
        (
            "javascript",
            'const MODS = ["./k", "./l"];\nfor (const m of MODS) require(m);\n',
            {("./k", "require", "dynamic"), ("./l", "require", "dynamic")},
        ),
    ],
)
def test_js_internal_imports_every_form(language: str, source: str, expected: set[tuple[str, str, str]]) -> None:
    usage = analyze_source(language, "pkg/index.js" if language == "javascript" else "pkg/index.ts", source)
    assert internal(usage) == expected
    assert usage.gaps == []
    assert all(i.names is None and i.language == language for i in usage.internal_imports)


def test_js_internal_import_records_file_line_col() -> None:
    # 列は imports と同じ決め方(同じ位置に書いた外部の require と同じ列)
    usage = analyze_source("javascript", "toString.js", 'var x = 1;\nvar baseToString = require("./_baseToString");\n')
    ext = analyze_source("javascript", "toString.js", 'var x = 1;\nvar baseToString = require("lodashxxxxxxxx");\n')
    [rec] = usage.internal_imports
    assert (rec.file, rec.line, rec.specifier) == ("toString.js", 2, "./_baseToString")
    assert rec.col == ext.imports[0].col


def test_js_external_imports_are_unchanged_by_internal_collection() -> None:
    # 内部の指定子は imports に出ない(第2版のまま)。外部の指定子は internal_imports に出ない
    usage = analyze_source("javascript", "a.js", 'require("./x");\nrequire("lodash/template");\ndefine(["./f", "axios"], f);\n')
    assert tops(usage) == {"lodash", "axios"}
    assert internal(usage) == {("./x", "require", "module"), ("./f", "amd", "module")}


# ---------------------------------------------------------------- A18 Python の全形式


def py_internal(usage: FileUsage) -> set[tuple[str, str, str, tuple[tuple[str, str | None], ...] | None]]:
    return {
        (
            i.specifier,
            i.kind,
            i.context,
            None if i.names is None else tuple((n.name, n.alias) for n in i.names),
        )
        for i in usage.internal_imports
    }


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("from . import a, b\n", {(".", "from_import", "module", (("a", None), ("b", None)))}),
        ("from .x import y as z\n", {(".x", "from_import", "module", (("y", "z"),))}),
        ("from ..p.q import r\n", {("..p.q", "from_import", "module", (("r", None),))}),
        ("def f():\n    from . import g\n", {(".", "from_import", "function", (("g", None),))}),
        (
            "from typing import TYPE_CHECKING\nif TYPE_CHECKING:\n    from .t import T\n",
            {(".t", "from_import", "type_only", (("T", None),))},
        ),
        (
            "import importlib\nimportlib.import_module('.m', package=__package__)\n",
            {(".m", "import_module", "dynamic", ())},
        ),
        (
            "import importlib\nMODS = ['.m1', '.m2']\nfor n in MODS:\n    importlib.import_module(n, package=__package__)\n",
            {(".m1", "import_module", "dynamic", ()), (".m2", "import_module", "dynamic", ())},
        ),
    ],
)
def test_python_internal_imports_every_form(source: str, expected: set[tuple[object, ...]]) -> None:
    usage = analyze_source("python", "pkg/mod.py", source)
    assert py_internal(usage) == expected
    assert "dynamic_import" not in gap_kinds(usage)


def test_python_absolute_self_import_stays_in_imports() -> None:
    # 部品の自分の名前への絶対の読み込みは、第2版どおり imports に出る(internal_imports には出ない)
    usage = analyze_source("python", "pkg/mod.py", "import pkg.sub\nfrom pkg import other\n")
    assert tops(usage) == {"pkg"}
    assert list(usage.internal_imports) == []


# ---------------------------------------------------------------- A19 値の決まらない内部の動的な読み込み


@pytest.mark.parametrize(
    ("language", "source"),
    [
        ("javascript", 'function f(name) {\n  return require("./" + name);\n}\n'),
        ("javascript", "async function f(x) {\n  return import(`./${x}`);\n}\n"),
        ("python", "import importlib\ndef f(name):\n    return importlib.import_module(name, package=__package__)\n"),
    ],
)
def test_unresolvable_internal_dynamic_import_is_a_gap(language: str, source: str) -> None:
    usage = analyze_source(language, "pkg/x.js" if language == "javascript" else "pkg/x.py", source)
    assert "dynamic_import" in gap_kinds(usage)
    assert list(usage.internal_imports) == []


# ---------------------------------------------------------------- 不変条件 6(プロパティ)

_SEGMENT = st.from_regex(r"[a-z_][a-z0-9_]{0,7}", fullmatch=True)
_REL_JS = st.builds(
    lambda prefix, parts: prefix + "/".join(parts),
    st.sampled_from(["./", "../", "../../"]),
    st.lists(_SEGMENT, min_size=1, max_size=3),
)


@settings(max_examples=60, deadline=None)
@given(specs=st.lists(_REL_JS, min_size=1, max_size=4, unique=True), loop=st.booleans())
def test_every_internal_js_specifier_is_reported(specs: list[str], loop: bool) -> None:
    if loop:
        source = "const MODS = [" + ", ".join(json.dumps(s) for s in specs) + "];\nfor (const m of MODS) require(m);\n"
    else:
        source = "".join(f"require({json.dumps(s)});\n" for s in specs)
    usage = analyze_source("javascript", "pkg/i.js", source)
    assert {i.specifier for i in usage.internal_imports} == set(specs)


@settings(max_examples=60, deadline=None)
@given(dots=st.integers(min_value=1, max_value=3), parts=st.lists(_SEGMENT, min_size=0, max_size=2), name=_SEGMENT)
def test_every_relative_python_import_is_reported(dots: int, parts: list[str], name: str) -> None:
    spec = "." * dots + ".".join(parts)
    usage = analyze_source("python", "pkg/a/b/c/m.py", f"from {spec} import {name}\n")
    assert [(i.specifier, tuple(n.name for n in i.names or ())) for i in usage.internal_imports] == [(spec, (name,))]


# ---------------------------------------------------------------- A16・A21 execute と to_dict


@pytest.fixture
def package_root(tmp_path: Path) -> Path:
    root = tmp_path / "pkg"
    write(root, "template.js", 'var a = require("./_a");\nvar _ = require("lodash/x");\nmodule.exports = a;\n')
    write(root, "_a.js", "module.exports = function a() {};\n")
    write(root, "esm/index.mjs", 'export * from "./util.mjs";\nimport "#private";\n')
    write(root, "py/__init__.py", "from . import core\nfrom .core import run\nimport yaml\n")
    write(root, "py/core.py", "from ..shared import helper\n\ndef run():\n    pass\n")
    return root


def _hashes(root: Path) -> dict[str, str]:
    return {
        p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(root.rglob("*"))
        if p.is_file()
    }


def test_without_flag_there_is_no_internal_imports_key(package_root: Path) -> None:
    data = ExternalUsageUseCase().execute(package_root).to_dict()
    assert "internal_imports" not in data


def test_with_flag_only_adds_internal_imports(package_root: Path) -> None:
    without = ExternalUsageUseCase().execute(package_root).to_dict()
    with_internal = ExternalUsageUseCase().execute(package_root, include_internal=True).to_dict()
    internal_rows = with_internal.pop("internal_imports")
    assert with_internal == without
    assert [(r["file"], r["specifier"], r["kind"], r["names"]) for r in internal_rows] == [
        ("esm/index.mjs", "./util.mjs", "export_from", None),
        ("esm/index.mjs", "#private", "import", None),
        ("py/__init__.py", ".", "from_import", [{"name": "core", "alias": None}]),
        ("py/__init__.py", ".core", "from_import", [{"name": "run", "alias": None}]),
        ("py/core.py", "..shared", "from_import", [{"name": "helper", "alias": None}]),
        ("template.js", "./_a", "require", None),
    ]
    assert set(internal_rows[0]) == {"language", "specifier", "kind", "names", "file", "line", "col", "context"}


def test_with_flag_is_deterministic_and_writes_nothing(package_root: Path) -> None:
    before = _hashes(package_root)
    first = json.dumps(ExternalUsageUseCase().execute(package_root, include_internal=True).to_dict(), ensure_ascii=False)
    second = json.dumps(ExternalUsageUseCase().execute(package_root, include_internal=True).to_dict(), ensure_ascii=False)
    assert first == second
    assert _hashes(package_root) == before
