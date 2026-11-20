"""comP の index.db の形式の版を確かめる。

comP 0.12.3 から、comP は metadata に schema_version を書く。MAGATAMA が読む列を comP が変えるときに
上がる。版がずれていても読み込みは止めず、どちらを更新すればよいかを警告で知らせる。
"""

SUPPORTED_COMP_SCHEMA_VERSIONS: frozenset[str] = frozenset({"1"})


def check_comp_schema_version(metadata: dict[str, str]) -> list[str]:
    """index.db の metadata から、読み込みに付ける警告を返す。

    - schema_version がない(metadata 表がない場合を含む): comP が 0.12.3 より古い
    - 対応外の版: MAGATAMA がこの comP の索引形式に対応していない
    例外は投げない。
    """
    found = metadata.get("schema_version")
    if found is None:
        return [
            "comP index has no schema_version (comP older than 0.12.3, or the daemon has not "
            "initialized the index yet). Update comP to keep MAGATAMA's results reliable."
        ]
    if found not in SUPPORTED_COMP_SCHEMA_VERSIONS:
        supported = ", ".join(sorted(SUPPORTED_COMP_SCHEMA_VERSIONS))
        return [
            f"comP index format {found!r} is not supported by this MAGATAMA (supports: {supported}). "
            "Update MAGATAMA so it reads this comP's index correctly."
        ]
    return []
