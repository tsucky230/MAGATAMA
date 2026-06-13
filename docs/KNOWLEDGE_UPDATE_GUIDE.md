# MAGATAMA 知識データベース更新ガイド

新しいバージョンのプログラミング言語やフレームワークがリリースされた際に、MAGATAMAの知識データベースを更新する方法を説明します。
（MAGATAMA は [YATA](https://github.com/nahisaho/YATA) のフォークで、フレームワーク知識機能は YATA 由来です。CLI コマンドは `magatama` です。）

## 目次

1. [概要](#概要)
2. [クイックスタート（自動更新）](#クイックスタート自動更新)
3. [前提条件](#前提条件)
4. [Step 1: GitHubからソースコードを取得](#step-1-githubからソースコードを取得)
5. [Step 2: ソースコード解析](#step-2-ソースコード解析)
6. [Step 3: 知識グラフの構築](#step-3-知識グラフの構築)
7. [Step 4: フレームワーク知識グラフの登録](#step-4-フレームワーク知識グラフの登録)
8. [Step 5: 検証とテスト](#step-5-検証とテスト)
9. [自動更新の設定](#自動更新の設定)
10. [トラブルシューティング](#トラブルシューティング)

---

## 概要

MAGATAMAの知識データベースは以下の2種類で構成されています：

| 種類 | 説明 | 更新頻度 |
|------|------|---------|
| **言語パーサー** | Tree-sitterによるAST解析定義 | 言語仕様変更時 |
| **フレームワーク知識グラフ** | フレームワークの構造・API・パターン | 新バージョンリリース時 |

```
┌─────────────────────────────────────────────────┐
│                MAGATAMA Knowledge DB            │
├─────────────────────────────────────────────────┤
│  ┌─────────────┐    ┌─────────────────────────┐ │
│  │  言語パーサー │    │ フレームワーク知識グラフ │ │
│  │  (24言語)    │    │ (47フレームワーク)       │ │
│  └─────────────┘    └─────────────────────────┘ │
└─────────────────────────────────────────────────┘
```

---

## クイックスタート（自動更新）

`update_knowledge_db.py` スクリプトを使用すると、全47フレームワークのリポジトリ更新と知識グラフの再構築を自動で行えます。

### 全フレームワークを更新

```bash
# 仮想環境を有効化
cd /path/to/MAGATAMA
source .venv/bin/activate

# 全フレームワークを一括更新（git pull + 知識グラフ再構築）
python scripts/update_knowledge_db.py
```

### よく使うオプション

```bash
# 特定のフレームワークのみ更新
python scripts/update_knowledge_db.py --frameworks react vue django

# 不足しているフレームワークをクローン
python scripts/update_knowledge_db.py --clone-missing

# git pullをスキップして知識グラフのみ再構築
python scripts/update_knowledge_db.py --no-update

# リポジトリ更新のみ（知識グラフ構築をスキップ）
python scripts/update_knowledge_db.py --no-analyze

# ドライラン（実際には実行しない）
python scripts/update_knowledge_db.py --dry-run

# 並列実行数を指定（デフォルト: 4）
python scripts/update_knowledge_db.py --parallel 8
```

### 出力例

```
================================================================================
🔄 MAGATAMA Knowledge Database Updater
================================================================================
Frameworks: 47
Base path: /path/to/MAGATAMA/frameworks

📥 Updating repositories...
  ✅ React: Already up to date
  ✅ Django: Already up to date
  ✅ FastAPI: Updated: Fast-forward
  ...

🧠 Rebuilding knowledge graphs...
  [ 1/47] React... ✅ 2,847 entities, 1,523 relationships
  [ 2/47] Django... ✅ 5,234 entities, 3,891 relationships
  ...

================================================================================
📊 Summary
================================================================================
Git operations: 45 updated, 0 cloned, 2 failed
Frameworks analyzed: 47
Total entities: 89,234
Total relationships: 45,678

📄 Summary saved to: /path/to/MAGATAMA/knowledge_graphs/update_summary.json
```

---

## 前提条件

### 必要なツール

```bash
# MAGATAMA環境
cd /path/to/MAGATAMA
source .venv/bin/activate

# 必要なパッケージ確認
pip list | grep -E "magatama|tree-sitter|networkx"
```

### 必要な権限

- GitHubへのアクセス（public repoの場合は不要）
- 書き込み権限のあるディレクトリ

---

## Step 1: GitHubからソースコードを取得

### 1.1 リポジトリのクローン

```bash
# 作業ディレクトリの作成
mkdir -p ~/magatama-knowledge-update
cd ~/magatama-knowledge-update

# フレームワークのソースコードを取得
# 例: Django 5.0
git clone --depth 1 --branch v5.0 https://github.com/django/django.git django-5.0

# 例: FastAPI 0.110
git clone --depth 1 --branch 0.110.0 https://github.com/tiangolo/fastapi.git fastapi-0.110

# 例: React 19
git clone --depth 1 --branch v19.0.0 https://github.com/facebook/react.git react-19
```

### 1.2 特定のタグ/ブランチを取得

```bash
# 利用可能なタグを確認
git ls-remote --tags https://github.com/django/django.git | tail -20

# 特定バージョンをチェックアウト
git clone https://github.com/django/django.git django-latest
cd django-latest
git checkout tags/v5.0 -b v5.0-branch
```

### 1.3 GitHub APIを使用した自動取得

```python
#!/usr/bin/env python3
"""
framework_downloader.py - フレームワークソースコード自動取得ツール
"""
import subprocess
import requests
from pathlib import Path

FRAMEWORKS = {
    "django": {
        "repo": "django/django",
        "language": "python",
        "extensions": ["*.py"],
    },
    "fastapi": {
        "repo": "tiangolo/fastapi",
        "language": "python",
        "extensions": ["*.py"],
    },
    "react": {
        "repo": "facebook/react",
        "language": "javascript",
        "extensions": ["*.js", "*.jsx", "*.ts", "*.tsx"],
    },
    "vue": {
        "repo": "vuejs/core",
        "language": "typescript",
        "extensions": ["*.ts", "*.vue"],
    },
    "nextjs": {
        "repo": "vercel/next.js",
        "language": "typescript",
        "extensions": ["*.ts", "*.tsx"],
    },
}

def get_latest_release(repo: str) -> str:
    """GitHubから最新リリースタグを取得"""
    url = f"https://api.github.com/repos/{repo}/releases/latest"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()["tag_name"]
    return "main"

def clone_framework(name: str, version: str = None, output_dir: str = "."):
    """フレームワークをクローン"""
    config = FRAMEWORKS.get(name)
    if not config:
        print(f"Unknown framework: {name}")
        return None
    
    repo = config["repo"]
    
    # バージョン未指定時は最新を取得
    if not version:
        version = get_latest_release(repo)
    
    output_path = Path(output_dir) / f"{name}-{version}"
    
    if output_path.exists():
        print(f"Already exists: {output_path}")
        return output_path
    
    # クローン実行
    cmd = [
        "git", "clone",
        "--depth", "1",
        "--branch", version,
        f"https://github.com/{repo}.git",
        str(output_path)
    ]
    
    print(f"Cloning {name} {version}...")
    subprocess.run(cmd, check=True)
    
    return output_path

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python framework_downloader.py <framework> [version]")
        print(f"Available: {', '.join(FRAMEWORKS.keys())}")
        sys.exit(1)
    
    framework = sys.argv[1]
    version = sys.argv[2] if len(sys.argv) > 2 else None
    
    path = clone_framework(framework, version, "./frameworks")
    if path:
        print(f"Downloaded to: {path}")
```

使用例:

```bash
# 最新バージョンを取得
python framework_downloader.py django

# 特定バージョンを取得
python framework_downloader.py django v5.0

# 複数フレームワークを一括取得
for fw in django fastapi react vue; do
    python framework_downloader.py $fw
done
```

---

## Step 2: ソースコード解析

### 2.1 MAGATAMAパーサーでディレクトリ解析

```bash
# MAGATAMAのCLIを使用
magatama parse ./frameworks/django-5.0 \
    --pattern "**/*.py" \
    --exclude "**/tests/**" \
    --exclude "**/migrations/**" \
    --output django-5.0-graph.json

# TypeScript/JavaScriptプロジェクトの場合
magatama parse ./frameworks/react-19 \
    --pattern "**/*.js" \
    --pattern "**/*.jsx" \
    --pattern "**/*.ts" \
    --pattern "**/*.tsx" \
    --exclude "**/node_modules/**" \
    --exclude "**/__tests__/**" \
    --output react-19-graph.json
```

### 2.2 Pythonスクリプトでの解析

```python
#!/usr/bin/env python3
"""
parse_framework.py - フレームワーク解析スクリプト
"""
from pathlib import Path
from magatama_core.application.usecases import ParseDirectoryUseCase, ParseFileUseCase
from magatama_core.infrastructure.parsers import PythonParser, TypeScriptParser
from magatama_core.infrastructure.graph import NetworkXKnowledgeGraph

def parse_framework(
    source_dir: str,
    framework_name: str,
    version: str,
    language: str = "python",
    exclude_patterns: list = None
):
    """フレームワークを解析して知識グラフを構築"""
    
    # パーサー選択
    parsers = {
        "python": PythonParser(),
        "typescript": TypeScriptParser(),
        "javascript": TypeScriptParser(),  # JSもTSパーサーで対応
    }
    parser = parsers.get(language)
    if not parser:
        raise ValueError(f"Unsupported language: {language}")
    
    # 知識グラフ初期化
    graph = NetworkXKnowledgeGraph()
    
    # ユースケース
    parse_file_uc = ParseFileUseCase(parser, graph)
    parse_dir_uc = ParseDirectoryUseCase(parse_file_uc, graph)
    
    # 除外パターン
    exclude = exclude_patterns or [
        "**/tests/**",
        "**/test/**",
        "**/__pycache__/**",
        "**/node_modules/**",
        "**/dist/**",
        "**/build/**",
    ]
    
    # 拡張子パターン
    patterns = {
        "python": ["**/*.py"],
        "typescript": ["**/*.ts", "**/*.tsx"],
        "javascript": ["**/*.js", "**/*.jsx"],
    }
    
    # 解析実行
    print(f"Parsing {framework_name} {version}...")
    result = parse_dir_uc.execute(
        directory=source_dir,
        patterns=patterns.get(language, ["**/*"]),
        exclude_patterns=exclude
    )
    
    print(f"  Files parsed: {result.files_parsed}")
    print(f"  Entities found: {result.entities_count}")
    print(f"  Relationships: {result.relationships_count}")
    
    # グラフを保存
    output_file = f"{framework_name}-{version}-knowledge-graph.json"
    graph.save(output_file)
    print(f"  Saved to: {output_file}")
    
    return graph, result

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 4:
        print("Usage: python parse_framework.py <source_dir> <framework_name> <version> [language]")
        sys.exit(1)
    
    source_dir = sys.argv[1]
    framework_name = sys.argv[2]
    version = sys.argv[3]
    language = sys.argv[4] if len(sys.argv) > 4 else "python"
    
    parse_framework(source_dir, framework_name, version, language)
```

使用例:

```bash
# Django解析
python parse_framework.py ./frameworks/django-5.0 django 5.0 python

# React解析
python parse_framework.py ./frameworks/react-19 react 19.0 javascript
```

### 2.3 解析結果の確認

```bash
# 統計情報を表示
magatama stats --graph django-5.0-knowledge-graph.json

# エンティティを検索
magatama query "Model" --type class --graph django-5.0-knowledge-graph.json

# 整合性検証
magatama validate --graph django-5.0-knowledge-graph.json
```

---

## Step 3: 知識グラフの構築

### 3.1 エンティティの拡張情報追加

解析結果に対して、ドキュメントやメタデータを追加します。

```python
#!/usr/bin/env python3
"""
enrich_knowledge_graph.py - 知識グラフの拡張
"""
import json
from pathlib import Path

def enrich_entity(entity: dict, framework_docs: dict) -> dict:
    """エンティティにドキュメント情報を追加"""
    
    name = entity.get("name", "")
    
    # 公式ドキュメントからの情報追加
    if name in framework_docs:
        doc_info = framework_docs[name]
        entity["documentation"] = doc_info.get("description", "")
        entity["examples"] = doc_info.get("examples", [])
        entity["since_version"] = doc_info.get("since", "")
        entity["deprecated"] = doc_info.get("deprecated", False)
        entity["deprecated_in"] = doc_info.get("deprecated_in", "")
        entity["replacement"] = doc_info.get("replacement", "")
    
    return entity

def enrich_graph(graph_file: str, docs_file: str, output_file: str):
    """知識グラフ全体を拡張"""
    
    with open(graph_file, "r") as f:
        graph = json.load(f)
    
    with open(docs_file, "r") as f:
        docs = json.load(f)
    
    # 各エンティティを拡張
    for entity_id, entity in graph.get("entities", {}).items():
        graph["entities"][entity_id] = enrich_entity(entity, docs)
    
    # 保存
    with open(output_file, "w") as f:
        json.dump(graph, f, indent=2, ensure_ascii=False)
    
    print(f"Enriched graph saved to: {output_file}")

# Django用ドキュメント情報の例
DJANGO_DOCS = {
    "Model": {
        "description": "Django ORMの基底クラス。データベーステーブルを表現",
        "examples": [
            "class Article(models.Model):\n    title = models.CharField(max_length=200)",
        ],
        "since": "1.0",
    },
    "View": {
        "description": "HTTPリクエストを処理するクラスベースビュー",
        "examples": [
            "class ArticleView(View):\n    def get(self, request):\n        return HttpResponse('Hello')",
        ],
        "since": "1.3",
    },
    # ... 他のエンティティ
}
```

### 3.2 関係性の強化

```python
#!/usr/bin/env python3
"""
enhance_relationships.py - 関係性の強化
"""
from magatama_core.infrastructure.graph import NetworkXKnowledgeGraph
from magatama_core.domain.entities import RelationshipType

def add_framework_specific_relationships(graph: NetworkXKnowledgeGraph, framework: str):
    """フレームワーク固有の関係性を追加"""
    
    if framework == "django":
        # Model → Manager の関係
        for entity in graph.get_entities_by_type("class"):
            if entity.name.endswith("Manager"):
                model_name = entity.name.replace("Manager", "")
                model = graph.get_entity_by_name(model_name)
                if model:
                    graph.add_relationship(
                        source_id=model.id,
                        target_id=entity.id,
                        relationship_type=RelationshipType.CONTAINS,
                        metadata={"role": "default_manager"}
                    )
        
        # View → Template の関係（template_name属性から）
        # ...
    
    elif framework == "react":
        # Component → Hook の関係
        # ...
    
    return graph
```

---

## Step 4: フレームワーク知識グラフの登録

### 4.1 MAGATAMAへの登録

```python
#!/usr/bin/env python3
"""
register_framework.py - フレームワーク知識グラフの登録
"""
from magatama_core.application.usecases import RegisterFrameworkUseCase
from magatama_core.infrastructure.graph import NetworkXKnowledgeGraph

def register_framework(
    graph_file: str,
    framework_name: str,
    version: str,
    category: str,
    description: str
):
    """フレームワーク知識グラフをMAGATAMAに登録"""
    
    # グラフ読み込み
    graph = NetworkXKnowledgeGraph()
    graph.load(graph_file)
    
    # 登録用メタデータ
    metadata = {
        "name": framework_name,
        "version": version,
        "category": category,  # web-framework, testing, data-science, etc.
        "description": description,
        "language": detect_primary_language(graph),
        "entity_count": graph.get_stats()["total_entities"],
        "relationship_count": graph.get_stats()["total_relationships"],
    }
    
    # 登録
    register_uc = RegisterFrameworkUseCase(graph)
    result = register_uc.execute(
        framework_id=f"{framework_name}-{version}",
        metadata=metadata
    )
    
    print(f"Registered: {framework_name} {version}")
    print(f"  Entities: {metadata['entity_count']}")
    print(f"  Relationships: {metadata['relationship_count']}")
    
    return result

def detect_primary_language(graph):
    """グラフから主要言語を検出"""
    extensions = {}
    for entity in graph.get_all_entities():
        if entity.location and entity.location.file_path:
            ext = entity.location.file_path.suffix
            extensions[ext] = extensions.get(ext, 0) + 1
    
    ext_to_lang = {
        ".py": "python",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".js": "javascript",
        ".jsx": "javascript",
        ".rs": "rust",
        ".go": "go",
    }
    
    if extensions:
        most_common = max(extensions, key=extensions.get)
        return ext_to_lang.get(most_common, "unknown")
    return "unknown"

if __name__ == "__main__":
    # 例: Django 5.0の登録
    register_framework(
        graph_file="django-5.0-knowledge-graph.json",
        framework_name="django",
        version="5.0",
        category="web-framework",
        description="The web framework for perfectionists with deadlines"
    )
```

### 4.2 MCPツールでの登録

```bash
# MAGATAMAサーバーが起動している状態で
magatama register-framework \
    --graph django-5.0-knowledge-graph.json \
    --name django \
    --version 5.0 \
    --category web-framework
```

### 4.3 組み込みフレームワークとして追加

MAGATAMAの組み込みフレームワークとして追加する場合:

```python
# packages/magatama-core/src/magatama_core/infrastructure/frameworks/django_5_0.py

"""Django 5.0 フレームワーク知識グラフ"""

from magatama_core.domain.entities import (
    ClassEntity,
    FunctionEntity,
    ModuleEntity,
)
from magatama_core.domain.value_objects import EntityId, Location

DJANGO_5_0_ENTITIES = [
    ClassEntity(
        id=EntityId("django.db.models.Model"),
        name="Model",
        module="django.db.models",
        docstring="The base class for all Django models.",
        methods=["save", "delete", "clean", "full_clean"],
        bases=["object"],
        metadata={
            "since": "1.0",
            "category": "orm",
            "examples": [
                "class Article(models.Model):\n    title = models.CharField(max_length=200)"
            ],
        }
    ),
    # ... 他のエンティティ
]

DJANGO_5_0_RELATIONSHIPS = [
    # Model -> Field relationships
    # View -> Template relationships
    # etc.
]

def get_django_5_0_graph():
    """Django 5.0の知識グラフを返す"""
    from magatama_core.infrastructure.graph import NetworkXKnowledgeGraph
    
    graph = NetworkXKnowledgeGraph()
    
    for entity in DJANGO_5_0_ENTITIES:
        graph.add_entity(entity)
    
    for rel in DJANGO_5_0_RELATIONSHIPS:
        graph.add_relationship(**rel)
    
    return graph
```

---

## Step 5: 検証とテスト

### 5.1 知識グラフの検証

```bash
# 整合性チェック
magatama validate --graph django-5.0-knowledge-graph.json --repair

# 統計情報確認
magatama stats --graph django-5.0-knowledge-graph.json --json
```

### 5.2 機能テスト

```python
#!/usr/bin/env python3
"""
test_framework_knowledge.py - フレームワーク知識のテスト
"""
import pytest
from magatama_core.application.usecases import (
    SearchFrameworkUseCase,
    GetFrameworkEntityUseCase,
    GetCodingGuidanceUseCase,
)

class TestDjango50Knowledge:
    """Django 5.0知識グラフのテスト"""
    
    @pytest.fixture
    def framework_graph(self):
        from magatama_core.infrastructure.frameworks.django_5_0 import get_django_5_0_graph
        return get_django_5_0_graph()
    
    def test_model_class_exists(self, framework_graph):
        """Modelクラスが存在する"""
        entity = framework_graph.get_entity_by_name("Model")
        assert entity is not None
        assert entity.type == "class"
    
    def test_model_has_methods(self, framework_graph):
        """Modelクラスが主要メソッドを持つ"""
        entity = framework_graph.get_entity_by_name("Model")
        assert "save" in entity.methods
        assert "delete" in entity.methods
    
    def test_search_middleware(self, framework_graph):
        """middlewareで検索できる"""
        search_uc = SearchFrameworkUseCase(framework_graph)
        results = search_uc.execute("middleware")
        assert len(results) > 0
    
    def test_coding_guidance_available(self, framework_graph):
        """コーディングガイダンスが取得できる"""
        guidance_uc = GetCodingGuidanceUseCase(framework_graph)
        result = guidance_uc.execute(
            framework="django",
            task="create model"
        )
        assert result.recommended_code is not None
        assert "models.Model" in result.recommended_code

# テスト実行
# pytest test_framework_knowledge.py -v
```

### 5.3 統合テスト

```bash
# 全テスト実行
cd /path/to/MAGATAMA
python -m pytest packages/magatama-core/tests/ -v

# フレームワーク関連のみ
python -m pytest packages/magatama-core/tests/ -k "framework" -v
```

---

## 自動更新の設定

### GitHub Actionsによる自動更新

```yaml
# .github/workflows/update-frameworks.yml
name: Update Framework Knowledge

on:
  schedule:
    # 毎週月曜日の午前3時（UTC）に実行
    - cron: '0 3 * * 1'
  workflow_dispatch:
    inputs:
      framework:
        description: 'Framework to update'
        required: false
        default: 'all'

jobs:
  check-updates:
    runs-on: ubuntu-latest
    outputs:
      updates: ${{ steps.check.outputs.updates }}
    steps:
      - uses: actions/checkout@v4
      
      - name: Check for framework updates
        id: check
        run: |
          python scripts/check_framework_updates.py > updates.json
          echo "updates=$(cat updates.json)" >> $GITHUB_OUTPUT

  update-framework:
    needs: check-updates
    if: needs.check-updates.outputs.updates != '[]'
    runs-on: ubuntu-latest
    strategy:
      matrix:
        framework: ${{ fromJson(needs.check-updates.outputs.updates) }}
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      
      - name: Install dependencies
        run: |
          pip install uv
          uv sync --all-packages
      
      - name: Download framework source
        run: |
          python scripts/framework_downloader.py ${{ matrix.framework.name }} ${{ matrix.framework.version }}
      
      - name: Parse and build knowledge graph
        run: |
          python scripts/parse_framework.py \
            ./frameworks/${{ matrix.framework.name }}-${{ matrix.framework.version }} \
            ${{ matrix.framework.name }} \
            ${{ matrix.framework.version }} \
            ${{ matrix.framework.language }}
      
      - name: Run tests
        run: |
          python -m pytest packages/magatama-core/tests/ -k "framework" -v
      
      - name: Create Pull Request
        uses: peter-evans/create-pull-request@v6
        with:
          title: "Update ${{ matrix.framework.name }} to ${{ matrix.framework.version }}"
          body: |
            Automated update of ${{ matrix.framework.name }} knowledge graph.
            
            - Version: ${{ matrix.framework.version }}
            - Entities: (see stats)
            - Tests: Passed
          branch: "update-${{ matrix.framework.name }}-${{ matrix.framework.version }}"
```

### 更新チェックスクリプト

```python
#!/usr/bin/env python3
"""
scripts/check_framework_updates.py - フレームワーク更新チェック
"""
import json
import requests
from pathlib import Path

FRAMEWORKS_CONFIG = Path("config/frameworks.json")

def get_current_versions():
    """現在登録されているバージョンを取得"""
    if FRAMEWORKS_CONFIG.exists():
        with open(FRAMEWORKS_CONFIG) as f:
            return json.load(f)
    return {}

def get_latest_version(repo: str) -> str:
    """GitHubから最新バージョンを取得"""
    url = f"https://api.github.com/repos/{repo}/releases/latest"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()["tag_name"]
    return None

def check_updates():
    """更新が必要なフレームワークをチェック"""
    current = get_current_versions()
    
    frameworks = {
        "django": {"repo": "django/django", "language": "python"},
        "fastapi": {"repo": "tiangolo/fastapi", "language": "python"},
        "react": {"repo": "facebook/react", "language": "javascript"},
        "vue": {"repo": "vuejs/core", "language": "typescript"},
        "nextjs": {"repo": "vercel/next.js", "language": "typescript"},
    }
    
    updates = []
    for name, config in frameworks.items():
        latest = get_latest_version(config["repo"])
        current_version = current.get(name, {}).get("version")
        
        if latest and latest != current_version:
            updates.append({
                "name": name,
                "version": latest,
                "language": config["language"],
                "current": current_version,
            })
    
    return updates

if __name__ == "__main__":
    updates = check_updates()
    print(json.dumps(updates))
```

---

## トラブルシューティング

### よくある問題と解決方法

#### 1. パース失敗

```bash
# エラー: UnicodeDecodeError
# 解決: エンコーディング指定
magatama parse ./framework --encoding utf-8

# エラー: 大きすぎるファイル
# 解決: 最大ファイルサイズを増加
export MAGATAMA_MAX_FILE_SIZE=52428800  # 50MB
```

#### 2. 知識グラフの不整合

```bash
# 検証して修復
magatama validate --graph framework.json --repair

# 手動で確認
magatama query "*" --type class --graph framework.json | head -20
```

#### 3. 登録失敗

```python
# デバッグモードで実行
import logging
logging.basicConfig(level=logging.DEBUG)

from magatama_core.application.usecases import RegisterFrameworkUseCase
# ...
```

### ログの確認

```bash
# 詳細ログを有効化
export MAGATAMA_LOG_LEVEL=DEBUG
magatama parse ./framework --output graph.json 2>&1 | tee parse.log
```

---

## 参考リンク

- [MAGATAMA GitHub Repository](https://github.com/tsucky230/MAGATAMA)
- [YATA GitHub Repository](https://github.com/nahisaho/YATA)（フォーク元）
- [Tree-sitter Documentation](https://tree-sitter.github.io/tree-sitter/)
- [GitHub API Documentation](https://docs.github.com/en/rest)

---

**最終更新**: 2025-12-31
