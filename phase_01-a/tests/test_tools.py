from pathlib import Path

import os

os.environ.setdefault("TAVILY_API_KEY", "test-key")

import tools
from tools import read_file, web_search, write_file


def test_read_file_exists(tmp_path: Path) -> None:
    file_path = tmp_path / "fixture.txt"
    file_path.write_text("known content", encoding="utf-8")

    assert read_file(str(file_path)) == "known content"


def test_read_file_missing() -> None:
    result = read_file("/nonexistent/path.txt")

    assert result == "Error: file not found – /nonexistent/path.txt"


def test_read_file_binary(tmp_path: Path) -> None:
    file_path = tmp_path / "binary.bin"
    file_path.write_bytes(bytes([0x00, 0xFF]))

    assert read_file(str(file_path)) == "Error: not a text file"


def test_write_file_creates(tmp_path: Path) -> None:
    file_path = tmp_path / "created.txt"

    result = write_file(str(file_path), "saved content")

    assert result == f"OK: wrote file – {file_path}"
    assert file_path.read_text(encoding="utf-8") == "saved content"


def test_write_file_bad_dir(tmp_path: Path) -> None:
    file_path = tmp_path / "missing" / "created.txt"

    result = write_file(str(file_path), "saved content")

    assert result == f"Error: parent directory not found – {file_path.parent}"


def test_web_search_mock(mocker) -> None:
    fake_response = {
        "results": [
            {"title": "T1", "url": "https://example.com/1", "content": "C1"},
            {"title": "T2", "url": "https://example.com/2", "content": "C2"},
        ]
    }
    mocker.patch.object(tools._tavily, "search", return_value=fake_response)

    result = web_search("anything")

    assert "T1" in result and "https://example.com/1" in result and "C1" in result
    assert "T2" in result


def test_web_search_api_error(mocker) -> None:
    mocker.patch.object(tools._tavily, "search", side_effect=RuntimeError("boom"))

    result = web_search("anything")

    assert result == "Error: web search failed – boom"


def test_tools_schema() -> None:
    assert isinstance(tools.TOOLS, list)
    names = [t["name"] for t in tools.TOOLS]
    assert names == ["web_search", "read_file", "write_file"]
    for tool in tools.TOOLS:
        assert set(tool.keys()) >= {"name", "description", "input_schema"}
        schema = tool["input_schema"]
        assert schema["type"] == "object"
        assert "properties" in schema and "required" in schema
        for required_field in schema["required"]:
            assert required_field in schema["properties"]