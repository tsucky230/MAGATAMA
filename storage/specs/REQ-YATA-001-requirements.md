# YATA 要件定義書

**Project**: YATA (八咫)
**Version**: 1.3
**Created**: 2025-12-31
**Status**: Draft
**Author**: MUSUBI SDD

---

## 1. 概要

### 1.1 目的

本文書は、YATA（八咫）MCP Serverの機能要件および非機能要件をEARS（Easy Approach to Requirements Syntax）形式で定義する。

### 1.2 スコープ

- 知識グラフ構築エンジン
- MCP Server実装
- CLIインターフェース
- 主要プログラミング言語対応（Python, TypeScript, JavaScript, Rust, Go）

### 1.3 参照

- [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) - Anthropic公式MCP仕様
- [MCP Specification](https://spec.modelcontextprotocol.io/) - MCPプロトコル詳細仕様
- [MCP SDK (Python)](https://github.com/modelcontextprotocol/python-sdk) - Python SDK
- [MCP SDK (TypeScript)](https://github.com/modelcontextprotocol/typescript-sdk) - TypeScript SDK
- [Context7](https://github.com/upstash/context7) - ライブラリドキュメント配信MCP
- [CodeGraphMCPServer](https://github.com/nahisaho/CodeGraphMCPServer) - コード解析MCP

### 1.4 MCPプロトコル概要

Model Context Protocol (MCP) はAnthropicが開発したオープンスタンダードで、AIアシスタントと外部システムを接続するためのプロトコル。

**MCPの主要コンポーネント**:

| コンポーネント | 説明 |
|----------------|------|
| **Tools** | AIが実行できる機能（検索、データ取得等） |
| **Resources** | AIがアクセスできるデータ（ファイル、DB等） |
| **Prompts** | 事前定義されたプロンプトテンプレート |

**トランスポート**:
- **stdio**: ローカルプロセス間通信
- **SSE (Server-Sent Events)**: HTTPベースのリモート通信

---

## 2. 機能要件

### 2.1 知識グラフ構築（Feature: Knowledge Graph Construction）

#### REQ-KGC-001: ライブラリソースコード解析

**Type**: Event-driven

**Requirement**:
> WHEN ユーザーがライブラリのソースコードパスを指定した時、
> システムはそのソースコードをAST（抽象構文木）解析し、
> エンティティ（クラス、関数、メソッド、型定義）を抽出しなければならない（SHALL）。

**Acceptance Criteria**:
- [ ] Tree-sitterを使用したAST解析が実行される
- [ ] クラス、関数、メソッド、型定義が抽出される
- [ ] 抽出されたエンティティにはファイルパス、行番号、スコープ情報が含まれる
- [ ] エラー時は適切なエラーメッセージを返す
- [ ] 実際のOSSライブラリ（例：requests, fastapi）での統合テストを実施する

**Priority**: High
**Traceability**: → TST-KGC-001

---

#### REQ-KGC-002: 関係性抽出

**Type**: Event-driven

**Requirement**:
> WHEN エンティティ抽出が完了した時、
> システムはエンティティ間の関係性（継承、実装、呼び出し、依存、型参照）を
> 抽出しなければならない（SHALL）。

**Acceptance Criteria**:
- [ ] 継承関係（extends, inherits）が抽出される
- [ ] インターフェース実装関係が抽出される
- [ ] 関数/メソッド呼び出し関係が抽出される
- [ ] インポート/依存関係が抽出される
- [ ] 型参照関係が抽出される

**Priority**: High
**Traceability**: → TST-KGC-002

---

#### REQ-KGC-003: グラフストレージ

**Type**: Ubiquitous

**Requirement**:
> システムは抽出したエンティティと関係性を
> グラフ構造として永続化しなければならない（SHALL）。

**Acceptance Criteria**:
- [ ] NetworkXグラフ形式で保存される
- [ ] SQLiteをバックエンドストレージとして使用する
- [ ] インクリメンタル更新をサポートする
- [ ] グラフデータはJSON形式でエクスポート可能

**Priority**: High
**Traceability**: → TST-KGC-003

---

#### REQ-KGC-004: ドキュメント統合

**Type**: Optional Feature

**Requirement**:
> WHERE ドキュメント統合機能が有効な場合、
> システムはMarkdown/RST形式のドキュメントを解析し、
> 知識グラフに統合しなければならない（SHALL）。

**Acceptance Criteria**:
- [ ] Markdownファイルからセクション、コードブロックを抽出できる
- [ ] RSTファイルからセクション、コードブロックを抽出できる
- [ ] ドキュメントとコードエンティティの関連付けが可能
- [ ] ドキュメントにバージョン情報を付与できる

**Priority**: Medium
**Traceability**: → TST-KGC-004

---

#### REQ-KGC-005: バージョン管理

**Type**: Ubiquitous

**Requirement**:
> システムはライブラリのバージョンごとに
> 知識グラフを管理しなければならない（SHALL）。

**Acceptance Criteria**:
- [ ] バージョン文字列（semver）でグラフを区別できる
- [ ] 複数バージョンの知識グラフを同時に保持できる
- [ ] バージョン間の差分（追加/削除/変更エンティティ一覧）を取得できる
- [ ] 古いバージョンのグラフを削除できる

**Priority**: Medium
**Traceability**: → TST-KGC-005

---

#### REQ-KGC-006: コミュニティ検出

**Type**: Optional Feature

**Requirement**:
> WHERE GraphRAG機能が有効な場合、
> システムは知識グラフ内のエンティティをコミュニティ（モジュールクラスタ）に
> 自動分類しなければならない（SHALL）。

**Acceptance Criteria**:
- [ ] Louvainアルゴリズムによるコミュニティ検出が実行される
- [ ] 各コミュニティにサマリー（説明文）が生成される
- [ ] コミュニティ階層（親子関係）をサポートする
- [ ] コミュニティ単位でのクエリが可能

**Priority**: Medium
**Traceability**: → TST-KGC-006

---

#### REQ-KGC-007: GitHubリポジトリ取得

**Type**: Event-driven

**Requirement**:
> WHEN ユーザーがGitHubリポジトリURLを指定した時、
> システムは当該リポジトリをクローンまたはAPI経由で取得し、
> ソースコードを解析対象として準備しなければならない（SHALL）。

**Acceptance Criteria**:
- [ ] GitHubリポジトリURL（`https://github.com/owner/repo`）を受け付ける
- [ ] `git clone --depth 1`による浅いクローンをサポートする
- [ ] 特定タグ/ブランチ/コミットを指定できる
- [ ] GitHub API経由でのファイル取得をサポートする（オプション）
- [ ] レートリミットを考慮した取得を行う（60req/h 未認証、5000req/h 認証時）
- [ ] ローカルキャッシュにクローン済みリポジトリを保存する
- [ ] GitHub Personal Access Token（PAT）による認証をサポートする
- [ ] 環境変数（`GITHUB_TOKEN`）からトークンを読み取る

**Priority**: High
**Traceability**: → TST-KGC-007

---

#### REQ-KGC-008: ライブラリメタデータ抽出

**Type**: Event-driven

**Requirement**:
> WHEN リポジトリ取得が完了した時、
> システムはライブラリのメタデータ（名前、バージョン、説明、ライセンス等）を
> 抽出しなければならない（SHALL）。

**Acceptance Criteria**:
- [ ] `package.json`（npm）からメタデータを抽出できる
- [ ] `pyproject.toml` / `setup.py`（Python）からメタデータを抽出できる
- [ ] `Cargo.toml`（Rust）からメタデータを抽出できる
- [ ] `go.mod`（Go）からメタデータを抽出できる
- [ ] README.mdから説明文を抽出できる
- [ ] GitHub APIからリポジトリ情報（stars, forks, topics）を取得できる

**Priority**: Medium
**Traceability**: → TST-KGC-008

---

### 2.2 MCP Server（Feature: MCP Server）

#### REQ-MCP-001: MCPプロトコル準拠

**Type**: Ubiquitous

**Requirement**:
> システムはMCP（Model Context Protocol）仕様に
> 準拠したサーバーを実装しなければならない（SHALL）。

**Acceptance Criteria**:
- [ ] MCP Specification 1.0に準拠する
- [ ] stdioトランスポートをサポートする
- [ ] SSEトランスポートをサポートする
- [ ] 正しいJSONスキーマを返す
- [ ] Claude Desktop / GitHub Copilot / Cursorとの実接続テストを実施する

**Priority**: High
**Traceability**: → TST-MCP-001

---

#### REQ-MCP-002: ライブラリ検索ツール

**Type**: Event-driven

**Requirement**:
> WHEN MCPクライアントが`resolve_library`ツールを呼び出した時、
> システムはクエリに基づいて適切なライブラリを検索し、
> ライブラリIDを返さなければならない（SHALL）。

**Acceptance Criteria**:
- [ ] ライブラリ名の部分一致検索が可能
- [ ] 類似度スコアでランキングされる
- [ ] 最大10件の候補を返す（`max_results`パラメータで変更可能）
- [ ] ライブラリが見つからない場合は空リストを返す

**Priority**: High
**Traceability**: → TST-MCP-002

---

#### REQ-MCP-003: ドキュメントクエリツール

**Type**: Event-driven

**Requirement**:
> WHEN MCPクライアントが`query_docs`ツールを呼び出した時、
> システムは指定されたライブラリの知識グラフから
> 関連するドキュメントとコード例を返さなければならない（SHALL）。

**Acceptance Criteria**:
- [ ] キーワードベースのグラフ検索で関連コンテンツを取得する
- [ ] （オプション）ベクトル埋め込みによるセマンティック検索をサポート
- [ ] コード例を含む応答を返す
- [ ] バージョン指定が可能（デフォルト: 最新バージョン）
- [ ] 最大トークン数を指定できる（デフォルト: 8000トークン）

**Priority**: High
**Traceability**: → TST-MCP-003

---

#### REQ-MCP-004: コード構造クエリツール

**Type**: Event-driven

**Requirement**:
> WHEN MCPクライアントが`query_code_structure`ツールを呼び出した時、
> システムは知識グラフから指定されたエンティティの
> 構造情報（シグネチャ、依存関係、使用例）を返さなければならない（SHALL）。

**Acceptance Criteria**:
- [ ] クラス/関数の完全なシグネチャを返す
- [ ] 引数と戻り値の型情報を含む
- [ ] 依存関係グラフを返す
- [ ] コード例（実装例）を含む

**Priority**: High
**Traceability**: → TST-MCP-004

---

#### REQ-MCP-005: グラフ探索ツール

**Type**: Event-driven

**Requirement**:
> WHEN MCPクライアントがグラフ探索ツール（`find_dependencies`, `find_callers`, `find_implementations`）を呼び出した時、
> システムは知識グラフを探索して関連エンティティを返さなければならない（SHALL）。

**Acceptance Criteria**:
- [ ] 指定したエンティティの依存先を取得できる
- [ ] 指定した関数の呼び出し元を取得できる
- [ ] インターフェースの実装クラスを取得できる
- [ ] 探索深度を指定できる

**Priority**: Medium
**Traceability**: → TST-MCP-005

---

#### REQ-MCP-006: MCPリソース提供

**Type**: Ubiquitous

**Requirement**:
> システムはMCPリソースとして以下を提供しなければならない（SHALL）：
> - ライブラリ一覧
> - エンティティ詳細
> - グラフ統計情報

**Acceptance Criteria**:
- [ ] `yata://libraries` - 登録済みライブラリ一覧
- [ ] `yata://entities/{id}` - エンティティ詳細
- [ ] `yata://stats` - グラフ統計情報
- [ ] リソースURIスキーマが一貫している

**Priority**: Medium
**Traceability**: → TST-MCP-006

---

#### REQ-MCP-007: MCPプロンプト提供

**Type**: Ubiquitous

**Requirement**:
> システムはAIコーディング支援用のプロンプトテンプレートを
> MCP Promptsとして提供しなければならない（SHALL）。

**Acceptance Criteria**:
- [ ] `implement_with_library` - ライブラリを使った実装ガイド
- [ ] `explain_api` - API説明プロンプト
- [ ] `migrate_version` - バージョン移行ガイド
- [ ] `best_practices` - ベストプラクティスガイド

**Priority**: Low
**Traceability**: → TST-MCP-007

---

#### REQ-MCP-008: エラー応答形式

**Type**: Unwanted Behavior

**Requirement**:
> IF MCPツール実行中にエラーが発生した場合、
> システムはMCP仕様に準拠したエラーレスポンスを返さなければならない（SHALL）。

**Acceptance Criteria**:
- [ ] エラーコード（-32600〜-32603、アプリケーション固有）を含む
- [ ] 人間可読なエラーメッセージを含む
- [ ] エラーの詳細情報（data フィールド）を含む
- [ ] クライアントがクラッシュしないこと

**Priority**: High
**Traceability**: → TST-MCP-008

---

### 2.3 CLIインターフェース（Feature: CLI Interface）

#### REQ-CLI-001: ライブラリインデックス作成

**Type**: Event-driven

**Requirement**:
> WHEN ユーザーが`yata index <path>`コマンドを実行した時、
> システムは指定されたパスのソースコードを解析し、
> 知識グラフを構築しなければならない（SHALL）。

**Acceptance Criteria**:
- [ ] ローカルパスを指定できる
- [ ] GitHubリポジトリURLを指定できる（`https://github.com/owner/repo`）
- [ ] バージョン/タグ/ブランチを指定できる（`--version`, `--tag`, `--branch`）
- [ ] GitHub認証トークンを指定できる（`--token`または環境変数`GITHUB_TOKEN`）
- [ ] 進捗状況を表示する（プログレスバー形式）
- [ ] 完了時に統計情報を表示する（エンティティ数、関係数、処理時間）

**Priority**: High
**Traceability**: → TST-CLI-001

---

#### REQ-CLI-002: サーバー起動

**Type**: Event-driven

**Requirement**:
> WHEN ユーザーが`yata serve`コマンドを実行した時、
> システムはMCPサーバーを起動しなければならない（SHALL）。

**Acceptance Criteria**:
- [ ] stdioモードで起動できる
- [ ] SSEモードで起動できる（`--port`オプション）
- [ ] 使用する知識グラフを指定できる
- [ ] 起動メッセージを表示する

**Priority**: High
**Traceability**: → TST-CLI-002

---

#### REQ-CLI-003: クエリ実行

**Type**: Event-driven

**Requirement**:
> WHEN ユーザーが`yata query <query>`コマンドを実行した時、
> システムは知識グラフに対してクエリを実行し、
> 結果を表示しなければならない（SHALL）。

**Acceptance Criteria**:
- [ ] 自然言語クエリを受け付ける
- [ ] 結果をJSON形式で出力できる
- [ ] 結果を人間可読形式で出力できる
- [ ] 最大結果数を指定できる

**Priority**: Medium
**Traceability**: → TST-CLI-003

---

#### REQ-CLI-004: 統計情報表示

**Type**: Event-driven

**Requirement**:
> WHEN ユーザーが`yata stats`コマンドを実行した時、
> システムは知識グラフの統計情報を表示しなければならない（SHALL）。

**Acceptance Criteria**:
- [ ] 登録ライブラリ数を表示する
- [ ] エンティティ数（種類別）を表示する
- [ ] 関係性数を表示する
- [ ] ストレージサイズを表示する

**Priority**: Low
**Traceability**: → TST-CLI-004

---

#### REQ-CLI-005: ヘルプ表示

**Type**: Ubiquitous

**Requirement**:
> システムは`--help`フラグで各コマンドの使用方法を
> 表示しなければならない（SHALL）。

**Acceptance Criteria**:
- [ ] 全コマンドの一覧を表示する
- [ ] 各コマンドの詳細ヘルプを表示する
- [ ] オプションの説明を含む
- [ ] 使用例を含む

**Priority**: High
**Traceability**: → TST-CLI-005

---

#### REQ-CLI-006: ウォッチモード

**Type**: Event-driven

**Requirement**:
> WHEN ユーザーが`yata watch <path>`コマンドを実行した時、
> システムはファイル変更を監視し、
> 変更検出時に自動的にインクリメンタルインデックスを実行しなければならない（SHALL）。

**Acceptance Criteria**:
- [ ] ファイルシステムの変更（作成/更新/削除）を検出する
- [ ] デバウンス時間を設定できる（デフォルト: 1秒）
- [ ] 変更されたファイルのみを再インデックスする
- [ ] ウォッチ開始/停止をログ出力する
- [ ] Ctrl+Cで正常終了する

**Priority**: Medium
**Traceability**: → TST-CLI-006

---

### 2.4 言語サポート（Feature: Language Support）

#### REQ-LANG-001: Python対応

**Type**: Ubiquitous

**Requirement**:
> システムはPythonソースコードを解析し、
> 以下のエンティティを抽出しなければならない（SHALL）：
> クラス、関数、メソッド、型ヒント、デコレータ、モジュール。

**Acceptance Criteria**:
- [ ] クラス定義（継承含む）を抽出できる
- [ ] 関数定義（引数、戻り値型）を抽出できる
- [ ] 型ヒント（typing module）を解析できる
- [ ] デコレータを認識できる
- [ ] __init__.py のエクスポートを認識できる

**Priority**: High
**Traceability**: → TST-LANG-001

---

#### REQ-LANG-002: TypeScript対応

**Type**: Ubiquitous

**Requirement**:
> システムはTypeScriptソースコードを解析し、
> 以下のエンティティを抽出しなければならない（SHALL）：
> クラス、関数、インターフェース、型定義、ジェネリクス、モジュール。

**Acceptance Criteria**:
- [ ] クラス定義を抽出できる
- [ ] インターフェース定義を抽出できる
- [ ] 型エイリアス（type）を抽出できる
- [ ] ジェネリクス型パラメータを認識できる
- [ ] export/importを認識できる

**Priority**: High
**Traceability**: → TST-LANG-002

---

#### REQ-LANG-003: JavaScript対応

**Type**: Ubiquitous

**Requirement**:
> システムはJavaScriptソースコードを解析し、
> 以下のエンティティを抽出しなければならない（SHALL）：
> クラス、関数、メソッド、JSDocコメント、モジュール。

**Acceptance Criteria**:
- [ ] ES6+クラスを抽出できる
- [ ] アロー関数を認識できる
- [ ] JSDocからの型情報を抽出できる
- [ ] CommonJS/ESMモジュールを認識できる

**Priority**: High
**Traceability**: → TST-LANG-003

---

#### REQ-LANG-004: Rust対応

**Type**: Ubiquitous

**Requirement**:
> システムはRustソースコードを解析し、
> 以下のエンティティを抽出しなければならない（SHALL）：
> struct、enum、trait、impl、関数、マクロ、モジュール。

**Acceptance Criteria**:
- [ ] struct/enum定義を抽出できる
- [ ] trait定義を抽出できる
- [ ] impl blockを抽出できる
- [ ] ジェネリクス/ライフタイムを認識できる
- [ ] pub/mod構造を認識できる

**Priority**: Medium
**Traceability**: → TST-LANG-004

---

#### REQ-LANG-005: Go対応

**Type**: Ubiquitous

**Requirement**:
> システムはGoソースコードを解析し、
> 以下のエンティティを抽出しなければならない（SHALL）：
> struct、interface、関数、メソッド、パッケージ。

**Acceptance Criteria**:
- [ ] struct定義を抽出できる
- [ ] interface定義を抽出できる
- [ ] メソッド（レシーバー付き関数）を抽出できる
- [ ] パッケージ構造を認識できる

**Priority**: Medium
**Traceability**: → TST-LANG-005

---

## 3. 非機能要件

### 3.1 パフォーマンス（NFR: Performance）

#### REQ-NFR-001: インデックス速度

**Type**: Ubiquitous

**Requirement**:
> システムは100,000行のソースコードを
> 30秒以内にインデックス化しなければならない（SHALL）。

**Acceptance Criteria**:
- [ ] ベンチマーク: 100K行/30秒以下
- [ ] インクリメンタル更新: 2秒以下
- [ ] パフォーマンステストを実行する

**Priority**: High
**Traceability**: → TST-NFR-001

---

#### REQ-NFR-002: クエリ応答時間

**Type**: Ubiquitous

**Requirement**:
> システムはMCPクエリに対して
> 500ミリ秒以内に応答しなければならない（SHALL）。

**Acceptance Criteria**:
- [ ] 平均応答時間: 200ms以下
- [ ] 95パーセンタイル: 500ms以下
- [ ] タイムアウト: 5秒

**Priority**: High
**Traceability**: → TST-NFR-002

---

#### REQ-NFR-003: メモリ使用量

**Type**: Ubiquitous

**Requirement**:
> システムは通常運用時に
> 500MB以下のメモリを使用しなければならない（SHALL）。

**Acceptance Criteria**:
- [ ] 起動時: 100MB以下
- [ ] 運用時（10ライブラリ）: 500MB以下
- [ ] メモリリークがない

**Priority**: Medium
**Traceability**: → TST-NFR-003

---

### 3.2 信頼性（NFR: Reliability）

#### REQ-NFR-004: エラーハンドリング

**Type**: Unwanted Behavior

**Requirement**:
> IF ソースコード解析中にエラーが発生した場合、
> システムは詳細なエラーメッセージを出力し、
> 可能な限り処理を継続しなければならない（SHALL）。

**Acceptance Criteria**:
- [ ] 構文エラーのあるファイルをスキップして継続
- [ ] エラー内容（ファイル、行、理由）をログ出力
- [ ] 部分的なインデックスを保存
- [ ] 致命的エラーは適切に報告

**Priority**: High
**Traceability**: → TST-NFR-004

---

#### REQ-NFR-005: データ整合性

**Type**: Ubiquitous

**Requirement**:
> システムは知識グラフのデータ整合性を
> 常に維持しなければならない（SHALL）。

**Acceptance Criteria**:
- [ ] トランザクション的な更新
- [ ] 孤立ノード/エッジの検出と警告
- [ ] グラフの検証機能

**Priority**: Medium
**Traceability**: → TST-NFR-005

---

### 3.3 可用性（NFR: Availability）

#### REQ-NFR-006: 起動時間

**Type**: Ubiquitous

**Requirement**:
> システムはMCPサーバーを
> 2秒以内に起動しなければならない（SHALL）。

**Acceptance Criteria**:
- [ ] コールドスタート: 2秒以下
- [ ] 初期化エラー時は明確なメッセージ

**Priority**: Medium
**Traceability**: → TST-NFR-006

---

### 3.4 セキュリティ（NFR: Security）

#### REQ-NFR-007: ローカル実行

**Type**: Ubiquitous

**Requirement**:
> システムはローカル環境で完全に動作し、
> 外部サービスへのデータ送信を行ってはならない（SHALL NOT）。
> ただし、GitHubリポジトリ取得（REQ-KGC-007）は例外とする。

**Acceptance Criteria**:
- [ ] ネットワークアクセスは明示的に設定した場合のみ
- [ ] ソースコードが外部に送信されない
- [ ] オフラインでも基本機能が動作（ローカルインデックス済みデータ利用）
- [ ] GitHub連携は`yata index <github-url>`実行時のみネットワークアクセス
- [ ] テレメトリ/使用状況データの外部送信は行わない

**Priority**: High
**Traceability**: → TST-NFR-007

---

### 3.5 拡張性（NFR: Extensibility）

#### REQ-NFR-008: 言語追加

**Type**: Ubiquitous

**Requirement**:
> システムは新しいプログラミング言語のサポートを
> プラグイン形式で追加できる設計としなければならない（SHALL）。

**Acceptance Criteria**:
- [ ] 言語エクストラクターインターフェースが定義されている
- [ ] 新言語追加にコア変更が不要
- [ ] 言語追加のドキュメントが存在する

**Priority**: Medium
**Traceability**: → TST-NFR-008

---

#### REQ-NFR-009: ログ出力

**Type**: Ubiquitous

**Requirement**:
> システムは構造化ログを出力し、
> 運用・デバッグに必要な情報を提供しなければならない（SHALL）。

**Acceptance Criteria**:
- [ ] JSON形式の構造化ログをサポートする
- [ ] ログレベル（DEBUG, INFO, WARNING, ERROR）を設定できる
- [ ] ファイル/コンソール出力を選択できる
- [ ] リクエストID/コリレーションIDを含む
- [ ] パフォーマンスに影響しない（ログ出力 < 1ms）

**Priority**: Medium
**Traceability**: → TST-NFR-009

---

## 4. 制約事項

### 4.1 技術的制約

| 制約 | 説明 |
|------|------|
| Python Version | 3.11以上 |
| MCP Version | Specification 1.0準拠 |
| AST Parser | Tree-sitter使用 |
| Graph Engine | NetworkX使用 |
| Storage | SQLite（単一ファイル） |

### 4.2 運用制約

| 制約 | 説明 |
|------|------|
| 同時接続 | 1クライアント（stdio）/ 複数（SSE） |
| 最大ライブラリ数 | 100（推奨） |
| 最大ファイルサイズ | 10MB/ファイル |

---

## 5. 用語定義

| 用語 | 定義 |
|------|------|
| YATA | 八咫（やた）- 本プロジェクトの名称 |
| MCP | Model Context Protocol - AIツールとの通信プロトコル |
| 知識グラフ | エンティティと関係性を表現するグラフ構造 |
| エンティティ | コード内の意味的単位（クラス、関数等） |
| GraphRAG | グラフベースのRetrieval-Augmented Generation |
| AST | Abstract Syntax Tree - 抽象構文木 |
| Tree-sitter | 高速なAST解析ライブラリ |

---

## 6. 要件トレーサビリティマトリクス

| 要件ID | カテゴリ | 優先度 | テストID | 設計参照 |
|--------|----------|--------|----------|----------|
| REQ-KGC-001 | 知識グラフ | High | TST-KGC-001 | DES-001 |
| REQ-KGC-002 | 知識グラフ | High | TST-KGC-002 | DES-001 |
| REQ-KGC-003 | 知識グラフ | High | TST-KGC-003 | DES-002 |
| REQ-KGC-004 | 知識グラフ | Medium | TST-KGC-004 | DES-003 |
| REQ-KGC-005 | 知識グラフ | Medium | TST-KGC-005 | DES-002 |
| REQ-KGC-006 | 知識グラフ | Medium | TST-KGC-006 | DES-013 |
| REQ-KGC-007 | 知識グラフ | High | TST-KGC-007 | DES-017 |
| REQ-KGC-008 | 知識グラフ | Medium | TST-KGC-008 | DES-017 |
| REQ-MCP-001 | MCP Server | High | TST-MCP-001 | DES-004 |
| REQ-MCP-002 | MCP Server | High | TST-MCP-002 | DES-005 |
| REQ-MCP-003 | MCP Server | High | TST-MCP-003 | DES-005 |
| REQ-MCP-004 | MCP Server | High | TST-MCP-004 | DES-005 |
| REQ-MCP-005 | MCP Server | Medium | TST-MCP-005 | DES-005 |
| REQ-MCP-006 | MCP Server | Medium | TST-MCP-006 | DES-006 |
| REQ-MCP-007 | MCP Server | Low | TST-MCP-007 | DES-007 |
| REQ-MCP-008 | MCP Server | High | TST-MCP-008 | DES-014 |
| REQ-CLI-001 | CLI | High | TST-CLI-001 | DES-008 |
| REQ-CLI-002 | CLI | High | TST-CLI-002 | DES-008 |
| REQ-CLI-003 | CLI | Medium | TST-CLI-003 | DES-008 |
| REQ-CLI-004 | CLI | Low | TST-CLI-004 | DES-008 |
| REQ-CLI-005 | CLI | High | TST-CLI-005 | DES-008 |
| REQ-CLI-006 | CLI | Medium | TST-CLI-006 | DES-015 |
| REQ-LANG-001 | 言語サポート | High | TST-LANG-001 | DES-009 |
| REQ-LANG-002 | 言語サポート | High | TST-LANG-002 | DES-009 |
| REQ-LANG-003 | 言語サポート | High | TST-LANG-003 | DES-009 |
| REQ-LANG-004 | 言語サポート | Medium | TST-LANG-004 | DES-009 |
| REQ-LANG-005 | 言語サポート | Medium | TST-LANG-005 | DES-009 |
| REQ-NFR-001 | パフォーマンス | High | TST-NFR-001 | DES-010 |
| REQ-NFR-002 | パフォーマンス | High | TST-NFR-002 | DES-010 |
| REQ-NFR-003 | パフォーマンス | Medium | TST-NFR-003 | DES-010 |
| REQ-NFR-004 | 信頼性 | High | TST-NFR-004 | DES-011 |
| REQ-NFR-005 | 信頼性 | Medium | TST-NFR-005 | DES-011 |
| REQ-NFR-006 | 可用性 | Medium | TST-NFR-006 | DES-010 |
| REQ-NFR-007 | セキュリティ | High | TST-NFR-007 | DES-012 |
| REQ-NFR-008 | 拡張性 | Medium | TST-NFR-008 | DES-009 |
| REQ-NFR-009 | 運用性 | Medium | TST-NFR-009 | DES-016 |

---

## 7. 変更履歴

| バージョン | 日付 | 著者 | 変更内容 |
|------------|------|------|----------|
| 1.0 | 2025-12-31 | MUSUBI SDD | 初版作成 |
| 1.1 | 2025-12-31 | MUSUBI SDD | レビュー反映: 4件の要件追加、3件の要件明確化 |
| 1.2 | 2025-12-31 | MUSUBI SDD | MCP公式仕様参照追加、GitHub連携要件(REQ-KGC-007/008)追加 |
| 1.3 | 2025-12-31 | MUSUBI SDD | 軽微な改善: GitHub認証(PAT)サポート追加、REQ-NFR-007例外明記、CLI統計情報詳細化 |

---

*Generated by MUSUBI SDD - Requirements Phase*
