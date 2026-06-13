"""Unit tests for YAML parser."""

import pytest

from magatama_core.domain.entities import EntityType
from magatama_core.infrastructure.parsers.yaml_parser import YAMLParser


class TestYAMLParser:
    """Test suite for YAML parser."""

    @pytest.fixture
    def parser(self):
        """Create parser instance."""
        return YAMLParser()

    def test_parse_simple_yaml(self, parser):
        """Test simple YAML parsing."""
        code = """
name: myapp
version: 1.0.0
"""
        result = parser.parse_string(code, "config.yaml")

        assert len(result.entities) >= 3

        name = next((e for e in result.entities if e.name == "name"), None)
        assert name is not None

        version = next((e for e in result.entities if e.name == "version"), None)
        assert version is not None

    def test_parse_nested_yaml(self, parser):
        """Test nested YAML parsing."""
        code = """
database:
  host: localhost
  port: 5432
"""
        result = parser.parse_string(code, "config.yaml")

        db = next((e for e in result.entities if e.name == "database"), None)
        assert db is not None

        host = next((e for e in result.entities if "host" in e.name), None)
        assert host is not None

    def test_parse_deeply_nested(self, parser):
        """Test deeply nested YAML."""
        code = """
level1:
  level2:
    level3:
      value: test
"""
        result = parser.parse_string(code, "config.yaml")

        assert len(result.entities) >= 4

    def test_parse_complex_yaml(self, parser):
        """Test parsing complex YAML structure."""
        code = """
application:
  name: myapp
  version: 1.0.0
  
database:
  primary:
    host: localhost
    port: 5432
  replica:
    host: replica.local
    port: 5432

features:
  auth: true
  cache: true
"""
        result = parser.parse_string(code, "app-config.yaml")

        assert len(result.entities) >= 10

    def test_module_entity_created(self, parser):
        """Test that document entity is always created."""
        code = "key: value"
        result = parser.parse_string(code, "test.yaml")

        module = next((e for e in result.entities if e.type == EntityType.MODULE), None)
        assert module is not None
        assert module.name == "test"

    def test_parse_docker_compose(self, parser):
        """Test parsing Docker Compose style YAML."""
        code = """
version: "3.8"

services:
  web:
    image: nginx
    ports:
      - "80:80"
  
  db:
    image: postgres
    environment:
      POSTGRES_DB: mydb
"""
        result = parser.parse_string(code, "docker-compose.yaml")

        services = next((e for e in result.entities if e.name == "services"), None)
        assert services is not None

    def test_parse_kubernetes_yaml(self, parser):
        """Test parsing Kubernetes style YAML."""
        code = """
apiVersion: v1
kind: Service
metadata:
  name: my-service
spec:
  selector:
    app: MyApp
  ports:
    - protocol: TCP
      port: 80
"""
        result = parser.parse_string(code, "service.yaml")

        assert len(result.entities) >= 5

        api_version = next((e for e in result.entities if e.name == "apiVersion"), None)
        assert api_version is not None

    def test_relationships_created(self, parser):
        """Test that relationships are created for nested keys."""
        code = """
parent:
  child: value
"""
        result = parser.parse_string(code, "test.yaml")

        assert len(result.relationships) >= 2

    def test_parse_github_actions(self, parser):
        """Test parsing GitHub Actions workflow YAML."""
        code = """
name: CI

on:
  push:
    branches:
      - main

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Build
        run: npm run build
"""
        result = parser.parse_string(code, "ci.yaml")

        name = next((e for e in result.entities if e.name == "name"), None)
        assert name is not None

        jobs = next((e for e in result.entities if e.name == "jobs"), None)
        assert jobs is not None
