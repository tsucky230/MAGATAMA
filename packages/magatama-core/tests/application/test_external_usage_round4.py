"""外部パッケージの利用の地図: 契約 第4版(グローバルオブジェクトを得る定番の Function('return this'))のテスト。

契約: KAGAMI の docs/contracts/magatama-external-usage.md の「第4版」。
`Function('return this')`・`new Function('return this')`(引数が 1 つの固定の文字列で、空白を除くと `return this` か
`return this;`)は dynamic_eval の gap にしない。それ以外の Function・eval・vm・タイマーは今までどおり。
設計役(KAGAMI 側)が持ち主のテストで、実装役は変更しない。
"""

from __future__ import annotations

import pytest

from magatama_core.application.usecases.external_usage_usecase import analyze_source


def eval_gaps(source: str) -> int:
    return sum(g.kind == "dynamic_eval" for g in analyze_source("javascript", "a.js", source).gaps)


@pytest.mark.parametrize(
    "source",
    [
        "var root = freeGlobal || Function('return this')();\n",
        'var g = new Function("return this")();\n',
        "var g = Function(`return this;`)();\n",
        "var g = Function('  return   this ;  ')();\n",
        "var g = globalThis.Function('return this')();\n",
    ],
)
def test_global_object_idiom_is_not_a_gap(source: str) -> None:
    assert eval_gaps(source) == 0


@pytest.mark.parametrize(
    "source",
    [
        "var g = Function('return this.x')();\n",
        "var g = Function('a', 'return this')();\n",
        "var g = Function('return ' + 'this')();\n",
        "var g = Function(code)();\n",
        "var g = Function('return this')['req' + 'uire'];\nFunction('return 1');\n",  # 2 つ目は gap のまま
        "var g = Function('return this[\"re\" + \"quire\"](\"x\")')();\n",
        "eval('return this');\n",
    ],
)
def test_other_code_execution_is_still_a_gap(source: str) -> None:
    assert eval_gaps(source) >= 1


def test_lodash_root_shape_has_no_gap_and_keeps_imports() -> None:
    source = (
        "var freeGlobal = require('./_freeGlobal');\n"
        "var freeSelf = typeof self == 'object' && self && self.Object === Object && self;\n"
        "var root = freeGlobal || freeSelf || Function('return this')();\n"
        "module.exports = root;\n"
    )
    usage = analyze_source("javascript", "_root.js", source)
    assert [g.kind for g in usage.gaps] == []
    assert [i.specifier for i in usage.internal_imports] == ["./_freeGlobal"]
