"""対象リポジトリの「外部パッケージの利用の地図」を作る。

脆弱性スキャナの検出を「このリポジトリはそのパッケージを使っていない」としてふるい分ける使い方
(MAGATAMA Advisor)のための解析。見逃し(使っているのに地図に出ない)が最も重い誤りなので、
地図に出せないものは必ず ``gaps``(調べ切れなかった箇所)に出す。対象のファイルは読むだけで書かない。

- Python は標準の ``ast`` で解析する。``ast`` が受け付けないソースは ``parse_error``
- JavaScript/TypeScript は tree-sitter で解析する(javascript は tree-sitter-javascript、typescript は
  tree-sitter-typescript の typescript 文法。``.tsx`` だけ tsx 文法)。構文木に ERROR・MISSING ノードがあれば ``parse_error``
- ``const x = require(...)``(動的な読み込みで決まったものを含む)の ``x`` は alias。Python の代入は alias にしない

契約 第2版(2026-11-21、レビューの指摘を受けた追加。下の各 docstring より優先する):
- R1 root の中を指すファイルのシンボリックリンクは、リンク先が「それ自体として走査される」(コードの言語が決まり、
  除外ディレクトリの中でない)ときだけ飛ばす。そうでなければリンクの名前(と R5 の shebang)で言語を決めて、リンクを解析する
- R2 Python の ``import_module(name, package)``(位置引数・キーワード引数とも)で name が ``.`` で始まるとき、
  package が決まればその top を ``dynamic`` の import として出す。決まらなければ ``dynamic_import`` の gap
- R3 JS/TS で次も require とみなす: ``require`` を代入した名前(``const r = require``)、``createRequire(...)``(``module``・
  ``node:module`` から)の戻り値を代入した名前、``module.require``。``require.call``・``require.apply`` は ``dynamic_import`` の gap。
  AMD の ``define([...], fn)``・``define("名前", [...], fn)``・``require([...], fn)`` は、一覧の文字列をそれぞれ import として出す
  (場所に応じた context)。一覧が文字列だけでなければ ``dynamic_import`` の gap
- R4 JS/TS の指定子 ``npm:<pkg>@<版>/<パス>`` は ``npm:`` と版を外して top を決める(``npm:@s/p@2/x`` → ``@s/p``)。module はそのまま。
  ``http:``・``https:``・``data:`` の URL はパッケージではないので、指定子をそのまま top にする
- R5 ``.pyw`` は python。拡張子のないファイルで、1行目が ``#!`` で始まり ``python`` を含むものは python、``node`` を含むものは
  javascript として解析する(それ以外の拡張子のないファイルは対象外)。``.pyx``・``.pxd`` は python、``.mdx`` は javascript の
  ``unsupported_file``。``.html`` の中のスクリプトは扱わない(限界)
- R6 Python の ``runpy.run_module(arg)`` は ``import_module`` と同じに扱う。``getattr(<任意>, "import_module" または "__import__")``、
  ``__builtins__.__import__``・``builtins.__import__`` の呼び出しは ``dynamic_import`` の gap
- R7 ``dynamic_eval`` は呼び出しに限らない。Python は組み込みの ``exec``・``eval``・``compile`` の名前を(呼び出し以外も含めて)
  参照したら gap。JS/TS は識別子 ``eval`` の参照(``(0, eval)(s)``・``const e = eval`` を含む)、``Function`` の呼び出し・new、
  ``new vm.Script(...)``・``vm.compileFunction(...)``、第1引数が文字列(式を含まないテンプレート文字列を含む)の
  ``setTimeout``・``setInterval`` も gap
- R8 動的な読み込みの候補にできる一覧・名前は、その名前のすべての参照が「添字の読み取り」「for 文・内包表記で回す」
  「動的な読み込みの引数(と、その添字を一度だけ代入した名前の初期化)」のどれかであるときだけ。ほかの参照(別の名前への代入、
  メソッドの呼び出し、関数への引数、``del``、累算代入など)があれば決まらない扱い。Python でファイル直下に ``from x import *``
  があれば、そのファイルの直下の名前はすべて決まらない扱い
- R9 Python の type_only は、``TYPE_CHECKING`` を ``typing``・``typing_extensions`` から import した名前(別名を含む)か、
  import したそれらのモジュール(別名を含む)の属性 ``.TYPE_CHECKING`` の ``if`` だけ。それ以外の ``TYPE_CHECKING`` は conditional
- R10 ディレクトリがシンボリックリンク・ジャンクションかどうかを判定できない(stat の失敗など)ときは、中に入らず
  ``unreadable`` の gap(language は "any")を出す
- 既存の解析器(``infrastructure/parsers``)と知識グラフは使わず、変えない
"""

from __future__ import annotations

import ast
import fnmatch
import os
import re
import stat
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, NamedTuple

SCHEMA_VERSION = "1"

LANGUAGES = ("python", "javascript", "typescript")

# 拡張子 → 言語。.pyi と .d.ts は、中の import をすべて type_only とする
PYTHON_EXTENSIONS = (".py", ".pyi", ".pyw")
JAVASCRIPT_EXTENSIONS = (".js", ".mjs", ".cjs", ".jsx")
TYPESCRIPT_EXTENSIONS = (".ts", ".tsx", ".mts", ".cts")

# コードを含みうるが解析しない拡張子 → gaps に unsupported_file として出すときの言語
UNSUPPORTED_EXTENSIONS: dict[str, str] = {
    ".vue": "javascript",
    ".svelte": "javascript",
    ".astro": "javascript",
    ".ipynb": "python",
    ".pyx": "python",
    ".pxd": "python",
    ".mdx": "javascript",
}

# 既定で除外するディレクトリ名。ほかに pyvenv.cfg を含むディレクトリ(仮想環境)も除外する
DEFAULT_EXCLUDED_DIR_NAMES = ("node_modules", ".git", "__pycache__", "site-packages")

IMPORT_CONTEXTS = ("module", "conditional", "function", "type_only", "dynamic")
USE_KINDS = ("call", "reference")
GAP_KINDS = (
    "parse_error",
    "unreadable",
    "dynamic_import",
    "outside_root",
    "unsupported_file",
    "dynamic_eval",
    "string_reference",
)


class RootNotFoundError(FileNotFoundError):
    """解析の対象(root)が存在しない、またはディレクトリでない。"""


@dataclass(frozen=True)
class ImportName:
    """``from a import x as y`` の ``x`` と ``y``。"""

    name: str
    alias: str | None = None


@dataclass(frozen=True)
class ImportRecord:
    """外部パッケージの読み込み1件。

    - module: 読み込みの指定そのもの(Python は ``a.b``、JS/TS は ``lodash/template`` や ``@scope/pkg/x``)
    - top: パッケージとして照合する名前。Python はドット区切りの先頭。JS/TS は先頭の区切り、
      スコープ付きは2段(``@scope/pkg``)。``importScripts`` のパスに ``node_modules/<pkg>/`` があればその pkg
    - alias: ``import a as b`` の ``b``、``import * as ns`` の ``ns``、``import x from`` の ``x``、
      ``const x = require(...)`` の ``x``。なければ None
    - names: ``from a import x as y`` や ``import { x as y } from`` の名前(なければ空)
    - context: ``module`` / ``conditional`` / ``function`` / ``type_only`` / ``dynamic``
      (優先順位: type_only > dynamic > function > conditional > module)
    - enclosing: 囲んでいる関数・メソッド・クラスの名前(ファイル直下なら None。入れ子は内側の名前)
    - line は1始まり、col は0始まり
    """

    language: str
    module: str
    top: str
    alias: str | None
    names: tuple[ImportName, ...]
    file: str
    line: int
    col: int
    context: str
    enclosing: str | None


@dataclass(frozen=True)
class UseRecord:
    """外部パッケージ由来の名前の利用1件(助言の材料)。

    - kind: ``call``(呼び出し)/ ``reference``(呼び出し以外の属性の参照)
    - name: 読み込みの束縛を解いた名前。``yaml.load``、``from yaml import load; load()`` → ``yaml.load``、
      ``const t = require("lodash/template"); t()`` → ``lodash/template``、
      ``import axios from "axios"; axios.get()`` → ``axios.get``
    - 呼び出しの戻り値への呼び出し(``jinja2.Template(...).render()`` の ``render``)は追わない
    """

    language: str
    kind: str
    name: str
    top: str
    file: str
    line: int
    col: int
    enclosing: str | None


@dataclass(frozen=True)
class GapRecord:
    """調べ切れなかった箇所1件。

    - kind: GAP_KINDS のどれか
    - language: LANGUAGES のどれか。どの言語にも関わりうるもの(``outside_root``)は ``any``
    - line: 分かれば1始まり。ファイル全体の問題(読めない、解析しない拡張子)なら None
    - candidates: ``string_reference`` では一致したパッケージ名を1件。それ以外は None
    """

    language: str
    kind: str
    file: str
    line: int | None
    detail: str
    candidates: tuple[str, ...] | None


@dataclass
class FileUsage:
    """1ファイルの解析結果。"""

    imports: list[ImportRecord] = field(default_factory=list)
    uses: list[UseRecord] = field(default_factory=list)
    gaps: list[GapRecord] = field(default_factory=list)


@dataclass
class ExternalUsageResult:
    """解析全体の結果。``to_dict()`` が CLI・MCP の出力の形。"""

    root: str
    tool_version: str
    files_scanned: dict[str, int]
    excluded_dirs: list[str]
    imports: list[ImportRecord]
    uses: list[UseRecord]
    gaps: list[GapRecord]
    schema_version: str = SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        """契約の JSON の形にする。

        キー: schema_version, tool {name: "magatama", version}, root(``/`` 区切りの絶対パス),
        files_scanned {python, javascript, typescript}(3言語とも必ず出す), excluded_dirs,
        imports, uses, gaps。各レコードは dataclass のフィールド名をそのままキーにし、
        names は ``[{"name": ..., "alias": ...}]``、candidates はリストか null にする。
        並び順は imports・uses・gaps とも (file, line(None は 0), col, その他のフィールド) の昇順で決定的。
        """
        imports = sorted(self.imports, key=_import_key)
        uses = sorted(self.uses, key=_use_key)
        gaps = sorted(self.gaps, key=_gap_key)
        return {
            "schema_version": self.schema_version,
            "tool": {"name": "magatama", "version": self.tool_version},
            "root": self.root,
            "files_scanned": {lang: self.files_scanned.get(lang, 0) for lang in LANGUAGES},
            "excluded_dirs": sorted(self.excluded_dirs),
            "imports": [
                {
                    "language": i.language,
                    "module": i.module,
                    "top": i.top,
                    "alias": i.alias,
                    "names": [{"name": n.name, "alias": n.alias} for n in i.names],
                    "file": i.file,
                    "line": i.line,
                    "col": i.col,
                    "context": i.context,
                    "enclosing": i.enclosing,
                }
                for i in imports
            ],
            "uses": [
                {
                    "language": u.language,
                    "kind": u.kind,
                    "name": u.name,
                    "top": u.top,
                    "file": u.file,
                    "line": u.line,
                    "col": u.col,
                    "enclosing": u.enclosing,
                }
                for u in uses
            ],
            "gaps": [
                {
                    "language": g.language,
                    "kind": g.kind,
                    "file": g.file,
                    "line": g.line,
                    "detail": g.detail,
                    "candidates": list(g.candidates) if g.candidates is not None else None,
                }
                for g in gaps
            ],
        }


def _import_key(i: ImportRecord) -> tuple[Any, ...]:
    names = tuple((n.name, n.alias or "") for n in i.names)
    return (
        i.file, i.line, i.col, i.language, i.module, i.top, i.alias or "", names, i.context,
        i.enclosing or "",
    )  # fmt: skip


def _use_key(u: UseRecord) -> tuple[Any, ...]:
    return (u.file, u.line, u.col, u.language, u.kind, u.name, u.top, u.enclosing or "")


def _gap_key(g: GapRecord) -> tuple[Any, ...]:
    return (g.file, g.line or 0, g.language, g.kind, g.detail, g.candidates or ())


def language_for(path: str) -> str | None:
    """拡張子から言語を返す(解析しない拡張子と対象外は None)。大文字小文字は区別しない。

    ``.d.ts`` は typescript。
    """
    ext = Path(path.lower()).suffix
    if ext in PYTHON_EXTENSIONS:
        return "python"
    if ext in JAVASCRIPT_EXTENSIONS:
        return "javascript"
    if ext in TYPESCRIPT_EXTENSIONS:
        return "typescript"
    return None


def analyze_source(
    language: str,
    rel_path: str,
    source: str,
    packages: frozenset[str] = frozenset(),
) -> FileUsage:
    """1ファイルのソースを解析する純粋関数(ファイル・ネットワーク・時計に触れない)。

    Args:
        language: ``python`` / ``javascript`` / ``typescript``
        rel_path: 出力に載せる root からの相対パス(``/`` 区切り)。``.pyi``・``.d.ts`` の判定にも使う
        source: ソースの文字列
        packages: import 名の集合。空でなければ、文字列リテラルがその名前と一致するか、
            ``名前.``・``名前/`` で始まるとき ``string_reference`` の gap を出す(読み込みとして拾えたものも含めて出す)

    拾う読み込み:
        Python: ``import a.b as c``、``from a.b import x as y``(どこにあっても)。相対 import(``from . import x``)は出さない。
            ``if TYPE_CHECKING:``(``typing.TYPE_CHECKING`` も)の中は type_only。``.pyi`` はすべて type_only。
            ファイル直下の if・try・with の中は conditional、関数・クラス・ラムダの中は function。
        JS/TS: ``import ... from "x"``、``import "x"``、``export ... from "x"``、``require("x")``、``import("x")``、
            ``importScripts("x")``。``./``・``../``・``/`` で始まる指定子は出さない。
            TS の ``import type``・``export type ... from``・名前がすべて ``type`` 修飾の ``import { type X }``、
            ``.d.ts`` は type_only。「文字列」は文字列リテラルと式を含まないテンプレート文字列。

    動的な読み込み(Python: ``importlib.import_module(arg)``・``__import__(arg)``・``from importlib import import_module``
    の別名。JS/TS: 文字列でない引数の ``require``・``import()``・``importScripts``):
        arg が次のどれかなら、取りうる値をすべて ``context="dynamic"`` の import として出す。
        - 文字列リテラル
        - 同じファイルの直下で、文字列か「文字列だけの list・tuple・配列」に一度だけ代入された名前
          (Python の ``NAME = ...``、JS/TS の ``const``・``let``・``var``)
        - その一覧の添字(``MODULES[0]``)、その一覧を回す for 文・内包表記の変数、
          または関数の中でそれら(添字)を一度だけ代入した名前(``const name = MODULES[0]; require(name)``)
        決まらないときは ``dynamic_import`` の gap(candidates=None)。f-string と式を含むテンプレート文字列も決まらない扱い。

    文字列のコードの実行(``dynamic_eval`` の gap): Python の ``exec``・``eval``・``compile``(組み込みの名前で呼ばれたもの)、
    JS/TS の ``eval``・``new Function(...)``・``Function(...)``・``vm.runInContext``・``vm.runInNewContext``・``vm.runInThisContext``。

    解析できない(Python の ``ast`` が SyntaxError・ValueError を出す、JS/TS の構文木に ERROR・MISSING がある)場合:
        ``parse_error`` の gap を1件出す(line は分かれば最初の誤りの行)。JS/TS は誤りのない部分から拾えた読み込みも出してよい。
        Python は読み込みを出さない。

    例外: language が LANGUAGES 以外なら ValueError。それ以外の入力(壊れたソースを含む)で例外を出さない。
    """
    if language not in LANGUAGES:
        raise ValueError(f"unsupported language: {language}")
    if language == "python":
        return _analyze_python(rel_path, source, packages)
    # 循環 import を避けるため、JS/TS の解析は使うときに読み込む
    from magatama_core.application.usecases.external_usage_js import analyze_js

    return analyze_js(language, rel_path, source, packages)


# ---------------------------------------------------------------- 共通の補助


def package_top(spec: str) -> str:
    """JS/TS の読み込み指定から、パッケージ名(スコープ付きは2段)を返す。"""
    if spec.startswith(("http:", "https:", "data:")):
        return spec  # URL はパッケージではないので、指定子そのものを top にする
    if spec.startswith("npm:"):
        # npm:<pkg>@<版>/<パス> は npm: と版を外す
        parts = spec[4:].split("/")
        if parts[0].startswith("@") and len(parts) >= 2:
            return parts[0] + "/" + parts[1].split("@", 1)[0]
        return parts[0].split("@", 1)[0]
    parts = spec.split("/")
    if spec.startswith("@") and len(parts) >= 2:
        return parts[0] + "/" + parts[1]
    return parts[0]


def is_relative_spec(spec: str) -> bool:
    """``./``・``../``・``/`` で始まる指定子(自分のコード)か。"""
    return spec in ("", ".", "..") or spec.startswith(("./", "../", "/"))


def string_reference_gaps(
    language: str, file: str, line: int, value: str, packages: frozenset[str]
) -> list[GapRecord]:
    """文字列リテラルがパッケージ名と一致するか、``名前.``・``名前/`` で始まるときの gap。"""
    gaps = []
    for pkg in sorted(packages):
        if value == pkg or value.startswith((pkg + ".", pkg + "/")):
            shown = value if len(value) <= 80 else value[:80] + "..."
            gaps.append(
                GapRecord(
                    language,
                    "string_reference",
                    file,
                    line,
                    f"文字列リテラル {shown!r} がパッケージ名 {pkg} と一致する",
                    (pkg,),
                )
            )
    return gaps


def parse_failure(language: str, rel_path: str, line: int | None, detail: str) -> FileUsage:
    """解析できなかったファイルの結果(parse_error を1件だけ持つ)。"""
    return FileUsage(gaps=[GapRecord(language, "parse_error", rel_path, line, detail, None)])


# ---------------------------------------------------------------- Python の解析

# 呼ぶと一覧の中身が変わるメソッド。呼ばれた名前は「一度だけ代入」でも値が決まらない扱いにする
_MUTATORS = frozenset(
    {
        "append",
        "extend",
        "insert",
        "pop",
        "remove",
        "clear",
        "sort",
        "reverse",
        "update",
        "add",
        "discard",
        "setdefault",
        "popitem",
    }
)
_DYNAMIC_IMPORT_CALLEES = frozenset(
    {"importlib.import_module", "importlib.__import__", "runpy.run_module"}
)
_TYPING_MODULES = ("typing", "typing_extensions")
_DYNAMIC_IMPORT_ATTRS = ("import_module", "__import__")
_EVAL_NAMES = ("exec", "eval", "compile")
_EVAL_CALLEES = frozenset({"builtins.exec", "builtins.eval", "builtins.compile"})
_COMPOUND_STATEMENTS = frozenset(
    {"Try", "TryStar", "With", "AsyncWith", "For", "AsyncFor", "While", "Match"}
)
MAX_RESOLVE_DEPTH = 8


class _PyScope:
    """名前の束縛を数えるスコープ(モジュールと関数・ラムダ。クラス本体は外側に含める)。"""

    def __init__(self, parent: _PyScope | None) -> None:
        self.parent = parent
        # 名前 -> 束縛の一覧。(種類, 値の式)。種類は assign / for / other
        self.bindings: dict[str, list[tuple[str, ast.expr | None]]] = {}

    def bind(self, name: str, kind: str = "other", value: ast.expr | None = None) -> None:
        self.bindings.setdefault(name, []).append((kind, value))


class _PyState(NamedTuple):
    enclosing: str | None
    in_func: bool
    cond: bool
    type_only: bool
    scope: _PyScope


class _PyAnalyzer:
    def __init__(self, rel_path: str, source: str, packages: frozenset[str]) -> None:
        self.file = rel_path
        self.packages = packages
        self.stub = rel_path.lower().endswith(".pyi")
        # ast の行は \n・\r\n・\r で数える
        self.lines = re.split(r"\r\n|\r|\n", source)
        self.usage = FileUsage()
        self.scope_of: dict[int, _PyScope] = {}
        # global 宣言・破壊的メソッドの対象など、代入が1回でも値が決まらない名前
        self.unstable: set[str] = set()
        # ローカル名 -> [(修飾名, from import で入れた名前か)]
        self.bindings: dict[str, list[tuple[str, bool]]] = {}
        self._registered: set[int] = set()
        # R8: 動的な読み込みの候補にできない名前(読み取り以外の参照がある名前)
        self.bad: set[str] = set()
        self.star = False  # ファイル直下に from x import * がある
        # R9: typing 由来の TYPE_CHECKING の名前と、typing のモジュールの名前
        self.tc_names: set[str] = set()
        self.typing_modules: set[str] = set()

    # ---- 位置(ast の col は UTF-8 のバイト数なので文字数に直す)
    def _col(self, node: ast.AST) -> int:
        lineno = int(getattr(node, "lineno", 1))
        offset = int(getattr(node, "col_offset", 0))
        if not 1 <= lineno <= len(self.lines):
            return offset
        line = self.lines[lineno - 1]
        if line.isascii():
            return offset
        raw = line.encode("utf-8", "surrogatepass")[:offset]
        return len(raw.decode("utf-8", "replace"))

    @staticmethod
    def _line(node: ast.AST) -> int:
        return int(getattr(node, "lineno", 1))

    # ---- 下準備: スコープごとの束縛と、import による名前の束縛
    def _bind_target(
        self, target: ast.expr, scope: _PyScope, kind: str, value: ast.expr | None
    ) -> None:
        if isinstance(target, ast.Name):
            scope.bind(target.id, kind, value)
            self._registered.add(id(target))

    def _add_binding(self, local: str, qualified: str, is_member: bool) -> None:
        known = self.bindings.setdefault(local, [])
        if (qualified, is_member) not in known:
            known.append((qualified, is_member))

    def _collect(self, node: ast.AST, scope: _PyScope) -> None:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            self._collect_function(node, scope)
            return
        if isinstance(node, ast.ClassDef):
            scope.bind(node.name)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                self._bind_target(target, scope, "assign", node.value)
        elif isinstance(node, ast.AnnAssign):
            if node.value is not None:
                self._bind_target(node.target, scope, "assign", node.value)
        elif isinstance(node, (ast.For, ast.AsyncFor, ast.comprehension)):
            self._bind_target(node.target, scope, "for", node.iter)
        elif isinstance(node, ast.Name):
            if isinstance(node.ctx, (ast.Store, ast.Del)) and id(node) not in self._registered:
                scope.bind(node.id)
        elif isinstance(node, ast.ExceptHandler):
            if node.name:
                scope.bind(node.name)
        elif isinstance(node, (ast.Global, ast.Nonlocal)):
            self.unstable.update(node.names)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                top = alias.name.split(".")[0]
                if alias.name in _TYPING_MODULES:
                    self.typing_modules.add(alias.asname or alias.name)
                scope.bind(alias.asname or top)
                self._add_binding(alias.asname or top, alias.name if alias.asname else top, False)
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                local = alias.asname or alias.name
                scope.bind(local)
                if node.module in _TYPING_MODULES and alias.name == "TYPE_CHECKING":
                    self.tc_names.add(local)
                if node.level == 0 and node.module and alias.name != "*":
                    self._add_binding(local, f"{node.module}.{alias.name}", True)
        elif isinstance(node, ast.Attribute):
            if isinstance(node.value, ast.Name) and node.attr in _MUTATORS:
                self.unstable.add(node.value.id)
        elif isinstance(node, ast.Subscript):
            if isinstance(node.value, ast.Name) and isinstance(node.ctx, (ast.Store, ast.Del)):
                self.unstable.add(node.value.id)
        elif isinstance(node, (ast.MatchAs, ast.MatchStar)):
            if node.name:
                scope.bind(node.name)
        elif isinstance(node, ast.MatchMapping):
            if node.rest:
                scope.bind(node.rest)
        for child in ast.iter_child_nodes(node):
            self._collect(child, scope)

    def _collect_function(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef | ast.Lambda, scope: _PyScope
    ) -> None:
        if not isinstance(node, ast.Lambda):
            scope.bind(node.name)
        inner = _PyScope(scope)
        self.scope_of[id(node)] = inner
        args = node.args
        for arg in [*args.posonlyargs, *args.args, *args.kwonlyargs, args.vararg, args.kwarg]:
            if arg is not None:
                inner.bind(arg.arg)
        for field_name, value in ast.iter_fields(node):
            state = inner if field_name == "body" else scope
            for child in value if isinstance(value, list) else [value]:
                if isinstance(child, ast.AST):
                    self._collect(child, state)

    # ---- 文字列の候補の解決
    def _resolve(
        self, node: ast.expr, scope: _PyScope, depth: int = 0
    ) -> tuple[str, list[str]] | None:
        """("str", 候補) か ("seq", 要素) を返す。決まらなければ None。"""
        if depth > MAX_RESOLVE_DEPTH:
            return None
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return ("str", [node.value])
        if isinstance(node, (ast.List, ast.Tuple)):
            items = []
            for elt in node.elts:
                if not (isinstance(elt, ast.Constant) and isinstance(elt.value, str)):
                    return None
                items.append(elt.value)
            return ("seq", items)
        if isinstance(node, ast.Subscript) and isinstance(node.ctx, ast.Load):
            base = self._resolve(node.value, scope, depth + 1)
            if base is None or base[0] != "seq":
                return None
            # 添字の値は追わず、一覧の全要素を候補にする(多めに出す)
            return ("seq", base[1]) if isinstance(node.slice, ast.Slice) else ("str", base[1])
        if isinstance(node, ast.Name):
            return self._lookup(node.id, scope, depth)
        return None

    def _lookup(self, name: str, scope: _PyScope, depth: int) -> tuple[str, list[str]] | None:
        if name in self.unstable or name in self.bad:
            return None
        current: _PyScope | None = scope
        while current is not None:
            found = current.bindings.get(name)
            if found is not None:
                if current.parent is None and self.star:
                    return None
                kind, value = found[0]
                if len(found) != 1 or value is None:
                    return None
                resolved = self._resolve(value, current, depth + 1)
                if kind == "assign":
                    return resolved
                if kind == "for" and resolved is not None and resolved[0] == "seq":
                    return ("str", resolved[1])
                return None
            current = current.parent
        return None

    # ---- R8: 名前の参照が「添字の読み取り」「for で回す」「動的な読み込みの引数」だけか
    def _is_dynamic_call(self, call: ast.Call) -> bool:
        chain = self._chain(call.func)
        if chain is None:
            return False
        root, attrs = chain
        if root not in self.bindings and not attrs and root == "__import__":
            return True
        return bool(_DYNAMIC_IMPORT_CALLEES & set(self._qualified(chain)))

    def _allowed_ref(self, node: ast.Name, parent: ast.AST | None, grand: ast.AST | None) -> bool:
        if isinstance(parent, ast.Subscript):
            return parent.value is node and isinstance(parent.ctx, ast.Load)
        if isinstance(parent, (ast.For, ast.AsyncFor, ast.comprehension)):
            return parent.iter is node
        if isinstance(parent, ast.Call):
            return bool(parent.args) and parent.args[0] is node and self._is_dynamic_call(parent)
        if isinstance(parent, ast.keyword) and isinstance(grand, ast.Call):
            return parent.arg in ("name", "mod_name") and self._is_dynamic_call(grand)
        return False

    def _scan_refs(self, tree: ast.Module) -> None:
        stack: list[tuple[ast.AST, ast.AST | None, ast.AST | None]] = [(tree, None, None)]
        while stack:
            node, parent, grand = stack.pop()
            if isinstance(node, ast.Name) and not isinstance(node.ctx, ast.Store):
                if not self._allowed_ref(node, parent, grand):
                    self.bad.add(node.id)
            stack.extend((child, node, parent) for child in ast.iter_child_nodes(node))

    # ---- 走査
    def run(self, tree: ast.Module) -> FileUsage:
        module_scope = _PyScope(None)
        self.scope_of[id(tree)] = module_scope
        self._collect(tree, module_scope)
        self.star = any(
            isinstance(n, ast.ImportFrom) and any(a.name == "*" for a in n.names) for n in tree.body
        )
        self._scan_refs(tree)
        state = _PyState(None, False, False, False, module_scope)
        for child in ast.iter_child_nodes(tree):
            self._visit(child, state)
        return self.usage

    def _children(self, node: ast.AST, st: _PyState) -> None:
        for child in ast.iter_child_nodes(node):
            self._visit(child, st)

    def _visit(self, node: ast.AST, st: _PyState) -> None:
        kind = type(node).__name__
        if kind in _COMPOUND_STATEMENTS:
            self._children(node, st._replace(cond=True))
            return
        handler = getattr(self, "_v_" + kind, None)
        if handler is None:
            self._children(node, st)
        else:
            handler(node, st)

    def _visit_fields(self, node: ast.AST, outer: _PyState, inner: _PyState) -> None:
        """body だけ内側の状態で、ほかのフィールド(デコレータ・既定値など)は外側で走査する。"""
        for field_name, value in ast.iter_fields(node):
            state = inner if field_name == "body" else outer
            for child in value if isinstance(value, list) else [value]:
                if isinstance(child, ast.AST):
                    self._visit(child, state)

    def _import_context(self, st: _PyState) -> str:
        if st.type_only or self.stub:
            return "type_only"
        if st.in_func:
            return "function"
        return "conditional" if st.cond else "module"

    def _v_Import(self, node: ast.Import, st: _PyState) -> None:
        for alias in node.names:
            self.usage.imports.append(
                ImportRecord(
                    "python",
                    alias.name,
                    alias.name.split(".")[0],
                    alias.asname,
                    (),
                    self.file,
                    self._line(node),
                    self._col(node),
                    self._import_context(st),
                    st.enclosing,
                )
            )

    def _v_ImportFrom(self, node: ast.ImportFrom, st: _PyState) -> None:
        if node.level or not node.module:
            return
        self.usage.imports.append(
            ImportRecord(
                "python",
                node.module,
                node.module.split(".")[0],
                None,
                tuple(ImportName(a.name, a.asname) for a in node.names),
                self.file,
                self._line(node),
                self._col(node),
                self._import_context(st),
                st.enclosing,
            )
        )

    def _v_FunctionDef(self, node: ast.FunctionDef | ast.AsyncFunctionDef, st: _PyState) -> None:
        scope = self.scope_of.get(id(node), st.scope)
        inner = st._replace(enclosing=node.name, in_func=True, scope=scope)
        self._visit_fields(node, st, inner)

    _v_AsyncFunctionDef = _v_FunctionDef

    def _v_Lambda(self, node: ast.Lambda, st: _PyState) -> None:
        inner = st._replace(in_func=True, scope=self.scope_of.get(id(node), st.scope))
        self._visit(node.args, st)
        self._visit(node.body, inner)

    def _v_ClassDef(self, node: ast.ClassDef, st: _PyState) -> None:
        self._visit_fields(node, st, st._replace(enclosing=node.name, in_func=True))

    def _is_type_checking(self, test: ast.expr) -> bool:
        if isinstance(test, ast.Name):
            return test.id in self.tc_names
        return (
            isinstance(test, ast.Attribute)
            and test.attr == "TYPE_CHECKING"
            and isinstance(test.value, ast.Name)
            and test.value.id in self.typing_modules
        )

    def _v_If(self, node: ast.If, st: _PyState) -> None:
        self._visit(node.test, st)
        body_state = st._replace(cond=True)
        if self._is_type_checking(node.test):
            body_state = body_state._replace(type_only=True)
        for child in node.body:
            self._visit(child, body_state)
        for child in node.orelse:
            self._visit(child, st._replace(cond=True))

    @staticmethod
    def _chain(node: ast.AST) -> tuple[str, list[str]] | None:
        attrs: list[str] = []
        while isinstance(node, ast.Attribute):
            attrs.append(node.attr)
            node = node.value
        if isinstance(node, ast.Name):
            return node.id, attrs[::-1]
        return None

    def _qualified(self, chain: tuple[str, list[str]]) -> list[str]:
        root, attrs = chain
        return [".".join([q, *attrs]) for q, _ in self.bindings.get(root, [])]

    def _use(self, kind: str, name: str, node: ast.AST, st: _PyState) -> None:
        self.usage.uses.append(
            UseRecord(
                "python",
                kind,
                name,
                name.split(".", maxsplit=1)[0],
                self.file,
                self._line(node),
                self._col(node),
                st.enclosing,
            )
        )

    def _gap(self, kind: str, node: ast.AST, detail: str) -> None:
        self.usage.gaps.append(GapRecord("python", kind, self.file, self._line(node), detail, None))

    def _v_Call(self, node: ast.Call, st: _PyState) -> None:
        chain = self._chain(node.func)
        qualified = self._qualified(chain) if chain else []
        if chain is not None:
            root, attrs = chain
            # import で束縛し直された名前は組み込みではない
            builtin = root not in self.bindings and not attrs
            if _EVAL_CALLEES & set(qualified):
                self._gap("dynamic_eval", node, f"{root} による文字列のコードの実行")
            if (builtin and root == "__import__") or _DYNAMIC_IMPORT_CALLEES & set(qualified):
                self._dynamic_import(node, st, set(qualified))
            elif (
                (root == "__builtins__" and attrs[:1] == ["__import__"])
                or "builtins.__import__" in qualified
                or (builtin and root == "getattr" and self._getattr_import(node))
            ):
                self._gap("dynamic_import", node, "間接的な動的 import(候補を追わない)")
        if not qualified:
            self._children(node, st)
            return
        for name in qualified:
            self._use("call", name, node.func, st)
        for child in [*node.args, *node.keywords]:
            self._visit(child, st)

    @staticmethod
    def _getattr_import(node: ast.Call) -> bool:
        return (
            len(node.args) >= 2
            and isinstance(node.args[1], ast.Constant)
            and node.args[1].value in _DYNAMIC_IMPORT_ATTRS
        )

    @staticmethod
    def _call_arg(node: ast.Call, index: int, *keywords: str) -> ast.expr | None:
        if len(node.args) > index:
            arg = node.args[index]
            return None if isinstance(arg, ast.Starred) else arg
        return next((kw.value for kw in node.keywords if kw.arg in keywords), None)

    def _dynamic_import(self, node: ast.Call, st: _PyState, names: set[str]) -> None:
        arg = self._call_arg(node, 0, "name", "mod_name")
        resolved = self._resolve(arg, st.scope) if arg is not None else None
        if resolved is None:
            self._gap("dynamic_import", node, "読み込む名前が静的に決まらない")
            return
        context = "type_only" if (st.type_only or self.stub) else "dynamic"
        modules: list[str] = []
        for module in dict.fromkeys(resolved[1]):
            if module.startswith(".") and "importlib.import_module" in names:
                # R2: 相対名は package が決まれば、その top を読み込みとして出す
                package = self._call_arg(node, 1, "package")
                packages = self._resolve(package, st.scope) if package is not None else None
                if packages is None:
                    self._gap("dynamic_import", node, "相対名の package が静的に決まらない")
                    return
                modules.extend(p for p in packages[1] if p and not p.startswith("."))
            elif module and not module.startswith("."):
                modules.append(module)
        for module in dict.fromkeys(modules):
            self.usage.imports.append(
                ImportRecord(
                    "python",
                    module,
                    module.split(".")[0],
                    None,
                    (),
                    self.file,
                    self._line(node),
                    self._col(node),
                    context,
                    st.enclosing,
                )
            )

    def _v_Attribute(self, node: ast.Attribute, st: _PyState) -> None:
        chain = self._chain(node)
        qualified = self._qualified(chain) if chain else []
        if not qualified:
            self._children(node, st)
            return
        for name in qualified:
            self._use("reference", name, node, st)

    def _v_Name(self, node: ast.Name, st: _PyState) -> None:
        if isinstance(node.ctx, ast.Load) and node.id in _EVAL_NAMES:
            if node.id not in self.bindings:
                # R7: 組み込みの exec・eval・compile は、呼び出し以外の参照も gap にする
                self._gap("dynamic_eval", node, f"{node.id} による文字列のコードの実行")
        # from import で入れた名前を呼ばずに使う場合(属性の参照と同じ扱い)
        if isinstance(node.ctx, ast.Load):
            for qualified, is_member in self.bindings.get(node.id, []):
                if is_member:
                    self._use("reference", qualified, node, st)

    def _v_Constant(self, node: ast.Constant, st: _PyState) -> None:
        if isinstance(node.value, str) and self.packages:
            self.usage.gaps.extend(
                string_reference_gaps(
                    "python", self.file, self._line(node), node.value, self.packages
                )
            )


def _analyze_python(rel_path: str, source: str, packages: frozenset[str]) -> FileUsage:
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            tree = ast.parse(source)
    except SyntaxError as exc:
        return parse_failure("python", rel_path, exc.lineno, f"構文エラー: {exc.msg}")
    except (ValueError, RecursionError, MemoryError) as exc:
        return parse_failure("python", rel_path, None, f"解析できない: {type(exc).__name__}")
    try:
        return _PyAnalyzer(rel_path, source, packages).run(tree)
    except Exception as exc:  # 解析器の不具合でも、黙って落とさず gap にする
        return parse_failure("python", rel_path, None, f"解析中の内部エラー: {type(exc).__name__}")


class ExternalUsageUseCase:
    """ディレクトリを走査し、全ファイルの解析結果をまとめる(外側の層)。"""

    def execute(
        self,
        root: str | Path,
        exclude: list[str] | None = None,
        packages: list[str] | None = None,
    ) -> ExternalUsageResult:
        """root 以下を解析する。root のファイルには書き込まない(キャッシュも作らない)。

        - root が存在しない・ディレクトリでない: RootNotFoundError
        - 除外: DEFAULT_EXCLUDED_DIR_NAMES のディレクトリ、pyvenv.cfg を含むディレクトリ、
          ``exclude`` の glob(root からの相対パスに ``fnmatch`` で照合。ディレクトリにもファイルにも効く)。
          除外したディレクトリは root からの相対パスで ``excluded_dirs`` に出す(その下は出さない)
        - ディレクトリのシンボリックリンク・ジャンクションはたどらない。リンク先が root の外なら
          ``outside_root`` の gap(language は "any"、line は None)。中なら何も出さない
        - ファイルのシンボリックリンク: リンク先が root の中なら読まずに飛ばす(実体を別に走査するため)。外なら ``outside_root``
        - 読めないファイル(OSError、UTF-8 として不正): ``unreadable`` の gap(その言語で)
        - UNSUPPORTED_EXTENSIONS のファイル: ``unsupported_file`` の gap
        - files_scanned は言語ごとに、analyze_source に渡したファイル数(unreadable を含まない)
        - 出力のパスは root からの相対で ``/`` 区切り
        """
        root_path = Path(root)
        if not root_path.is_dir():
            raise RootNotFoundError(f"解析の対象がディレクトリではない: {root_path}")
        walk = _Walk(
            root=str(root_path),
            real_root=os.path.realpath(root_path),
            patterns=list(exclude or []),
            packages=frozenset(packages or []),
        )
        walk.run()
        return ExternalUsageResult(
            root=root_path.resolve().as_posix(),
            tool_version=_tool_version(),
            files_scanned=walk.files_scanned,
            excluded_dirs=sorted(walk.excluded_dirs),
            imports=sorted(walk.imports, key=_import_key),
            uses=sorted(walk.uses, key=_use_key),
            gaps=sorted(walk.gaps, key=_gap_key),
        )


def _tool_version() -> str:
    try:
        from importlib.metadata import version

        return version("magatama-core")
    except Exception:
        return "unknown"


_IO_REPARSE_TAG_MOUNT_POINT = 0xA0000003


class _Walk:
    """root 以下の走査の状態。"""

    def __init__(
        self, root: str, real_root: str, patterns: list[str], packages: frozenset[str]
    ) -> None:
        self.root = root
        self.raw_real_root = real_root
        self.real_root = os.path.normcase(real_root)
        self.patterns = patterns
        self.packages = packages
        self.files_scanned = dict.fromkeys(LANGUAGES, 0)
        self.excluded_dirs: list[str] = []
        self.imports: list[ImportRecord] = []
        self.uses: list[UseRecord] = []
        self.gaps: list[GapRecord] = []

    def _inside_root(self, path: str) -> bool:
        target = os.path.normcase(os.path.realpath(path))
        try:
            return os.path.commonpath([self.real_root, target]) == self.real_root
        except ValueError:  # ドライブが違う
            return False

    def _matches(self, rel: str) -> bool:
        return any(fnmatch.fnmatchcase(rel, pattern) for pattern in self.patterns)

    def _excluded_dir(self, path: str, name: str, rel: str) -> bool:
        return (
            name in DEFAULT_EXCLUDED_DIR_NAMES
            or (Path(path) / "pyvenv.cfg").is_file()
            or self._matches(rel)
        )

    def _gap(self, language: str, kind: str, rel: str, detail: str) -> None:
        self.gaps.append(GapRecord(language, kind, rel, None, detail, None))

    def run(self) -> None:
        pending = [("", self.root)]
        while pending:
            rel_dir, path = pending.pop()
            try:
                with os.scandir(path) as it:
                    entries = sorted(it, key=lambda e: e.name)
            except OSError as exc:
                self._gap("any", "unreadable", rel_dir or ".", f"ディレクトリを読めない: {exc}")
                continue
            for entry in entries:
                rel = f"{rel_dir}/{entry.name}" if rel_dir else entry.name
                self._entry(entry, rel, pending)

    def _language_of(self, path: str, name: str) -> str | None:
        """拡張子で言語を決める。拡張子がなければ、1行目の shebang で決める(R5)。"""
        language = language_for(name)
        if language is not None or Path(name).suffix or not Path(path).is_file():
            return language
        try:
            with open(path, "rb") as handle:
                first = handle.read(256).split(b"\n", 1)[0]
        except OSError:
            return None
        if not first.startswith(b"#!"):
            return None
        line = first.decode("utf-8", "ignore").lower()
        if "python" in line:
            return "python"
        return "javascript" if "node" in line else None

    def _target_scanned(self, real: str) -> bool:
        """リンク先が、それ自体として走査されるか(R1)。"""
        try:
            parts = os.path.relpath(real, self.raw_real_root).replace(os.sep, "/").split("/")
        except ValueError:
            return False
        for index, part in enumerate(parts[:-1]):
            current = str(Path(self.raw_real_root).joinpath(*parts[: index + 1]))
            if self._excluded_dir(current, part, "/".join(parts[: index + 1])):
                return False
        if self._matches("/".join(parts)):
            return False
        return self._language_of(real, parts[-1]) is not None

    def _entry(self, entry: os.DirEntry[str], rel: str, pending: list[tuple[str, str]]) -> None:
        try:
            info = entry.stat(follow_symlinks=False)
        except OSError as exc:
            # R10: リンクかどうか判定できないものには入らない
            self._gap("any", "unreadable", rel, f"種別を判定できない: {type(exc).__name__}")
            return
        is_link = stat.S_ISLNK(info.st_mode)
        # Python 3.11 では、ジャンクションは symlink にならないので reparse タグで見分ける
        junction = stat.S_ISDIR(info.st_mode) and (
            getattr(info, "st_reparse_tag", 0) == _IO_REPARSE_TAG_MOUNT_POINT
        )
        dir_link = junction or (is_link and Path(entry.path).is_dir())
        if dir_link or stat.S_ISDIR(info.st_mode):
            if self._excluded_dir(entry.path, entry.name, rel):
                self.excluded_dirs.append(rel)
            elif dir_link:
                # たどらない。root の外を指すときだけ、調べていない場所として gap にする
                if not self._inside_root(entry.path):
                    self._gap("any", "outside_root", rel, "root の外を指すディレクトリのリンク")
            else:
                pending.append((rel, entry.path))
            return
        if self._matches(rel):
            return
        language = self._language_of(entry.path, entry.name)
        unsupported = UNSUPPORTED_EXTENSIONS.get(Path(entry.name.lower()).suffix)
        if language is None and unsupported is None:
            return
        if is_link:
            if not self._inside_root(entry.path):
                self._gap("any", "outside_root", rel, "root の外を指すファイルのリンク")
                return
            if self._target_scanned(os.path.realpath(entry.path)):
                return  # 実体を別に走査する
        if language is None:
            assert unsupported is not None
            self._gap(unsupported, "unsupported_file", rel, "解析しない拡張子(コードを含みうる)")
            return
        self._scan_file(entry.path, rel, language)

    def _scan_file(self, path: str, rel: str, language: str) -> None:
        try:
            with open(path, "rb") as handle:
                source = handle.read().decode("utf-8-sig")
        except (OSError, UnicodeDecodeError) as exc:
            self._gap(language, "unreadable", rel, f"読めない: {type(exc).__name__}")
            return
        usage = analyze_source(language, rel, source, self.packages)
        self.files_scanned[language] += 1
        self.imports.extend(usage.imports)
        self.uses.extend(usage.uses)
        self.gaps.extend(usage.gaps)
