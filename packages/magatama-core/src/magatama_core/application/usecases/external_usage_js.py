"""JavaScript/TypeScript の外部パッケージ利用の解析(tree-sitter)。

契約は ``external_usage_usecase`` の docstring。ここは ``analyze_source`` から呼ばれる補助で、
既存の ``infrastructure/parsers`` は使わない。構文木の ERROR・MISSING は ``parse_error`` にする。
"""

from __future__ import annotations

import re
from collections.abc import Callable
from functools import cache
from typing import NamedTuple

import tree_sitter_javascript
import tree_sitter_typescript
from tree_sitter import Language, Node, Parser

from magatama_core.application.usecases.external_usage_usecase import (
    FileUsage,
    GapRecord,
    ImportName,
    ImportRecord,
    InternalImportRecord,
    UseRecord,
    is_relative_spec,
    package_top,
    parse_failure,
    string_reference_gaps,
)

_FUNCTION_TYPES = frozenset(
    {
        "function_declaration",
        "generator_function_declaration",
        "function_expression",
        "function",
        "generator_function",
        "arrow_function",
        "method_definition",
    }
)
_CLASS_TYPES = frozenset({"class_declaration", "class", "abstract_class_declaration"})
_CONDITIONAL_TYPES = frozenset(
    {
        "if_statement",
        "switch_statement",
        "try_statement",
        "ternary_expression",
        "for_statement",
        "for_in_statement",
        "while_statement",
        "do_statement",
        "with_statement",
        "augmented_assignment_expression",
    }
)
_LOGICAL_OPERATORS = frozenset({"&&", "||", "??"})
_WRAPPERS = frozenset(
    {
        "parenthesized_expression",
        "as_expression",
        "satisfies_expression",
        "non_null_expression",
        "type_assertion",
    }
)
_AWAIT_WRAPPERS = _WRAPPERS | {"await_expression"}
_TYPE_CONTEXTS = frozenset(
    {
        "type_annotation",
        "type_alias_declaration",
        "type_query",
        "type_arguments",
        "interface_declaration",
        "extends_type_clause",
        "implements_clause",
    }
)
# 呼ぶと配列の中身が変わるメソッド。呼ばれた名前は「一度だけ代入」でも値が決まらない扱いにする
_MUTATORS = frozenset(
    {"push", "pop", "shift", "unshift", "splice", "sort", "reverse", "fill", "copyWithin"}
)
_VM_EVAL_METHODS = frozenset(
    {"runInContext", "runInNewContext", "runInThisContext", "compileFunction"}
)
_TIMER_NAMES = frozenset({"setTimeout", "setInterval"})
_INDIRECT_REQUIRE = frozenset({"call", "apply", "bind"})
_MODULE_SPECS = frozenset({"module", "node:module"})
# 宣言の名前の位置(参照ではない)になる親のノード
_DECLARATION_PARENTS = frozenset(
    {
        "formal_parameters",
        "rest_pattern",
        "array_pattern",
        "object_pattern",
        "pair_pattern",
        "import_specifier",
        "namespace_import",
        "import_clause",
        "import_require_clause",
        "catch_clause",
    }
)
_NON_DEPS = frozenset(
    {
        "function_expression",
        "function",
        "generator_function",
        "arrow_function",
        "object",
        "string",
        "template_string",
        "number",
        "null",
        "undefined",
    }
)
_GLOBAL_OBJECTS = frozenset({"window", "self", "global", "globalThis"})
_PATTERN_IDENTIFIERS = frozenset({"identifier", "shorthand_property_identifier_pattern"})
_NODE_MODULES = re.compile(r"(?<![^/])node_modules/((?:@[^/]+/)?[^/]+)/")
_MAX_RESOLVE_DEPTH = 8
_SIMPLE_ESCAPES = {"n": "\n", "t": "\t", "r": "\r", "b": "\b", "f": "\f", "v": "\v", "0": "\0"}


@cache
def _parser(kind: str) -> Parser:
    if kind == "javascript":
        language = tree_sitter_javascript.language()
    elif kind == "tsx":
        language = tree_sitter_typescript.language_tsx()
    else:
        language = tree_sitter_typescript.language_typescript()
    return Parser(Language(language))


def _text(node: Node | None) -> str:
    return node.text.decode("utf-8", "replace") if node is not None and node.text else ""


def _unescape(raw: str) -> str:
    """文字列リテラルのエスケープ1つ(``\\n``、``\\x41``、``\\u0041``、``\\u{41}``)を戻す。"""
    if len(raw) < 2:
        return raw
    char = raw[1]
    try:
        if char in _SIMPLE_ESCAPES and len(raw) == 2:
            return _SIMPLE_ESCAPES[char]
        if char == "x":
            return chr(int(raw[2:], 16))
        if char == "u":
            return chr(int(raw[2:].strip("{}"), 16))
    except ValueError:
        return raw
    return "" if char in "\r\n  " else raw[1:]


def _string_value(node: Node) -> str | None:
    """文字列リテラルと、式を含まないテンプレート文字列の値。それ以外は None。"""
    if node.type not in ("string", "template_string"):
        return None
    parts = []
    for child in node.children:
        if child.type == "template_substitution":
            return None
        if child.type == "string_fragment":
            parts.append(_text(child))
        elif child.type == "escape_sequence":
            parts.append(_unescape(_text(child)))
    return "".join(parts)


def _unwrap(node: Node) -> Node:
    while node.type in _WRAPPERS and node.named_children:
        node = node.named_children[0]
    return node


def _identifiers_in(node: Node) -> list[str]:
    names = []
    stack = [node]
    while stack:
        current = stack.pop()
        if current.type in _PATTERN_IDENTIFIERS:
            names.append(_text(current))
        stack.extend(current.children)
    return names


class _Scope:
    """名前の束縛を数えるスコープ(プログラムと関数。ブロックは関数に含める)。"""

    def __init__(self, parent: _Scope | None) -> None:
        self.parent = parent
        # 名前 -> 束縛の一覧。(種類, 値の式)。種類は assign / for / other
        self.bindings: dict[str, list[tuple[str, Node | None]]] = {}

    def bind(self, name: str, kind: str = "other", value: Node | None = None) -> None:
        self.bindings.setdefault(name, []).append((kind, value))


class _State(NamedTuple):
    scope: _Scope
    enclosing: str | None
    in_func: bool
    cond: bool


class _JsAnalyzer:
    def __init__(self, language: str, rel_path: str, source: str, packages: frozenset[str]) -> None:
        self.language = language
        self.file = rel_path
        self.packages = packages
        lowered = rel_path.lower()
        self.declaration_file = lowered.endswith((".d.ts", ".d.mts", ".d.cts"))
        self.src = source.encode("utf-8", "replace")
        self.lines = self.src.split(b"\n")
        self.usage = FileUsage()
        self.scope_of: dict[int, _Scope] = {}
        self.unstable: set[str] = set()  # 再代入・破壊的メソッドの対象など、値が決まらない名前
        # R8: 動的な読み込みの候補にできない名前(読み取り以外の参照がある名前)
        self.bad: set[str] = set()
        # R3: require として呼べる名前(const r = require など)
        self.require_names: set[str] = {"require"}
        # ローカル名 -> [(修飾名, 名前付き import・分割代入で入れた名前か, パッケージ名)]
        self.bindings: dict[str, list[tuple[str, bool, str]]] = {}

    # ---- 位置(tree-sitter の列はバイト数なので文字数に直す)
    def _line(self, node: Node) -> int:
        return int(node.start_point[0]) + 1

    def _col(self, node: Node) -> int:
        row, col = node.start_point
        if not 0 <= row < len(self.lines):
            return int(col)
        return len(self.lines[row][:col].decode("utf-8", "replace"))

    def _add_binding(self, local: str, module: str, members: list[str] | None = None) -> None:
        """``local`` が ``module`` (の ``members`` を辿った先)を指すと記録する。"""
        if not local:
            return
        entry = (".".join([module, *(members or [])]), bool(members), package_top(module))
        known = self.bindings.setdefault(local, [])
        if entry not in known:
            known.append(entry)

    # ---- 名前の決まり方の下準備(スコープごとの束縛)
    def collect(self, root: Node) -> _Scope:
        scope = _Scope(None)
        self.scope_of[root.id] = scope
        self._collect(root, scope)
        return scope

    def _name_of(self, node: Node, field: str = "name") -> str:
        return _text(node.child_by_field_name(field))

    def _collect(self, node: Node, scope: _Scope) -> None:
        kind = node.type
        if kind in _FUNCTION_TYPES:
            scope = self._collect_function(node, scope)
        elif kind == "variable_declarator":
            name = node.child_by_field_name("name")
            value = node.child_by_field_name("value")
            if name is not None and name.type == "identifier":
                scope.bind(_text(name), "assign" if value is not None else "other", value)
            elif name is not None:
                for ident in _identifiers_in(name):
                    scope.bind(ident)
        elif kind in ("class_declaration", "abstract_class_declaration", "enum_declaration"):
            scope.bind(self._name_of(node))
        elif kind == "catch_clause":
            parameter = node.child_by_field_name("parameter")
            for ident in _identifiers_in(parameter) if parameter is not None else []:
                scope.bind(ident)
        elif kind == "for_in_statement":
            self._collect_for(node, scope)
        elif kind in (
            "import_specifier",
            "namespace_import",
            "import_require_clause",
            "import_clause",
        ):
            for child in node.named_children:
                if child.type == "identifier":
                    scope.bind(_text(child))
        elif kind in ("assignment_expression", "augmented_assignment_expression"):
            self._collect_write(node.child_by_field_name("left"))
        elif kind == "update_expression" or (
            kind == "unary_expression" and _text(node.child_by_field_name("operator")) == "delete"
        ):
            self._collect_write(node.child_by_field_name("argument"))
        elif kind == "member_expression":
            obj = node.child_by_field_name("object")
            prop = node.child_by_field_name("property")
            if obj is not None and obj.type == "identifier" and _text(prop) in _MUTATORS:
                self.unstable.add(_text(obj))
        for child in node.children:
            self._collect(child, scope)

    def _collect_function(self, node: Node, scope: _Scope) -> _Scope:
        inner = _Scope(scope)
        self.scope_of[node.id] = inner
        name = node.child_by_field_name("name")
        if name is not None:
            if node.type in ("function_declaration", "generator_function_declaration"):
                scope.bind(_text(name))
            else:
                inner.bind(_text(name))
        for field in ("parameters", "parameter"):
            params = node.child_by_field_name(field)
            for ident in _identifiers_in(params) if params is not None else []:
                inner.bind(ident)
        return inner

    def _collect_for(self, node: Node, scope: _Scope) -> None:
        left = node.child_by_field_name("left")
        right = node.child_by_field_name("right")
        operator = _text(node.child_by_field_name("operator"))
        if left is None:
            return
        declared = node.child_by_field_name("kind") is not None
        if left.type == "identifier":
            if not declared:
                self.unstable.add(_text(left))
            elif operator == "of" and right is not None:
                scope.bind(_text(left), "for", right)
            else:
                scope.bind(_text(left))
        else:
            for ident in _identifiers_in(left):
                if declared:
                    scope.bind(ident)
                else:
                    self.unstable.add(ident)

    def _collect_write(self, target: Node | None) -> None:
        """再代入・要素の書き換えの対象になった名前は、値が決まらない扱いにする。"""
        if target is None:
            return
        target = _unwrap(target)
        if target.type in ("member_expression", "subscript_expression"):
            obj = target.child_by_field_name("object")
            if obj is not None and obj.type == "identifier":
                self.unstable.add(_text(obj))
            return
        self.unstable.update(_identifiers_in(target))

    # ---- 文字列の候補の解決
    def _resolve(self, node: Node, scope: _Scope, depth: int = 0) -> tuple[str, list[str]] | None:
        """("str", 候補) か ("seq", 要素) を返す。決まらなければ None。"""
        if depth > _MAX_RESOLVE_DEPTH:
            return None
        node = _unwrap(node)
        if node.type in ("string", "template_string"):
            value = _string_value(node)
            return ("str", [value]) if value is not None else None
        if node.type == "array":
            items = []
            for child in node.named_children:
                if child.type == "comment":
                    continue
                value = _string_value(child)
                if value is None:
                    return None
                items.append(value)
            return ("seq", items)
        if node.type == "subscript_expression":
            obj = node.child_by_field_name("object")
            base = self._resolve(obj, scope, depth + 1) if obj is not None else None
            if base is None or base[0] != "seq":
                return None
            # 添字の値は追わず、一覧の全要素を候補にする(多めに出す)
            return ("str", base[1])
        if node.type == "identifier":
            return self._lookup(_text(node), scope, depth)
        return None

    def _lookup(self, name: str, scope: _Scope, depth: int) -> tuple[str, list[str]] | None:
        if name in self.unstable or name in self.bad:
            return None
        current: _Scope | None = scope
        while current is not None:
            found = current.bindings.get(name)
            if found is not None:
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

    # ---- 走査(状態を持ち回る)
    def _function_name(self, node: Node) -> str | None:
        name = _text(node.child_by_field_name("name"))
        if name:
            return name
        parent = node.parent
        if parent is None:
            return None
        if parent.type == "variable_declarator":
            return _text(parent.child_by_field_name("name")) or None
        if parent.type in ("pair", "public_field_definition", "field_definition"):
            return (
                _text(parent.child_by_field_name("key") or parent.child_by_field_name("name"))
                or None
            )
        if parent.type == "assignment_expression":
            left = parent.child_by_field_name("left")
            if left is not None and left.type == "member_expression":
                left = left.child_by_field_name("property")
            return _text(left) or None
        return None

    def _walk(self, node: Node, st: _State, visit: Callable[[Node, _State], bool]) -> None:
        if not visit(node, st):
            return
        kind = node.type
        child_state = st
        if kind in _FUNCTION_TYPES:
            child_state = st._replace(
                scope=self.scope_of.get(node.id, st.scope),
                enclosing=self._function_name(node) or st.enclosing,
                in_func=True,
            )
        elif kind in _CLASS_TYPES:
            child_state = st._replace(
                enclosing=_text(node.child_by_field_name("name")) or st.enclosing, in_func=True
            )
        elif kind in _CONDITIONAL_TYPES:
            child_state = st._replace(cond=True)
        elif kind == "binary_expression" and _text(node.child_by_field_name("operator")) in (
            _LOGICAL_OPERATORS
        ):
            # 右辺は左辺の結果しだいで実行される
            right = node.child_by_field_name("right")
            for child in node.children:
                state = st._replace(cond=True) if right is not None and child == right else st
                self._walk(child, state, visit)
            return
        for child in node.children:
            self._walk(child, child_state, visit)

    # ---- 1回目: 読み込み
    def _context(self, node: Node, st: _State, *, type_only: bool = False) -> str:
        if type_only or self.declaration_file or self._in_type_position(node):
            return "type_only"
        if st.in_func:
            return "function"
        return "conditional" if st.cond else "module"

    @staticmethod
    def _in_type_position(node: Node) -> bool:
        parent = node.parent
        while parent is not None:
            if parent.type in _TYPE_CONTEXTS:
                return True
            parent = parent.parent
        return False

    def _record(
        self,
        node: Node,
        st: _State,
        module: str,
        context: str,
        alias: str | None = None,
        names: tuple[ImportName, ...] = (),
        top: str | None = None,
    ) -> None:
        self.usage.imports.append(
            ImportRecord(
                self.language,
                module,
                top or package_top(module),
                alias,
                names,
                self.file,
                self._line(node),
                self._col(node),
                context,
                st.enclosing,
            )
        )

    def _record_internal(self, node: Node, specifier: str, kind: str, context: str) -> None:
        self.usage.internal_imports.append(
            InternalImportRecord(
                self.language,
                specifier,
                kind,
                None,
                self.file,
                self._line(node),
                self._col(node),
                context,
            )
        )

    @staticmethod
    def _is_internal(specifier: str) -> bool:
        return is_relative_spec(specifier) or specifier.startswith("#")

    def _gap(self, kind: str, node: Node, detail: str) -> None:
        self.usage.gaps.append(
            GapRecord(self.language, kind, self.file, self._line(node), detail, None)
        )

    def _imports_visit(self, node: Node, st: _State) -> bool:
        kind = node.type
        if kind == "import_statement" or (
            kind == "export_statement" and node.child_by_field_name("source") is not None
        ):
            self._static_statement(node, st)
            return False
        if kind == "call_expression":
            self._call_import(node, st)
        return True

    @staticmethod
    def _has_type_token(node: Node) -> bool:
        return any(child.type == "type" for child in node.children)

    @staticmethod
    def _specifiers(clause: Node) -> list[Node]:
        return [
            c for c in clause.named_children if c.type in ("import_specifier", "export_specifier")
        ]

    def _static_statement(self, node: Node, st: _State) -> None:
        require_clause = next((c for c in node.children if c.type == "import_require_clause"), None)
        source = (require_clause or node).child_by_field_name("source")
        spec = _string_value(source) if source is not None else None
        if spec is None:
            return
        is_import = node.type == "import_statement"
        locals_: list[str] = []  # 既定・名前空間の import で入る名前(alias の候補)
        specifiers: list[Node] = []
        if require_clause is not None:
            ident = next((c for c in require_clause.named_children if c.type == "identifier"), None)
            locals_.append(_text(ident))
        for child in node.named_children:
            if child.type == "namespace_export":
                ident = next((c for c in child.named_children if c.type == "identifier"), None)
                locals_.append(_text(ident))
            elif child.type == "export_clause":
                specifiers.extend(self._specifiers(child))
            elif child.type == "import_clause":
                for part in child.named_children:
                    if part.type == "identifier":
                        locals_.append(_text(part))
                    elif part.type == "namespace_import":
                        ident = next(
                            (c for c in part.named_children if c.type == "identifier"), None
                        )
                        locals_.append(_text(ident))
                    elif part.type == "named_imports":
                        specifiers.extend(self._specifiers(part))
        names: list[ImportName] = []
        for spec_node in specifiers:
            name_node = spec_node.child_by_field_name("name")
            name = _string_value(name_node) if name_node is not None else None
            name = _text(name_node) if name is None else name
            alias_node = spec_node.child_by_field_name("alias")
            local = _text(alias_node) if alias_node is not None else None
            names.append(ImportName(name, local))
            if is_import and not is_relative_spec(spec):
                self._bind_member(local or name, name, spec, [])
        if is_import and not is_relative_spec(spec):
            for local in locals_:
                self._add_binding(local, spec)
        type_only = self._has_type_token(node) or (
            bool(specifiers) and not locals_ and all(self._has_type_token(s) for s in specifiers)
        )
        context = self._context(node, st, type_only=type_only)
        if self._is_internal(spec):
            self._record_internal(node, spec, "import" if is_import else "export_from", context)
        if is_relative_spec(spec):
            return
        alias = next((name for name in locals_ if name), None)
        self._record(node, st, spec, context, alias, tuple(names))

    def _binding_target(self, call: Node) -> tuple[Node | None, list[str]]:
        """``const x = require(...)``(後ろに ``.a.b`` が続いてもよい)の宣言と、続く属性の一覧。"""
        node = call
        attrs: list[str] = []
        while True:
            parent = node.parent
            if parent is None:
                return None, attrs
            if parent.type in _AWAIT_WRAPPERS:
                node = parent
            elif (
                parent.type == "member_expression" and parent.child_by_field_name("object") == node
            ):
                attrs.append(_text(parent.child_by_field_name("property")))
                node = parent
            elif (
                parent.type == "variable_declarator" and parent.child_by_field_name("value") == node
            ):
                return parent.child_by_field_name("name"), attrs
            else:
                return None, attrs

    def _bind_loaded(self, call: Node, module: str) -> tuple[str | None, tuple[ImportName, ...]]:
        """読み込みの結果を受ける名前(alias と分割代入の names)を束縛表に入れる。"""
        target, attrs = self._binding_target(call)
        if target is None:
            return None, ()
        if target.type == "identifier":
            local = _text(target)
            self._add_binding(local, module, attrs)
            return (None if attrs else local), ()
        names = []
        if target.type == "object_pattern":
            for part in target.named_children:
                if part.type == "shorthand_property_identifier_pattern":
                    name = _text(part)
                    names.append(ImportName(name, None))
                    self._bind_member(name, name, module, attrs)
                elif part.type == "pair_pattern":
                    key = _text(part.child_by_field_name("key"))
                    value = part.child_by_field_name("value")
                    if value is not None and value.type == "identifier":
                        names.append(ImportName(key, _text(value)))
                        self._bind_member(_text(value), key, module, attrs)
        return None, tuple(names)

    def _bind_member(self, local: str, member: str, module: str, attrs: list[str]) -> None:
        # default は読み込んだものそのもの(module.exports)として扱う
        self._add_binding(local, module, attrs if member == "default" else [*attrs, member])

    def _is_load_callee(self, function: Node) -> bool:
        if function.type == "import":
            return True
        if function.type == "identifier":
            return _text(function) in self.require_names or _text(function) == "importScripts"
        return function.type == "member_expression" and _text(function) == "module.require"

    def _call_import(self, node: Node, st: _State) -> None:
        function = node.child_by_field_name("function")
        arguments = node.child_by_field_name("arguments")
        if function is None or arguments is None:
            return
        args = [a for a in arguments.named_children if a.type != "comment"]
        name = _text(function)
        if function.type == "import":
            self._load_call(node, st, args, "import()", "dynamic_import")
        elif function.type == "identifier" and name == "define":
            self._amd_define(node, st, args)
        elif function.type == "identifier" and name in self.require_names:
            if name == "require" and args and args[0].type == "array":
                self._amd_list(node, st, args[0])
            else:
                self._load_call(node, st, args, "require", "require")
        elif function.type == "member_expression" and name == "module.require":
            self._load_call(node, st, args, "module.require", "require")
        elif function.type == "member_expression" and self._is_indirect_require(function):
            self._gap("dynamic_import", node, "require の間接的な呼び出し(候補を追わない)")
        elif self._is_import_scripts(function):
            self._import_scripts(node, st, args)

    def _is_indirect_require(self, function: Node) -> bool:
        obj = function.child_by_field_name("object")
        prop = _text(function.child_by_field_name("property"))
        return (
            obj is not None
            and obj.type == "identifier"
            and _text(obj) in self.require_names
            and prop in _INDIRECT_REQUIRE
        )

    def _amd_list(self, node: Node, st: _State, array: Node) -> None:
        """AMD の依存の一覧。文字列をそれぞれ読み込みとして出し、文字列以外があれば gap にする。"""
        unresolved = False
        for child in array.named_children:
            if child.type == "comment":
                continue
            value = _string_value(child)
            if value is None:
                unresolved = True
            elif self._is_internal(value):
                self._record_internal(node, value, "amd", self._context(node, st))
            if value is not None and not is_relative_spec(value):
                self._record(node, st, value, self._context(node, st))
        if unresolved:
            self._gap("dynamic_import", node, "AMD の依存の一覧が文字列だけではない")

    def _amd_define(self, node: Node, st: _State, args: list[Node]) -> None:
        if not args:
            return
        index = 1 if len(args) > 1 and _string_value(args[0]) is not None else 0
        deps = args[index]
        if deps.type == "array":
            self._amd_list(node, st, deps)
        elif deps.type not in _NON_DEPS:
            self._gap("dynamic_import", node, "AMD の依存の一覧が静的に決まらない")

    @staticmethod
    def _is_import_scripts(function: Node) -> bool:
        if function.type == "identifier":
            return _text(function) == "importScripts"
        if function.type == "member_expression":
            return _text(function.child_by_field_name("property")) == "importScripts"
        return False

    def _load_call(
        self,
        node: Node,
        st: _State,
        args: list[Node],
        label: str,
        internal_kind: str,
    ) -> None:
        if not args:
            return
        arg = args[0]
        literal = _string_value(arg)
        if literal is not None:
            context = self._context(node, st)
            if self._is_internal(literal):
                self._record_internal(node, literal, internal_kind, context)
            if not is_relative_spec(literal):
                alias, names = self._bind_loaded(node, literal)
                self._record(node, st, literal, context, alias, names)
            return
        resolved = None if arg.type == "spread_element" else self._resolve(arg, st.scope)
        if resolved is None:
            self._gap("dynamic_import", node, f"{label} の引数が静的に決まらない")
            return
        context = self._context(node, st)
        if context != "type_only":
            context = "dynamic"
        for module in dict.fromkeys(resolved[1]):
            if self._is_internal(module):
                self._record_internal(node, module, internal_kind, context)
            if is_relative_spec(module):
                continue
            alias, names = self._bind_loaded(node, module)
            self._record(node, st, module, context, alias, names)

    def _import_scripts(self, node: Node, st: _State, args: list[Node]) -> None:
        unresolved = False
        for arg in args:
            literal = _string_value(arg)
            resolved = ("str", [literal]) if literal is not None else self._resolve(arg, st.scope)
            if resolved is None or arg.type == "spread_element":
                unresolved = True
                continue
            context = self._context(node, st)
            if literal is None and context != "type_only":
                context = "dynamic"
            for path in dict.fromkeys(resolved[1]):
                found = _NODE_MODULES.findall(path)
                if found:
                    self._record(node, st, path, context, top=found[-1])
                else:
                    self._record_internal(node, path, "import_scripts", context)
        if unresolved:
            self._gap("dynamic_import", node, "importScripts の引数が静的に決まらない")

    # ---- 2回目: 利用・文字列の参照・文字列のコードの実行
    def _chain(self, node: Node) -> tuple[str, list[str]] | None:
        props: list[str] = []
        node = _unwrap(node)
        while node.type in ("member_expression", "subscript_expression"):
            obj = node.child_by_field_name("object")
            if obj is None:
                return None
            if node.type == "member_expression":
                prop = node.child_by_field_name("property")
                if prop is None:
                    return None
                props.append(_text(prop))
            else:
                index = node.child_by_field_name("index")
                value = _string_value(index) if index is not None else None
                if value is None:
                    return None
                props.append(value)
            node = _unwrap(obj)
        if node.type == "identifier":
            return _text(node), props[::-1]
        return None

    def _qualified(self, chain: tuple[str, list[str]]) -> list[tuple[str, str]]:
        """連なりの先頭の名前を import の束縛で解いた (名前, パッケージ名) の一覧。"""
        root, props = chain
        return [(".".join([q, *props]), top) for q, _, top in self.bindings.get(root, [])]

    def _use(self, kind: str, name: str, top: str, node: Node, st: _State) -> None:
        self.usage.uses.append(
            UseRecord(
                self.language,
                kind,
                name,
                top,
                self.file,
                self._line(node),
                self._col(node),
                st.enclosing,
            )
        )

    def _uses_visit(self, node: Node, st: _State) -> bool:
        kind = node.type
        if kind in ("call_expression", "new_expression"):
            return self._callee_visit(node, st)
        if kind in ("member_expression", "subscript_expression"):
            chain = self._chain(node)
            qualified = self._qualified(chain) if chain else []
            for name, top in qualified:
                self._use("reference", name, top, node, st)
            return not qualified
        if kind in ("identifier", "shorthand_property_identifier"):
            if _text(node) == "eval":
                # R7: eval は呼び出し以外の参照((0, eval)(s)、const e = eval)も gap にする
                self._gap("dynamic_eval", node, "eval による文字列のコードの実行")
            self._bare_reference(node, st)
        elif kind in ("string", "template_string"):
            self._string_reference(node)
        return True

    def _string_reference(self, node: Node) -> None:
        if not self.packages:
            return
        value = _string_value(node)
        if value is None and node.type == "template_string":
            # 式を含むテンプレート文字列は、先頭の固定部分が「名前.」「名前/」のときだけ照合する
            first = node.named_children[0] if node.named_children else None
            if first is not None and first.type == "string_fragment":
                head = _text(first)
                value = head if head.endswith((".", "/")) else None
        if value is None:
            return
        self.usage.gaps.extend(
            string_reference_gaps(self.language, self.file, self._line(node), value, self.packages)
        )

    # 式の中の値として使われる位置(宣言・import の名前を参照と取り違えないための許可リスト)
    _VALUE_PARENTS = frozenset(
        {
            "arguments",
            "array",
            "return_statement",
            "await_expression",
            "spread_element",
            "ternary_expression",
            "binary_expression",
            "sequence_expression",
            "jsx_expression",
            "parenthesized_expression",
        }
    )

    def _bare_reference(self, node: Node, st: _State) -> None:
        # 名前付き import・分割代入で入れた名前を、呼ばずに式の中で使う場合
        parent = node.parent
        entries = self.bindings.get(_text(node))
        if not entries or parent is None:
            return
        value_fields = {
            "pair": "value",
            "variable_declarator": "value",
            "assignment_expression": "right",
            "arrow_function": "body",
        }
        if parent.type in value_fields:
            if parent.child_by_field_name(value_fields[parent.type]) != node:
                return
        elif parent.type not in self._VALUE_PARENTS:
            return
        for qualified, is_member, top in entries:
            if is_member:
                self._use("reference", qualified, top, node, st)

    def _callee_visit(self, node: Node, st: _State) -> bool:
        is_new = node.type == "new_expression"
        function = node.child_by_field_name("constructor" if is_new else "function")
        if function is None:
            return True
        self._eval_gap(node, function, is_new)
        chain = self._chain(function)
        qualified = self._qualified(chain) if chain else []
        if not qualified:
            return True
        for name, top in qualified:
            self._use("call", name, top, function, st)
        # 呼び出しの先の連なりは1件にまとめたので、引数だけを続けて走査する
        for child in node.children:
            if child.type in ("arguments", "type_arguments"):
                self._walk(child, st, self._uses_visit)
        return False

    def _eval_gap(self, node: Node, function: Node, is_new: bool) -> None:
        function = _unwrap(function)
        hit = ""
        if function.type == "identifier":
            name = _text(function)
            if name == "Function" or (name in _VM_EVAL_METHODS and not is_new):
                hit = name
            elif name in _TIMER_NAMES and not is_new:
                hit = name if self._timer_has_code(node) else ""
        elif function.type == "member_expression":
            obj = _text(function.child_by_field_name("object"))
            prop = _text(function.child_by_field_name("property"))
            timer = prop in _TIMER_NAMES and obj in _GLOBAL_OBJECTS and self._timer_has_code(node)
            if (
                (prop in _VM_EVAL_METHODS and not is_new)
                or (prop == "Script" and is_new)
                or (prop in ("eval", "Function") and obj in _GLOBAL_OBJECTS)
                or timer
            ):
                hit = prop
        if hit == "Function" and self._is_global_object_idiom(node):
            return  # 契約 第4版: Function('return this') はグローバルオブジェクトを得るだけ
        if hit:
            self._gap("dynamic_eval", node, f"{hit} による文字列のコードの実行")

    @staticmethod
    def _is_global_object_idiom(node: Node) -> bool:
        """契約 第4版: 引数がちょうど 1 つの固定の文字列で、空白を除くと ``return this`` か ``return this;``。"""
        arguments = node.child_by_field_name("arguments")
        if arguments is None:
            return False
        args = [a for a in arguments.named_children if a.type != "comment"]
        if len(args) != 1:
            return False
        value = _string_value(args[0])
        return value is not None and re.fullmatch(r"\s*return\s+this\s*;?\s*", value) is not None

    @staticmethod
    def _timer_has_code(node: Node) -> bool:
        """setTimeout・setInterval の第1引数が文字列(コードの文字列)か。"""
        arguments = node.child_by_field_name("arguments")
        args = [a for a in arguments.named_children if a.type != "comment"] if arguments else []
        return bool(args) and _string_value(_unwrap(args[0])) is not None

    # ---- 下準備: require の別名(R3)と、候補にできない名前(R8)
    def _scan_names(self, root: Node) -> None:
        nodes = []
        stack = [root]
        while stack:
            current = stack.pop()
            nodes.append(current)
            stack.extend(current.children)
        create_names: set[str] = set()
        declarators = []
        for current in nodes:
            if current.type == "import_statement":
                source = current.child_by_field_name("source")
                if source is not None and _string_value(source) in _MODULE_SPECS:
                    for spec in self._descendants(current, "import_specifier"):
                        if _text(spec.child_by_field_name("name")) == "createRequire":
                            alias = spec.child_by_field_name("alias")
                            create_names.add(_text(alias) or "createRequire")
            elif current.type == "variable_declarator":
                declarators.append(current)
                self._scan_create_require(current, create_names)
        changed = True
        while changed:
            changed = False
            for decl in declarators:
                name = decl.child_by_field_name("name")
                value = decl.child_by_field_name("value")
                if name is None or name.type != "identifier" or value is None:
                    continue
                value = _unwrap(value)
                local = _text(name)
                if local in self.require_names:
                    continue
                is_alias = value.type == "identifier" and _text(value) in self.require_names
                if value.type == "call_expression":
                    function = value.child_by_field_name("function")
                    is_alias = function is not None and _text(function) in create_names
                if is_alias:
                    self.require_names.add(local)
                    changed = True
        for current in nodes:
            if current.type in ("identifier", "shorthand_property_identifier"):
                if not self._ref_allowed(current):
                    self.bad.add(_text(current))

    @staticmethod
    def _descendants(node: Node, kind: str) -> list[Node]:
        found = []
        stack = [node]
        while stack:
            current = stack.pop()
            if current.type == kind:
                found.append(current)
            stack.extend(current.children)
        return found

    @staticmethod
    def _scan_create_require(decl: Node, create_names: set[str]) -> None:
        """``const { createRequire } = require("module")`` の分割代入。"""
        name = decl.child_by_field_name("name")
        value = decl.child_by_field_name("value")
        if name is None or name.type != "object_pattern" or value is None:
            return
        if value.type != "call_expression" or _text(value.child_by_field_name("function")) != (
            "require"
        ):
            return
        arguments = value.child_by_field_name("arguments")
        first = arguments.named_children[0] if arguments and arguments.named_children else None
        if first is None or _string_value(first) not in _MODULE_SPECS:
            return
        for part in name.named_children:
            if part.type == "shorthand_property_identifier_pattern":
                if _text(part) == "createRequire":
                    create_names.add("createRequire")
            elif part.type == "pair_pattern":
                if _text(part.child_by_field_name("key")) == "createRequire":
                    create_names.add(_text(part.child_by_field_name("value")))

    def _ref_allowed(self, node: Node) -> bool:
        """名前の参照が「添字の読み取り」「for-of で回す」「動的な読み込みの引数」(か、宣言の名前)か。"""
        parent = node.parent
        if parent is None:
            return False
        kind = parent.type
        if kind == "variable_declarator":
            return parent.child_by_field_name("name") == node
        if kind in _FUNCTION_TYPES or kind in _CLASS_TYPES:
            return parent.child_by_field_name("name") == node or (
                parent.child_by_field_name("parameter") == node
            )
        if kind in ("required_parameter", "optional_parameter"):
            return parent.child_by_field_name("pattern") == node
        if kind == "assignment_pattern":
            return parent.child_by_field_name("left") == node
        if kind in _DECLARATION_PARENTS:
            return True
        if kind == "for_in_statement":
            if parent.child_by_field_name("left") == node:
                return True
            return parent.child_by_field_name("right") == node and (
                _text(parent.child_by_field_name("operator")) == "of"
            )
        if kind == "subscript_expression":
            return parent.child_by_field_name("object") == node
        if kind == "arguments":
            call = parent.parent
            function = call.child_by_field_name("function") if call is not None else None
            first = next((a for a in parent.named_children if a.type != "comment"), None)
            return function is not None and first == node and self._is_load_callee(function)
        return False

    # ---- 入口
    def run(self, root: Node) -> FileUsage:
        self._scan_names(root)
        scope = self.collect(root)
        start = _State(scope, None, False, False)
        self._walk(root, start, self._imports_visit)
        self._walk(root, start, self._uses_visit)
        return self.usage


def _first_error_line(root: Node) -> int | None:
    stack = [root]
    while stack:
        node = stack.pop()
        if node.is_error or node.is_missing:
            return int(node.start_point[0]) + 1
        # 子は後ろから積んで、先頭の誤りから見つける
        stack.extend(child for child in reversed(node.children) if child.has_error)
    return None


def analyze_js(language: str, rel_path: str, source: str, packages: frozenset[str]) -> FileUsage:
    """JavaScript/TypeScript 1ファイルの解析(``analyze_source`` から呼ばれる)。"""
    kind = "javascript"
    if language == "typescript":
        kind = "tsx" if rel_path.lower().endswith(".tsx") else "typescript"
    try:
        analyzer = _JsAnalyzer(language, rel_path, source, packages)
        tree = _parser(kind).parse(analyzer.src)
        root: Node = tree.root_node
        usage = analyzer.run(root)
    except RecursionError:
        return parse_failure(language, rel_path, None, "構造が深すぎて解析できない")
    except Exception as exc:  # 解析器の不具合でも、黙って落とさず gap にする
        return parse_failure(language, rel_path, None, f"解析中の内部エラー: {type(exc).__name__}")
    if root.has_error:
        usage.gaps.append(
            GapRecord(
                language,
                "parse_error",
                rel_path,
                _first_error_line(root),
                "構文木に ERROR・MISSING がある",
                None,
            )
        )
    return usage


__all__ = ["analyze_js"]
