import os
import logging
from pathlib import Path

import pikepdf

import pdf_remove_password
from pdf_remove_password import process_file, remove_password


def test_output_preserves_source_modification_time(tmp_path: Path) -> None:
    source = tmp_path / "documento (senha).pdf"
    destination = tmp_path / "documento.pdf"
    password = "senha"

    with pikepdf.new() as pdf:
        pdf.add_blank_page(page_size=(100, 100))
        pdf.save(source, encryption=pikepdf.Encryption(user=password, owner="proprietario", R=4))

    expected_mtime_ns = 1_700_000_000_123_456_700
    os.utime(source, ns=(expected_mtime_ns, expected_mtime_ns))

    remove_password(source, destination, password)

    assert destination.stat().st_mtime_ns == source.stat().st_mtime_ns


def test_invalid_password_is_handled_without_exposing_it(tmp_path: Path, caplog) -> None:
    password = "senha-correta"
    supplied_password = "senha-incorreta"
    source = tmp_path / f"documento ({supplied_password}).pdf"

    with pikepdf.new() as pdf:
        pdf.add_blank_page(page_size=(100, 100))
        pdf.save(source, encryption=pikepdf.Encryption(user=password, owner="proprietario", R=4))

    logger = logging.getLogger("test_invalid_password")
    with caplog.at_level(logging.INFO, logger=logger.name):
        result = process_file(source, dry_run=False, logger=logger)

    assert result == "failed_password"
    assert source.exists()
    assert not (tmp_path / "documento.pdf").exists()
    assert supplied_password not in caplog.text
    assert "documento (...).pdf" in caplog.text


def test_protected_pdf_without_password_in_name_generates_warning(tmp_path: Path, caplog) -> None:
    source = tmp_path / "documento-protegido.pdf"
    with pikepdf.new() as pdf:
        pdf.add_blank_page(page_size=(100, 100))
        pdf.save(source, encryption=pikepdf.Encryption(user="senha", owner="proprietario", R=4))

    logger = logging.getLogger("test_protected_without_named_password")
    with caplog.at_level(logging.INFO, logger=logger.name):
        result = process_file(source, dry_run=False, logger=logger)

    assert result == "ignored_protected_without_password_name"
    assert "arquivo_protegido_sem_senha_no_nome arquivo=documento-protegido.pdf" in caplog.text
    assert source.exists()


def test_unprotected_pdf_with_parentheses_is_ignored_before_destination_check(tmp_path: Path, caplog) -> None:
    source = tmp_path / "documento (nao-e-senha).pdf"
    destination = tmp_path / "documento.pdf"
    destination.write_bytes(b"destino existente")
    with pikepdf.new() as pdf:
        pdf.add_blank_page(page_size=(100, 100))
        pdf.save(source)

    logger = logging.getLogger("test_unprotected_with_parentheses")
    with caplog.at_level(logging.INFO, logger=logger.name):
        result = process_file(source, dry_run=False, logger=logger)

    assert result == "ignored_not_protected"
    assert "ignorado_pdf_sem_senha arquivo=documento (...).pdf" in caplog.text
    assert source.exists()
    assert destination.read_bytes() == b"destino existente"


def test_uses_earlier_named_password_after_windows_numeric_suffix(tmp_path: Path) -> None:
    password = "senha-correta"
    source = tmp_path / f"documento ({password})(1).pdf"
    destination = tmp_path / "documento (1).pdf"
    logger = logging.getLogger("test_windows_suffix_password")
    with pikepdf.new() as pdf:
        pdf.add_blank_page(page_size=(100, 100))
        pdf.save(source, encryption=pikepdf.Encryption(user=password, owner="proprietario", R=4))

    result = process_file(source, dry_run=False, logger=logger)

    assert result == "processed"
    assert destination.exists()
    assert not source.exists()


def test_invalid_xmp_metadata_is_logged_as_warning_and_ignored(tmp_path: Path, caplog, monkeypatch) -> None:
    source = tmp_path / "documento (senha).pdf"
    source.write_bytes(b"conteudo-de-teste")

    def raise_invalid_xmp(*args, **kwargs):
        raise ValueError("Metadata seems to be XML but not XMP")

    monkeypatch.setattr(pdf_remove_password.pikepdf, "open", raise_invalid_xmp)
    logger = logging.getLogger("test_invalid_xmp_metadata")
    with caplog.at_level(logging.INFO, logger=logger.name):
        result = process_file(source, dry_run=False, logger=logger)

    assert result == "ignored_invalid_xmp_metadata"
    assert "metadados_xmp_invalidos arquivo=documento (...).pdf" in caplog.text
    assert source.exists()
