from pathlib import Path

from tools import read_file, write_file


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