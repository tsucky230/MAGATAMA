"""Use cases package."""

from magatama_core.application.usecases.comp_usecase import (
    LoadCompIndexResult,
    LoadCompIndexUseCase,
)
from magatama_core.application.usecases.framework_usecase import (
    # REQ-009: API Compatibility
    APICompatibilityUseCase,
    CodeContextUseCase,
    # REQ-006: Code Evolution
    CodeEvolutionUseCase,
    # REQ-010: Code Navigation
    CodeNavigationUseCase,
    CodePatternResult,
    # REQ-005: Code Quality
    CodeQualityUseCase,
    # REQ-002: Code Recommendation
    CodeRecommendationUseCase,
    CodeSnippetResult,
    CodingGuidanceResult,
    # REQ-007: Coding Guidance
    CodingGuidanceUseCase,
    CompatibilityIssue,
    CompatibilityResult,
    # REQ-003: Impact Analysis
    DependencyImpactUseCase,
    # REQ-001: Documentation Generation
    DocumentationGenerationUseCase,
    DocumentationResult,
    EvolutionEvent,
    EvolutionResult,
    FrameworkInfo,
    FrameworkKnowledgeUseCase,
    FrameworkPatternResults,
    FrameworkSearchResult,
    FrameworkSearchResults,
    FrameworkSemanticSearchUseCase,
    HybridSearchResult,
    # REQ-004: Hybrid Search
    HybridSearchUseCase,
    ImpactAnalysisResult,
    NavigationNode,
    NavigationResult,
    PatternDetectionResult,
    # REQ-008: Pattern Detection
    PatternDetectionUseCase,
    PatternMatch,
    QualityAnalysisResult,
    QualityMetric,
    SemanticSearchUseCase,
)
from magatama_core.application.usecases.parse_usecase import (
    IncrementalParseResult,
    IncrementalParseUseCase,
    ParseDirectoryUseCase,
    ParseFileUseCase,
    ParseResult,
)

__all__ = [
    "LoadCompIndexUseCase",
    "LoadCompIndexResult",
    "ParseFileUseCase",
    "ParseDirectoryUseCase",
    "ParseResult",
    "IncrementalParseUseCase",
    "IncrementalParseResult",
    "FrameworkKnowledgeUseCase",
    "FrameworkInfo",
    "FrameworkSearchResult",
    "CodePatternResult",
    "CodeContextUseCase",
    "SemanticSearchUseCase",
    "FrameworkSemanticSearchUseCase",
    "FrameworkSearchResults",
    "FrameworkPatternResults",
    # REQ-001
    "DocumentationGenerationUseCase",
    "DocumentationResult",
    # REQ-002
    "CodeRecommendationUseCase",
    "CodeSnippetResult",
    # REQ-003
    "DependencyImpactUseCase",
    "ImpactAnalysisResult",
    # REQ-004
    "HybridSearchUseCase",
    "HybridSearchResult",
    # REQ-005
    "CodeQualityUseCase",
    "QualityAnalysisResult",
    "QualityMetric",
    # REQ-006
    "CodeEvolutionUseCase",
    "EvolutionResult",
    "EvolutionEvent",
    # REQ-007
    "CodingGuidanceUseCase",
    "CodingGuidanceResult",
    # REQ-008
    "PatternDetectionUseCase",
    "PatternDetectionResult",
    "PatternMatch",
    # REQ-009
    "APICompatibilityUseCase",
    "CompatibilityResult",
    "CompatibilityIssue",
    # REQ-010
    "CodeNavigationUseCase",
    "NavigationResult",
    "NavigationNode",
]
