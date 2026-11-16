# MAGATAMA（勾玉）— 変更前に、波及先を見に行く

> [Read in English](README.md)

直したい関数は見つかった。でも、そこを変えると誰が影響を受けるのか。前にそのファイルを触った理由は何だったのか。大きなリポジトリでは、こちらを確かめるほうに時間がかかります。

**comP がコードの関係を索引にし、MAGATAMA が変更前の確認に使える形へまとめます。** ファイルを指定すると、含まれるシンボル、呼び出し元などの波及候補、そのファイル、判断の根拠となる依存関係を返します。comP に作業履歴があれば、そのコードに言及した過去の依頼も調べられます。

## 変更する前に、確認する場所がわかる

共有ライブラリの関数を直す場面を考えてください。名前で検索するだけでは、別モジュールからの利用を見落とすかもしれません。全ファイルを読む方法では、見つけた関係を自分でつなぎ合わせる必要があります。

| 手順 | 得られるもの |
| --- | --- |
| comP で索引を作る | ファイル・シンボル・依存関係のローカルな地図 |
| MAGATAMA に変更対象を渡す | 波及候補と、その候補に至る依存関係 |
| 開発者が結果を確認する | 読むべき箇所と、実行するテストを選ぶ材料 |

メインのアプリと追加のライブラリを含む小さな検証データでは、次のように示せます。

~~~text
変更対象: E:/dev/shared/src/app.py
変更シンボル: main
波及候補: src/app.py の main
根拠: src/app.py の main が変更対象を呼び出す
~~~

これは**確認の出発点**です。実行時の影響をすべて証明するものではありません。ファイル名が曖昧な場合、索引に依存関係がない・読み飛ばした関係がある場合、または同じファイルが二重登録されている場合は、**unknown（要確認）**を返します。

## comP と併用すると何が増えるか

comP 単体でも関連コードの検索、影響グラフ、過去セッションの想起ができます。シンボルを探すときは comP が入口です。MAGATAMA はそのグラフをファイル単位の変更確認に使い、作業履歴をコードと結び付け、patrol の結果を次のセッションへ残します。

| 知りたいこと | 使う入口 |
| --- | --- |
| 「最初に読む関数はどれ？」 | comP の run_pipeline / get_context |
| 「このファイルを変えたら、どこを確認する？」 | MAGATAMA の analyze_change_scope |
| 「前にこのファイルを触った理由は？」 | 履歴を読み込んだ後の get_entity_history |
| 「前回から何が変わった？」 | MAGATAMA の patrol と comP の session_recall |

連携機能には comP の索引が必要です。comP の会話自動記録は**ベータ機能で、既定では OFF**です。履歴を調べるには、.comp/session-memory.json または .comp/history/ に記録が必要です。このリポジトリの Claude Stop hook は MAGATAMA の開発用で、PyPI からのインストールには含まれません。

## 自分のリポジトリで試す

1. VS Code に [comP を導入して起動](https://github.com/tsucky230/comP#installation--setup-3-steps)します。対象プロジェクトに .comp/index.db ができたことを確認してください。comP 自体を AI に接続する場合は、comP の **Setup Agents** コマンドを使えます。
2. `analyze_change_scope` は MAGATAMA v0.7.0 に含まれます。ソースのチェックアウトから試す場合は、次のコマンドを使います。

~~~bash
git clone https://github.com/tsucky230/MAGATAMA.git
cd MAGATAMA
uv sync --all-packages --dev
uv run magatama info
~~~

3. MAGATAMA を MCP サーバーとして登録します。.mcp.json を使うクライアントでは、次の設定が入口です。

~~~json
{
  "mcpServers": {
    "magatama": {
      "command": "uv",
      "args": ["run", "--directory", "<MAGATAMAのチェックアウト先>", "magatama", "serve"]
    }
  }
}
~~~

登録後は AI クライアントを再起動してください。クライアントごとの差は[設定ガイド](docs/AI_TOOLS_SETUP.md)を参照してください。

4. チャットで、自分のプロジェクトのパスを指定します。

~~~text
get_external_graph_info(path="<対象プロジェクト>") で索引を確認して。
続けて analyze_change_scope(path="<対象プロジェクト>",
files=["src/変更予定のファイル.py"]) を実行して。
波及候補のファイルと、それぞれの依存関係の根拠を教えて。
risk が unknown なら、確認が必要な索引の状態も教えて。
~~~

メインルートのファイルは相対パスです。追加ルートまで索引する comP の版では、そのファイルは絶対パスで保存されます。同名ファイルがあるときはフルパスを指定してください。

## 数字の読み方

以前の[概要把握の計測](OVERVIEW_jp.md)では、このリポジトリの選んだソースを読む場合の推定入力 **145,978 トークン**と、概要作成に使った comP の簡潔な要約 **289 トークン**を比較しました。これは当時の索引で行った一つの「概要把握」の計測です。変更影響の正確さや、どのプロジェクトでも同じ割合で節約できることを示す数字ではありません。

変更確認で大切なのは、具体的な波及先と、その根拠です。結果をコードやテストと照合してから編集してください。high / medium / low は、索引にある関係を使った目安です。

## 地図の使い道を広げる

- **PR の確認:** 差分に含まれない呼び出し元が波及候補にないか確かめる。
- **共有ライブラリの更新:** comP が複数ルートを索引していれば、利用側まで依存関係を追う。
- **作業の再開:** get_entity_history と comP の session_recall で、ファイルに結び付いた過去の判断を探す。
- **留守中の変更確認:** magatama patrol の記録を、次のセッションで読む。

必要な索引と履歴がある環境では、これらを今のツールで試せます。テストの自動選択や PR への自動注釈は今後の案で、現行機能ではありません。

## 詳しく読む・開発する

- [English README](README.md)
- [Web で読む](docs/index_ja.html)
- [comP 連携仕様と調査結果](docs/COMP_INTEGRATION.md)
- [AI ツール別設定](docs/AI_TOOLS_SETUP.md)
- [技術的な概観と計測方法](OVERVIEW_jp.md)
- [変更履歴](CHANGELOG.md)
- [comP](https://github.com/tsucky230/comP)

ソースから開発する場合は uv sync --all-packages --dev、テストは uv run pytest です。Python 3.11 以降を対象とし、[YATA](https://github.com/nahisaho/YATA) を基にしています。ライセンスは MIT です。報告や改善案は [GitHub リポジトリ](https://github.com/tsucky230/MAGATAMA) へどうぞ。
