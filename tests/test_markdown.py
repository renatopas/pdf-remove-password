import logging
from collections import Counter
from pathlib import Path

import pikepdf
import pymupdf4llm

import pdf_remove_password
from pdf_remove_password import create_markdown_atomically, main, markdown_output_path, process_file


def test_markdown_output_path_uses_decrypted_pdf_name(tmp_path: Path) -> None:
    assert markdown_output_path(tmp_path / "Contrato (rascunho).PDF") == (
        tmp_path / "Contrato (rascunho).md"
    )


def test_create_markdown_publishes_complete_utf8_file(tmp_path: Path) -> None:
    pdf_path = tmp_path / "documento.pdf"
    pdf_path.write_bytes(b"pdf")
    logger = logging.getLogger("test_markdown_success")

    result = create_markdown_atomically(
        pdf_path,
        lambda path: "# Título\n\nConteúdo em português.\n",
        log_name="documento.pdf",
        logger=logger,
    )

    assert result == "markdown_created"
    assert (tmp_path / "documento.md").read_text(encoding="utf-8") == (
        "# Título\n\nConteúdo em português.\n"
    )
    assert not list(tmp_path.glob(".documento.md.*.tmp"))


def test_markdown_collision_does_not_call_converter_or_overwrite(tmp_path: Path) -> None:
    pdf_path = tmp_path / "documento.pdf"
    destination = tmp_path / "documento.md"
    destination.write_text("existente", encoding="utf-8")
    called = False

    def converter(path: Path) -> str:
        nonlocal called
        called = True
        return "novo"

    result = create_markdown_atomically(
        pdf_path,
        converter,
        log_name="documento.pdf",
        logger=logging.getLogger("test_markdown_collision"),
    )

    assert result == "markdown_collision"
    assert destination.read_text(encoding="utf-8") == "existente"
    assert called is False


def test_markdown_conversion_failure_leaves_no_partial_file(tmp_path: Path, caplog) -> None:
    pdf_path = tmp_path / "documento.pdf"
    secret_content = "conteudo-documental-sensivel"

    def failing_converter(path: Path) -> str:
        raise RuntimeError(secret_content)

    logger = logging.getLogger("test_markdown_failure")
    with caplog.at_level(logging.INFO, logger=logger.name):
        result = create_markdown_atomically(
            pdf_path,
            failing_converter,
            log_name="documento.pdf",
            logger=logger,
        )

    assert result == "markdown_failed"
    assert not (tmp_path / "documento.md").exists()
    assert not list(tmp_path.glob(".documento.md.*.tmp"))
    assert secret_content not in caplog.text


def test_processed_pdf_generates_markdown_after_copy_is_validated(tmp_path: Path) -> None:
    password = "senha-correta"
    source = tmp_path / f"documento ({password}).pdf"
    decrypted = tmp_path / "documento.pdf"
    markdown_results: Counter[str] = Counter()
    converter_inputs: list[Path] = []

    with pikepdf.new() as pdf:
        pdf.add_blank_page(page_size=(100, 100))
        pdf.save(source, encryption=pikepdf.Encryption(user=password, owner="proprietario", R=4))

    def converter(path: Path) -> str:
        converter_inputs.append(path)
        with pikepdf.open(path):
            pass
        return "# Documento\n"

    result = process_file(
        source,
        dry_run=False,
        logger=logging.getLogger("test_markdown_process"),
        markdown_converter=converter,
        markdown_results=markdown_results,
    )

    assert result == "processed"
    assert converter_inputs == [decrypted]
    assert (tmp_path / "documento.md").read_text(encoding="utf-8") == "# Documento\n"
    assert markdown_results == Counter(markdown_created=1)
    assert not source.exists()
    assert (tmp_path / "originais-protegidos" / source.name).exists()


def test_markdown_failure_does_not_revert_processed_pdf(tmp_path: Path) -> None:
    password = "senha-correta"
    source = tmp_path / f"documento ({password}).pdf"
    decrypted = tmp_path / "documento.pdf"
    markdown_results: Counter[str] = Counter()

    with pikepdf.new() as pdf:
        pdf.add_blank_page(page_size=(100, 100))
        pdf.save(source, encryption=pikepdf.Encryption(user=password, owner="proprietario", R=4))

    def failing_converter(path: Path) -> str:
        raise pdf_remove_password.MarkdownEnvironmentError("tesseract_nao_instalado")

    result = process_file(
        source,
        dry_run=False,
        logger=logging.getLogger("test_markdown_failure_after_pdf"),
        markdown_converter=failing_converter,
        markdown_results=markdown_results,
    )

    assert result == "processed"
    assert decrypted.exists()
    assert not (tmp_path / "documento.md").exists()
    assert (tmp_path / "originais-protegidos" / source.name).exists()
    assert markdown_results == Counter(markdown_failed=1)


def test_pymupdf_converter_is_initialized_only_on_first_conversion(monkeypatch, tmp_path: Path) -> None:
    built: list[tuple[Path | None, bool]] = []
    converted: list[Path] = []
    artifacts = tmp_path / "modelos"

    def validate(*, require_ocr: bool = False) -> Path | None:
        return artifacts if require_ocr else None

    def build(path: Path | None, *, use_ocr: bool = False):
        built.append((path, use_ocr))
        def convert(pdf_path: Path) -> str:
            converted.append(pdf_path)
            return "# Conteúdo misto\n\nTexto nativo e OCR.\n"
        return convert

    monkeypatch.setattr(pdf_remove_password, "validate_markdown_environment", validate)
    monkeypatch.setattr(pdf_remove_password, "build_pymupdf_converter", build)
    converter = pdf_remove_password.pymupdf_markdown_converter()

    assert built == []
    assert converter(tmp_path / "primeiro.pdf").startswith("# Conteúdo misto")
    assert converter(tmp_path / "segundo.pdf").startswith("# Conteúdo misto")
    assert built == [(None, False)]
    assert converted == [tmp_path / "primeiro.pdf", tmp_path / "segundo.pdf"]


def test_pymupdf_converter_disables_ocr_by_default(
    monkeypatch, tmp_path: Path
) -> None:
    calls: list[tuple[str, dict]] = []

    def fake_to_markdown(path: str, **options) -> str:
        calls.append((path, options))
        return "texto nativo"

    monkeypatch.setattr(pymupdf4llm, "to_markdown", fake_to_markdown)
    converter = pdf_remove_password.build_pymupdf_converter(None)

    assert converter(tmp_path / "documento.pdf") == "texto nativo"
    assert calls == [
        (
            str(tmp_path / "documento.pdf"),
            {"use_ocr": False, "force_ocr": False},
        )
    ]


def test_pymupdf_converter_enables_selective_bilingual_ocr_explicitly(
    monkeypatch, tmp_path: Path, capsys
) -> None:
    calls: list[tuple[str, dict]] = []
    tessdata = tmp_path / "tessdata"

    def fake_to_markdown(path: str, **options) -> str:
        print("conteudo-que-nao-pode-vazar")
        calls.append((path, options))
        return "texto"

    monkeypatch.setattr(pymupdf4llm, "to_markdown", fake_to_markdown)
    converter = pdf_remove_password.build_pymupdf_converter(tessdata, use_ocr=True)

    assert converter(tmp_path / "documento.pdf") == "texto"
    assert calls == [
        (
            str(tmp_path / "documento.pdf"),
            {
                "use_ocr": True,
                "force_ocr": False,
                "ocr_language": "por+eng",
            },
        )
    ]
    assert "conteudo-que-nao-pode-vazar" not in capsys.readouterr().out


def test_ocr_requires_markdown(tmp_path: Path) -> None:
    import pytest

    with pytest.raises(SystemExit) as error:
        main([str(tmp_path), "--ocr"])

    assert error.value.code == 2


def test_unprotected_pdf_generates_markdown_without_decryption(tmp_path: Path) -> None:
    source = tmp_path / "documento.pdf"
    converter_inputs: list[Path] = []
    markdown_results: Counter[str] = Counter()
    with pikepdf.new() as pdf:
        pdf.add_blank_page(page_size=(100, 100))
        pdf.save(source)

    def converter(path: Path) -> str:
        converter_inputs.append(path)
        return "# Documento sem criptografia\n"

    result = process_file(
        source,
        dry_run=False,
        logger=logging.getLogger("test_unprotected_markdown"),
        markdown_converter=converter,
        markdown_results=markdown_results,
    )

    assert result == "ignored_not_protected"
    assert converter_inputs == [source]
    assert (tmp_path / "documento.md").read_text(encoding="utf-8") == (
        "# Documento sem criptografia\n"
    )
    assert markdown_results == Counter(markdown_created=1)
    assert source.exists()
    assert not (tmp_path / "originais-protegidos").exists()


def test_unprotected_pdf_markdown_collision_preserves_existing_file(tmp_path: Path) -> None:
    source = tmp_path / "documento.pdf"
    destination = tmp_path / "documento.md"
    destination.write_text("existente", encoding="utf-8")
    markdown_results: Counter[str] = Counter()
    with pikepdf.new() as pdf:
        pdf.add_blank_page(page_size=(100, 100))
        pdf.save(source)

    result = process_file(
        source,
        dry_run=False,
        logger=logging.getLogger("test_unprotected_markdown_collision"),
        markdown_converter=lambda path: "novo",
        markdown_results=markdown_results,
    )

    assert result == "ignored_not_protected"
    assert destination.read_text(encoding="utf-8") == "existente"
    assert markdown_results == Counter(markdown_collision=1)
    assert source.exists()


def test_dry_run_markdown_does_not_validate_or_initialize_converter(
    tmp_path: Path, monkeypatch
) -> None:
    source = tmp_path / "documento (senha).pdf"
    source.write_bytes(b"nao precisa ser aberto")

    def must_not_run(*args, **kwargs):
        raise AssertionError("O conversor não deve ser validado ou inicializado")

    monkeypatch.setattr(pdf_remove_password, "validate_markdown_environment", must_not_run)
    monkeypatch.setattr(pdf_remove_password, "pymupdf_markdown_converter", must_not_run)

    result = main([str(tmp_path), "--dry-run", "--markdown"])

    assert result == 0
    assert source.exists()
    assert not (tmp_path / "documento.md").exists()
    assert not (tmp_path / "remove-senha-pdf.log").exists()
    assert not (tmp_path / "originais-protegidos").exists()
