#!/usr/bin/env python3
"""
MAGATAMA Knowledge Database Updater

Updates cloned framework repositories and rebuilds knowledge graphs.

Usage:
    # Update all frameworks
    python scripts/update_knowledge_db.py

    # Update specific frameworks
    python scripts/update_knowledge_db.py --frameworks react vue django

    # Clone missing frameworks and update
    python scripts/update_knowledge_db.py --clone-missing

    # Skip git pull and only rebuild knowledge graphs
    python scripts/update_knowledge_db.py --no-update

    # Dry run (show what would be done)
    python scripts/update_knowledge_db.py --dry-run
"""

import argparse
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "packages" / "magatama-core" / "src"))

from magatama_core.application.usecases.parse_usecase import ParseFileUseCase
from magatama_core.infrastructure.parsers import (
    CParser,
    CppParser,
    CSharpParser,
    DartParser,
    ElixirParser,
    GoParser,
    JavaParser,
    JavaScriptParser,
    KotlinParser,
    PhpParser,
    PythonParser,
    RubyParser,
    RustParser,
    ScalaParser,
    SwiftParser,
    TypeScriptParser,
    ZigParser,
)
from magatama_core.infrastructure.storage import NetworkXKnowledgeGraph

# =============================================================================
# Framework Configuration
# =============================================================================


@dataclass
class FrameworkConfig:
    """Configuration for a framework repository."""

    name: str
    directory: str
    language: str
    patterns: list[str]
    repo_url: str
    branch: str | None = None
    exclude_patterns: list[str] = field(
        default_factory=lambda: [
            "**/__pycache__/**",
            "**/node_modules/**",
            "**/vendor/**",
            "**/dist/**",
            "**/build/**",
            "**/.git/**",
            "**/test/**",
            "**/tests/**",
            "**/spec/**",
            "**/examples/**",
            "**/docs/**",
            "**/fixtures/**",
            "**/mocks/**",
            "**/coverage/**",
        ]
    )


# Complete framework registry (47 frameworks)
FRAMEWORKS: list[FrameworkConfig] = [
    # === Frontend JavaScript/TypeScript ===
    FrameworkConfig(
        name="React",
        directory="react",
        language="ts",
        patterns=["packages/**/*.ts", "packages/**/*.tsx", "packages/**/*.js"],
        repo_url="https://github.com/facebook/react.git",
    ),
    FrameworkConfig(
        name="Angular",
        directory="angular",
        language="ts",
        patterns=["packages/**/*.ts"],
        repo_url="https://github.com/angular/angular.git",
    ),
    FrameworkConfig(
        name="Vue",
        directory="vue",
        language="ts",
        patterns=["packages/**/*.ts"],
        repo_url="https://github.com/vuejs/core.git",
    ),
    FrameworkConfig(
        name="Svelte",
        directory="svelte",
        language="ts",
        patterns=["packages/**/*.ts", "packages/**/*.js"],
        repo_url="https://github.com/sveltejs/svelte.git",
    ),
    FrameworkConfig(
        name="Next.js",
        directory="nextjs",
        language="ts",
        patterns=["packages/**/*.ts", "packages/**/*.tsx"],
        repo_url="https://github.com/vercel/next.js.git",
    ),
    FrameworkConfig(
        name="Nuxt",
        directory="nuxt",
        language="ts",
        patterns=["packages/**/*.ts"],
        repo_url="https://github.com/nuxt/nuxt.git",
    ),
    FrameworkConfig(
        name="Ember",
        directory="ember",
        language="ts",
        patterns=["packages/**/*.ts", "packages/**/*.js"],
        repo_url="https://github.com/emberjs/ember.js.git",
    ),
    FrameworkConfig(
        name="Backbone",
        directory="backbone",
        language="js",
        patterns=["**/*.js"],
        repo_url="https://github.com/jashkenas/backbone.git",
    ),
    FrameworkConfig(
        name="Alpine.js",
        directory="alpine",
        language="ts",
        patterns=["packages/**/*.ts", "packages/**/*.js"],
        repo_url="https://github.com/alpinejs/alpine.git",
    ),
    FrameworkConfig(
        name="Astro",
        directory="astro",
        language="ts",
        patterns=["packages/**/*.ts", "packages/**/*.tsx"],
        repo_url="https://github.com/withastro/astro.git",
    ),
    FrameworkConfig(
        name="SolidJS",
        directory="solidjs",
        language="ts",
        patterns=["packages/**/*.ts", "packages/**/*.tsx"],
        repo_url="https://github.com/solidjs/solid.git",
    ),
    FrameworkConfig(
        name="Remix",
        directory="remix",
        language="ts",
        patterns=["packages/**/*.ts", "packages/**/*.tsx"],
        repo_url="https://github.com/remix-run/remix.git",
    ),
    FrameworkConfig(
        name="htmx",
        directory="htmx",
        language="js",
        patterns=["src/**/*.js"],
        repo_url="https://github.com/bigskysoftware/htmx.git",
    ),
    FrameworkConfig(
        name="Qwik",
        directory="qwik",
        language="ts",
        patterns=["packages/**/*.ts", "packages/**/*.tsx"],
        repo_url="https://github.com/QwikDev/qwik.git",
    ),
    # === Backend JavaScript/TypeScript ===
    FrameworkConfig(
        name="Express",
        directory="express",
        language="js",
        patterns=["lib/**/*.js"],
        repo_url="https://github.com/expressjs/express.git",
    ),
    FrameworkConfig(
        name="NestJS",
        directory="nestjs",
        language="ts",
        patterns=["packages/**/*.ts"],
        repo_url="https://github.com/nestjs/nest.git",
    ),
    FrameworkConfig(
        name="Koa",
        directory="koa",
        language="js",
        patterns=["lib/**/*.js"],
        repo_url="https://github.com/koajs/koa.git",
    ),
    FrameworkConfig(
        name="Fastify",
        directory="fastify",
        language="js",
        patterns=["lib/**/*.js", "types/**/*.ts"],
        repo_url="https://github.com/fastify/fastify.git",
    ),
    FrameworkConfig(
        name="Hono",
        directory="hono",
        language="ts",
        patterns=["src/**/*.ts"],
        repo_url="https://github.com/honojs/hono.git",
    ),
    FrameworkConfig(
        name="tRPC",
        directory="trpc",
        language="ts",
        patterns=["packages/**/*.ts"],
        repo_url="https://github.com/trpc/trpc.git",
    ),
    FrameworkConfig(
        name="Bun",
        directory="bun",
        language="ts",
        patterns=["src/**/*.ts", "packages/**/*.ts"],
        repo_url="https://github.com/oven-sh/bun.git",
    ),
    # === Python ===
    FrameworkConfig(
        name="Django",
        directory="django",
        language="py",
        patterns=["django/**/*.py"],
        repo_url="https://github.com/django/django.git",
    ),
    FrameworkConfig(
        name="Flask",
        directory="flask",
        language="py",
        patterns=["src/**/*.py"],
        repo_url="https://github.com/pallets/flask.git",
    ),
    FrameworkConfig(
        name="FastAPI",
        directory="fastapi",
        language="py",
        patterns=["fastapi/**/*.py"],
        repo_url="https://github.com/tiangolo/fastapi.git",
    ),
    FrameworkConfig(
        name="LangChain",
        directory="langchain",
        language="py",
        patterns=["libs/**/*.py"],
        repo_url="https://github.com/langchain-ai/langchain.git",
    ),
    FrameworkConfig(
        name="Haystack",
        directory="haystack",
        language="py",
        patterns=["haystack/**/*.py"],
        repo_url="https://github.com/deepset-ai/haystack.git",
    ),
    FrameworkConfig(
        name="Streamlit",
        directory="streamlit",
        language="py",
        patterns=["lib/**/*.py"],
        repo_url="https://github.com/streamlit/streamlit.git",
    ),
    FrameworkConfig(
        name="LangGraph",
        directory="langgraph",
        language="py",
        patterns=["libs/**/*.py"],
        repo_url="https://github.com/langchain-ai/langgraph.git",
    ),
    # === Ruby ===
    FrameworkConfig(
        name="Rails",
        directory="rails",
        language="rb",
        patterns=["**/*.rb"],
        repo_url="https://github.com/rails/rails.git",
    ),
    # === PHP ===
    FrameworkConfig(
        name="Laravel",
        directory="laravel",
        language="php",
        patterns=["src/**/*.php"],
        repo_url="https://github.com/laravel/framework.git",
    ),
    FrameworkConfig(
        name="Symfony",
        directory="symfony",
        language="php",
        patterns=["src/**/*.php"],
        repo_url="https://github.com/symfony/symfony.git",
    ),
    FrameworkConfig(
        name="CodeIgniter",
        directory="codeigniter",
        language="php",
        patterns=["system/**/*.php"],
        repo_url="https://github.com/codeigniter4/CodeIgniter4.git",
    ),
    # === Java ===
    FrameworkConfig(
        name="Spring Boot",
        directory="spring-boot",
        language="java",
        patterns=["**/*.java"],
        repo_url="https://github.com/spring-projects/spring-boot.git",
    ),
    # === Go ===
    FrameworkConfig(
        name="Gin",
        directory="gin",
        language="go",
        patterns=["**/*.go"],
        repo_url="https://github.com/gin-gonic/gin.git",
    ),
    FrameworkConfig(
        name="Echo",
        directory="echo",
        language="go",
        patterns=["**/*.go"],
        repo_url="https://github.com/labstack/echo.git",
    ),
    FrameworkConfig(
        name="Fiber",
        directory="fiber",
        language="go",
        patterns=["**/*.go"],
        repo_url="https://github.com/gofiber/fiber.git",
    ),
    # === Rust ===
    FrameworkConfig(
        name="Actix-web",
        directory="actix-web",
        language="rs",
        patterns=["**/*.rs"],
        repo_url="https://github.com/actix/actix-web.git",
    ),
    FrameworkConfig(
        name="Axum",
        directory="axum",
        language="rs",
        patterns=["**/*.rs"],
        repo_url="https://github.com/tokio-rs/axum.git",
    ),
    FrameworkConfig(
        name="Tauri",
        directory="tauri",
        language="rs",
        patterns=["**/*.rs"],
        repo_url="https://github.com/tauri-apps/tauri.git",
    ),
    # === Elixir ===
    FrameworkConfig(
        name="Phoenix",
        directory="phoenix",
        language="ex",
        patterns=["lib/**/*.ex"],
        repo_url="https://github.com/phoenixframework/phoenix.git",
    ),
    # === Database/ORM ===
    FrameworkConfig(
        name="Prisma",
        directory="prisma",
        language="ts",
        patterns=["packages/**/*.ts"],
        repo_url="https://github.com/prisma/prisma.git",
    ),
    FrameworkConfig(
        name="Drizzle",
        directory="drizzle",
        language="ts",
        patterns=["drizzle-orm/**/*.ts"],
        repo_url="https://github.com/drizzle-team/drizzle-orm.git",
    ),
    # === Mobile ===
    FrameworkConfig(
        name="React Native",
        directory="react-native",
        language="ts",
        patterns=["packages/**/*.ts", "packages/**/*.tsx", "packages/**/*.js"],
        repo_url="https://github.com/facebook/react-native.git",
    ),
    FrameworkConfig(
        name="Flutter",
        directory="flutter",
        language="dart",
        patterns=["packages/**/*.dart"],
        repo_url="https://github.com/flutter/flutter.git",
    ),
    FrameworkConfig(
        name="Expo",
        directory="expo",
        language="ts",
        patterns=["packages/**/*.ts", "packages/**/*.tsx"],
        repo_url="https://github.com/expo/expo.git",
    ),
    FrameworkConfig(
        name="SwiftUI",
        directory="swiftui-source",
        language="swift",
        patterns=["**/*.swift"],
        repo_url="https://github.com/nicklockwood/SwiftFormat.git",  # SwiftUI is closed source, using SwiftFormat as example
    ),
    FrameworkConfig(
        name="Jetpack Compose",
        directory="jetpack-compose",
        language="kt",
        patterns=["compose/**/*.kt"],
        repo_url="https://github.com/androidx/androidx.git",
    ),
]


# =============================================================================
# Parser Registry
# =============================================================================


def get_parsers() -> dict:
    """Initialize all available language parsers."""
    return {
        ".py": PythonParser(),
        ".ts": TypeScriptParser(),
        ".tsx": TypeScriptParser(),
        ".js": JavaScriptParser(),
        ".jsx": JavaScriptParser(),
        ".rs": RustParser(),
        ".go": GoParser(),
        ".rb": RubyParser(),
        ".java": JavaParser(),
        ".cs": CSharpParser(),
        ".php": PhpParser(),
        ".swift": SwiftParser(),
        ".kt": KotlinParser(),
        ".kts": KotlinParser(),
        ".dart": DartParser(),
        ".ex": ElixirParser(),
        ".exs": ElixirParser(),
        ".scala": ScalaParser(),
        ".c": CParser(),
        ".h": CParser(),
        ".cpp": CppParser(),
        ".hpp": CppParser(),
        ".zig": ZigParser(),
    }


# =============================================================================
# Git Operations
# =============================================================================


def git_pull(repo_path: Path, dry_run: bool = False) -> tuple[bool, str]:
    """
    Update a git repository with git pull.

    Returns:
        (success, message)
    """
    if not (repo_path / ".git").exists():
        return False, "Not a git repository"

    if dry_run:
        return True, "[DRY RUN] Would run: git pull"

    try:
        result = subprocess.run(
            ["git", "pull", "--ff-only"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=120,
        )

        if result.returncode == 0:
            if "Already up to date" in result.stdout:
                return True, "Already up to date"
            return True, f"Updated: {result.stdout.strip()}"
        else:
            return False, f"Failed: {result.stderr.strip()}"
    except subprocess.TimeoutExpired:
        return False, "Timeout (>120s)"
    except Exception as e:
        return False, str(e)


def git_clone(
    repo_url: str, target_path: Path, branch: str | None = None, dry_run: bool = False
) -> tuple[bool, str]:
    """
    Clone a git repository.

    Returns:
        (success, message)
    """
    if target_path.exists():
        return False, "Directory already exists"

    if dry_run:
        return True, f"[DRY RUN] Would clone: {repo_url}"

    try:
        cmd = ["git", "clone", "--depth", "1"]
        if branch:
            cmd.extend(["--branch", branch])
        cmd.extend([repo_url, str(target_path)])

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,
        )

        if result.returncode == 0:
            return True, "Cloned successfully"
        else:
            return False, f"Clone failed: {result.stderr.strip()}"
    except subprocess.TimeoutExpired:
        return False, "Timeout (>300s)"
    except Exception as e:
        return False, str(e)


# =============================================================================
# Knowledge Graph Building
# =============================================================================


def analyze_framework(fw: FrameworkConfig, base_path: Path, dry_run: bool = False) -> dict:
    """
    Analyze a framework and build its knowledge graph.

    Returns:
        Dictionary with analysis results
    """
    fw_path = base_path / fw.directory

    if not fw_path.exists():
        return {"name": fw.name, "directory": fw.directory, "error": "Directory not found"}

    if dry_run:
        return {
            "name": fw.name,
            "directory": fw.directory,
            "dry_run": True,
            "message": "[DRY RUN] Would analyze framework",
        }

    # Create fresh parsers for each framework
    parsers = get_parsers()

    # Create knowledge graph
    graph = NetworkXKnowledgeGraph()
    parse_file_usecase = ParseFileUseCase(parsers=parsers, knowledge_graph=graph)

    files_processed = 0
    errors = []

    try:
        # Find all matching files
        all_files = []
        for pattern in fw.patterns:
            all_files.extend(fw_path.glob(pattern))

        # Filter out excluded patterns
        filtered_files = []
        exclude_keywords = [
            "__pycache__",
            "node_modules",
            "test",
            "tests",
            "spec",
            ".git",
            "fixtures",
            "mocks",
        ]

        for f in all_files:
            excluded = False
            for keyword in exclude_keywords:
                if keyword in str(f):
                    excluded = True
                    break
            if not excluded and f.is_file():
                filtered_files.append(f)

        # Parse files
        for file_path in filtered_files:
            try:
                parse_file_usecase.execute(file_path)
                files_processed += 1
            except Exception as e:
                if "already exists" not in str(e):
                    errors.append(f"{file_path.name}: {str(e)[:50]}")

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

        # Save knowledge graph
        output_dir = base_path.parent / "knowledge_graphs"
        output_dir.mkdir(exist_ok=True)
        graph_file = output_dir / f"{fw.directory}.json"
        graph.save(graph_file)

        return {
            "name": fw.name,
            "directory": fw.directory,
            "language": fw.language,
            "files_processed": files_processed,
            "entities": len(all_entities),
            "relationships": len(all_rels),
            "entity_types": type_counts,
            "relationship_types": rel_counts,
            "graph_file": str(graph_file),
            "errors": errors[:5] if errors else [],  # Limit errors
        }
    except Exception as e:
        return {"name": fw.name, "directory": fw.directory, "error": str(e)}


# =============================================================================
# Main Functions
# =============================================================================


def update_repositories(
    frameworks: list[FrameworkConfig],
    base_path: Path,
    clone_missing: bool = False,
    dry_run: bool = False,
    parallel: int = 4,
) -> list[dict]:
    """
    Update all framework repositories.

    Returns:
        List of update results
    """
    results = []

    def process_framework(fw: FrameworkConfig) -> dict:
        fw_path = base_path / fw.directory

        if fw_path.exists():
            success, message = git_pull(fw_path, dry_run=dry_run)
            return {
                "name": fw.name,
                "directory": fw.directory,
                "action": "pull",
                "success": success,
                "message": message,
            }
        elif clone_missing:
            success, message = git_clone(fw.repo_url, fw_path, fw.branch, dry_run=dry_run)
            return {
                "name": fw.name,
                "directory": fw.directory,
                "action": "clone",
                "success": success,
                "message": message,
            }
        else:
            return {
                "name": fw.name,
                "directory": fw.directory,
                "action": "skip",
                "success": False,
                "message": "Directory not found (use --clone-missing to clone)",
            }

    # Process in parallel
    with ThreadPoolExecutor(max_workers=parallel) as executor:
        futures = {executor.submit(process_framework, fw): fw for fw in frameworks}

        for future in as_completed(futures):
            result = future.result()
            results.append(result)

            # Print progress
            status = "✅" if result["success"] else "❌"
            print(f"  {status} {result['name']}: {result['message']}")

    return results


def rebuild_knowledge_graphs(
    frameworks: list[FrameworkConfig],
    base_path: Path,
    dry_run: bool = False,
) -> list[dict]:
    """
    Rebuild knowledge graphs for all frameworks.

    Returns:
        List of analysis results
    """
    results = []

    for i, fw in enumerate(frameworks, 1):
        print(f"  [{i:2d}/{len(frameworks)}] {fw.name}...", end=" ", flush=True)

        result = analyze_framework(fw, base_path, dry_run=dry_run)
        results.append(result)

        if "error" in result:
            print(f"❌ {result['error']}")
        elif result.get("dry_run"):
            print("[DRY RUN]")
        else:
            print(f"✅ {result['entities']:,} entities, {result['relationships']:,} relationships")

    return results


def save_summary(results: dict, output_path: Path):
    """Save analysis summary to JSON file."""
    summary = {
        "timestamp": datetime.now().isoformat(),
        "version": "0.4.0",
        **results,
    }

    output_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False))
    print(f"\n📄 Summary saved to: {output_path}")


def print_summary(update_results: list[dict], analysis_results: list[dict]):
    """Print a summary of the update and analysis."""
    print()
    print("=" * 80)
    print("📊 Summary")
    print("=" * 80)

    # Update summary
    if update_results:
        updated = len([r for r in update_results if r["success"] and r["action"] == "pull"])
        cloned = len([r for r in update_results if r["success"] and r["action"] == "clone"])
        failed = len([r for r in update_results if not r["success"]])

        print(f"Git operations: {updated} updated, {cloned} cloned, {failed} failed")

    # Analysis summary
    if analysis_results:
        successful = [r for r in analysis_results if "error" not in r and not r.get("dry_run")]
        total_entities = sum(r.get("entities", 0) for r in successful)
        total_relationships = sum(r.get("relationships", 0) for r in successful)

        print(f"Frameworks analyzed: {len(successful)}")
        print(f"Total entities: {total_entities:,}")
        print(f"Total relationships: {total_relationships:,}")

    print()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Update MAGATAMA knowledge database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--frameworks",
        "-f",
        nargs="+",
        help="Specific frameworks to update (by directory name)",
    )
    parser.add_argument(
        "--clone-missing",
        action="store_true",
        help="Clone missing framework repositories",
    )
    parser.add_argument(
        "--no-update",
        action="store_true",
        help="Skip git pull and only rebuild knowledge graphs",
    )
    parser.add_argument(
        "--no-analyze",
        action="store_true",
        help="Only update repositories, skip knowledge graph analysis",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes",
    )
    parser.add_argument(
        "--parallel",
        "-p",
        type=int,
        default=4,
        help="Number of parallel git operations (default: 4)",
    )
    parser.add_argument(
        "--base-path",
        type=Path,
        default=Path("/home/nahisaho/GitHub/MAGATAMA/frameworks"),
        help="Base path for framework repositories",
    )

    args = parser.parse_args()

    # Filter frameworks if specified
    if args.frameworks:
        frameworks = [fw for fw in FRAMEWORKS if fw.directory in args.frameworks]
        if not frameworks:
            print(f"❌ No matching frameworks found for: {args.frameworks}")
            print(f"Available: {[fw.directory for fw in FRAMEWORKS]}")
            sys.exit(1)
    else:
        frameworks = FRAMEWORKS

    print("=" * 80)
    print("🔄 MAGATAMA Knowledge Database Updater")
    print("=" * 80)
    print(f"Frameworks: {len(frameworks)}")
    print(f"Base path: {args.base_path}")
    if args.dry_run:
        print("Mode: DRY RUN")
    print()

    update_results = []
    analysis_results = []

    # Step 1: Update repositories
    if not args.no_update:
        print("📥 Updating repositories...")
        update_results = update_repositories(
            frameworks,
            args.base_path,
            clone_missing=args.clone_missing,
            dry_run=args.dry_run,
            parallel=args.parallel,
        )
        print()

    # Step 2: Rebuild knowledge graphs
    if not args.no_analyze:
        print("🧠 Rebuilding knowledge graphs...")
        analysis_results = rebuild_knowledge_graphs(
            frameworks,
            args.base_path,
            dry_run=args.dry_run,
        )

    # Print summary
    print_summary(update_results, analysis_results)

    # Save summary
    if not args.dry_run and analysis_results:
        output_dir = args.base_path.parent / "knowledge_graphs"
        output_dir.mkdir(exist_ok=True)

        save_summary(
            {
                "frameworks_count": len(frameworks),
                "update_results": update_results,
                "analysis_results": analysis_results,
            },
            output_dir / "update_summary.json",
        )


if __name__ == "__main__":
    main()
