# Project Structure

**Project**: YATA (八咫)
**Last Updated**: 2025-12-31
**Version**: 1.0

---

## Architecture Pattern

**Primary Pattern**: Clean Architecture + MCP Server

> YATAはClean Architectureパターンを採用し、MCPプロトコルを通じてAIコーディングツールにコンテキストを提供するサーバーアプリケーションです。
> コア機能は独立したドメイン層として実装され、MCP Interface層を通じて公開されます。

---

## Architecture Layers (YATA Specific)

### Layer 1: Domain / Core

**Purpose**: 知識グラフのコアロジックとエンティティ定義
**Location**: `src/yata/core/`
**Rules**:

- フレームワーク非依存の純粋なPythonコード
- MCPプロトコルへの依存なし
- 外部I/O操作なし

**Contents**:
| ファイル | 説明 |
|----------|------|
| `entities.py` | エンティティモデル（Class, Function, Method等） |
| `relations.py` | 関係性モデル（Inherits, Calls, Depends等） |
| `graph.py` | グラフ操作ロジック |
| `indexer.py` | インデックス作成ロジック |

### Layer 2: Application / Use Cases

**Purpose**: ユースケースの実装とサービスオーケストレーション
**Location**: `src/yata/application/`
**Rules**:

- Domain層のみに依存
- Infrastructure層のインターフェースを定義（Ports）
- 直接のI/O操作なし

**Contents**:
| ファイル | 説明 |
|----------|------|
| `library_service.py` | ライブラリ管理サービス |
| `query_service.py` | クエリ実行サービス |
| `index_service.py` | インデックス作成サービス |
| `ports.py` | インフラ層へのインターフェース |

### Layer 3: Infrastructure / Adapters

**Purpose**: 外部システムとの統合（ストレージ、パーサー）
**Location**: `src/yata/infrastructure/`
**Rules**:

- Application層のPortsを実装
- 全てのI/O操作をここに集約
- 具体的な技術実装

**Contents**:
| サブディレクトリ | 説明 |
|------------------|------|
| `storage/` | SQLite永続化、キャッシュ |
| `parsers/` | Tree-sitterパーサー実装 |

### Layer 4: Interface / Presentation

**Purpose**: MCPプロトコルインターフェース、CLI
**Location**: `src/yata/mcp/`, `src/yata/cli/`
**Rules**:

- Application層のサービスを呼び出し
- 入力バリデーションとレスポンス整形
- MCPプロトコル準拠

**Contents**:
| ファイル | 説明 |
|----------|------|
| `mcp/tools.py` | MCPツール定義（14ツール） |
| `mcp/resources.py` | MCPリソース定義 |
| `mcp/prompts.py` | MCPプロンプト定義 |
| `cli/commands.py` | CLIコマンド実装 |

### Layer Dependency Rules

```
┌─────────────────────────────────────────┐
│   Interface Layer (MCP/CLI)             │ ← Entry points
├─────────────────────────────────────────┤
│   Application Layer (Services)          │ ← Use Cases
├─────────────────────────────────────────┤
│   Infrastructure Layer (Storage/Parser) │ ← I/O & External
├─────────────────────────────────────────┤
│   Domain Layer (Core)                   │ ← Pure logic
└─────────────────────────────────────────┘

Dependency Direction: ↓ (outer → inner)
Domain layer has NO dependencies
```

---

## Directory Organization

### Root Structure (YATA)

```
YATA/
├── src/yata/              # メインパッケージ
│   ├── __init__.py
│   ├── __main__.py        # CLI entry point
│   ├── server.py          # MCP server main
│   ├── config.py          # Configuration
│   ├── core/              # Domain layer
│   │   ├── __init__.py
│   │   ├── entities.py    # エンティティモデル
│   │   ├── relations.py   # 関係性モデル
│   │   ├── graph.py       # グラフ操作
│   │   └── indexer.py     # インデックスロジック
│   ├── application/       # Application layer
│   │   ├── __init__.py
│   │   ├── library_service.py
│   │   ├── query_service.py
│   │   ├── index_service.py
│   │   └── ports.py       # インフラ層インターフェース
│   ├── infrastructure/    # Infrastructure layer
│   │   ├── __init__.py
│   │   ├── storage/
│   │   │   ├── __init__.py
│   │   │   ├── sqlite.py
│   │   │   └── cache.py
│   │   └── parsers/
│   │       ├── __init__.py
│   │       ├── base.py    # パーサーインターフェース
│   │       ├── python.py
│   │       ├── typescript.py
│   │       ├── javascript.py
│   │       ├── rust.py
│   │       └── go.py
│   └── mcp/               # MCP Interface layer
│       ├── __init__.py
│       ├── tools.py       # MCP Tools (14種)
│       ├── resources.py   # MCP Resources
│       └── prompts.py     # MCP Prompts
├── tests/                 # テストスイート
│   ├── unit/              # ユニットテスト
│   ├── integration/       # 統合テスト
│   └── fixtures/          # テストフィクスチャ
├── docs/                  # ドキュメント
├── storage/               # SDD artifacts
│   ├── specs/             # 要件、設計、タスク
│   ├── changes/           # 変更仕様
│   └── archive/           # アーカイブ
├── steering/              # Project memory
│   ├── structure.ja.md    # このファイル
│   ├── tech.ja.md         # 技術スタック
│   ├── product.ja.md      # 製品コンテキスト
│   ├── project.yml        # プロジェクト設定
│   └── rules/             # Constitutional governance
├── templates/             # ドキュメントテンプレート
├── pyproject.toml         # Python project config
├── README.md              # プロジェクト説明
└── AGENTS.md              # AI Agent設定
```

---

## MCP Tools Architecture (Article II: CLI Interface)

YATAは14種類のMCPツールを提供します。

### Tool Categories

#### Library Discovery Tools
| ツール | 説明 | パラメータ |
|--------|------|-----------|
| `resolve_library` | ライブラリ名からIDを解決 | query, library_name |
| `list_libraries` | 登録済みライブラリ一覧 | - |

#### Documentation Tools
| ツール | 説明 | パラメータ |
|--------|------|-----------|
| `query_docs` | ドキュメント検索 | library_id, query, version |
| `get_api_reference` | API詳細取得 | library_id, entity_name |

#### Code Structure Tools
| ツール | 説明 | パラメータ |
|--------|------|-----------|
| `query_code_structure` | コード構造クエリ | library_id, query |
| `find_dependencies` | 依存関係取得 | entity_id, depth |
| `find_callers` | 呼び出し元取得 | entity_id |
| `find_implementations` | 実装クラス取得 | interface_id |

#### GraphRAG Tools
| ツール | 説明 | パラメータ |
|--------|------|-----------|
| `global_search` | グローバル検索 | query |
| `local_search` | ローカル検索 | query, entity_id |

#### Management Tools
| ツール | 説明 | パラメータ |
|--------|------|-----------|
| `index_library` | ライブラリインデックス作成 | path, name, version |
| `get_stats` | 統計情報取得 | library_id |
| `remove_library` | ライブラリ削除 | library_id |
| `update_library` | ライブラリ更新 | library_id, incremental |
│   │   └── page.tsx
│   └── register/
│       └── page.tsx
├── dashboard/
│   └── page.tsx
├── api/                  # API routes
│   ├── auth/
│   │   └── route.ts
│   └── users/
│       └── route.ts
├── layout.tsx            # Root layout
└── page.tsx              # Home page
```

### Application Guidelines

- **Library Usage**: Applications import from `lib/` modules
- **Thin Controllers**: API routes delegate to library services
- **No Business Logic**: Business logic belongs in libraries

---

## Component Organization

### UI Components

```
components/
├── ui/                   # Base UI components (shadcn/ui)
│   ├── button.tsx
│   ├── input.tsx
│   └── card.tsx
├── auth/                 # Feature-specific components
│   ├── LoginForm.tsx
│   └── RegisterForm.tsx
├── dashboard/
│   └── StatsCard.tsx
└── shared/               # Shared components
    ├── Header.tsx
    └── Footer.tsx
```

### Component Guidelines

- **Composition**: Prefer composition over props drilling
- **Types**: All props typed with TypeScript
- **Tests**: Component tests with React Testing Library

---

## Database Organization

### Schema Organization

```
prisma/
├── schema.prisma         # Prisma schema
├── migrations/           # Database migrations
│   ├── 001_create_users_table/
│   │   └── migration.sql
│   └── 002_create_sessions_table/
│       └── migration.sql
└── seed.ts               # Database seed data
```

### Database Guidelines

- **Migrations**: All schema changes via migrations
- **Naming**: snake_case for tables and columns
- **Indexes**: Index foreign keys and frequently queried columns

---

## Test Organization

### Test Structure

```
tests/
├── unit/                 # Unit tests (per library)
│   └── auth/
│       └── service.test.ts
├── integration/          # Integration tests (real services)
│   └── auth/
│       └── login.test.ts
├── e2e/                  # End-to-end tests
│   └── auth/
│       └── user-flow.test.ts
└── fixtures/             # Test data and fixtures
    └── users.ts
```

### Test Guidelines

- **Test-First**: Tests written BEFORE implementation (Article III)
- **Real Services**: Integration tests use real DB/cache (Article IX)
- **Coverage**: Minimum 80% coverage
- **Naming**: `*.test.ts` for unit, `*.integration.test.ts` for integration

---

## Documentation Organization

### Documentation Structure

```
docs/
├── architecture/         # Architecture documentation
│   ├── c4-diagrams/
│   └── adr/              # Architecture Decision Records
├── api/                  # API documentation
│   ├── openapi.yaml
│   └── graphql.schema
├── guides/               # Developer guides
│   ├── getting-started.md
│   └── contributing.md
└── runbooks/             # Operational runbooks
    ├── deployment.md
    └── troubleshooting.md
```

---

## SDD Artifacts Organization

### Storage Directory

```
storage/
├── specs/                # Specifications
│   ├── auth-requirements.md
│   ├── auth-design.md
│   ├── auth-tasks.md
│   └── payment-requirements.md
├── changes/              # Delta specifications (brownfield)
│   ├── add-2fa.md
│   └── upgrade-jwt.md
├── features/             # Feature tracking
│   ├── auth.json
│   └── payment.json
└── validation/           # Validation reports
    ├── auth-validation-report.md
    └── payment-validation-report.md
```

---

## Naming Conventions

### File Naming

- **TypeScript**: `PascalCase.tsx` for components, `camelCase.ts` for utilities
- **React Components**: `PascalCase.tsx` (e.g., `LoginForm.tsx`)
- **Utilities**: `camelCase.ts` (e.g., `formatDate.ts`)
- **Tests**: `*.test.ts` or `*.spec.ts`
- **Constants**: `SCREAMING_SNAKE_CASE.ts` (e.g., `API_ENDPOINTS.ts`)

### Directory Naming

- **Features**: `kebab-case` (e.g., `user-management/`)
- **Components**: `kebab-case` or `PascalCase` (consistent within project)

### Variable Naming

- **Variables**: `camelCase`
- **Constants**: `SCREAMING_SNAKE_CASE`
- **Types/Interfaces**: `PascalCase`
- **Enums**: `PascalCase`

---

## Integration Patterns

### Library → Application Integration

```typescript
// ✅ CORRECT: Application imports from library
import { AuthService } from '@/lib/auth';

const authService = new AuthService(repository);
const result = await authService.login(credentials);
```

```typescript
// ❌ WRONG: Library imports from application
// Libraries must NOT depend on application code
import { AuthContext } from '@/app/contexts/auth'; // Violation!
```

### Service → Repository Pattern

```typescript
// Service layer (business logic)
export class AuthService {
  constructor(private repository: UserRepository) {}

  async login(credentials: LoginRequest): Promise<LoginResponse> {
    // Business logic here
    const user = await this.repository.findByEmail(credentials.email);
    // ...
  }
}

// Repository layer (data access)
export class UserRepository {
  constructor(private prisma: PrismaClient) {}

  async findByEmail(email: string): Promise<User | null> {
    return this.prisma.user.findUnique({ where: { email } });
  }
}
```

---

## Deployment Structure

### Deployment Units

**Projects** (independently deployable):

1. YATA - Main application

> ⚠️ **Simplicity Gate (Article VII)**: Maximum 3 projects initially.
> If adding more projects, document justification in Phase -1 Gate approval.

### Environment Structure

```
environments/
├── development/
│   └── .env.development
├── staging/
│   └── .env.staging
└── production/
    └── .env.production
```

---

## Multi-Language Support

### Language Policy

- **Primary Language**: English
- **Documentation**: English first (`.md`), then Japanese (`.ja.md`)
- **Code Comments**: English
- **UI Strings**: i18n framework

### i18n Organization

```
locales/
├── en/
│   ├── common.json
│   └── auth.json
└── ja/
    ├── common.json
    └── auth.json
```

---

## Version Control

### Branch Organization

- `main` - Production branch
- `develop` - Development branch
- `feature/*` - Feature branches
- `hotfix/*` - Hotfix branches
- `release/*` - Release branches

### Commit Message Convention

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types**: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

**Example**:

```
feat(auth): implement user login (REQ-AUTH-001)

Add login functionality with email and password authentication.
Session created with 24-hour expiry.

Closes REQ-AUTH-001
```

---

## Constitutional Compliance

This structure enforces:

- **Article I**: Library-first pattern in `lib/`
- **Article II**: CLI interfaces per library
- **Article III**: Test structure supports Test-First
- **Article VI**: Steering files maintain project memory

---

## Changelog

### Version 1.1 (Planned)

- [Future changes]

---

**Last Updated**: 2025-12-31
**Maintained By**: {{MAINTAINER}}
