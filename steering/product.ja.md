# Product Context

**Project**: YATA (八咫 - やた)
**Last Updated**: 2026-01-01
**Version**: 1.1

---

## Product Vision

**Vision Statement**: AI Codingの文脈理解を革新し、開発者がより正確で効率的なコード生成を実現できるようにする

> YATA（八咫）は、日本神話の八咫鏡（やたのかがみ）から名付けられたプロジェクトです。八咫鏡が真実を映し出すように、YATAはプログラミング言語やフレームワークの「真のコンテキスト」をAIに提供し、幻覚（ハルシネーション）のない正確なコード生成を支援します。

**Mission**: プログラミング言語・フレームワークのソースコードを知識グラフとして構造化し、MCPプロトコルを通じてAIコーディングツールに最新かつ正確なコンテキストを提供する

> CodeGraphMCPServerのコード分析機能を活用してソースコードの構造を解析し、Context7のようなドキュメンテーション配信機能と組み合わせることで、AIが必要とする文脈情報を効率的に提供します。

---

## Product Overview

### What is YATA?

YATAは、AI Codingアシスタント（GitHub Copilot、Claude、Cursor等）に対して、プログラミング言語やフレームワークの最新ドキュメントとコード構造を提供するMCP（Model Context Protocol）サーバーです。

> 従来のAIコーディングツールは、トレーニングデータに含まれる古い情報に依存しているため、最新のAPIや推奨されるベストプラクティスを認識できません。YATAは、ソースコードの静的解析による知識グラフと、最新ドキュメントの組み合わせにより、この課題を解決します。

### Problem Statement

**Problem**: AI Codingツールの文脈理解の限界

> 1. **古いトレーニングデータ**: LLMは数ヶ月〜数年前のデータで学習しており、最新のAPI変更を認識できない
> 2. **ハルシネーション**: 存在しないAPIやメソッドを生成してしまう
> 3. **文脈不足**: フレームワーク固有のベストプラクティスやパターンを理解していない
> 4. **バージョン非互換**: 特定バージョンに対応したコードを生成できない

### Solution

**Solution**: 知識グラフベースのコンテキスト配信システム

> 1. **リアルタイムコード解析**: CodeGraphMCPServerの技術を活用し、ソースコードをAST解析してエンティティと関係性を抽出
> 2. **知識グラフ構築**: 解析結果をグラフ構造として保存し、効率的な検索を可能にする
> 3. **MCP配信**: MCPプロトコルを通じて、AIツールにコンテキストを配信
> 4. **ドキュメント統合**: 公式ドキュメントとソースコードの両方からコンテキストを提供

---

## Target Users

### Primary Users

#### User Persona 1: AIコーディング開発者

**Demographics**:

- **Role**: ソフトウェアエンジニア / フルスタック開発者
- **Organization Size**: スタートアップ〜大企業
- **Technical Level**: 中級〜上級

**Goals**:

- AIコーディングツールでより正確なコードを生成したい
- 最新のフレームワークAPIを使用したコードを書きたい
- ドキュメント検索の時間を削減したい

**Pain Points**:

- AIが古いAPIや存在しないメソッドを提案する
- フレームワークのベストプラクティスに従ったコードが生成されない
- バージョン固有の情報を得るのが難しい

**Use Cases**:

- 新しいフレームワークの機能を使ったコード生成
- レガシーコードの最新バージョンへの移行支援
- フレームワーク固有のパターンに従ったコード実装

---

#### User Persona 2: ライブラリ/フレームワーク開発者

**Demographics**:

- **Role**: OSS開発者 / フレームワークメンテナー
- **Organization Size**: 個人〜大規模OSSプロジェクト
- **Technical Level**: 上級

**Goals**:

- 自分のライブラリの正しい使用方法をAIに学習させたい
- ユーザーが正しいコードを書けるよう支援したい

**Pain Points**:

- AIが古いバージョンのAPIを推奨してしまう
- ユーザーがdeprecatedな機能を使い続ける

**Use Cases**:

- 自分のライブラリの知識グラフを作成してAIに提供
- ユーザーが最新のAPI使用方法を学習できるようにする

---

### Secondary Users

- **企業のテックリード**: チーム全体のAIコーディング品質向上
- **教育機関**: プログラミング教育でのAI活用

---

## Market & Business Context

### Market Opportunity

**Market Size**: AI Coding Tools市場は2025年に$10B規模

**Target Market**: AI Coding Toolsを利用する開発者

> Context7などの競合製品はクラウド依存でプライバシー懸念がある。YATAは完全ローカル実行で差別化。

### Business Model

**Revenue Model**: OSS (MIT License)

> オープンソースとして提供し、コミュニティ貢献を促進

### Competitive Landscape

| Competitor | Strengths | Weaknesses | Our Differentiation |
| ---------- | --------- | ---------- | ------------------- |
| Context7 | クラウドDB充実 | プライバシー懸念、5言語のみ | 完全ローカル、21言語対応 |
| CodeGraph MCP | 高速解析 | フレームワーク知識なし | 27フレームワーク知識グラフ |

---

## Core Product Capabilities (実装済み)

### Phase 1: MVP機能 (Sprint 1-12)

1. **コード解析エンジン**
   - **Description**: 21言語対応のTree-sitter AST解析
   - **User Value**: あらゆる言語のソースコードを解析可能
   - **Priority**: P0 (Critical) ✅ 実装済み

2. **知識グラフ構築**
   - **Description**: NetworkXによるエンティティ・関係性グラフ
   - **User Value**: コード構造の可視化と検索
   - **Priority**: P0 (Critical) ✅ 実装済み

3. **MCP Server**
   - **Description**: 32種類のMCPツール提供
   - **User Value**: Claude/Copilot/Cursorとの統合
   - **Priority**: P0 (Critical) ✅ 実装済み

### Phase 2: Context7 Superior機能 (Sprint 13-15)

4. **ドキュメント自動生成 (REQ-001)**
   - **Description**: JSDoc/docstring形式の自動生成
   - **User Value**: ドキュメント作成の効率化
   - **Priority**: P0 (Critical) ✅ 実装済み

5. **コード推奨 (REQ-002)**
   - **Description**: 知識グラフベースのコード提案
   - **User Value**: ベストプラクティスに従ったコード
   - **Priority**: P0 (Critical) ✅ 実装済み

6. **依存関係影響分析 (REQ-003)**
   - **Description**: 変更影響範囲の自動特定
   - **User Value**: リファクタリング時の安全性向上
   - **Priority**: P1 (High) ✅ 実装済み

7. **ハイブリッド検索 (REQ-004)**
   - **Description**: キーワード+セマンティック統合検索
   - **User Value**: 意味的に類似したコードも発見
   - **Priority**: P1 (High) ✅ 実装済み

8. **コード品質分析 (REQ-005)**
   - **Description**: 循環的複雑度、結合度、凝集度メトリクス
   - **User Value**: コード品質の定量評価
   - **Priority**: P1 (High) ✅ 実装済み

9. **コード進化追跡 (REQ-006)**
   - **Description**: Git履歴からホットスポット検出
   - **User Value**: リファクタリング優先順位の判断
   - **Priority**: P2 (Medium) ✅ 実装済み

10. **AIコーディングガイダンス (REQ-007)**
    - **Description**: フレームワーク推奨コード生成
    - **User Value**: ベストプラクティスに従ったコード
    - **Priority**: P1 (High) ✅ 実装済み

11. **デザインパターン検出 (REQ-008)**
    - **Description**: 10種類のパターン自動検出
    - **User Value**: コード設計の理解向上
    - **Priority**: P2 (Medium) ✅ 実装済み

12. **API互換性チェック (REQ-009)**
    - **Description**: バージョン間の破壊的変更検出
    - **User Value**: バージョンアップ時のリスク軽減
    - **Priority**: P1 (High) ✅ 実装済み

13. **コードナビゲーション (REQ-010)**
    - **Description**: 関係性グラフの探索機能
    - **User Value**: コードベースの理解向上
    - **Priority**: P2 (Medium) ✅ 実装済み

### Future Features (Roadmap)

14. **リアルタイム同期**
    - **Description**: ファイル変更の即座反映
    - **User Value**: 常に最新のコンテキスト
    - **Priority**: P2 (Medium)

15. **マルチリポジトリ対応**
    - **Description**: 複数リポジトリの統合グラフ
    - **User Value**: モノレポ/マイクロサービス対応
    - **Priority**: P3 (Low)

---

## Product Principles

### Design Principles

1. **{{PRINCIPLE_1}}**
   - [Description of what this means for product decisions]

2. **{{PRINCIPLE_2}}**
   - [Description]

3. **{{PRINCIPLE_3}}**
   - [Description]

**Examples**:

- **Simplicity First**: Favor simple solutions over complex ones
- **User Empowerment**: Give users control and flexibility
- **Speed & Performance**: Fast response times (< 200ms)

### User Experience Principles

1. **{{UX_PRINCIPLE_1}}**
   - [How this guides UX decisions]

2. **{{UX_PRINCIPLE_2}}**
   - [How this guides UX decisions]

**Examples**:

- **Progressive Disclosure**: Show advanced features only when needed
- **Accessibility First**: WCAG 2.1 AA compliance
- **Mobile-First**: Design for mobile, enhance for desktop

---

## Success Metrics

### Key Performance Indicators (KPIs)

#### Business Metrics

| Metric                              | Target            | Measurement    |
| ----------------------------------- | ----------------- | -------------- |
| **Monthly Active Users (MAU)**      | {{MAU_TARGET}}    | [How measured] |
| **Monthly Recurring Revenue (MRR)** | ${{MRR_TARGET}}   | [How measured] |
| **Customer Acquisition Cost (CAC)** | ${{CAC_TARGET}}   | [How measured] |
| **Customer Lifetime Value (LTV)**   | ${{LTV_TARGET}}   | [How measured] |
| **Churn Rate**                      | < {{CHURN_RATE}}% | [How measured] |

#### Product Metrics

| Metric                       | Target                | Measurement    |
| ---------------------------- | --------------------- | -------------- |
| **Daily Active Users (DAU)** | {{DAU_TARGET}}        | [How measured] |
| **Feature Adoption Rate**    | > {{ADOPTION_RATE}}%  | [How measured] |
| **User Retention (Day 7)**   | > {{RETENTION_RATE}}% | [How measured] |
| **Net Promoter Score (NPS)** | > {{NPS_TARGET}}      | [How measured] |

#### Technical Metrics

| Metric                      | Target  | Measurement             |
| --------------------------- | ------- | ----------------------- |
| **API Response Time (p95)** | < 200ms | Monitoring dashboard    |
| **Uptime**                  | 99.9%   | Status page             |
| **Error Rate**              | < 0.1%  | Error tracking (Sentry) |
| **Page Load Time**          | < 2s    | Web vitals              |

---

## Product Roadmap

### Phase 1: MVP (Months 1-3)

**Goal**: Launch minimum viable product

**Features**:

- [Feature 1]
- [Feature 2]
- [Feature 3]

**Success Criteria**:

- [Criterion 1]
- [Criterion 2]

---

### Phase 2: Growth (Months 4-6)

**Goal**: Achieve product-market fit

**Features**:

- [Feature 4]
- [Feature 5]
- [Feature 6]

**Success Criteria**:

- [Criterion 1]
- [Criterion 2]

---

### Phase 3: Scale (Months 7-12)

**Goal**: Scale to {{USER_TARGET}} users

**Features**:

- [Feature 7]
- [Feature 8]
- [Feature 9]

**Success Criteria**:

- [Criterion 1]
- [Criterion 2]

---

## User Workflows

### Primary Workflow 1: {{WORKFLOW_1_NAME}}

**User Goal**: {{USER_GOAL}}

**Steps**:

1. User [action 1]
2. System [response 1]
3. User [action 2]
4. System [response 2]
5. User achieves [goal]

**Success Criteria**:

- User completes workflow in < {{TIME}} minutes
- Success rate > {{SUCCESS_RATE}}%

---

### Primary Workflow 2: {{WORKFLOW_2_NAME}}

**User Goal**: {{USER_GOAL}}

**Steps**:

1. [Step 1]
2. [Step 2]
3. [Step 3]

**Success Criteria**:

- [Criterion 1]
- [Criterion 2]

---

## Business Domain

### Domain Concepts

Key concepts and terminology used in this domain:

1. **{{CONCEPT_1}}**: [Definition and importance]
2. **{{CONCEPT_2}}**: [Definition and importance]
3. **{{CONCEPT_3}}**: [Definition and importance]

**Example for SaaS Authentication**:

- **Identity Provider (IdP)**: Service that authenticates users
- **Single Sign-On (SSO)**: One login for multiple applications
- **Multi-Factor Authentication (MFA)**: Additional verification step

### Business Rules

1. **{{RULE_1}}**
   - [Description of business rule]
   - **Example**: [Concrete example]

2. **{{RULE_2}}**
   - [Description]
   - **Example**: [Example]

**Example for E-commerce**:

- **Inventory Reservation**: Reserved items held for 10 minutes during checkout
- **Refund Window**: Refunds allowed within 30 days of purchase

---

## Constraints & Requirements

### Business Constraints

- **Budget**: ${{BUDGET}}
- **Timeline**: {{TIMELINE}}
- **Team Size**: {{TEAM_SIZE}} engineers
- **Launch Date**: {{LAUNCH_DATE}}

### Compliance Requirements

- **{{COMPLIANCE_1}}**: [Description, e.g., GDPR, SOC 2, HIPAA]
- **{{COMPLIANCE_2}}**: [Description]
- **Data Residency**: [Requirements, e.g., EU data stays in EU]

### Non-Functional Requirements

- **Performance**: API response < 200ms (95th percentile)
- **Availability**: 99.9% uptime SLA
- **Scalability**: Support {{CONCURRENT_USERS}} concurrent users
- **Security**: OWASP Top 10 compliance
- **Accessibility**: WCAG 2.1 AA compliance

---

## Stakeholders

### Internal Stakeholders

| Role                    | Name                 | Responsibilities                  |
| ----------------------- | -------------------- | --------------------------------- |
| **Product Owner**       | {{PO_NAME}}          | Vision, roadmap, priorities       |
| **Tech Lead**           | {{TECH_LEAD_NAME}}   | Architecture, technical decisions |
| **Engineering Manager** | {{EM_NAME}}          | Team management, delivery         |
| **QA Lead**             | {{QA_LEAD_NAME}}     | Quality assurance, testing        |
| **Design Lead**         | {{DESIGN_LEAD_NAME}} | UX/UI design                      |

### External Stakeholders

| Role                        | Name        | Responsibilities            |
| --------------------------- | ----------- | --------------------------- |
| **Customer Advisory Board** | [Members]   | Product feedback            |
| **Investors**               | [Names]     | Funding, strategic guidance |
| **Partners**                | [Companies] | Integration, co-marketing   |

---

## Go-to-Market Strategy

### Launch Strategy

**Target Launch Date**: {{LAUNCH_DATE}}

**Launch Phases**:

1. **Private Beta** ({{START_DATE}} - {{END_DATE}})
   - Invite-only, 50 beta users
   - Focus: Gather feedback, fix critical bugs

2. **Public Beta** ({{START_DATE}} - {{END_DATE}})
   - Open signup
   - Focus: Validate product-market fit

3. **General Availability** ({{LAUNCH_DATE}})
   - Full public launch
   - Focus: Acquisition and growth

### Marketing Channels

- **{{CHANNEL_1}}**: [Strategy, e.g., Content marketing, SEO]
- **{{CHANNEL_2}}**: [Strategy, e.g., Social media, Twitter/LinkedIn]
- **{{CHANNEL_3}}**: [Strategy, e.g., Paid ads, Google/Facebook]
- **{{CHANNEL_4}}**: [Strategy, e.g., Partnerships, integrations]

---

## Risk Assessment

### Product Risks

| Risk       | Probability     | Impact          | Mitigation            |
| ---------- | --------------- | --------------- | --------------------- |
| {{RISK_1}} | High/Medium/Low | High/Medium/Low | [Mitigation strategy] |
| {{RISK_2}} | High/Medium/Low | High/Medium/Low | [Mitigation strategy] |

**Example Risks**:

- **Low adoption**: Users don't understand value → Clear onboarding, demos
- **Performance issues**: System slow at scale → Load testing, optimization
- **Security breach**: Data compromised → Security audit, penetration testing

---

## Customer Support

### Support Channels

- **Email**: support@{{COMPANY}}.com
- **Chat**: In-app live chat (business hours)
- **Documentation**: docs.{{COMPANY}}.com
- **Community**: Forum/Discord/Slack

### Support SLA

| Tier              | Response Time | Resolution Time |
| ----------------- | ------------- | --------------- |
| **Critical (P0)** | < 1 hour      | < 4 hours       |
| **High (P1)**     | < 4 hours     | < 24 hours      |
| **Medium (P2)**   | < 24 hours    | < 3 days        |
| **Low (P3)**      | < 48 hours    | Best effort     |

---

## Product Analytics

### Analytics Tools

- **{{ANALYTICS_TOOL_1}}**: [Purpose, e.g., Google Analytics, Mixpanel]
- **{{ANALYTICS_TOOL_2}}**: [Purpose, e.g., Amplitude, Heap]

### Events to Track

| Event               | Description            | Purpose           |
| ------------------- | ---------------------- | ----------------- |
| `user_signup`       | New user registration  | Track acquisition |
| `feature_used`      | User uses core feature | Track engagement  |
| `payment_completed` | User completes payment | Track conversion  |
| `error_occurred`    | User encounters error  | Track reliability |

---

## Localization & Internationalization

### Supported Languages

- **Primary**: English (en-US)
- **Secondary**: [Languages, e.g., Japanese (ja-JP), Spanish (es-ES)]

### Localization Strategy

- **UI Strings**: i18n framework (next-intl, react-i18next)
- **Date/Time**: Locale-aware formatting
- **Currency**: Multi-currency support
- **Right-to-Left (RTL)**: Support for Arabic, Hebrew (if needed)

---

## Data & Privacy

### Data Collection

**What data we collect**:

- User account information (email, name)
- Usage analytics (anonymized)
- Error logs (for debugging)

**What data we DON'T collect**:

- [Sensitive data we avoid, e.g., passwords (only hashed), payment details (tokenized)]

### Privacy Policy

- **GDPR Compliance**: Right to access, delete, export data
- **Data Retention**: [Retention period, e.g., 90 days for logs]
- **Third-Party Sharing**: [Who we share data with, why]

---

## Integrations

### Integrations (実装済み)

| Integration | Purpose | Priority |
| ----------------- | --------- | -------- |
| Claude Desktop | MCP Server連携 | P0 ✅ |
| GitHub Copilot | VS Code連携 | P0 ✅ |
| Cursor | MCP Server連携 | P0 ✅ |

### Planned Integrations

| Integration | Purpose | Timeline |
| ----------------- | --------- | -------- |
| JetBrains IDEs | IntelliJ連携 | Q2 2026 |
| Neovim | LSP連携 | Q3 2026 |

---

## Changelog

### Version 0.3.0 (2025-12-31) - Context7 Superior Release

- 10 REQs実装完了（Phase 1-3）
- MCPツール: 19 → 32
- テスト数: 568 → 658
- フレームワーク知識グラフ: 27
- デザインパターン検出: 10パターン

### Version 0.2.0 (2025-12-30)

- フレームワーク知識グラフ機能追加
- 27フレームワーク対応

### Version 0.1.0 (2025-12-20)

- 初期リリース
- 21言語パーサー
- 基本MCPツール

---

**Last Updated**: 2025-12-31
**Maintained By**: YATA Development Team
