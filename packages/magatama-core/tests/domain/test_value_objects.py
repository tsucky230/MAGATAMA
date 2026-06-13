"""
Value Objects Tests - RED Phase First (Article III)

REQ-KGC-001: Location (file, line, column)
REQ-KGC-005: Version (semver)
"""

import pytest

from magatama_core.domain.value_objects.ids import EntityId, LibraryId
from magatama_core.domain.value_objects.location import Location
from magatama_core.domain.value_objects.version import Version


class TestLocation:
    """Test Location value object."""

    @pytest.mark.unit
    def test_location_creation(self) -> None:
        """Test creating a valid location."""
        loc = Location(file="main.py", line=10, column=5)
        assert loc.file == "main.py"
        assert loc.line == 10
        assert loc.column == 5

    @pytest.mark.unit
    def test_location_default_column(self) -> None:
        """Test location with default column (0)."""
        loc = Location(file="main.py", line=10)
        assert loc.column == 0

    @pytest.mark.unit
    def test_location_immutable(self) -> None:
        """Test that location is immutable."""
        loc = Location(file="main.py", line=10)
        with pytest.raises(Exception):  # pydantic frozen model
            loc.line = 20  # type: ignore

    @pytest.mark.unit
    def test_location_equality(self) -> None:
        """Test location equality based on values."""
        loc1 = Location(file="main.py", line=10, column=5)
        loc2 = Location(file="main.py", line=10, column=5)
        assert loc1 == loc2

    @pytest.mark.unit
    def test_location_invalid_line(self) -> None:
        """Test that line must be positive."""
        with pytest.raises(ValueError):
            Location(file="main.py", line=0)

    @pytest.mark.unit
    def test_location_invalid_column(self) -> None:
        """Test that column must be non-negative."""
        with pytest.raises(ValueError):
            Location(file="main.py", line=10, column=-1)

    @pytest.mark.unit
    def test_location_str(self) -> None:
        """Test location string representation."""
        loc = Location(file="main.py", line=10, column=5)
        assert str(loc) == "main.py:10:5"


class TestVersion:
    """Test Version value object (semver)."""

    @pytest.mark.unit
    def test_version_creation(self) -> None:
        """Test creating a valid version."""
        ver = Version(major=1, minor=2, patch=3)
        assert ver.major == 1
        assert ver.minor == 2
        assert ver.patch == 3

    @pytest.mark.unit
    def test_version_from_string(self) -> None:
        """Test parsing version from string."""
        ver = Version.from_string("1.2.3")
        assert ver.major == 1
        assert ver.minor == 2
        assert ver.patch == 3

    @pytest.mark.unit
    def test_version_from_string_with_v_prefix(self) -> None:
        """Test parsing version with 'v' prefix."""
        ver = Version.from_string("v1.2.3")
        assert ver.major == 1
        assert ver.minor == 2
        assert ver.patch == 3

    @pytest.mark.unit
    def test_version_from_string_with_prerelease(self) -> None:
        """Test parsing version with prerelease."""
        ver = Version.from_string("1.2.3-alpha.1")
        assert ver.major == 1
        assert ver.minor == 2
        assert ver.patch == 3
        assert ver.prerelease == "alpha.1"

    @pytest.mark.unit
    def test_version_str(self) -> None:
        """Test version string representation."""
        ver = Version(major=1, minor=2, patch=3)
        assert str(ver) == "1.2.3"

    @pytest.mark.unit
    def test_version_str_with_prerelease(self) -> None:
        """Test version string with prerelease."""
        ver = Version(major=1, minor=2, patch=3, prerelease="alpha.1")
        assert str(ver) == "1.2.3-alpha.1"

    @pytest.mark.unit
    def test_version_comparison(self) -> None:
        """Test version comparison."""
        v1 = Version(major=1, minor=0, patch=0)
        v2 = Version(major=2, minor=0, patch=0)
        v3 = Version(major=1, minor=1, patch=0)
        assert v1 < v2
        assert v1 < v3
        assert v2 > v3

    @pytest.mark.unit
    def test_version_equality(self) -> None:
        """Test version equality."""
        v1 = Version(major=1, minor=2, patch=3)
        v2 = Version(major=1, minor=2, patch=3)
        assert v1 == v2

    @pytest.mark.unit
    def test_version_invalid_string(self) -> None:
        """Test invalid version string."""
        with pytest.raises(ValueError):
            Version.from_string("invalid")


class TestEntityId:
    """Test EntityId value object."""

    @pytest.mark.unit
    def test_entity_id_creation(self) -> None:
        """Test creating an entity ID."""
        eid = EntityId(value="func_001")
        assert eid.value == "func_001"

    @pytest.mark.unit
    def test_entity_id_generate(self) -> None:
        """Test generating a unique entity ID."""
        eid1 = EntityId.generate()
        eid2 = EntityId.generate()
        assert eid1 != eid2

    @pytest.mark.unit
    def test_entity_id_equality(self) -> None:
        """Test entity ID equality."""
        eid1 = EntityId(value="func_001")
        eid2 = EntityId(value="func_001")
        assert eid1 == eid2

    @pytest.mark.unit
    def test_entity_id_hash(self) -> None:
        """Test entity ID can be used as dict key."""
        eid = EntityId(value="func_001")
        d = {eid: "test"}
        assert d[EntityId(value="func_001")] == "test"


class TestLibraryId:
    """Test LibraryId value object."""

    @pytest.mark.unit
    def test_library_id_creation(self) -> None:
        """Test creating a library ID."""
        lid = LibraryId(value="requests")
        assert lid.value == "requests"

    @pytest.mark.unit
    def test_library_id_from_name_version(self) -> None:
        """Test creating library ID from name and version."""
        lid = LibraryId.from_name_version("requests", "2.31.0")
        assert "requests" in lid.value
        assert "2.31.0" in lid.value

    @pytest.mark.unit
    def test_library_id_equality(self) -> None:
        """Test library ID equality."""
        lid1 = LibraryId(value="requests")
        lid2 = LibraryId(value="requests")
        assert lid1 == lid2
