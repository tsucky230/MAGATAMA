"""外部パッケージの利用の地図(ExternalUsageUseCase / analyze_source)のテスト。

契約: magatama_core/application/usecases/external_usage_usecase.py の docstring。
最も重い誤りは「使っているのに地図に出ない(見逃し)」。罠の表は MAGATAMA Advisor の正解データ
(Python・JS/TS の検証用プロジェクト)と同じ作り。設計役(MAGATAMA Advisor 側)が持ち主のテストで、
実装役は変更しない。
"""

from __future__ import annotations

import ast
import hashlib
import json
import os
from pathlib import Path

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from magatama_core.application.usecases.external_usage_usecase import (
    ExternalUsageUseCase,
    FileUsage,
    ImportName,
    RootNotFoundError,
    analyze_source,
    language_for,
)

# ---------------------------------------------------------------- 補助


def imports_of(usage: FileUsage) -> list[tuple]:
    """比較用に (module, top, alias, names, line, context, enclosing) を並べる。"""
    return sorted(
        (i.module, i.top, i.alias, i.names, i.line, i.context, i.enclosing) for i in usage.imports
    )


def tops(usage_or_imports) -> set[str]:
    items = (
        usage_or_imports.imports if isinstance(usage_or_imports, FileUsage) else usage_or_imports
    )
    return {i.top for i in items}


def gaps_of(usage: FileUsage, kind: str) -> list:
    return [g for g in usage.gaps if g.kind == kind]


def col_of(source: str, line: int, text: str) -> int:
    return source.splitlines()[line - 1].index(text)


# ---------------------------------------------------------------- 言語の判定


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("a.py", "python"),
        ("a.pyi", "python"),
        ("A.PY", "python"),
        ("a.js", "javascript"),
        ("a.mjs", "javascript"),
        ("a.cjs", "javascript"),
        ("a.jsx", "javascript"),
        ("a.ts", "typescript"),
        ("a.tsx", "typescript"),
        ("a.mts", "typescript"),
        ("a.cts", "typescript"),
        ("types/a.d.ts", "typescript"),
        ("a.vue", None),
        ("a.ipynb", None),
        ("a.md", None),
        ("Makefile", None),
    ],
)
def test_language_for(path: str, expected: str | None) -> None:
    assert language_for(path) == expected


def test_unknown_language_raises() -> None:
    with pytest.raises(ValueError):
        analyze_source("ruby", "a.rb", "require 'x'")


# ---------------------------------------------------------------- Python の罠(正解データと同じ作り)

PY_CONFIG_LOADER = """import yaml


def load_config(path):
    with open(path, encoding="utf-8") as f:
        return yaml.load(f, Loader=yaml.FullLoader)
"""

PY_RENDER = """def render_greeting(name):
    import jinja2

    return jinja2.Template("Hello {{ name }}").render(name=name)
"""

PY_PLUGINS = """import importlib

PLUGIN_MODULES = ["urllib3"]


def load_plugins():
    return [importlib.import_module(name) for name in PLUGIN_MODULES]


def fetch(url):
    http = load_plugins()[0].PoolManager()
    return http.request("GET", url).data
"""


def test_python_top_level_import_and_dangerous_call() -> None:
    usage = analyze_source("python", "app/config_loader.py", PY_CONFIG_LOADER)
    assert imports_of(usage) == [("yaml", "yaml", None, (), 1, "module", None)]
    assert usage.imports[0].col == 0
    assert usage.imports[0].language == "python"
    assert usage.imports[0].file == "app/config_loader.py"
    uses = sorted((u.kind, u.name, u.top, u.line, u.col, u.enclosing) for u in usage.uses)
    assert uses == [
        ("call", "yaml.load", "yaml", 6, col_of(PY_CONFIG_LOADER, 6, "yaml.load"), "load_config"),
        (
            "reference",
            "yaml.FullLoader",
            "yaml",
            6,
            col_of(PY_CONFIG_LOADER, 6, "yaml.FullLoader"),
            "load_config",
        ),
    ]
    assert usage.gaps == []


def test_python_import_inside_function_is_found() -> None:
    usage = analyze_source("python", "app/render.py", PY_RENDER)
    assert imports_of(usage) == [("jinja2", "jinja2", None, (), 2, "function", "render_greeting")]
    names = {(u.kind, u.name) for u in usage.uses}
    assert ("call", "jinja2.Template") in names
    assert all(not u.name.endswith(".render") for u in usage.uses)  # 戻り値への呼び出しは追わない
    assert usage.gaps == []


def test_python_dynamic_import_resolved_from_module_constant_list() -> None:
    usage = analyze_source("python", "app/plugins.py", PY_PLUGINS)
    found = imports_of(usage)
    assert ("importlib", "importlib", None, (), 1, "module", None) in found
    assert ("urllib3", "urllib3", None, (), 7, "dynamic", "load_plugins") in found
    assert gaps_of(usage, "dynamic_import") == []


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        # 別名・サブモジュール
        ("import os.path as p\n", [("os.path", "os", "p", (), 1, "module", None)]),
        (
            "from a.b import x as y, z\n",
            [("a.b", "a", None, (ImportName("x", "y"), ImportName("z", None)), 1, "module", None)],
        ),
        (
            "import a, b.c\n",
            [("a", "a", None, (), 1, "module", None), ("b.c", "b", None, (), 1, "module", None)],
        ),
        # 相対 import は出さない
        ("from . import sibling\nfrom .mod import x\nfrom ..pkg import y\n", []),
        # 条件つき(try・if・with)
        (
            "try:\n    import ujson as json\nexcept ImportError:\n    import json\n",
            [
                ("json", "json", None, (), 4, "conditional", None),
                ("ujson", "ujson", "json", (), 2, "conditional", None),
            ],
        ),
        (
            "import sys\nif sys.version_info < (3, 11):\n    import tomli\n",
            [
                ("sys", "sys", None, (), 1, "module", None),
                ("tomli", "tomli", None, (), 3, "conditional", None),
            ],
        ),
        # 型検査のときだけの import
        (
            "from typing import TYPE_CHECKING\nif TYPE_CHECKING:\n    import yaml\n",
            [
                ("typing", "typing", None, (ImportName("TYPE_CHECKING", None),), 1, "module", None),
                ("yaml", "yaml", None, (), 3, "type_only", None),
            ],
        ),
        (
            "import typing\nif typing.TYPE_CHECKING:\n    from yaml import Loader\n",
            [
                ("typing", "typing", None, (), 1, "module", None),
                ("yaml", "yaml", None, (ImportName("Loader", None),), 3, "type_only", None),
            ],
        ),
        # クラスのメソッドの中、ラムダの中
        (
            "class C:\n    def m(self):\n        import requests\n        return requests\n",
            [("requests", "requests", None, (), 3, "function", "m")],
        ),
        (
            "class C:\n    import attr\n",
            [("attr", "attr", None, (), 2, "function", "C")],
        ),
        # __import__ と import_module の別名(文字列)
        ("x = __import__('yaml')\n", [("yaml", "yaml", None, (), 1, "dynamic", None)]),
        (
            "from importlib import import_module as im\nm = im('yaml')\n",
            [
                (
                    "importlib",
                    "importlib",
                    None,
                    (ImportName("import_module", "im"),),
                    1,
                    "module",
                    None,
                ),
                ("yaml", "yaml", None, (), 2, "dynamic", None),
            ],
        ),
        # 一覧の添字は、一覧の全要素(多めに出す)
        (
            "import importlib\nMODS = ('a', 'b')\nm = importlib.import_module(MODS[1])\n",
            [
                ("a", "a", None, (), 3, "dynamic", None),
                ("b", "b", None, (), 3, "dynamic", None),
                ("importlib", "importlib", None, (), 1, "module", None),
            ],
        ),
        # for 文の変数
        (
            "import importlib\nMODS = ['a']\ndef f():\n    for n in MODS:\n        importlib.import_module(n)\n",
            [
                ("a", "a", None, (), 5, "dynamic", "f"),
                ("importlib", "importlib", None, (), 1, "module", None),
            ],
        ),
    ],
)
def test_python_import_forms(source: str, expected: list[tuple]) -> None:
    usage = analyze_source("python", "m.py", source)
    assert imports_of(usage) == sorted(expected)


def test_pyi_imports_are_type_only() -> None:
    usage = analyze_source("python", "stubs/m.pyi", "import yaml\nfrom jinja2 import Template\n")
    assert {(i.top, i.context) for i in usage.imports} == {
        ("yaml", "type_only"),
        ("jinja2", "type_only"),
    }


@pytest.mark.parametrize(
    "source",
    [
        "import importlib\ndef f(name):\n    return importlib.import_module(name)\n",
        "import importlib\nx = 'p'\nimportlib.import_module(f'plugins.{x}')\n",
        "def f(n):\n    return __import__(n)\n",
        "import importlib\nNAME = 'a'\nNAME = 'b' + 'c'\nimportlib.import_module(NAME)\n",
    ],
)
def test_python_unresolvable_dynamic_import_is_a_gap(source: str) -> None:
    usage = analyze_source("python", "m.py", source)
    gaps = gaps_of(usage, "dynamic_import")
    assert len(gaps) == 1
    assert gaps[0].candidates is None
    assert gaps[0].language == "python"
    assert gaps[0].line == len(source.rstrip("\n").splitlines())
    assert all(i.context != "dynamic" for i in usage.imports)


@pytest.mark.parametrize(
    ("source", "count"),
    [
        ("exec('import yaml')\n", 1),
        ("x = eval(s)\n", 1),
        ("code = compile(s, 'f', 'exec')\n", 1),
        ("def f(s):\n    exec(s)\n    return eval(s)\n", 2),
    ],
)
def test_python_dynamic_eval_is_a_gap(source: str, count: int) -> None:
    usage = analyze_source("python", "m.py", source)
    assert len(gaps_of(usage, "dynamic_eval")) == count


def test_python_from_import_and_alias_calls_are_resolved() -> None:
    source = "from yaml import load\nimport yaml as y\nload(s)\ny.safe_load(s)\n"
    usage = analyze_source("python", "m.py", source)
    assert {(u.kind, u.name, u.top) for u in usage.uses} == {
        ("call", "yaml.load", "yaml"),
        ("call", "yaml.safe_load", "yaml"),
    }


def test_python_syntax_error_is_parse_error_without_imports() -> None:
    usage = analyze_source("python", "broken.py", "import yaml\ndef f(:\n    pass\n")
    gaps = gaps_of(usage, "parse_error")
    assert len(gaps) == 1
    assert gaps[0].line == 2
    assert usage.imports == []


def test_python_string_reference_safety_net() -> None:
    source = 'INSTALLED_APPS = ["yaml.contrib", "yamlfoo", "other"]\nmod = sys.modules["yaml"]\n'
    usage = analyze_source("python", "settings.py", source, packages=frozenset({"yaml"}))
    refs = gaps_of(usage, "string_reference")
    assert sorted((g.line, g.candidates) for g in refs) == [(1, ("yaml",)), (2, ("yaml",))]
    assert analyze_source("python", "settings.py", source).gaps == []  # packages なしでは出さない


# ---------------------------------------------------------------- JS/TS の罠(正解データと同じ作り)

JS_RENDER = """function renderGreeting(name) {
  const template = require("lodash/template");
  return template("Hello <%= name %>")({ name });
}

module.exports = { renderGreeting };
"""

JS_HTTP = """const CLIENT_MODULES = ["axios"];

function loadClient() {
  const name = CLIENT_MODULES[0];
  return require(name);
}

async function fetchText(url) {
  const client = loadClient();
  const response = await client.get(url);
  return response.data;
}

module.exports = { fetchText };
"""

TS_TOKEN = """import type { JwtPayload } from "jsonwebtoken";

export function subjectOf(payload: JwtPayload): string | undefined {
  return payload.sub;
}
"""

JS_MAIN = """const { renderGreeting } = require("./render");
const { fetchText } = require("./http");

async function main(argv) {
  console.log(renderGreeting(argv[2] || "world"));
}

main(process.argv);
"""


def test_js_require_of_subpath_inside_function() -> None:
    usage = analyze_source("javascript", "src/render.js", JS_RENDER)
    assert imports_of(usage) == [
        ("lodash/template", "lodash", "template", (), 2, "function", "renderGreeting")
    ]
    assert [(u.kind, u.name, u.top, u.line) for u in usage.uses] == [
        ("call", "lodash/template", "lodash", 3)
    ]
    assert usage.gaps == []


def test_js_dynamic_require_resolved_from_constant_array() -> None:
    usage = analyze_source("javascript", "src/http.js", JS_HTTP)
    assert imports_of(usage) == [("axios", "axios", None, (), 5, "dynamic", "loadClient")]
    assert gaps_of(usage, "dynamic_import") == []


def test_ts_import_type_is_type_only() -> None:
    usage = analyze_source("typescript", "src/token.ts", TS_TOKEN)
    assert imports_of(usage) == [
        (
            "jsonwebtoken",
            "jsonwebtoken",
            None,
            (ImportName("JwtPayload", None),),
            1,
            "type_only",
            None,
        )
    ]


def test_js_relative_requires_are_not_reported() -> None:
    usage = analyze_source("javascript", "src/main.js", JS_MAIN)
    assert usage.imports == []
    assert usage.gaps == []


@pytest.mark.parametrize(
    ("language", "source", "expected"),
    [
        (
            "javascript",
            'import axios from "axios";\n',
            [("axios", "axios", "axios", (), 1, "module", None)],
        ),
        (
            "javascript",
            'import * as fs from "fs-extra";\n',
            [("fs-extra", "fs-extra", "fs", (), 1, "module", None)],
        ),
        (
            "javascript",
            'import { a as b, c } from "@scope/pkg/sub";\n',
            [
                (
                    "@scope/pkg/sub",
                    "@scope/pkg",
                    None,
                    (ImportName("a", "b"), ImportName("c", None)),
                    1,
                    "module",
                    None,
                )
            ],
        ),
        (
            "javascript",
            'import "side-effect-pkg";\n',
            [("side-effect-pkg", "side-effect-pkg", None, (), 1, "module", None)],
        ),
        (
            "javascript",
            'export { x } from "re-export";\n',
            [("re-export", "re-export", None, (ImportName("x", None),), 1, "module", None)],
        ),
        (
            "javascript",
            "const m = require(`lodash`);\n",
            [("lodash", "lodash", "m", (), 1, "module", None)],
        ),
        (
            "javascript",
            "async function f() {\n  await import('dayjs');\n}\n",
            [("dayjs", "dayjs", None, (), 2, "function", "f")],
        ),
        (
            "javascript",
            "if (process.env.X) {\n  require('debug');\n}\n",
            [("debug", "debug", None, (), 2, "conditional", None)],
        ),
        (
            "javascript",
            'importScripts("node_modules/vuln-pkg/dist/index.js");\n',
            [("node_modules/vuln-pkg/dist/index.js", "vuln-pkg", None, (), 1, "module", None)],
        ),
        ("javascript", 'importScripts("lib/local.js");\n', []),
        (
            "javascript",
            'const x = require("./x");\nimport y from "../y";\nimport z from "/abs/z";\n',
            [],
        ),
        (
            "javascript",
            'const CLIENTS = ["a", "b"];\nconst c = require(CLIENTS[1]);\n',
            [("a", "a", "c", (), 2, "dynamic", None), ("b", "b", "c", (), 2, "dynamic", None)],
        ),
        (
            "typescript",
            'export type { T } from "types-pkg";\n',
            [("types-pkg", "types-pkg", None, (ImportName("T", None),), 1, "type_only", None)],
        ),
        (
            "typescript",
            'import { type A } from "pkg-a";\nimport { type B, C } from "pkg-b";\n',
            [
                ("pkg-a", "pkg-a", None, (ImportName("A", None),), 1, "type_only", None),
                (
                    "pkg-b",
                    "pkg-b",
                    None,
                    (ImportName("B", None), ImportName("C", None)),
                    2,
                    "module",
                    None,
                ),
            ],
        ),
        (
            "typescript",
            'import express from "express";\nconst app: express.Express = express();\n',
            [("express", "express", "express", (), 1, "module", None)],
        ),
    ],
)
def test_js_ts_import_forms(language: str, source: str, expected: list[tuple]) -> None:
    usage = analyze_source(
        language, "src/m." + ("ts" if language == "typescript" else "js"), source
    )
    assert imports_of(usage) == sorted(expected)


def test_dts_imports_are_type_only() -> None:
    usage = analyze_source("typescript", "types/index.d.ts", 'import { Foo } from "foo-lib";\n')
    assert [(i.top, i.context) for i in usage.imports] == [("foo-lib", "type_only")]


@pytest.mark.parametrize(
    "source",
    [
        "function f(n) {\n  return require(n);\n}\n",
        "const n = 'p';\nconst m = require(`./plugins/${n}`);\n",
        "async function f(n) {\n  return import(n);\n}\n",
        "importScripts(self.location + '/x.js');\n",
        "let NAME = 'a';\nNAME = 'b';\nrequire(NAME);\n",
    ],
)
def test_js_unresolvable_dynamic_import_is_a_gap(source: str) -> None:
    usage = analyze_source("javascript", "src/m.js", source)
    gaps = gaps_of(usage, "dynamic_import")
    assert len(gaps) == 1
    assert gaps[0].candidates is None
    assert gaps[0].language == "javascript"


@pytest.mark.parametrize(
    ("source", "count"),
    [
        ("eval('require(\"x\")');\n", 1),
        ("const f = new Function('a', 'return a');\n", 1),
        ("const f = Function('return 1');\n", 1),
        (
            "const vm = require('vm');\nvm.runInNewContext(code);\nvm.runInThisContext(code);\nvm.runInContext(code, ctx);\n",
            3,
        ),
    ],
)
def test_js_dynamic_eval_is_a_gap(source: str, count: int) -> None:
    usage = analyze_source("javascript", "src/m.js", source)
    assert len(gaps_of(usage, "dynamic_eval")) == count


def test_js_calls_through_import_bindings() -> None:
    source = (
        'import axios from "axios";\nimport { get } from "lodash";\naxios.get(u);\nget(o, "a");\n'
    )
    usage = analyze_source("javascript", "src/m.js", source)
    assert {(u.kind, u.name, u.top) for u in usage.uses} == {
        ("call", "axios.get", "axios"),
        ("call", "lodash.get", "lodash"),
    }


def test_js_syntax_error_is_parse_error() -> None:
    usage = analyze_source("javascript", "src/broken.js", 'import x from "x";\nfunction (\n')
    assert len(gaps_of(usage, "parse_error")) == 1


def test_js_string_reference_safety_net() -> None:
    source = 'const plugins = ["lodash/fp", "lodashx"];\n'
    usage = analyze_source("javascript", "src/m.js", source, packages=frozenset({"lodash"}))
    assert [(g.line, g.candidates) for g in gaps_of(usage, "string_reference")] == [
        (1, ("lodash",))
    ]


# ---------------------------------------------------------------- ディレクトリの走査(外側の層)


def write(root: Path, rel: str, content: str | bytes) -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(content, bytes):
        path.write_bytes(content)
    else:
        path.write_text(content, encoding="utf-8")
    return path


@pytest.fixture
def py_sample(tmp_path: Path) -> Path:
    root = tmp_path / "vuln-sample"
    write(
        root,
        "requirements.txt",
        "PyYAML==5.3.1\nJinja2==2.11.2\nurllib3==1.26.4\nrequests==2.25.0\n",
    )
    write(root, "app/config_loader.py", PY_CONFIG_LOADER)
    write(root, "app/render.py", PY_RENDER)
    write(root, "app/plugins.py", PY_PLUGINS)
    write(
        root,
        "app/main.py",
        "import sys\n\nfrom app.config_loader import load_config\n\n\ndef main(argv):\n    return load_config(argv[1])\n",
    )
    return root


@pytest.fixture
def js_sample(tmp_path: Path) -> Path:
    root = tmp_path / "vuln-sample-js"
    write(root, "package.json", '{"dependencies": {"axios": "0.21.1", "minimist": "1.2.5"}}\n')
    write(root, "src/render.js", JS_RENDER)
    write(root, "src/http.js", JS_HTTP)
    write(root, "src/token.ts", TS_TOKEN)
    write(root, "src/main.js", JS_MAIN)
    return root


def test_execute_python_sample(py_sample: Path) -> None:
    result = ExternalUsageUseCase().execute(py_sample)
    found = {(i.top, i.file, i.context) for i in result.imports}
    assert ("yaml", "app/config_loader.py", "module") in found
    assert ("jinja2", "app/render.py", "function") in found
    assert ("urllib3", "app/plugins.py", "dynamic") in found
    assert "requests" not in tops(result.imports)
    assert all("requests" not in (g.candidates or ()) for g in result.gaps)
    assert result.files_scanned == {"python": 4, "javascript": 0, "typescript": 0}
    assert ("call", "yaml.load") in {(u.kind, u.name) for u in result.uses}


def test_execute_js_sample(js_sample: Path) -> None:
    result = ExternalUsageUseCase().execute(js_sample)
    found = {(i.module, i.top, i.context) for i in result.imports}
    assert found == {
        ("lodash/template", "lodash", "function"),
        ("axios", "axios", "dynamic"),
        ("jsonwebtoken", "jsonwebtoken", "type_only"),
    }
    assert "minimist" not in tops(result.imports)
    assert result.gaps == []
    assert result.files_scanned == {"python": 0, "javascript": 3, "typescript": 1}


def test_execute_excludes_default_dirs_and_venv_and_globs(tmp_path: Path) -> None:
    root = tmp_path / "x"
    write(root, "app.py", "import yaml\n")
    write(root, "node_modules/minimist/index.js", 'require("evil-dep");\n')
    write(root, ".venv/pyvenv.cfg", "home = x\n")
    write(root, ".venv/lib/site.py", "import venv_only_dep\n")
    write(root, "myenv/pyvenv.cfg", "home = x\n")
    write(root, "myenv/lib/x.py", "import env_only_dep\n")
    write(root, "build/gen.py", "import build_only_dep\n")
    write(root, ".git/hooks/h.py", "import git_only_dep\n")
    result = ExternalUsageUseCase().execute(root, exclude=["build"])
    assert tops(result.imports) == {"yaml"}
    assert sorted(result.excluded_dirs) == [".git", ".venv", "build", "myenv", "node_modules"]


def test_execute_reports_unreadable_unsupported_and_parse_errors(tmp_path: Path) -> None:
    root = tmp_path / "x"
    write(root, "ok.py", "import yaml\n")
    write(root, "broken.py", "def f(:\n")
    write(root, "broken.ts", "import x from 'x';\nfunction (\n")
    write(root, "latin1.py", b"# \xff\xfe not utf-8\nimport hidden_dep\n")
    write(root, "comp.vue", '<script>\nimport v from "vue-only-dep";\n</script>\n')
    write(root, "nb.ipynb", '{"cells": []}\n')
    write(root, "ev.py", "exec(open('x').read())\n")
    result = ExternalUsageUseCase().execute(root)
    kinds = sorted((g.kind, g.language, g.file) for g in result.gaps)
    assert kinds == [
        ("dynamic_eval", "python", "ev.py"),
        ("parse_error", "python", "broken.py"),
        ("parse_error", "typescript", "broken.ts"),
        ("unreadable", "python", "latin1.py"),
        ("unsupported_file", "javascript", "comp.vue"),
        ("unsupported_file", "python", "nb.ipynb"),
    ]
    assert result.files_scanned == {"python": 3, "javascript": 0, "typescript": 1}


def _link_dir(link: Path, target: Path) -> None:
    try:
        link.symlink_to(target, target_is_directory=True)
    except OSError:
        import _winapi  # Windows で symlink の権限がないときはジャンクションで同じ状況を作る

        _winapi.CreateJunction(str(target), str(link))


def test_execute_does_not_follow_directory_links_and_stops_on_loops(tmp_path: Path) -> None:
    root = tmp_path / "x"
    write(root, "a/app.py", "import yaml\n")
    _link_dir(root / "a" / "loop", root)  # root の中へのループ
    outside = tmp_path / "outside"
    write(outside, "ext.py", "import outside_dep\n")
    _link_dir(root / "ext", outside)  # root の外
    result = ExternalUsageUseCase().execute(root)
    assert tops(result.imports) == {"yaml"}
    assert result.files_scanned["python"] == 1
    assert [(g.kind, g.language, g.file) for g in result.gaps] == [("outside_root", "any", "ext")]


def test_execute_file_symlink_inside_root_is_not_double_counted(tmp_path: Path) -> None:
    root = tmp_path / "x"
    real = write(root, "real.py", "import yaml\n")
    try:
        (root / "alias.py").symlink_to(real)
    except OSError:
        pytest.fail("この環境ではファイルのシンボリックリンクを作れない(テストの前提を見直す)")
    result = ExternalUsageUseCase().execute(root)
    assert result.files_scanned["python"] == 1
    assert [i.file for i in result.imports] == ["real.py"]


def _snapshot(root: Path) -> dict[str, str]:
    snap: dict[str, str] = {}
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        for name in dirnames + filenames:
            path = Path(dirpath) / name
            rel = path.relative_to(root).as_posix()
            snap[rel] = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else "<dir>"
    return snap


def test_execute_does_not_write_into_root(py_sample: Path, js_sample: Path) -> None:
    for root in (py_sample, js_sample):
        before = _snapshot(root)
        ExternalUsageUseCase().execute(root, packages=["yaml", "lodash"])
        assert _snapshot(root) == before


def test_execute_is_deterministic(py_sample: Path) -> None:
    first = json.dumps(ExternalUsageUseCase().execute(py_sample).to_dict(), ensure_ascii=False)
    second = json.dumps(ExternalUsageUseCase().execute(py_sample).to_dict(), ensure_ascii=False)
    assert first == second


def test_execute_missing_or_file_root_raises(tmp_path: Path) -> None:
    with pytest.raises(RootNotFoundError):
        ExternalUsageUseCase().execute(tmp_path / "nope")
    file_root = write(tmp_path, "f.py", "import yaml\n")
    with pytest.raises(RootNotFoundError):
        ExternalUsageUseCase().execute(file_root)


def test_to_dict_shape(py_sample: Path) -> None:
    write(py_sample, "app/settings.py", 'APPS = ["yaml"]\n')
    data = ExternalUsageUseCase().execute(py_sample, packages=["yaml"]).to_dict()
    assert list(data) == [
        "schema_version",
        "tool",
        "root",
        "files_scanned",
        "excluded_dirs",
        "imports",
        "uses",
        "gaps",
    ]
    assert data["schema_version"] == "1"
    assert data["tool"]["name"] == "magatama"
    assert data["tool"]["version"]
    assert "\\" not in data["root"]
    assert Path(data["root"]) == py_sample.resolve()
    yaml_import = next(i for i in data["imports"] if i["top"] == "yaml")
    assert yaml_import == {
        "language": "python",
        "module": "yaml",
        "top": "yaml",
        "alias": None,
        "names": [],
        "file": "app/config_loader.py",
        "line": 1,
        "col": 0,
        "context": "module",
        "enclosing": None,
    }
    keys = [(i["file"], i["line"], i["col"]) for i in data["imports"]]
    assert keys == sorted(keys)
    ref = next(g for g in data["gaps"] if g["kind"] == "string_reference")
    assert ref["candidates"] == ["yaml"]
    json.dumps(data)  # そのまま JSON にできる


# ---------------------------------------------------------------- 不変条件(プロパティテスト)

_SETTINGS = settings(max_examples=200, deadline=None, suppress_health_check=[HealthCheck.too_slow])


def _py_parses(text: str) -> bool:
    try:
        ast.parse(text)
    except (SyntaxError, ValueError):
        return False
    return True


@_SETTINGS
@given(st.text())
def test_property_python_never_raises_and_unparsable_is_a_gap(text: str) -> None:
    usage = analyze_source("python", "p.py", text)
    if not _py_parses(text):
        assert gaps_of(usage, "parse_error"), "解析できないソースが gaps に出ていない"
        assert usage.imports == []
    for record in usage.imports:
        assert record.top and not record.top.startswith(".")
        assert record.line >= 1


_JS_FRAGMENTS = st.lists(
    st.sampled_from(
        [
            'import a from "pkg";',
            'require("pkg2");',
            "require(x);",
            "function f(",
            "{",
            "}",
            ")",
            "`${",
            "const s = 'str';",
            "import(",
            "export { y } from 'z';",
            "eval(s);",
            "\n",
        ]
    ),
    max_size=12,
).map("".join)


def _js_has_error(text: str) -> bool:
    import tree_sitter_javascript
    from tree_sitter import Language, Parser

    parser = Parser(Language(tree_sitter_javascript.language()))
    return parser.parse(text.encode("utf-8")).root_node.has_error


@_SETTINGS
@given(st.one_of(st.text(), _JS_FRAGMENTS))
def test_property_javascript_never_raises_and_unparsable_is_a_gap(text: str) -> None:
    usage = analyze_source("javascript", "p.js", text)
    if _js_has_error(text):
        assert gaps_of(usage, "parse_error"), "解析できないソースが gaps に出ていない"
    for record in usage.imports:
        assert record.top and not record.top.startswith((".", "/"))
        assert record.line >= 1
