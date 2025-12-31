# YATA トラブルシューティングガイド

よくある問題と解決方法をまとめています。

---

## YATA について

**YATA（八咫）** は、[MUSUBI](https://github.com/nahisaho/musubi)（Ultimate Specification Driven Development）を強化するシステムとして誕生しました。

YATA は [CodeGraph MCP Server](https://github.com/nahisaho/CodeGraphMCPServer) に続く **2つ目の MCP Server** です。CodeGraph MCP Server がコードベースの知識グラフ構築に特化しているのに対し、YATA はフレームワーク知識グラフ、デザインパターン検出、コード品質分析など、より高度な AI コーディング支援機能を提供します。

YATA は [Context7](https://context7.com/) を超える機能を実装しています。詳細は [YATA vs Context7](YATA_vs_Context7.md) を参照してください。

| プロジェクト | 役割 |
|-------------|------|
| [MUSUBI](https://github.com/nahisaho/musubi) | Ultimate Specification Driven Development フレームワーク |
| [CodeGraph MCP Server](https://github.com/nahisaho/CodeGraphMCPServer) | コードベース知識グラフ構築 MCP Server（1st） |
| **YATA** | AI コーディング支援 MCP Server（2nd） |
| [Context7](https://context7.com/) | ライブラリドキュメント提供 MCP Server（比較対象） |

---

## 目次

- [インストール関連](#インストール関連)
- [MCP サーバー関連](#mcp-サーバー関連)
- [解析関連](#解析関連)
- [パフォーマンス関連](#パフォーマンス関連)
- [AI ツール連携関連](#ai-ツール連携関連)
- [エラーメッセージ一覧](#エラーメッセージ一覧)

---

## インストール関連

### `uv` コマンドが見つからない

**症状:**

```
bash: uv: command not found
```

**解決方法:**

```bash
# uv をインストール
curl -LsSf https://astral.sh/uv/install.sh | sh

# シェルを再起動、または
source ~/.bashrc  # または ~/.zshrc
```

### 依存関係のインストールエラー

**症状:**

```
Error: Could not find tree-sitter-python
```

**解決方法:**

```bash
# キャッシュをクリアして再インストール
uv cache clean
uv sync --all-packages --reinstall
```

### Python バージョンエラー

**症状:**

```
Requires Python 3.11+
```

**解決方法:**

```bash
# Python 3.11+ をインストール
# macOS
brew install python@3.12

# Ubuntu
sudo apt install python3.12

# uv で指定バージョンを使用
uv python install 3.12
```

---

## MCP サーバー関連

### サーバーが起動しない

**症状:**

```
Error: Failed to start server
```

**確認事項:**

1. ポートが使用中でないか確認（SSE モード時）：

```bash
lsof -i :8080
# 使用中なら別ポートを指定
yata serve --transport sse --port 8081
```

2. 依存関係が正しくインストールされているか：

```bash
uv run python -c "import fastmcp; print(fastmcp.__version__)"
```

### stdio モードでハングする

**症状:**

サーバーを起動するとプロンプトが戻ってこない。

**説明:**

これは正常な動作です。stdio モードでは、サーバーは標準入出力を使って MCP クライアントと通信します。

**確認方法:**

```bash
# 別ターミナルで動作確認
echo '{"jsonrpc":"2.0","method":"initialize","id":1,"params":{}}' | yata serve | head -1
```

### SSE モードで接続できない

**症状:**

```
Connection refused: localhost:8080
```

**解決方法:**

1. サーバーが起動しているか確認：

```bash
curl http://localhost:8080/health
```

2. ファイアウォール設定を確認
3. 正しいポートを指定しているか確認

---

## 解析関連

### ファイルが認識されない

**症状:**

```
No files matched pattern
```

**解決方法:**

1. パターンを確認：

```bash
# デフォルトパターン
yata parse ./src --pattern "**/*.py"

# 複数パターン
yata parse ./src --pattern "**/*.py" --pattern "**/*.ts"
```

2. 絶対パスで試す：

```bash
yata parse /absolute/path/to/project
```

### 構文エラーがあるファイルの解析

**症状:**

```
Parse error in file.py
```

**説明:**

構文エラーがあるファイルでも、YATA は解析を試みます。エラーが発生した部分は無視され、解析可能な部分のみが処理されます。

**対処方法:**

1. ファイルの構文エラーを修正
2. または、そのファイルを除外：

```bash
yata parse ./src --exclude "**/broken_file.py"
```

### エンコーディングエラー

**症状:**

```
UnicodeDecodeError: 'utf-8' codec can't decode byte
```

**解決方法:**

1. ファイルを UTF-8 で保存し直す
2. バイナリファイルを除外：

```bash
yata parse ./src --exclude "**/*.bin" --exclude "**/*.exe"
```

---

## パフォーマンス関連

### 大規模プロジェクトでの遅延

**症状:**

解析に数分以上かかる。

**最適化方法:**

1. 不要なディレクトリを除外：

```bash
yata parse ./src \
  --exclude "**/node_modules/**" \
  --exclude "**/.git/**" \
  --exclude "**/dist/**" \
  --exclude "**/build/**" \
  --exclude "**/__pycache__/**"
```

2. ファイルパターンを絞る：

```bash
# 特定の拡張子のみ
yata parse ./src --pattern "**/*.py" --pattern "**/*.ts"
```

3. グラフを保存して再利用：

```bash
# 初回解析
yata parse ./src --output graph.json

# 以降はグラフをロード
yata query "search_term" --graph graph.json
```

### メモリ使用量が高い

**症状:**

メモリ使用量が 500MB を超える。

**対処方法:**

1. 解析対象を分割：

```bash
# サブディレクトリごとに解析
yata parse ./src/module1 --output module1.json
yata parse ./src/module2 --output module2.json
```

2. 除外パターンを追加して対象を絞る

### クエリが遅い

**症状:**

検索に 1 秒以上かかる。

**最適化方法:**

1. 具体的な検索条件を指定：

```bash
# 型を指定
yata query "process" --type function

# 結果数を制限
yata query "process" --max-results 10
```

---

## AI ツール連携関連

### Claude Desktop でツールが表示されない

**確認手順:**

1. 設定ファイルの JSON が有効か確認：

```bash
cat ~/Library/Application\ Support/Claude/claude_desktop_config.json | jq .
```

2. Claude Desktop を完全に再起動
3. コマンドを直接実行して動作確認：

```bash
uv run --directory /path/to/yata yata serve
```

### VS Code Copilot で認識されない

**確認手順:**

1. `.vscode/mcp.json` の設定を確認
2. VS Code を再起動
3. Copilot 拡張機能を無効化→有効化

### Cursor で接続エラー

**確認手順:**

1. `.cursor/mcp.json` の設定を確認
2. Cursor を再起動
3. 開発者ツール（F12）でエラーログを確認

---

## エラーメッセージ一覧

### `EntityNotFoundError: Entity not found: xxx`

**原因:** 指定された ID のエンティティが存在しない。

**対処:** エンティティ名を確認、または再度解析を実行。

### `EntityAlreadyExistsError: Entity already exists: xxx`

**原因:** 同じ ID のエンティティを重複して追加しようとした。

**対処:** グラフをクリアしてから再解析：

```bash
yata parse ./src --output graph.json  # 上書き
```

### `ParserNotFoundError: No parser for extension: .xxx`

**原因:** 対応していないファイル拡張子。

**対処:** サポートされている拡張子のファイルのみを解析：
- Python: `.py`
- TypeScript: `.ts`, `.tsx`
- JavaScript: `.js`, `.jsx`
- Rust: `.rs`
- Go: `.go`

### `ConfigurationError: Invalid configuration`

**原因:** 設定ファイルの形式が不正。

**対処:** JSON 形式を検証。

### `TimeoutError: Operation timed out`

**原因:** 操作がタイムアウト。

**対処:** 解析対象を絞る、または除外パターンを追加。

---

## デバッグ方法

### 詳細ログの有効化

```bash
# 環境変数でログレベルを設定
export YATA_LOG_LEVEL=DEBUG
yata parse ./src
```

### MCP 通信のデバッグ

```bash
# MCP Inspector を使用
npx @anthropic/mcp-inspector yata serve
```

### プロファイリング

```bash
# ベンチマーク実行
yata benchmark ./src --json > benchmark.json
```

---

## サポート

問題が解決しない場合：

1. [GitHub Issues](https://github.com/nahisaho/YATA/issues) で報告
2. 以下の情報を含めてください：
   - OS とバージョン
   - Python バージョン
   - YATA バージョン（`yata info`）
   - エラーメッセージの全文
   - 再現手順
