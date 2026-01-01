#!/usr/bin/env python3
"""
Framework Knowledge Graph Analyzer

Analyzes 25 major web frameworks and creates knowledge graphs.
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "packages" / "yata-core" / "src"))

from yata_core.infrastructure.parsers import (
    PythonParser,
    TypeScriptParser,
    JavaScriptParser,
    RustParser,
    GoParser,
    RubyParser,
    JavaParser,
    CSharpParser,
    PhpParser,
    SwiftParser,
    KotlinParser,
    DartParser,
    ElixirParser,
)
from yata_core.infrastructure.storage import NetworkXKnowledgeGraph
from yata_core.application.usecases.parse_usecase import ParseDirectoryUseCase, ParseFileUseCase


@dataclass
class FrameworkConfig:
    """Configuration for a framework."""
    name: str
    path: str
    language: str
    patterns: list[str]
    exclude_patterns: list[str] = field(default_factory=lambda: [
        "**/__pycache__/**", "**/node_modules/**", "**/vendor/**",
        "**/dist/**", "**/build/**", "**/.git/**", "**/test/**",
        "**/tests/**", "**/spec/**", "**/examples/**", "**/docs/**"
    ])


# Framework configurations
FRAMEWORKS = [
    # Frontend JavaScript/TypeScript
    FrameworkConfig("React", "react", "ts", ["packages/**/*.ts", "packages/**/*.tsx", "packages/**/*.js"]),
    FrameworkConfig("Angular", "angular", "ts", ["packages/**/*.ts"]),
    FrameworkConfig("Vue", "vue", "ts", ["packages/**/*.ts"]),
    FrameworkConfig("Svelte", "svelte", "ts", ["packages/**/*.ts", "packages/**/*.js"]),
    FrameworkConfig("Next.js", "nextjs", "ts", ["packages/**/*.ts", "packages/**/*.tsx"]),
    FrameworkConfig("Nuxt", "nuxt", "ts", ["packages/**/*.ts"]),
    FrameworkConfig("Ember", "ember", "ts", ["packages/**/*.ts", "packages/**/*.js"]),
    FrameworkConfig("Backbone", "backbone", "js", ["**/*.js"]),
    FrameworkConfig("Alpine.js", "alpine", "ts", ["packages/**/*.ts", "packages/**/*.js"]),
    FrameworkConfig("SolidJS", "solidjs", "ts", ["packages/**/*.ts", "packages/**/*.tsx"]),
    FrameworkConfig("Qwik", "qwik", "ts", ["packages/**/*.ts", "packages/**/*.tsx"]),
    FrameworkConfig("Remix", "remix", "ts", ["packages/**/*.ts", "packages/**/*.tsx"]),
    FrameworkConfig("Astro", "astro", "ts", ["packages/**/*.ts"]),
    FrameworkConfig("HTMX", "htmx", "js", ["src/**/*.js", "**/*.js"]),
    
    # Backend JavaScript/TypeScript
    FrameworkConfig("Express", "express", "js", ["lib/**/*.js"]),
    FrameworkConfig("NestJS", "nestjs", "ts", ["packages/**/*.ts"]),
    FrameworkConfig("Koa", "koa", "js", ["lib/**/*.js"]),
    FrameworkConfig("Fastify", "fastify", "js", ["lib/**/*.js", "types/**/*.ts"]),
    FrameworkConfig("Hono", "hono", "ts", ["src/**/*.ts", "packages/**/*.ts"]),
    FrameworkConfig("tRPC", "trpc", "ts", ["packages/**/*.ts"]),
    FrameworkConfig("Bun", "bun", "ts", ["src/**/*.ts", "packages/**/*.ts"]),
    
    # Python
    FrameworkConfig("Django", "django", "py", ["django/**/*.py"]),
    FrameworkConfig("Flask", "flask", "py", ["src/**/*.py"]),
    FrameworkConfig("FastAPI", "fastapi", "py", ["fastapi/**/*.py"]),
    FrameworkConfig("Streamlit", "streamlit", "py", ["lib/**/*.py", "streamlit/**/*.py"]),
    FrameworkConfig("Haystack", "haystack", "py", ["haystack/**/*.py"]),
    FrameworkConfig("LangChain", "langchain", "py", ["libs/**/*.py"]),
    FrameworkConfig("LangGraph", "langgraph", "py", ["libs/**/*.py"]),
    
    # Ruby
    FrameworkConfig("Rails", "rails", "rb", ["**/*.rb"]),
    
    # PHP
    FrameworkConfig("Laravel", "laravel", "php", ["src/**/*.php"]),
    FrameworkConfig("Symfony", "symfony", "php", ["src/**/*.php"]),
    FrameworkConfig("CodeIgniter", "codeigniter", "php", ["system/**/*.php"]),
    
    # Java/Kotlin
    FrameworkConfig("Spring Boot", "spring-boot", "java", ["**/*.java"]),
    FrameworkConfig("Jetpack Compose", "jetpack-compose", "kt", ["**/*.kt"]),
    
    # Go
    FrameworkConfig("Gin", "gin", "go", ["**/*.go"]),
    FrameworkConfig("Echo", "echo", "go", ["**/*.go"]),
    FrameworkConfig("Fiber", "fiber", "go", ["**/*.go"]),
    
    # Rust
    FrameworkConfig("Actix-Web", "actix-web", "rs", ["**/*.rs"]),
    FrameworkConfig("Axum", "axum", "rs", ["**/*.rs"]),
    
    # Mobile
    FrameworkConfig("React Native", "react-native", "ts", ["packages/**/*.ts", "packages/**/*.tsx", "packages/**/*.js"]),
    FrameworkConfig("Flutter", "flutter", "dart", ["packages/**/*.dart"]),
    FrameworkConfig("Expo", "expo", "ts", ["packages/**/*.ts", "packages/**/*.tsx"]),
    FrameworkConfig("SwiftUI", "swiftui-source", "swift", ["**/*.swift"]),
    
    # Desktop
    FrameworkConfig("Tauri", "tauri", "rs", ["**/*.rs"]),
    
    # Database/ORM
    FrameworkConfig("Prisma", "prisma", "ts", ["packages/**/*.ts"]),
    FrameworkConfig("Drizzle", "drizzle", "ts", ["**/*.ts"]),
    
    # Elixir
    FrameworkConfig("Phoenix", "phoenix", "ex", ["lib/**/*.ex", "**/*.ex"]),
]


def get_parsers():
    """Initialize all available parsers."""
    return {
        '.py': PythonParser(),
        '.ts': TypeScriptParser(),
        '.tsx': TypeScriptParser(),
        '.js': JavaScriptParser(),
        '.jsx': JavaScriptParser(),
        '.rs': RustParser(),
        '.go': GoParser(),
        '.rb': RubyParser(),
        '.java': JavaParser(),
        '.cs': CSharpParser(),
        '.php': PhpParser(),
        '.swift': SwiftParser(),
        '.kt': KotlinParser(),
        '.dart': DartParser(),
        '.ex': ElixirParser(),
        '.exs': ElixirParser(),
    }


def analyze_framework(fw: FrameworkConfig, base_path: Path, parsers: dict) -> dict:
    """Analyze a single framework and return results."""
    fw_path = base_path / fw.path
    
    if not fw_path.exists():
        return {"name": fw.name, "error": "Directory not found"}
    
    # Create fresh parsers for each framework to avoid counter conflicts
    fresh_parsers = get_parsers()
    
    # Create knowledge graph with duplicate-tolerant repository
    graph = NetworkXKnowledgeGraph()
    parse_file_usecase = ParseFileUseCase(parsers=fresh_parsers, knowledge_graph=graph)
    
    # Manually process files to skip duplicates
    total_entities = 0
    total_relationships = 0
    files_processed = 0
    errors = []
    
    try:
        # Find all matching files
        all_files = []
        for pattern in fw.patterns:
            all_files.extend(fw_path.glob(pattern))
        
        # Filter out excluded patterns
        filtered_files = []
        for f in all_files:
            excluded = False
            for exclude in fw.exclude_patterns:
                if f.match(exclude) or any(p in str(f) for p in ['__pycache__', 'node_modules', 'test', 'spec', '.git']):
                    excluded = True
                    break
            if not excluded and f.is_file():
                filtered_files.append(f)
        
        for file_path in filtered_files:
            try:
                result = parse_file_usecase.execute(file_path)
                total_entities += result.entities_count
                total_relationships += result.relationships_count
                files_processed += 1
            except Exception as e:
                # Skip duplicate entity errors and continue
                if "already exists" not in str(e):
                    errors.append(f"{file_path}: {str(e)}")
        
        # Get statistics
        all_entities = graph.entities.all()
        all_rels = graph.relationships.all()
        
        type_counts = {}
        for e in all_entities:
            t = e.type.value
            type_counts[t] = type_counts.get(t, 0) + 1
        
        rel_counts = {}
        for r in all_rels:
            t = r.type.value
            rel_counts[t] = rel_counts.get(t, 0) + 1
        
        # Save individual graph
        output_dir = base_path.parent / "knowledge_graphs"
        output_dir.mkdir(exist_ok=True)
        graph_file = output_dir / f"{fw.path}.json"
        graph.save(graph_file)
        
        return {
            "name": fw.name,
            "language": fw.language,
            "files_processed": files_processed,
            "entities": len(all_entities),
            "relationships": len(all_rels),
            "entity_types": type_counts,
            "relationship_types": rel_counts,
            "graph_file": str(graph_file),
        }
    except Exception as e:
        return {"name": fw.name, "error": str(e)}


def main():
    """Main entry point."""
    base_path = Path("/home/nahisaho/GitHub/YATA/frameworks")
    parsers = get_parsers()
    
    print("=" * 80)
    print("🎯 Framework Knowledge Graph Analyzer")
    print("=" * 80)
    print(f"Analyzing {len(FRAMEWORKS)} frameworks...")
    print()
    
    results = []
    total_entities = 0
    total_relationships = 0
    
    for i, fw in enumerate(FRAMEWORKS, 1):
        print(f"[{i:2d}/{len(FRAMEWORKS)}] Analyzing {fw.name}...", end=" ", flush=True)
        result = analyze_framework(fw, base_path, parsers)
        results.append(result)
        
        if "error" in result:
            print(f"❌ {result['error']}")
        else:
            print(f"✅ {result['entities']} entities, {result['relationships']} relationships")
            total_entities += result.get("entities", 0)
            total_relationships += result.get("relationships", 0)
    
    print()
    print("=" * 80)
    print("📊 Summary")
    print("=" * 80)
    print(f"Total frameworks analyzed: {len([r for r in results if 'error' not in r])}")
    print(f"Total entities: {total_entities:,}")
    print(f"Total relationships: {total_relationships:,}")
    print()
    
    # Save summary
    output_dir = base_path.parent / "knowledge_graphs"
    output_dir.mkdir(exist_ok=True)
    summary_file = output_dir / "summary.json"
    
    summary = {
        "timestamp": datetime.now().isoformat(),
        "total_frameworks": len(FRAMEWORKS),
        "successful": len([r for r in results if "error" not in r]),
        "total_entities": total_entities,
        "total_relationships": total_relationships,
        "frameworks": results,
    }
    
    summary_file.write_text(json.dumps(summary, indent=2, ensure_ascii=False))
    print(f"Summary saved to: {summary_file}")
    
    # Print detailed results table
    print()
    print("=" * 80)
    print("📋 Detailed Results")
    print("=" * 80)
    print(f"{'Framework':<20} {'Language':<8} {'Files':<8} {'Entities':<10} {'Relations':<10}")
    print("-" * 80)
    
    for r in sorted(results, key=lambda x: x.get("entities", 0), reverse=True):
        if "error" not in r:
            print(f"{r['name']:<20} {r['language']:<8} {r['files_processed']:<8} {r['entities']:<10} {r['relationships']:<10}")
        else:
            print(f"{r['name']:<20} ERROR: {r['error']}")


if __name__ == "__main__":
    main()
