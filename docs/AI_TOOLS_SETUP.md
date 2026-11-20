# AI ツール設定ガイド

このガイドでは、MAGATAMA MCP Server を各種 AI コーディングツールと連携させる方法を説明します。
（MAGATAMA は [YATA](https://github.com/nahisaho/YATA) のフォークです。CLI コマンドは `magatama` です。）

## comP に MAGATAMA の更新を任せる（おすすめ）

VS Code 拡張機能の [comP](https://github.com/tsucky230/comP)（0.12.3 以降）を使っている場合は、
comP が MAGATAMA を登録し、comP が動作を確かめた版に保ちます。
comP は Marketplace から自動で更新されるので、MAGATAMA を手で更新しなくても追随します。

1. [uv](https://docs.astral.sh/uv/) を入れる（comP は MAGATAMA を `uvx` で起動します）
2. VS Code の設定 `comp.magatama.manage` を ON にするか、
   コマンドパレットで **comP: Let comP manage MAGATAMA** を実行する
3. **comP: Setup Agents** を実行する。comP は自分の登録の隣に、次の登録を足します

```json
"magatama": {
  "command": "uvx",
  "args": ["magatama@0.7.3", "serve"],
  "env": { "COMP_MANAGED_BY": "comP" }
}
```

- `COMP_MANAGED_BY` は comP が書いた登録の目印です。comP が書き換えるのはこの目印のある登録だけで、
  版は上げる方向にしか変えません。ご自身で書いた登録は変更しません。
- comP は登録を書いた直後に、その版を裏でダウンロードします。エージェントの初回起動がダウンロード待ちになりません。
- ご自身の登録（`magatama serve`、`uv run --directory ...`）を使い続ける場合は、comP が起動時に版を確かめ、
  comP が動作を確かめた版より古ければお知らせします。

以下の手動の設定も、これまでどおり使えます。

## 目次

- [comP に MAGATAMA の更新を任せる（おすすめ）](#comp-に-magatama-の更新を任せるおすすめ)
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
    "magatama": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/MAGATAMA", "magatama", "serve"],
      "env": {}
    }
  }
}
```

> **注意**: `/path/to/MAGATAMA` を実際の MAGATAMA インストールパスに置き換えてください。

### Windows

1. 設定ファイルを開きます：

```
%APPDATA%\Claude\claude_desktop_config.json
```

2. 以下の設定を追加：

```json
{
  "mcpServers": {
    "magatama": {
      "command": "uv",
      "args": ["run", "--directory", "C:\\path\\to\\magatama", "magatama", "serve"]
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
    "magatama": {
      "command": "magatama",
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
    "magatama": {
      "command": "uv",
      "args": ["run", "--directory", "${workspaceFolder}", "magatama", "serve"]
    }
  }
}
```

### グローバル設定

VS Code の `settings.json` に追加：

```json
{
  "github.copilot.chat.experimental.mcpServers": {
    "magatama": {
      "command": "magatama",
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
    "magatama": {
      "type": "sse",
      "url": "http://localhost:8080"
    }
  }
}
```

別ターミナルでサーバーを起動：

```bash
magatama serve --transport sse --port 8080
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
    "magatama": {
      "command": "magatama",
      "args": ["serve"]
    }
  }
}
```

または、プロジェクトルートに `.cursor/mcp.json` を作成：

```json
{
  "mcpServers": {
    "magatama": {
      "command": "uv",
      "args": ["run", "--directory", ".", "magatama", "serve"]
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
      "name": "magatama",
      "command": "magatama",
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
magatama serve --help

# サーバー情報表示
magatama info
```

### MCP Inspector を使った確認

```bash
# MCP Inspector でサーバーをテスト
npx @anthropic/mcp-inspector magatama serve
```

ブラウザで http://localhost:5173 を開いて対話的にツールをテスト。

### 動作確認チェックリスト

- [ ] `magatama info` でバージョンとツール一覧が表示される
- [ ] `magatama parse <file>` でファイル解析ができる
- [ ] AI ツールから MCP サーバーに接続できる
- [ ] AI ツールで MAGATAMA ツールが利用可能になっている

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

**原因2: MAGATAMA がインストールされていない**

```bash
# 開発版を使用する場合
cd /path/to/MAGATAMA
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
uv run --directory /path/to/MAGATAMA magatama serve

# エラーログを確認
magatama serve 2>&1 | head -50
```

### "Unknown tool" エラー

AI ツールが MAGATAMA のツールを認識していない場合：

1. AI ツールを再起動
2. MCP サーバー設定をリロード
3. `magatama info` でツール一覧を確認

### パフォーマンスが遅い

**大規模プロジェクトの場合:**

1. 除外パターンを設定：

```bash
magatama parse ./src --exclude "**/node_modules/**" --exclude "**/.git/**"
```

2. グラフを保存して再利用：

```bash
magatama parse ./src --output graph.json
magatama query "ClassName" --graph graph.json
```

### メモリ不足

**対策:**

1. 解析対象を絞る
2. 不要なファイルを除外
3. SQLite ストレージを使用（今後対応予定）

---

## よくある質問

### Q: どの言語がサポートされていますか？

A: Python, TypeScript/TSX, JavaScript/JSX, Rust, Go をはじめ、合計 24 言語が
サポートされています。

### Q: プライベートコードは外部に送信されますか？

A: いいえ。MAGATAMA は完全にローカルで動作し、コードやデータを外部に送信しません。

### Q: 複数のプロジェクトを同時に扱えますか？

A: はい。各プロジェクトで個別に MCP サーバーを設定できます。または、複数のディレクトリをまとめて解析することもできます。

### Q: グラフデータはどこに保存されますか？

A: デフォルトではメモリ上に保持されます。`--output` オプションで JSON ファイルに保存できます。

---

詳細なトラブルシューティングは [TROUBLESHOOTING.md](TROUBLESHOOTING.md) を参照してください。
