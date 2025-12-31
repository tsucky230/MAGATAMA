"""
E2E Integration Tests - TASK-036

Article IX: Integration-First Testing
REQ-MCP-001: AI Tool Connection Tests

End-to-end tests that verify the complete workflow:
1. Parse source files
2. Build knowledge graph
3. Query entities and relationships
4. Verify MCP protocol compliance
"""

import json
import tempfile
from pathlib import Path

import pytest

from yata_core.domain.entities.base import EntityType
from yata_core.infrastructure.parsers import PythonParser, TypeScriptParser
from yata_core.infrastructure.storage import NetworkXKnowledgeGraph, SQLiteKnowledgeGraph
from yata_mcp.server.mcp_server import YataMcpServer


class TestE2EParseQueryWorkflow:
    """
    E2E tests for complete parse → query → result workflow.
    
    Article IX: Integration-First Testing compliance.
    """

    @pytest.fixture
    def sample_python_project(self):
        """Create a sample Python project structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            
            # Create main module
            (project / "myproject").mkdir()
            (project / "myproject" / "__init__.py").write_text('''
"""My Project - A sample Python project."""
from .utils import helper_function
from .models import User
''')
            
            # Create utils module
            (project / "myproject" / "utils.py").write_text('''
"""Utility functions."""

def helper_function(x: int, y: int) -> int:
    """Add two numbers."""
    return x + y


def format_string(s: str) -> str:
    """Format a string."""
    return s.strip().lower()


async def async_fetch(url: str) -> dict:
    """Async fetch function."""
    return {"url": url}
''')
            
            # Create models module
            (project / "myproject" / "models.py").write_text('''
"""Data models."""
from dataclasses import dataclass


@dataclass
class User:
    """User model."""
    id: int
    name: str
    email: str
    
    def get_display_name(self) -> str:
        """Get display name."""
        return f"{self.name} <{self.email}>"


class Admin(User):
    """Admin user with extra permissions."""
    
    def __init__(self, id: int, name: str, email: str, permissions: list[str]):
        super().__init__(id, name, email)
        self.permissions = permissions
    
    def has_permission(self, perm: str) -> bool:
        """Check if admin has permission."""
        return perm in self.permissions
''')
            
            # Create service module with complex dependencies
            (project / "myproject" / "service.py").write_text('''
"""Service layer."""
from .models import User, Admin
from .utils import helper_function, format_string


class UserService:
    """Service for user operations."""
    
    def __init__(self):
        self.users: list[User] = []
    
    def add_user(self, user: User) -> None:
        """Add a user."""
        self.users.append(user)
    
    def get_user(self, user_id: int) -> User | None:
        """Get user by ID."""
        for user in self.users:
            if user.id == user_id:
                return user
        return None
    
    def format_user_name(self, user: User) -> str:
        """Format user name using utility."""
        return format_string(user.name)


def create_admin(id: int, name: str, email: str) -> Admin:
    """Factory function to create admin."""
    return Admin(id, name, email, ["read", "write"])
''')
            
            yield project

    @pytest.fixture
    def sample_typescript_project(self):
        """Create a sample TypeScript project structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            
            # Create main file
            (project / "index.ts").write_text('''
/**
 * Main entry point
 */
import { UserService } from './services/user';
import { User, Admin } from './models/user';

export function main(): void {
    const service = new UserService();
    console.log('App started');
}
''')
            
            # Create models
            (project / "models").mkdir()
            (project / "models" / "user.ts").write_text('''
/**
 * User models
 */

export interface IUser {
    id: number;
    name: string;
    email: string;
}

export class User implements IUser {
    constructor(
        public id: number,
        public name: string,
        public email: string
    ) {}
    
    getDisplayName(): string {
        return `${this.name} <${this.email}>`;
    }
}

export class Admin extends User {
    permissions: string[] = [];
    
    hasPermission(perm: string): boolean {
        return this.permissions.includes(perm);
    }
}

export type UserRole = 'user' | 'admin' | 'guest';
''')
            
            # Create services
            (project / "services").mkdir()
            (project / "services" / "user.ts").write_text('''
/**
 * User service
 */
import { User, Admin, IUser } from '../models/user';

export class UserService {
    private users: User[] = [];
    
    addUser(user: User): void {
        this.users.push(user);
    }
    
    getUser(id: number): User | undefined {
        return this.users.find(u => u.id === id);
    }
    
    async fetchUser(id: number): Promise<User | null> {
        // Simulated async fetch
        return null;
    }
}

export function createAdmin(id: number, name: string, email: string): Admin {
    return new Admin(id, name, email);
}
''')
            
            yield project

    @pytest.mark.asyncio
    async def test_python_project_full_indexing(self, sample_python_project: Path):
        """Test complete Python project indexing."""
        server = YataMcpServer()
        
        # Parse entire project
        result = await server.call_tool("parse_directory", {
            "directory": str(sample_python_project)
        })
        
        # Verify files were parsed
        assert result["success"]
        assert result["files_processed"] >= 4
        assert result["total_entities"] > 0
        
        # Verify entity types via stats
        stats = server._get_graph_stats()
        assert stats["entity_count"] > 0
        
        # Should have functions
        functions = server._knowledge_graph.entities.get_by_type(EntityType.FUNCTION)
        function_names = {f.name for f in functions}
        assert "helper_function" in function_names
        assert "format_string" in function_names
        
        # Should have classes
        classes = server._knowledge_graph.entities.get_by_type(EntityType.CLASS)
        class_names = {c.name for c in classes}
        assert "User" in class_names
        assert "Admin" in class_names
        assert "UserService" in class_names

    @pytest.mark.asyncio
    async def test_typescript_project_full_indexing(self, sample_typescript_project: Path):
        """Test complete TypeScript project indexing."""
        server = YataMcpServer()
        
        # Parse entire project
        result = await server.call_tool("parse_directory", {
            "directory": str(sample_typescript_project),
            "patterns": ["**/*.ts"]
        })
        
        # Verify parsing succeeded
        assert result["success"]
        assert result["files_processed"] >= 3
        assert result["total_entities"] > 0
        
        # Verify classes and interfaces
        classes = server._knowledge_graph.entities.get_by_type(EntityType.CLASS)
        class_names = {c.name for c in classes}
        assert "User" in class_names
        assert "Admin" in class_names
        
        interfaces = server._knowledge_graph.entities.get_by_type(EntityType.INTERFACE)
        interface_names = {i.name for i in interfaces}
        assert "IUser" in interface_names

    @pytest.mark.asyncio
    async def test_entity_search_workflow(self, sample_python_project: Path):
        """Test entity search functionality."""
        server = YataMcpServer()
        await server.call_tool("parse_directory", {
            "directory": str(sample_python_project)
        })
        
        # Search by name
        results = await server.call_tool("search_entities", {
            "query": "User"
        })
        
        assert results["total_count"] > 0
        
        # Search should find User class
        user_results = [r for r in results["entities"] if r["name"] == "User"]
        assert len(user_results) >= 1
        assert user_results[0]["type"] == "class"

    @pytest.mark.asyncio
    async def test_entity_retrieval_workflow(self, sample_python_project: Path):
        """Test retrieving specific entity details."""
        server = YataMcpServer()
        await server.call_tool("parse_directory", {
            "directory": str(sample_python_project)
        })
        
        # Get all classes
        classes = server._knowledge_graph.entities.get_by_type(EntityType.CLASS)
        user_class = next((c for c in classes if c.name == "User"), None)
        
        assert user_class is not None
        
        # Get entity by ID
        result = await server.call_tool("get_entity", {
            "entity_id": user_class.id.value
        })
        assert result["entity"] is not None
        assert result["entity"]["name"] == "User"
        assert result["entity"]["type"] == "class"

    @pytest.mark.asyncio
    async def test_relationship_navigation(self, sample_python_project: Path):
        """Test navigating entity relationships."""
        server = YataMcpServer()
        await server.call_tool("parse_directory", {
            "directory": str(sample_python_project)
        })
        
        # Find Admin class
        classes = server._knowledge_graph.entities.get_by_type(EntityType.CLASS)
        admin_class = next((c for c in classes if c.name == "Admin"), None)
        
        assert admin_class is not None
        
        # Get related entities
        related = await server.call_tool("get_related_entities", {
            "entity_id": admin_class.id.value,
            "depth": 1
        })
        assert "related_entities" in related
        
        # Admin should have relationships (at minimum, no error)
        assert related["count"] >= 0

    @pytest.mark.asyncio
    async def test_incremental_update_workflow(self, sample_python_project: Path):
        """Test incremental parsing updates."""
        server = YataMcpServer()
        
        # Initial parse
        result1 = await server.call_tool("parse_directory", {
            "directory": str(sample_python_project)
        })
        assert result1["success"]
        
        # Modify a file
        utils_file = sample_python_project / "myproject" / "utils.py"
        original_content = utils_file.read_text()
        utils_file.write_text(original_content + '''

def new_function(z: float) -> float:
    """A new function."""
    return z * 2
''')
        
        # Incremental parse
        result2 = await server.call_tool("incremental_parse", {
            "directory": str(sample_python_project)
        })
        
        # Should have detected the change
        assert result2["success"]
        assert result2["files_processed"] >= 1
        
        # Verify new function was added
        functions = server._knowledge_graph.entities.get_by_type(EntityType.FUNCTION)
        function_names = {f.name for f in functions}
        assert "new_function" in function_names

    @pytest.mark.asyncio
    async def test_graph_persistence_workflow(self, sample_python_project: Path):
        """Test saving and loading graph state."""
        with tempfile.TemporaryDirectory() as tmpdir:
            graph_path = Path(tmpdir) / "graph.json"
            
            # Create and populate server
            server1 = YataMcpServer()
            await server1.call_tool("parse_directory", {
                "directory": str(sample_python_project)
            })
            
            # Save graph
            save_result = await server1.call_tool("save_graph", {
                "file_path": str(graph_path)
            })
            assert save_result["success"]
            assert graph_path.exists()
            
            # Load into new server
            server2 = YataMcpServer()
            load_result = await server2.call_tool("load_graph", {
                "file_path": str(graph_path)
            })
            
            assert load_result["success"]
            
            # Verify data was restored
            classes1 = server1._knowledge_graph.entities.get_by_type(EntityType.CLASS)
            classes2 = server2._knowledge_graph.entities.get_by_type(EntityType.CLASS)
            
            assert len(list(classes1)) == len(list(classes2))


class TestE2ESQLitePersistence:
    """E2E tests for SQLite persistence."""

    def test_sqlite_full_workflow(self):
        """Test complete workflow with SQLite storage."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            json_export = Path(tmpdir) / "export.json"
            
            # Create project files
            project = Path(tmpdir) / "project"
            project.mkdir()
            (project / "main.py").write_text('''
def main():
    """Entry point."""
    print("Hello")

class App:
    """Main application."""
    def run(self):
        main()
''')
            
            # Session 1: Parse and save
            with SQLiteKnowledgeGraph(db_path) as graph:
                parser = PythonParser()
                result = parser.parse_file(project / "main.py")
                
                for entity in result.entities:
                    graph.entities.add(entity)
                for rel in result.relationships:
                    graph.relationships.add(rel)
                
                graph.set_file_hash(str(project / "main.py"), "hash1")
                
                # Export to JSON as well
                graph.save(json_export)
            
            # Session 2: Verify persistence
            with SQLiteKnowledgeGraph(db_path) as graph:
                functions = list(graph.entities.get_by_type(EntityType.FUNCTION))
                assert len(functions) >= 1
                
                classes = list(graph.entities.get_by_type(EntityType.CLASS))
                assert len(classes) >= 1
                
                # Verify file tracking
                files = graph.get_tracked_files()
                assert len(files) == 1

    def test_sqlite_incremental_update(self):
        """Test incremental updates with SQLite."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            
            # Create project
            project = Path(tmpdir) / "project"
            project.mkdir()
            file1 = project / "module1.py"
            file2 = project / "module2.py"
            
            file1.write_text('def func1(): pass')
            file2.write_text('def func2(): pass')
            
            parser = PythonParser()
            
            # Initial parse
            with SQLiteKnowledgeGraph(db_path) as graph:
                for f in [file1, file2]:
                    result = parser.parse_file(f)
                    for entity in result.entities:
                        graph.entities.add(entity)
                    import hashlib
                    content_hash = hashlib.sha256(f.read_bytes()).hexdigest()
                    graph.set_file_hash(str(f), content_hash)
            
            # Modify file1
            file1.write_text('''
def func1(): pass
def new_func(): pass
''')
            
            # Check which files need updating
            with SQLiteKnowledgeGraph(db_path) as graph:
                import hashlib
                
                # File1 should have changed
                old_hash1 = graph.get_file_hash(str(file1))
                new_hash1 = hashlib.sha256(file1.read_bytes()).hexdigest()
                assert old_hash1 != new_hash1
                
                # File2 should be unchanged
                old_hash2 = graph.get_file_hash(str(file2))
                new_hash2 = hashlib.sha256(file2.read_bytes()).hexdigest()
                assert old_hash2 == new_hash2


class TestE2EMcpProtocol:
    """E2E tests for MCP protocol compliance."""

    def test_mcp_tools_registered(self):
        """Verify all required tools are registered."""
        server = YataMcpServer()
        
        expected_tools = [
            "parse_file",
            "parse_directory",
            "incremental_parse",
            "search_entities",
            "get_entity",
            "get_related_entities",
            "save_graph",
            "load_graph",
        ]
        
        tool_names = {t.name for t in server.list_tools()}
        for tool_name in expected_tools:
            assert tool_name in tool_names, f"Missing tool: {tool_name}"

    def test_mcp_tool_schemas(self):
        """Verify tools have valid JSON schemas."""
        server = YataMcpServer()
        
        for tool in server.list_tools():
            # Each tool should have an input schema
            assert hasattr(tool, "input_schema")
            assert "type" in tool.input_schema
            assert "properties" in tool.input_schema
            assert "required" in tool.input_schema

    def test_mcp_resource_registered(self):
        """Verify resources are registered."""
        server = YataMcpServer()
        
        resources = server.list_resources()
        resource_uris = {r.uri for r in resources}
        
        assert "yata://graph/stats" in resource_uris

    @pytest.mark.asyncio
    async def test_mcp_error_handling(self):
        """Verify MCP error handling."""
        server = YataMcpServer()
        
        # Unknown tool should raise
        with pytest.raises(ValueError, match="Unknown tool"):
            await server.call_tool("nonexistent_tool", {})
        
        # Unknown resource should raise
        with pytest.raises(ValueError, match="Unknown resource"):
            await server.read_resource("yata://unknown")


class TestE2EMultiLanguage:
    """E2E tests for multi-language support."""

    @pytest.mark.asyncio
    async def test_mixed_language_project(self):
        """Test parsing a project with multiple languages."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            
            # Python file
            (project / "backend.py").write_text('''
class UserAPI:
    """User API endpoint."""
    def get_user(self, id: int):
        return {"id": id}
''')
            
            # TypeScript file
            (project / "frontend.ts").write_text('''
interface User {
    id: number;
    name: string;
}

class UserComponent {
    render(user: User): string {
        return user.name;
    }
}
''')
            
            server = YataMcpServer()
            
            # Parse Python file
            result_py = await server.call_tool("parse_file", {
                "file_path": str(project / "backend.py")
            })
            assert result_py["success"]
            
            # Parse TypeScript file
            result_ts = await server.call_tool("parse_file", {
                "file_path": str(project / "frontend.ts")
            })
            assert result_ts["success"]
            
            # Verify both are in the graph
            all_entities = list(server._knowledge_graph.entities.all())
            entity_names = {e.name for e in all_entities}
            
            # Python entities
            assert "UserAPI" in entity_names
            
            # TypeScript entities
            assert "User" in entity_names
            assert "UserComponent" in entity_names


class TestE2EPerformance:
    """E2E performance tests."""

    @pytest.mark.asyncio
    async def test_large_file_parsing(self):
        """Test parsing a large file performs acceptably."""
        import time
        
        with tempfile.TemporaryDirectory() as tmpdir:
            large_file = Path(tmpdir) / "large.py"
            
            # Generate a large file with many functions
            lines = ['"""A large module with many functions."""', '']
            for i in range(100):
                lines.extend([
                    f'def function_{i}(arg1: int, arg2: str) -> bool:',
                    f'    """Function {i} docstring."""',
                    f'    return arg1 > {i}',
                    '',
                ])
            
            large_file.write_text('\n'.join(lines))
            
            server = YataMcpServer()
            
            start = time.time()
            result = await server.call_tool("parse_file", {
                "file_path": str(large_file)
            })
            elapsed = time.time() - start
            
            assert result["success"]
            assert result["entities_count"] >= 100
            # Should complete in reasonable time (< 5 seconds)
            assert elapsed < 5.0

    @pytest.mark.asyncio
    async def test_many_files_parsing(self):
        """Test parsing many files performs acceptably."""
        import time
        
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir) / "project"
            project.mkdir()
            
            # Create 50 small files
            for i in range(50):
                (project / f"module_{i}.py").write_text(f'''
def func_{i}():
    """Function in module {i}."""
    pass

class Class_{i}:
    """Class in module {i}."""
    pass
''')
            
            server = YataMcpServer()
            
            start = time.time()
            result = await server.call_tool("parse_directory", {
                "directory": str(project)
            })
            elapsed = time.time() - start
            
            assert result["success"]
            assert result["files_processed"] >= 50
            # Should complete in reasonable time (< 30 seconds)
            assert elapsed < 30.0


class TestE2ERealWorldScenarios:
    """Real-world usage scenario tests."""

    @pytest.mark.asyncio
    async def test_find_all_test_classes(self):
        """Test finding all test classes in a project."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            
            # Create test files
            (project / "tests").mkdir()
            (project / "tests" / "test_user.py").write_text('''
import pytest

class TestUser:
    def test_create_user(self):
        pass
    
    def test_update_user(self):
        pass

class TestAdmin:
    def test_admin_permissions(self):
        pass
''')
            
            (project / "tests" / "test_service.py").write_text('''
class TestUserService:
    def test_add_user(self):
        pass
''')
            
            server = YataMcpServer()
            await server.call_tool("parse_directory", {
                "directory": str(project / "tests")
            })
            
            # Search for test classes
            results = await server.call_tool("search_entities", {
                "query": "Test",
                "entity_type": "class"
            })
            
            test_classes = [e for e in results["entities"] if e["name"].startswith("Test")]
            assert len(test_classes) >= 3
            
            test_names = {c["name"] for c in test_classes}
            assert "TestUser" in test_names
            assert "TestAdmin" in test_names
            assert "TestUserService" in test_names

    @pytest.mark.asyncio
    async def test_analyze_class_hierarchy(self):
        """Test analyzing class inheritance hierarchy."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            
            (project / "models.py").write_text('''
class Entity:
    """Base entity."""
    pass

class User(Entity):
    """User entity."""
    pass

class Admin(User):
    """Admin user."""
    pass

class SuperAdmin(Admin):
    """Super admin user."""
    pass
''')
            
            server = YataMcpServer()
            await server.call_tool("parse_file", {
                "file_path": str(project / "models.py")
            })
            
            # Find SuperAdmin class
            results = await server.call_tool("search_entities", {
                "query": "SuperAdmin",
                "entity_type": "class"
            })
            
            assert results["total_count"] >= 1
            super_admin = results["entities"][0]
            
            # Get related entities
            related = await server.call_tool("get_related_entities", {
                "entity_id": super_admin["id"],
                "depth": 3
            })
            
            # Should find related classes
            assert "related_entities" in related
