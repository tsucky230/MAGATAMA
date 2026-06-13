# YATA テスト戦略設計書

**Project**: YATA (八咫)
**Document ID**: DES-YATA-004
**Version**: 1.0
**Created**: 2025-12-31
**Status**: Draft
**Author**: MUSUBI SDD

---

## 1. 概要

本文書は、YATA MCP Serverのテスト戦略を定義する。MUSUBI憲法 Article III（Test-First Imperative）およびArticle IX（Integration-First Testing）に準拠する。

---

## 2. テストピラミッド

```
                    ┌─────────┐
                    │  E2E    │  ← 5%: MCPクライアント統合
                   ─┴─────────┴─
                  ┌─────────────┐
                  │ Integration │  ← 25%: 実サービス統合
                 ─┴─────────────┴─
                ┌─────────────────┐
                │   Unit Tests    │  ← 70%: Domain/Application層
               ─┴─────────────────┴─
```

| レベル | 対象 | 実行時間目標 | カバレッジ目標 |
|--------|------|--------------|----------------|
| Unit | Domain, Application層 | < 10秒 | 90% |
| Integration | Infrastructure層 | < 60秒 | 80% |
| E2E | MCP Server全体 | < 120秒 | 主要パス |

---

## 3. Red-Green-Blue サイクル（Article III）

### 3.1 ワークフロー

```
┌─────────────────────────────────────────────────────────────┐
│  1. RED: 失敗するテストを書く                                │
│     - 要件ID（REQ-XXX-NNN）をテスト名に含める                │
│     - テストが失敗することを確認                             │
├─────────────────────────────────────────────────────────────┤
│  2. GREEN: テストを通す最小限のコードを書く                  │
│     - 実装はテストを通すことのみに集中                       │
│     - パフォーマンスや美しさは後回し                         │
├─────────────────────────────────────────────────────────────┤
│  3. BLUE: リファクタリング                                   │
│     - テストが通る状態を維持                                 │
│     - コード品質の向上                                       │
│     - DRY, SOLID原則の適用                                  │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 コミット規約

```bash
# Red phase
git commit -m "test(REQ-KGC-001): add failing test for AST parsing"

# Green phase  
git commit -m "feat(REQ-KGC-001): implement basic AST parsing"

# Blue phase
git commit -m "refactor(REQ-KGC-001): extract parser interface"
```

---

## 4. ユニットテスト戦略

### 4.1 Domain層テスト

**対象**: `core/` ディレクトリ

```python
# tests/unit/core/test_entities.py
import pytest
from magatama.core.entities import Entity, EntityKind

class TestEntity:
    """REQ-KGC-001: エンティティ抽出"""
    
    def test_create_class_entity(self):
        """クラスエンティティが正しく作成される"""
        entity = Entity(
            kind=EntityKind.CLASS,
            name="MyClass",
            qualified_name="mymodule.MyClass",
            file_path="src/mymodule.py",
            line_start=10,
            line_end=50,
        )
        assert entity.kind == EntityKind.CLASS
        assert entity.name == "MyClass"
    
    def test_entity_requires_name(self):
        """名前なしエンティティは作成できない"""
        with pytest.raises(ValueError):
            Entity(kind=EntityKind.CLASS, name="")
```

### 4.2 Application層テスト

**対象**: `application/` ディレクトリ  
**方針**: Portsをモック化

```python
# tests/unit/application/test_library_service.py
import pytest
from unittest.mock import Mock
from magatama.application.library_service import LibraryService
from magatama.application.ports import StoragePort

class TestLibraryService:
    """REQ-MCP-002: ライブラリ検索"""
    
    @pytest.fixture
    def mock_storage(self):
        return Mock(spec=StoragePort)
    
    @pytest.fixture
    def service(self, mock_storage):
        return LibraryService(storage=mock_storage)
    
    def test_resolve_library_by_name(self, service, mock_storage):
        """ライブラリ名で検索できる"""
        mock_storage.search_libraries.return_value = [
            {"id": "lib-001", "name": "requests", "score": 0.95}
        ]
        
        result = service.resolve_library("requests")
        
        assert result[0]["name"] == "requests"
        mock_storage.search_libraries.assert_called_once()
```

---

## 5. 統合テスト戦略（Article IX）

### 5.1 実サービス使用原則

| サービス | テスト方針 | 理由 |
|----------|-----------|------|
| **SQLite** | ✅ 実DB使用 | ローカル、高速、コスト無し |
| **Tree-sitter** | ✅ 実パーサー使用 | ローカル、高速 |
| **FileSystem** | ✅ 実ファイル使用 | tmpdir fixture活用 |
| **GitHub API** | ⚠️ 条件付きモック | レートリミット、コスト |

### 5.2 SQLite統合テスト

```python
# tests/integration/storage/test_sqlite_storage.py
import pytest
import tempfile
from pathlib import Path
from magatama.infrastructure.storage.sqlite import SQLiteStorage
from magatama.core.graph import KnowledgeGraph

class TestSQLiteStorage:
    """REQ-KGC-003: グラフストレージ"""
    
    @pytest.fixture
    def db_path(self, tmp_path):
        """テスト用一時DBファイル"""
        return tmp_path / "test.sqlite"
    
    @pytest.fixture
    def storage(self, db_path):
        """実SQLiteストレージ"""
        return SQLiteStorage(db_path=str(db_path))
    
    def test_save_and_load_graph(self, storage):
        """グラフの保存と読み込み"""
        graph = KnowledgeGraph()
        graph.add_entity(...)
        
        storage.save_graph("lib-001", graph)
        loaded = storage.load_graph("lib-001")
        
        assert loaded.entity_count == graph.entity_count
    
    def test_incremental_update(self, storage):
        """インクリメンタル更新"""
        # ... 実DBでの更新テスト
```

### 5.3 Tree-sitter統合テスト

```python
# tests/integration/parsers/test_python_parser.py
import pytest
from magatama.infrastructure.parsers.python import PythonParser

class TestPythonParser:
    """REQ-LANG-001: Python対応"""
    
    @pytest.fixture
    def parser(self):
        return PythonParser()
    
    @pytest.fixture
    def sample_code(self):
        return '''
class MyClass:
    """Sample class docstring."""
    
    def my_method(self, arg: str) -> int:
        """Method docstring."""
        return len(arg)

def standalone_function(x: int, y: int) -> int:
    return x + y
'''
    
    def test_extract_class(self, parser, sample_code):
        """クラスを抽出できる"""
        entities = parser.parse(sample_code, "sample.py")
        
        classes = [e for e in entities if e.kind == "class"]
        assert len(classes) == 1
        assert classes[0].name == "MyClass"
    
    def test_extract_method_with_signature(self, parser, sample_code):
        """メソッドのシグネチャを抽出できる"""
        entities = parser.parse(sample_code, "sample.py")
        
        methods = [e for e in entities if e.kind == "method"]
        assert any(m.signature == "my_method(self, arg: str) -> int" for m in methods)
```

### 5.4 GitHub API テスト方針

```python
# tests/integration/github/test_github_client.py
import pytest
import os
from magatama.infrastructure.github.client import GitHubClient

# GitHub APIテストはCI環境でのみ実行（レートリミット考慮）
@pytest.mark.skipif(
    os.getenv("GITHUB_TOKEN") is None,
    reason="GITHUB_TOKEN not available"
)
class TestGitHubClient:
    """REQ-KGC-007: GitHubリポジトリ取得"""
    
    @pytest.fixture
    def client(self):
        return GitHubClient(token=os.getenv("GITHUB_TOKEN"))
    
    def test_clone_public_repo(self, client, tmp_path):
        """公開リポジトリをクローンできる"""
        result = client.clone(
            url="https://github.com/psf/requests",
            dest=tmp_path / "requests",
            depth=1
        )
        assert (tmp_path / "requests" / "README.md").exists()


# モック使用時の正当化ドキュメント
"""
GitHub API モック使用理由:
- 未認証時: 60 req/hour のレートリミット
- CI環境でのトークン管理が複雑
- 外部サービス依存によるテスト不安定化

代替策:
- GITHUB_TOKEN設定時のみ実APIテスト実行
- ローカル開発時はモックを許容
"""
```

---

## 6. E2Eテスト戦略

### 6.1 MCP統合テスト

```python
# tests/e2e/test_mcp_integration.py
import pytest
import subprocess
import json

class TestMCPIntegration:
    """REQ-MCP-001: MCPプロトコル準拠"""
    
    @pytest.fixture
    def mcp_server(self):
        """実MCPサーバープロセス"""
        proc = subprocess.Popen(
            ["python", "-m", "magatama", "serve", "--transport", "stdio"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        yield proc
        proc.terminate()
    
    def test_initialize_handshake(self, mcp_server):
        """MCP初期化ハンドシェイク"""
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test", "version": "1.0"}
            }
        }
        
        mcp_server.stdin.write(json.dumps(request).encode() + b"\n")
        mcp_server.stdin.flush()
        
        response = json.loads(mcp_server.stdout.readline())
        
        assert "result" in response
        assert "serverInfo" in response["result"]
    
    def test_list_tools(self, mcp_server):
        """ツール一覧取得"""
        # initialize first, then list tools
        ...
```

---

## 7. テストデータ管理

### 7.1 Fixture構造

```
tests/
├── fixtures/
│   ├── code_samples/
│   │   ├── python/
│   │   │   ├── simple_class.py
│   │   │   ├── complex_module.py
│   │   │   └── syntax_error.py
│   │   ├── typescript/
│   │   │   └── ...
│   │   └── ...
│   ├── graphs/
│   │   ├── small_graph.json
│   │   └── large_graph.json
│   └── mcp_requests/
│       ├── initialize.json
│       └── query_docs.json
├── conftest.py           # 共通fixture
├── unit/
├── integration/
└── e2e/
```

### 7.2 conftest.py

```python
# tests/conftest.py
import pytest
from pathlib import Path

@pytest.fixture
def fixtures_path():
    return Path(__file__).parent / "fixtures"

@pytest.fixture
def code_samples(fixtures_path):
    return fixtures_path / "code_samples"

@pytest.fixture
def python_samples(code_samples):
    return code_samples / "python"
```

---

## 8. カバレッジ要件

### 8.1 目標値

| メトリクス | 目標 | 必須 |
|-----------|------|------|
| Line Coverage | 85% | 80% |
| Branch Coverage | 80% | 75% |
| Function Coverage | 90% | 85% |

### 8.2 除外対象

```ini
# pyproject.toml
[tool.coverage.run]
omit = [
    "*/tests/*",
    "*/__main__.py",
    "*/cli/commands.py",  # E2Eでカバー
]
```

---

## 9. CI/CD統合

### 9.1 GitHub Actions

```yaml
# .github/workflows/test.yml
name: Test
on: [push, pull_request]

jobs:
  unit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run unit tests
        run: pytest tests/unit -v --cov=magatama
  
  integration:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run integration tests
        run: pytest tests/integration -v
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
  
  e2e:
    runs-on: ubuntu-latest
    needs: [unit, integration]
    steps:
      - uses: actions/checkout@v4
      - name: Run E2E tests
        run: pytest tests/e2e -v
```

---

## 10. 要件トレーサビリティ

| テストID | 要件ID | テストファイル | 種別 |
|----------|--------|----------------|------|
| TST-KGC-001 | REQ-KGC-001 | test_python_parser.py | Integration |
| TST-KGC-002 | REQ-KGC-002 | test_relation_extractor.py | Integration |
| TST-KGC-003 | REQ-KGC-003 | test_sqlite_storage.py | Integration |
| TST-KGC-007 | REQ-KGC-007 | test_github_client.py | Integration |
| TST-MCP-001 | REQ-MCP-001 | test_mcp_integration.py | E2E |
| TST-MCP-002 | REQ-MCP-002 | test_library_service.py | Unit |
| TST-NFR-001 | REQ-NFR-001 | test_performance.py | Integration |

---

## 11. 変更履歴

| バージョン | 日付 | 著者 | 変更内容 |
|------------|------|------|----------|
| 1.0 | 2025-12-31 | MUSUBI SDD | 初版作成 |

---

*Generated by MUSUBI SDD - Design Phase (Test Strategy)*
