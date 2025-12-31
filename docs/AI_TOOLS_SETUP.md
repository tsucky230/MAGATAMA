# AI ツール設定ガイド

このガイドでは、YATA MCP Server を各種 AI コーディングツールと連携させる方法を説明します。

## 目次

- [Claude Desktop](#claude-desktop)
- [GitHub Copilot (VS Code)](#github-copilot-vs-code)
- [Cursor](#cursor)
- [Continue](#continue)
- [設定の確認方法](#設定の確認方法)
- [一般的なトラブルシューティング](#一般的なトラブルシューティング)

---

## Claude Desktop

### macOS

1. 設定ファイルを開きます：

```bash
code ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

2. 以下の設定を追加：

```json
{
  "mcpServers": {
    "yata": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/yata", "yata", "serve"],
      "env": {}
    }
  }
}
```

> **注意**: `/path/to/yata` を実際の YATA インストールパスに置き換えてください。

### Windows

1. 設定ファイルを開きます：

```
%APPDATA%\Claude\claude_desktop_config.json
```

2. 以下の設定を追加：

```json
{
  "mcpServers": {
    "yata": {
      "command": "uv",
      "args": ["run", "--directory", "C:\\path\\to\\yata", "yata", "serve"]
    }
  }
}
```

### Linux

1. 設定ファイルを開きます：

```bash
code ~/.config/Claude/claude_desktop_config.json
```

2. macOS と同じ形式で設定。

### グローバルインストール版（PyPI）

```json
{
  "mcpServers": {
    "yata": {
      "command": "yata",
      "args": ["serve"]
    }
  }
}
```

---

## GitHub Copilot (VS Code)

### プロジェクトローカル設定

1. プロジェクトルートに `.vscode/mcp.json` を作成：

```json
{
  "mcpServers": {
    "yata": {
      "command": "uv",
      "args": ["run", "--directory", "${workspaceFolder}", "yata", "serve"]
    }
  }
}
```

### グローバル設定

VS Code の `settings.json` に追加：

```json
{
  "github.copilot.chat.experimental.mcpServers": {
    "yata": {
      "command": "yata",
      "args": ["serve"]
    }
  }
}
```

### SSE モードでの使用

開発中の動作確認に便利です：

```json
{
  "mcpServers": {
    "yata": {
      "type": "sse",
      "url": "http://localhost:8080"
    }
  }
}
```

別ターミナルでサーバーを起動：

```bash
yata serve --transport sse --port 8080
```

---

## Cursor

### 設定方法

1. Settings (⌘,) を開く
2. "MCP Servers" セクションを探す
3. 以下を追加：

```json
{
  "mcpServers": {
    "yata": {
      "command": "yata",
      "args": ["serve"]
    }
  }
}
```

または、プロジェクトルートに `.cursor/mcp.json` を作成：

```json
{
  "mcpServers": {
    "yata": {
      "command": "uv",
      "args": ["run", "--directory", ".", "yata", "serve"]
    }
  }
}
```

---

## Continue

### VS Code Extension 設定

`.continue/config.json`:

```json
{
  "mcpServers": [
    {
      "name": "yata",
      "command": "yata",
      "args": ["serve"]
    }
  ]
}
```

---

## 設定の確認方法

### サーバー起動テスト

```bash
# 基本動作確認
yata serve --help

# サーバー情報表示
yata info
```

### MCP Inspector を使った確認

```bash
# MCP Inspector でサーバーをテスト
npx @anthropic/mcp-inspector yata serve
```

ブラウザで http://localhost:5173 を開いて対話的にツールをテスト。

### 動作確認チェックリスト

- [ ] `yata info` でバージョンとツール一覧が表示される
- [ ] `yata parse <file>` でファイル解析ができる
- [ ] AI ツールから MCP サーバーに接続できる
- [ ] AI ツールで YATA ツールが利用可能になっている

---

## 一般的なトラブルシューティング

### サーバーが起動しない

**原因1: uv が見つからない**

```bash
# uv のインストールを確認
which uv

# インストールされていない場合
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**原因2: YATA がインストールされていない**

```bash
# 開発版を使用する場合
cd /path/to/yata
uv sync --all-packages
```

### AI ツールからサーバーに接続できない

**確認事項:**

1. パスが正しいか確認
2. コマンドを直接実行して動作確認
3. 設定ファイルの JSON が有効か確認

**デバッグ方法:**

```bash
# 直接コマンドを実行
uv run --directory /path/to/yata yata serve

# エラーログを確認
yata serve 2>&1 | head -50
```

### "Unknown tool" エラー

AI ツールが YATA のツールを認識していない場合：

1. AI ツールを再起動
2. MCP サーバー設定をリロード
3. `yata info` でツール一覧を確認

### パフォーマンスが遅い

**大規模プロジェクトの場合:**

1. 除外パターンを設定：

```bash
yata parse ./src --exclude "**/node_modules/**" --exclude "**/.git/**"
```

2. グラフを保存して再利用：

```bash
yata parse ./src --output graph.json
yata query "ClassName" --graph graph.json
```

### メモリ不足

**対策:**

1. 解析対象を絞る
2. 不要なファイルを除外
3. SQLite ストレージを使用（今後対応予定）

---

## よくある質問

### Q: どの言語がサポートされていますか？

A: Python, TypeScript/TSX, JavaScript/JSX, Rust, Go がサポートされています。

### Q: プライベートコードは外部に送信されますか？

A: いいえ。YATA は完全にローカルで動作し、コードやデータを外部に送信しません。

### Q: 複数のプロジェクトを同時に扱えますか？

A: はい。各プロジェクトで個別に MCP サーバーを設定できます。または、複数のディレクトリをまとめて解析することもできます。

### Q: グラフデータはどこに保存されますか？

A: デフォルトではメモリ上に保持されます。`--output` オプションで JSON ファイルに保存できます。

---

詳細なトラブルシューティングは [TROUBLESHOOTING.md](TROUBLESHOOTING.md) を参照してください。
