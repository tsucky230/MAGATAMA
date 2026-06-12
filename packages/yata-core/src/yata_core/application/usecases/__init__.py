"""Use cases package."""

from yata_core.application.usecases.comp_usecase import (
    LoadCompIndexUseCase,
    LoadCompIndexResult,
)
from yata_core.application.usecases.parse_usecase import (
    ParseFileUseCase,
    ParseDirectoryUseCase,
    ParseResult,
    IncrementalParseUseCase,
    IncrementalParseResult,
)
from yata_core.application.usecases.framework_usecase import (
    FrameworkKnowledgeUseCase,
    FrameworkInfo,
    FrameworkSearchResult,
    CodePatternResult,
    CodeContextUseCase,
    SemanticSearchUseCase,
    FrameworkSemanticSearchUseCase,
    FrameworkSearchResults,
    FrameworkPatternResults,
    # REQ-001: Documentation Generation
    DocumentationGenerationUseCase,
    DocumentationResult,
    # REQ-002: Code Recommendation
    CodeRecommendationUseCase,
    CodeSnippetResult,
    # REQ-003: Impact Analysis
    DependencyImpactUseCase,
    ImpactAnalysisResult,
    # REQ-004: Hybrid Search
    HybridSearchUseCase,
    HybridSearchResult,
    # REQ-005: Code Quality
    CodeQualityUseCase,
    QualityAnalysisResult,
    QualityMetric,
    # REQ-006: Code Evolution
    CodeEvolutionUseCase,
    EvolutionResult,
    EvolutionEvent,
    # REQ-007: Coding Guidance
    CodingGuidanceUseCase,
    CodingGuidanceResult,
    # REQ-008: Pattern Detection
    PatternDetectionUseCase,
    PatternDetectionResult,
    PatternMatch,
    # REQ-009: API Compatibility
    APICompatibilityUseCase,
    CompatibilityResult,
    CompatibilityIssue,
    # REQ-010: Code Navigation
    CodeNavigationUseCase,
    NavigationResult,
    NavigationNode,
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
