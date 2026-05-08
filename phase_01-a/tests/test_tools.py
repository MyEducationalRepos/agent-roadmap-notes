from pathlib import Path

import os

os.environ.setdefault("TAVILY_API_KEY", "test-key")

import tools
from tools import dispatch, read_file, web_search, write_file


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
    fake_client = mocker.MagicMock()
    fake_client.search.return_value = fake_response
    mocker.patch.object(tools, "_get_tavily", return_value=fake_client)

    result = web_search("anything")

    assert "T1" in result and "https://example.com/1" in result and "C1" in result
    assert "T2" in result


def test_web_search_api_error(mocker) -> None:
    fake_client = mocker.MagicMock()
    fake_client.search.side_effect = RuntimeError("boom")
    mocker.patch.object(tools, "_get_tavily", return_value=fake_client)

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


def test_dispatch_write_roundtrip(tmp_path: Path) -> None:
    target = tmp_path / "out.txt"

    result = dispatch("write_file", {"path": str(target), "content": "hi"}, "tu_1")

    assert result["type"] == "tool_result"
    assert result["tool_use_id"] == "tu_1"
    assert result["is_error"] is False
    assert target.read_text(encoding="utf-8") == "hi"


def test_dispatch_unknown() -> None:
    result = dispatch("nope", {}, "tu_2")

    assert result["is_error"] is True
    assert "unknown tool" in result["content"]
    assert result["tool_use_id"] == "tu_2"


def test_dispatch_exception(mocker) -> None:
    mocker.patch.object(tools, "read_file", side_effect=RuntimeError("kaboom"))
    mocker.patch.dict(tools._HANDLERS, {"read_file": tools.read_file})

    result = dispatch("read_file", {"path": "/x"}, "tu_3")

    assert result["is_error"] is True
    assert "tool raised" in result["content"]
    assert "kaboom" in result["content"]