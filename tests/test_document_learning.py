import pytest

from anka.core.errors import FileProcessingError
from anka.files.learning import DocumentLearner


def test_txt_reading_and_relevance(tmp_path):
    path = tmp_path / "not.txt"
    path.write_text("ANKA güvenli görev onayı ile çalışır. Hafıza kalıcıdır.", encoding="utf-8")
    name, content = DocumentLearner().read(str(path))
    assert name == "not.txt"
    assert "görev" in DocumentLearner().relevant_excerpt(content, "görev onayı")


def test_unsupported_file_is_rejected(tmp_path):
    path = tmp_path / "bad.exe"
    path.write_bytes(b"x")
    with pytest.raises(FileProcessingError):
        DocumentLearner().read(str(path))


def test_corrupt_pdf_is_reported_without_parser_details(tmp_path):
    path = tmp_path / "bozuk.pdf"
    path.write_bytes(b"bu bir pdf degil")

    with pytest.raises(FileProcessingError) as error:
        DocumentLearner().read(str(path))

    assert "Traceback" not in str(error.value)
