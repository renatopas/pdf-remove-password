import os
import logging
from pathlib import Path

import pikepdf
import pytest

import pdf_remove_password
from pdf_remove_password import main, process_file, read_authorized_passwords, remove_password


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


def test_read_authorized_passwords_ignores_blank_lines_and_comments(tmp_path: Path) -> None:
    password_file = tmp_path / "senhas.txt"
    password_file.write_text("\n  # comentario\n  primeira  \nsegunda\n", encoding="utf-8")

    assert read_authorized_passwords(password_file) == ("primeira", "segunda")


def test_read_authorized_passwords_rejects_empty_and_oversized_lists(tmp_path: Path) -> None:
    empty_file = tmp_path / "vazio.txt"
    empty_file.write_text("\n# comentario\n", encoding="utf-8")
    oversized_file = tmp_path / "muitas.txt"
    oversized_file.write_text("\n".join(f"senha-{index}" for index in range(11)), encoding="utf-8")

    with pytest.raises(ValueError, match="arquivo_de_senhas_vazio"):
        read_authorized_passwords(empty_file)
    with pytest.raises(ValueError, match="arquivo_de_senhas_acima_do_limite"):
        read_authorized_passwords(oversized_file)
    with pytest.raises(ValueError, match="arquivo_de_senhas_inexistente_ou_ilegivel"):
        read_authorized_passwords(tmp_path / "ausente.txt")


def test_authorized_passwords_fallback_without_password_in_name(tmp_path: Path, caplog) -> None:
    password = "senha-correta"
    wrong_password = "senha-incorreta"
    source = tmp_path / "documento-protegido.pdf"
    destination = tmp_path / "documento-protegido-sem-senha.pdf"
    logger = logging.getLogger("test_authorized_passwords_without_name")
    with pikepdf.new() as pdf:
        pdf.add_blank_page(page_size=(100, 100))
        pdf.save(source, encryption=pikepdf.Encryption(user=password, owner="proprietario", R=4))

    with caplog.at_level(logging.INFO, logger=logger.name):
        result = process_file(
            source,
            dry_run=False,
            logger=logger,
            authorized_passwords=(wrong_password, password),
        )

    assert result == "processed"
    assert destination.exists()
    assert not source.exists()
    assert password not in caplog.text
    assert wrong_password not in caplog.text


def test_authorized_passwords_fallback_after_named_password_fails(tmp_path: Path, caplog) -> None:
    password = "senha-correta"
    named_password = "senha-errada"
    source = tmp_path / f"documento ({named_password}).pdf"
    destination = tmp_path / "documento.pdf"
    logger = logging.getLogger("test_authorized_passwords_after_name")
    with pikepdf.new() as pdf:
        pdf.add_blank_page(page_size=(100, 100))
        pdf.save(source, encryption=pikepdf.Encryption(user=password, owner="proprietario", R=4))

    with caplog.at_level(logging.INFO, logger=logger.name):
        result = process_file(source, dry_run=False, logger=logger, authorized_passwords=(password,))

    assert result == "processed"
    assert destination.exists()
    assert not source.exists()
    assert password not in caplog.text
    assert named_password not in caplog.text
    assert "documento (...).pdf" in caplog.text


def test_authorized_passwords_fallback_after_all_named_groups_fail(tmp_path: Path, caplog) -> None:
    password = "senha-correta"
    source = tmp_path / "documento (errada)(1).pdf"
    destination = tmp_path / "documento (errada).pdf"
    logger = logging.getLogger("test_authorized_passwords_after_all_groups")
    with pikepdf.new() as pdf:
        pdf.add_blank_page(page_size=(100, 100))
        pdf.save(source, encryption=pikepdf.Encryption(user=password, owner="proprietario", R=4))

    with caplog.at_level(logging.INFO, logger=logger.name):
        result = process_file(source, dry_run=False, logger=logger, authorized_passwords=(password,))

    assert result == "processed"
    assert destination.exists()
    assert not source.exists()
    assert password not in caplog.text
    assert "errada" not in caplog.text


def test_named_password_candidates_are_tried_right_to_left(tmp_path: Path, monkeypatch) -> None:
    source = tmp_path / "documento (primeira)(segunda)(terceira).pdf"
    source.write_bytes(b"pdf")
    logger = logging.getLogger("test_named_candidates_order")
    attempts: list[tuple[str, str]] = []

    def fake_inspect_pdf_protection(source: Path, log_name: str, logger: logging.Logger) -> str:
        return "protected"

    def fake_remove_password(source: Path, destination: Path, password: str) -> None:
        attempts.append((password, destination.name))
        if password == "segunda":
            destination.write_bytes(b"sem senha")
            return
        raise pikepdf.PasswordError("senha invalida")

    def fake_move(source_path: str, destination_path: str) -> None:
        Path(destination_path).parent.mkdir(exist_ok=True)
        Path(source_path).rename(destination_path)

    monkeypatch.setattr(pdf_remove_password, "inspect_pdf_protection", fake_inspect_pdf_protection)
    monkeypatch.setattr(pdf_remove_password, "remove_password", fake_remove_password)
    monkeypatch.setattr(pdf_remove_password.shutil, "move", fake_move)

    result = process_file(source, dry_run=False, logger=logger)

    assert result == "processed"
    assert attempts == [
        ("terceira", "documento (primeira)(segunda).pdf"),
        ("segunda", "documento (primeira)(terceira).pdf"),
    ]


def test_destination_collision_for_one_named_candidate_continues_to_next(tmp_path: Path) -> None:
    password = "senha-correta"
    source = tmp_path / f"documento ({password})(1).pdf"
    colliding_destination = tmp_path / f"documento ({password}).pdf"
    final_destination = tmp_path / "documento (1).pdf"
    colliding_destination.write_bytes(b"destino existente")
    logger = logging.getLogger("test_candidate_collision_continues")
    with pikepdf.new() as pdf:
        pdf.add_blank_page(page_size=(100, 100))
        pdf.save(source, encryption=pikepdf.Encryption(user=password, owner="proprietario", R=4))

    result = process_file(source, dry_run=False, logger=logger)

    assert result == "processed"
    assert colliding_destination.read_bytes() == b"destino existente"
    assert final_destination.exists()
    assert not source.exists()


def test_stops_at_first_successful_authorized_password(tmp_path: Path, monkeypatch) -> None:
    source = tmp_path / "documento.pdf"
    source.write_bytes(b"pdf")
    logger = logging.getLogger("test_stops_at_first_success")
    attempts: list[str] = []

    def fake_inspect_pdf_protection(source: Path, log_name: str, logger: logging.Logger) -> str:
        return "protected"

    def fake_remove_password(source: Path, destination: Path, password: str) -> None:
        attempts.append(password)
        if password == "primeira":
            destination.write_bytes(b"sem senha")
            return
        raise pikepdf.PasswordError("senha invalida")

    def fake_move(source_path: str, destination_path: str) -> None:
        Path(destination_path).parent.mkdir(exist_ok=True)
        Path(source_path).rename(destination_path)

    monkeypatch.setattr(pdf_remove_password, "inspect_pdf_protection", fake_inspect_pdf_protection)
    monkeypatch.setattr(pdf_remove_password, "remove_password", fake_remove_password)
    monkeypatch.setattr(pdf_remove_password.shutil, "move", fake_move)

    result = process_file(
        source,
        dry_run=False,
        logger=logger,
        authorized_passwords=("errada", "primeira", "segunda"),
    )

    assert result == "processed"
    assert attempts == ["errada", "primeira"]


def test_dry_run_with_authorized_passwords_does_not_create_or_move_files(tmp_path: Path) -> None:
    password_file = tmp_path / "senhas.txt"
    password_file.write_text("senha-correta\n", encoding="utf-8")
    source = tmp_path / "documento.pdf"
    with pikepdf.new() as pdf:
        pdf.add_blank_page(page_size=(100, 100))
        pdf.save(source, encryption=pikepdf.Encryption(user="senha-correta", owner="proprietario", R=4))

    result = main([str(tmp_path), "--dry-run", "--authorized-passwords", str(password_file)])

    assert result == 0
    assert source.exists()
    assert not (tmp_path / "documento-sem-senha.pdf").exists()
    assert not (tmp_path / "originais-protegidos").exists()
    assert not (tmp_path / "remove-senha-pdf.log").exists()
