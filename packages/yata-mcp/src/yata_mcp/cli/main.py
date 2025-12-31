"""YATA CLI - Command Line Interface.

This module provides the main CLI for the YATA MCP server.
"""

import click
from pathlib import Path
from rich.console import Console
from rich.table import Table

from yata_mcp import __version__
from yata_mcp.server import YataMcpServer


console = Console()


@click.group()
@click.version_option(version=__version__, prog_name="YATA")
@click.pass_context
def cli(ctx: click.Context) -> None:
    """YATA - AI Coding Support via Model Context Protocol.
    
    YATA (八咫) provides knowledge graph context to AI coding assistants
    via the Model Context Protocol (MCP).
    """
    ctx.ensure_object(dict)
    ctx.obj["server"] = YataMcpServer()


@cli.command()
@click.argument("path", type=click.Path(exists=True))
@click.option(
    "--pattern", "-p",
    multiple=True,
    default=["**/*.py"],
    help="Glob pattern for files to include",
)
@click.option(
    "--exclude", "-e",
    multiple=True,
    default=[],
    help="Glob pattern for files to exclude",
)
@click.pass_context
def parse(
    ctx: click.Context,
    path: str,
    pattern: tuple[str, ...],
    exclude: tuple[str, ...],
) -> None:
    """Parse source files and build knowledge graph.
    
    PATH can be a file or directory.
    """
    import asyncio
    
    server: YataMcpServer = ctx.obj["server"]
    path_obj = Path(path)
    
    if path_obj.is_file():
        console.print(f"[blue]Parsing file:[/blue] {path}")
        result = asyncio.run(
            server.call_tool("parse_file", {"file_path": path})
        )
        
        if result["success"]:
            console.print(f"[green]✓[/green] Parsed {result['entities_count']} entities")
        else:
            console.print(f"[red]✗[/red] Errors: {result['errors']}")
            raise SystemExit(1)
    else:
        console.print(f"[blue]Parsing directory:[/blue] {path}")
        result = asyncio.run(
            server.call_tool("parse_directory", {
                "directory": path,
                "patterns": list(pattern),
                "exclude_patterns": list(exclude),
            })
        )
        
        if result["success"]:
            console.print(
                f"[green]✓[/green] Parsed {result['files_processed']} files, "
                f"{result['total_entities']} entities"
            )
        else:
            console.print(f"[red]✗[/red] Errors: {result['errors']}")
            raise SystemExit(1)


@cli.command()
@click.option(
    "--transport", "-t",
    type=click.Choice(["stdio", "sse"]),
    default="stdio",
    help="Transport type (default: stdio)",
)
@click.option(
    "--port", "-p",
    type=int,
    default=8080,
    help="Port for SSE transport (default: 8080)",
)
def serve(transport: str, port: int) -> None:
    """Start the MCP server.
    
    The server can run in two modes:
    - stdio: Standard input/output (for direct integration)
    - sse: Server-Sent Events over HTTP (for web clients)
    """
    from yata_mcp.server.protocol import create_mcp_server
    
    if transport == "sse":
        console.print(f"[blue]Starting YATA MCP Server (SSE)[/blue]")
        console.print(f"  Port: {port}")
        mcp = create_mcp_server()
        mcp.settings.port = port
        mcp.run(transport="sse")
    else:
        # stdio mode - run silently for MCP clients
        mcp = create_mcp_server()
        mcp.run(transport="stdio")


@cli.command()
def info() -> None:
    """Show YATA server information."""
    table = Table(title="YATA Server Information")
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Name", "YATA (八咫)")
    table.add_row("Version", __version__)
    table.add_row("Protocol", "MCP (Model Context Protocol)")
    
    server = YataMcpServer()
    tools = server.list_tools()
    resources = server.list_resources()
    
    table.add_row("Tools", str(len(tools)))
    table.add_row("Resources", str(len(resources)))
    
    console.print(table)
    
    # Show tools
    console.print("\n[bold]Available Tools:[/bold]")
    for tool in tools:
        console.print(f"  • [cyan]{tool.name}[/cyan]: {tool.description}")
    
    # Show resources
    console.print("\n[bold]Available Resources:[/bold]")
    for resource in resources:
        console.print(f"  • [cyan]{resource.uri}[/cyan]: {resource.description}")


@cli.command()
@click.argument("output", type=click.Path())
@click.pass_context
def save(ctx: click.Context, output: str) -> None:
    """Save the knowledge graph to a file.
    
    OUTPUT is the path to save the JSON file.
    """
    import asyncio
    
    server: YataMcpServer = ctx.obj["server"]
    output_path = Path(output)
    
    console.print(f"[blue]Saving knowledge graph to:[/blue] {output}")
    result = asyncio.run(
        server.call_tool("save_graph", {"file_path": str(output_path)})
    )
    
    if result["success"]:
        console.print(f"[green]✓[/green] Saved {result['entities_count']} entities, {result['relationships_count']} relationships")
    else:
        console.print(f"[red]✗[/red] Error: {result.get('error', 'Unknown error')}")
        raise SystemExit(1)


@cli.command()
@click.argument("input_file", type=click.Path(exists=True))
@click.pass_context
def load(ctx: click.Context, input_file: str) -> None:
    """Load a knowledge graph from a file.
    
    INPUT_FILE is the path to the JSON file to load.
    """
    import asyncio
    
    server: YataMcpServer = ctx.obj["server"]
    input_path = Path(input_file)
    
    console.print(f"[blue]Loading knowledge graph from:[/blue] {input_file}")
    result = asyncio.run(
        server.call_tool("load_graph", {"file_path": str(input_path)})
    )
    
    if result["success"]:
        console.print(f"[green]✓[/green] Loaded {result['entities_count']} entities, {result['relationships_count']} relationships")
    else:
        console.print(f"[red]✗[/red] Error: {result.get('error', 'Unknown error')}")
        raise SystemExit(1)


@cli.command()
@click.argument("query_text")
@click.option(
    "--type", "-t",
    "entity_type",
    type=click.Choice([
        "module", "class", "function", "method",
        "variable", "constant", "parameter", "interface",
        "type_alias", "enum", "property", "decorator", "import"
    ]),
    default=None,
    help="Filter by entity type",
)
@click.option(
    "--max-results", "-n",
    type=int,
    default=20,
    help="Maximum number of results (default: 20)",
)
@click.option(
    "--json", "output_json",
    is_flag=True,
    help="Output in JSON format",
)
@click.option(
    "--graph", "-g",
    type=click.Path(exists=True),
    default=None,
    help="Path to knowledge graph file to load",
)
@click.pass_context
def query(
    ctx: click.Context,
    query_text: str,
    entity_type: str | None,
    max_results: int,
    output_json: bool,
    graph: str | None,
) -> None:
    """Search entities in the knowledge graph.
    
    QUERY_TEXT is the search query (matches entity names).
    
    Examples:
    
        yata query "parse" --type function
        
        yata query "User" --max-results 5 --json
        
        yata query "config" --graph ./my_graph.json
    """
    import asyncio
    import json as json_module
    
    server: YataMcpServer = ctx.obj["server"]
    
    # Load graph if specified
    if graph:
        result = asyncio.run(
            server.call_tool("load_graph", {"file_path": graph})
        )
        if not result["success"]:
            console.print(f"[red]✗[/red] Failed to load graph: {result.get('error')}")
            raise SystemExit(1)
    
    # Build search arguments
    search_args: dict = {
        "query": query_text,
        "limit": max_results,
    }
    if entity_type:
        search_args["entity_type"] = entity_type
    
    # Execute search
    result = asyncio.run(
        server.call_tool("search_entities", search_args)
    )
    
    entities = result.get("entities", [])
    
    if output_json:
        # JSON output
        console.print(json_module.dumps(entities, indent=2, ensure_ascii=False))
    else:
        # Human-readable output
        if not entities:
            console.print(f"[yellow]No entities found matching '{query_text}'[/yellow]")
            return
        
        console.print(f"[bold]Found {len(entities)} entities:[/bold]\n")
        
        for entity in entities:
            type_color = {
                "module": "blue",
                "class": "green",
                "function": "yellow",
                "method": "cyan",
                "variable": "magenta",
            }.get(entity.get("type", ""), "white")
            
            console.print(
                f"  [{type_color}]{entity.get('type', 'unknown')}[/{type_color}] "
                f"[bold]{entity.get('name', 'N/A')}[/bold]"
            )
            if entity.get("location"):
                loc = entity["location"]
                console.print(f"    📁 {loc.get('file', 'N/A')}:{loc.get('line', '?')}")
            if entity.get("docstring"):
                doc = entity["docstring"][:80] + "..." if len(entity.get("docstring", "")) > 80 else entity.get("docstring", "")
                console.print(f"    📝 {doc}")
            console.print()


@cli.command()
@click.option(
    "--graph", "-g",
    type=click.Path(exists=True),
    default=None,
    help="Path to knowledge graph file to load",
)
@click.option(
    "--json", "output_json",
    is_flag=True,
    help="Output in JSON format",
)
@click.pass_context
def stats(
    ctx: click.Context,
    graph: str | None,
    output_json: bool,
) -> None:
    """Show knowledge graph statistics.
    
    Displays information about registered entities and relationships.
    
    Examples:
    
        yata stats
        
        yata stats --graph ./my_graph.json
        
        yata stats --json
    """
    import asyncio
    import json as json_module
    
    server: YataMcpServer = ctx.obj["server"]
    
    # Load graph if specified
    if graph:
        result = asyncio.run(
            server.call_tool("load_graph", {"file_path": graph})
        )
        if not result["success"]:
            console.print(f"[red]✗[/red] Failed to load graph: {result.get('error')}")
            raise SystemExit(1)
    
    # Read stats resource
    stats_data = asyncio.run(
        asyncio.to_thread(server.read_resource_sync, "yata://graph/stats")
    )
    
    if output_json:
        console.print(json_module.dumps(stats_data, indent=2, ensure_ascii=False))
    else:
        table = Table(title="Knowledge Graph Statistics")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green", justify="right")
        
        table.add_row("Total Entities", str(stats_data.get("entity_count", 0)))
        table.add_row("Total Relationships", str(stats_data.get("relationship_count", 0)))
        
        # Entity types breakdown
        entity_types = stats_data.get("entities_by_type", {})
        if entity_types:
            console.print(table)
            console.print()
            
            type_table = Table(title="Entities by Type")
            type_table.add_column("Type", style="cyan")
            type_table.add_column("Count", style="green", justify="right")
            
            for etype, count in sorted(entity_types.items(), key=lambda x: -x[1]):
                type_table.add_row(etype, str(count))
            
            console.print(type_table)
        else:
            console.print(table)


@cli.command()
@click.option(
    "--graph", "-g",
    type=click.Path(exists=True),
    default=None,
    help="Path to knowledge graph file to load",
)
@click.option(
    "--repair", "-r",
    is_flag=True,
    help="Automatically repair found issues",
)
@click.option(
    "--json", "output_json",
    is_flag=True,
    help="Output in JSON format",
)
@click.pass_context
def validate(
    ctx: click.Context,
    graph: str | None,
    repair: bool,
    output_json: bool,
) -> None:
    """Validate knowledge graph integrity.
    
    Checks for orphaned entities, invalid references, and duplicates.
    Use --repair to automatically fix found issues.
    
    Examples:
    
        yata validate --graph ./my_graph.json
        
        yata validate --graph ./my_graph.json --repair
        
        yata validate --json
    """
    import asyncio
    import json as json_module
    
    from yata_core.application.services import GraphValidator
    
    server: YataMcpServer = ctx.obj["server"]
    
    # Load graph if specified
    if graph:
        graph_path = Path(graph).resolve()
        console.print(f"[blue]Loading graph:[/blue] {graph_path}")
        result = asyncio.run(
            server.call_tool("load_graph", {"path": str(graph_path)})
        )
        if not result.get("success"):
            console.print(f"[red]✗[/red] Failed to load graph: {result.get('error', 'unknown error')}")
            raise SystemExit(1)
    
    # Get the knowledge graph
    kg = server._knowledge_graph
    
    # Create validator
    validator = GraphValidator(kg)
    
    # Run validation
    console.print(f"[blue]Validating graph integrity...[/blue]")
    validation_result = validator.validate()
    
    if output_json:
        output = {
            "is_valid": validation_result.is_valid,
            "entities_checked": validation_result.entities_checked,
            "relationships_checked": validation_result.relationships_checked,
            "error_count": validation_result.error_count,
            "warning_count": validation_result.warning_count,
            "issues": [
                {
                    "type": issue.issue_type,
                    "severity": issue.severity,
                    "description": issue.description,
                }
                for issue in validation_result.issues
            ],
        }
        console.print(json_module.dumps(output, indent=2, ensure_ascii=False))
    else:
        # Human-readable output
        if validation_result.is_valid:
            console.print(f"[green]✓[/green] Graph is valid")
        else:
            console.print(f"[red]✗[/red] Graph has integrity issues")
        
        console.print(f"  Entities checked: {validation_result.entities_checked}")
        console.print(f"  Relationships checked: {validation_result.relationships_checked}")
        
        if validation_result.issues:
            console.print()
            
            # Group issues by severity
            errors = [i for i in validation_result.issues if i.severity == "error"]
            warnings = [i for i in validation_result.issues if i.severity == "warning"]
            
            if errors:
                console.print(f"[red]Errors ({len(errors)}):[/red]")
                for issue in errors[:10]:  # Show first 10
                    console.print(f"  • {issue.description}")
                if len(errors) > 10:
                    console.print(f"  ... and {len(errors) - 10} more")
            
            if warnings:
                console.print(f"[yellow]Warnings ({len(warnings)}):[/yellow]")
                for issue in warnings[:10]:  # Show first 10
                    console.print(f"  • {issue.description}")
                if len(warnings) > 10:
                    console.print(f"  ... and {len(warnings) - 10} more")
    
    # Repair if requested
    if repair and not validation_result.is_valid:
        console.print()
        console.print("[blue]Repairing graph...[/blue]")
        repair_result = validator.repair()
        
        if repair_result.success:
            console.print(f"[green]✓[/green] Repair completed")
            if repair_result.invalid_relationships_removed > 0:
                console.print(f"  Removed {repair_result.invalid_relationships_removed} invalid relationships")
            if repair_result.orphaned_entities_removed > 0:
                console.print(f"  Removed {repair_result.orphaned_entities_removed} orphaned entities")
            if repair_result.duplicate_entities_removed > 0:
                console.print(f"  Removed {repair_result.duplicate_entities_removed} duplicate entities")
            
            # Save repaired graph if path was specified
            if graph:
                console.print(f"[blue]Saving repaired graph to:[/blue] {graph}")
                save_result = asyncio.run(
                    server.call_tool("save_graph", {"path": graph})
                )
                if save_result.get("success"):
                    console.print(f"[green]✓[/green] Graph saved")
                else:
                    console.print(f"[red]✗[/red] Failed to save: {save_result.get('error')}")
        else:
            console.print(f"[red]✗[/red] Repair failed")
    
    # Exit with error code if validation failed
    if not validation_result.is_valid and not repair:
        raise SystemExit(1)


@cli.command()
@click.argument("directory", type=click.Path(exists=True))
@click.option(
    "--pattern", "-p",
    multiple=True,
    default=["**/*.py"],
    help="Glob pattern for files to include",
)
@click.option(
    "--json", "output_json",
    is_flag=True,
    help="Output in JSON format",
)
def benchmark(
    directory: str,
    pattern: tuple[str, ...],
    output_json: bool,
) -> None:
    """Run performance benchmark on a directory.
    
    Measures indexing and parsing performance metrics.
    
    Examples:
    
        yata benchmark ./src
        
        yata benchmark ./src --pattern "**/*.py" --json
    """
    import json as json_module
    from yata_core.application.services import measure_indexing_performance
    
    dir_path = Path(directory).resolve()
    
    if not output_json:
        console.print(f"[blue]Running benchmark on:[/blue] {dir_path}")
        console.print(f"  Patterns: {', '.join(pattern)}")
        console.print()
    
    # Run benchmark
    metrics = measure_indexing_performance(
        directory=dir_path,
        patterns=list(pattern),
    )
    
    if output_json:
        console.print(json_module.dumps(metrics, indent=2, ensure_ascii=False))
    else:
        # Human-readable output
        console.print("[bold]Performance Metrics[/bold]\n")
        
        table = Table()
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green", justify="right")
        
        table.add_row("Files parsed", str(metrics["files_parsed"]))
        table.add_row("Entities extracted", str(metrics["entities_extracted"]))
        table.add_row("Relationships extracted", str(metrics["relationships_extracted"]))
        table.add_row("Total time", f"{metrics['total_time_ms']:.1f} ms")
        table.add_row("Time per file", f"{metrics['time_per_file_ms']:.2f} ms")
        table.add_row("Throughput", f"{metrics['files_per_second']:.1f} files/sec")
        table.add_row("Entities per file", f"{metrics['entities_per_file']:.1f}")
        
        console.print(table)


@cli.command()
@click.argument("directory", type=click.Path(exists=True))
@click.option(
    "--pattern", "-p",
    multiple=True,
    default=["**/*.py", "**/*.ts", "**/*.tsx", "**/*.js", "**/*.jsx", "**/*.rs", "**/*.go"],
    help="Glob pattern for files to watch",
)
@click.option(
    "--exclude", "-e",
    multiple=True,
    default=["**/node_modules/**", "**/__pycache__/**", "**/.git/**"],
    help="Glob pattern for files to exclude",
)
@click.option(
    "--debounce", "-d",
    type=float,
    default=1.0,
    help="Debounce delay in seconds (default: 1.0)",
)
@click.option(
    "--output", "-o",
    type=click.Path(),
    default=None,
    help="Path to save knowledge graph (auto-save on changes)",
)
@click.pass_context
def watch(
    ctx: click.Context,
    directory: str,
    pattern: tuple[str, ...],
    exclude: tuple[str, ...],
    debounce: float,
    output: str | None,
) -> None:
    """Watch directory for changes and update knowledge graph.
    
    Monitors DIRECTORY for file changes and automatically re-indexes
    modified files using incremental parsing.
    
    Press Ctrl+C to stop watching.
    
    Examples:
    
        yata watch ./src
        
        yata watch ./src --pattern "**/*.py" --debounce 2.0
        
        yata watch ./src --output ./graph.json
    """
    import asyncio
    import time
    import signal
    import sys
    from datetime import datetime
    
    try:
        from watchdog.observers import Observer
        from watchdog.events import FileSystemEventHandler, FileSystemEvent
    except ImportError:
        console.print("[red]✗[/red] watchdog package is required for watch command")
        console.print("  Install with: pip install watchdog")
        raise SystemExit(1)
    
    server: YataMcpServer = ctx.obj["server"]
    dir_path = Path(directory).resolve()
    
    # Initial parse
    console.print(f"[blue]Initial parsing of:[/blue] {dir_path}")
    result = asyncio.run(
        server.call_tool("incremental_parse", {
            "directory": str(dir_path),
            "patterns": list(pattern),
            "exclude_patterns": list(exclude),
        })
    )
    console.print(
        f"[green]✓[/green] Parsed {result['files_processed']} files, "
        f"{result['total_entities']} entities"
    )
    
    # Track pending changes for debouncing
    pending_changes: dict[str, float] = {}
    last_process_time = time.time()
    
    class ChangeHandler(FileSystemEventHandler):
        """Handler for file system events."""
        
        def _should_process(self, path: str) -> bool:
            """Check if file matches patterns and not excluded."""
            import fnmatch
            rel_path = str(Path(path).relative_to(dir_path))
            
            # Check exclude patterns first
            for exc in exclude:
                if fnmatch.fnmatch(rel_path, exc) or fnmatch.fnmatch(Path(path).name, exc):
                    return False
            
            # Check include patterns
            for pat in pattern:
                if fnmatch.fnmatch(rel_path, pat) or fnmatch.fnmatch(Path(path).name, pat.split("/")[-1]):
                    return True
            return False
        
        def on_any_event(self, event: FileSystemEvent) -> None:
            if event.is_directory:
                return
            if not self._should_process(event.src_path):
                return
            pending_changes[event.src_path] = time.time()
    
    def process_changes() -> None:
        """Process pending changes after debounce."""
        nonlocal last_process_time
        
        now = time.time()
        if not pending_changes:
            return
        
        # Check if enough time has passed since last change
        oldest_change = min(pending_changes.values())
        if now - oldest_change < debounce:
            return
        
        # Process changes
        console.print(f"\n[yellow]Detected changes in {len(pending_changes)} file(s)[/yellow]")
        pending_changes.clear()
        
        result = asyncio.run(
            server.call_tool("incremental_parse", {
                "directory": str(dir_path),
                "patterns": list(pattern),
                "exclude_patterns": list(exclude),
            })
        )
        
        timestamp = datetime.now().strftime("%H:%M:%S")
        console.print(
            f"[{timestamp}] [green]✓[/green] "
            f"Processed: {result['files_processed']}, "
            f"Skipped: {result['files_skipped']}, "
            f"Removed: {result['files_removed']}"
        )
        
        # Auto-save if output specified
        if output:
            save_result = asyncio.run(
                server.call_tool("save_graph", {"file_path": output})
            )
            if save_result["success"]:
                console.print(f"[{timestamp}] [blue]💾[/blue] Saved to {output}")
        
        last_process_time = now
    
    # Setup file watcher
    event_handler = ChangeHandler()
    observer = Observer()
    observer.schedule(event_handler, str(dir_path), recursive=True)
    
    # Handle Ctrl+C gracefully
    running = True
    
    def signal_handler(sig, frame):
        nonlocal running
        running = False
        console.print("\n[yellow]Stopping watch...[/yellow]")
    
    signal.signal(signal.SIGINT, signal_handler)
    
    observer.start()
    console.print(f"\n[bold green]Watching for changes...[/bold green]")
    console.print(f"  Directory: {dir_path}")
    console.print(f"  Patterns: {', '.join(pattern)}")
    console.print(f"  Debounce: {debounce}s")
    console.print("\nPress Ctrl+C to stop\n")
    
    try:
        while running:
            process_changes()
            time.sleep(0.1)
    finally:
        observer.stop()
        observer.join()
        console.print("[green]✓[/green] Watch stopped")


def main() -> None:
    """Main entry point."""
    cli()


if __name__ == "__main__":
    main()
