"""Remove a senha de PDFs autorizados, usando senhas explicitamente fornecidas."""

from __future__ import annotations

import argparse
import contextlib
import importlib.util
import logging
import os
import re
import shutil
import sys
import tempfile
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterator, MutableMapping

import pikepdf


ORIGINALS_DIRECTORY = "originais-protegidos"
DEFAULT_LOG_FILENAME = "remove-senha-pdf.log"
INVALID_XMP_METADATA_MESSAGE = "Metadata seems to be XML but not XMP"
AUTHORIZED_PASSWORDS_LIMIT = 10
FALLBACK_OUTPUT_SUFFIX = "-sem-senha"
TESSDATA_ENV = "TESSDATA_PREFIX"
MarkdownConverter = Callable[[Path], str]


class MarkdownEnvironmentError(RuntimeError):
    """Falha de configuração com código seguro para registro."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class FilenameInfo:
    """Dados derivados de um nome de PDF, sem registrar a senha."""

    password: str
    output_name: str


def extract_password_candidates(filename: str) -> list[FilenameInfo]:
    """Retorna grupos de parênteses como candidatas explícitas, da esquerda à direita.

    Cada candidata inclui o nome de saída correspondente à remoção daquele
    grupo específico. Não são geradas nem adivinhadas senhas.
    """
    path = Path(filename)
    if path.suffix.lower() != ".pdf":
        return []

    stem = path.stem
    groups = list(re.finditer(r"\(([^()]*)\)", stem))
    if not groups:
        return []

    candidates: list[FilenameInfo] = []
    for group in groups:
        password = group.group(1)
        if not password:
            continue
        before = stem[: group.start()]
        after = stem[group.end() :]
        if before[-1:].isspace() and after[:1].isspace():
            after = after.lstrip()
        output_stem = (before + after).strip()
        if output_stem:
            candidates.append(FilenameInfo(password=password, output_name=f"{output_stem}{path.suffix}"))
    return candidates


def extract_password_and_output_name(filename: str) -> FilenameInfo | None:
    """Retorna o último grupo de parênteses antes de `.pdf`."""
    candidates = extract_password_candidates(filename)
    return candidates[-1] if candidates else None


def try_passwords_for_destination(
    source: Path,
    destination: Path,
    passwords: tuple[str, ...],
    *,
    log_name: str,
    logger: logging.Logger,
) -> str:
    """Tenta senhas já fornecidas para um destino específico, sem expor valores."""
    for password in passwords:
        try:
            remove_password(source, destination, password)
        except pikepdf.PasswordError:
            # A próxima tentativa, se houver, será outra senha explicitamente fornecida.
            continue
        except (pikepdf.PdfError, OSError, ValueError, RuntimeError) as error:
            # Não registrar a exceção: bibliotecas podem incluir dados sensíveis nela.
            if destination.exists():
                try:
                    destination.unlink()
                except OSError:
                    pass
            if is_invalid_xmp_metadata_error(error):
                logger.warning("metadados_xmp_invalidos arquivo=%s", log_name)
                return "ignored_invalid_xmp_metadata"
            logger.error("falha_ao_abrir_ou_salvar_pdf arquivo=%s", log_name)
            return "failed_copy"

        return "password_matched"

    return "password_failed"


def fallback_output_name(filename: str) -> str:
    """Calcula um nome de saída quando a senha não veio do nome do arquivo."""
    path = Path(filename)
    return f"{path.stem}{FALLBACK_OUTPUT_SUFFIX}{path.suffix}"


def markdown_output_path(pdf_path: Path) -> Path:
    """Calcula o destino Markdown a partir da cópia descriptografada."""
    return pdf_path.with_suffix(".md")


def validate_markdown_environment(*, require_ocr: bool = False) -> Path | None:
    """Valida PyMuPDF4LLM e, quando solicitado, o ambiente do Tesseract."""
    if importlib.util.find_spec("pymupdf") is None:
        raise MarkdownEnvironmentError("pymupdf_nao_instalado")
    if importlib.util.find_spec("pymupdf4llm") is None:
        raise MarkdownEnvironmentError("pymupdf4llm_nao_instalado")

    if not require_ocr:
        return None

    tesseract_executable = shutil.which("tesseract")
    if tesseract_executable is None:
        raise MarkdownEnvironmentError("tesseract_nao_instalado_ou_fora_do_path")

    configured_tessdata = os.environ.get(TESSDATA_ENV)
    tessdata_path = (
        Path(configured_tessdata).expanduser()
        if configured_tessdata
        else Path(tesseract_executable).resolve().parent / "tessdata"
    )
    if not tessdata_path.is_dir():
        raise MarkdownEnvironmentError("tessdata_nao_encontrado")
    if not (tessdata_path / "por.traineddata").is_file():
        raise MarkdownEnvironmentError("tessdata_portugues_nao_instalado")
    if not (tessdata_path / "eng.traineddata").is_file():
        raise MarkdownEnvironmentError("tessdata_ingles_nao_instalado")
    return tessdata_path


def build_pymupdf_converter(
    tessdata_path: Path | None, *, use_ocr: bool = False
) -> MarkdownConverter:
    """Cria conversor local; OCR seletivo só é habilitado explicitamente."""
    # Import tardio mantém a dependência opcional fora do fluxo padrão e do
    # modo --dry-run. PyMuPDF usa TESSDATA_PREFIX para localizar idiomas.
    if use_ocr and tessdata_path is not None:
        os.environ[TESSDATA_ENV] = str(tessdata_path)
    import pymupdf4llm

    def convert(pdf_path: Path) -> str:
        # Algumas versões emitem diagnósticos diretamente em stdout/stderr.
        # Descartá-los evita ruído e possível exposição de conteúdo documental.
        with open(os.devnull, "w", encoding="utf-8") as sink:
            with contextlib.redirect_stdout(sink), contextlib.redirect_stderr(sink):
                return pymupdf4llm.to_markdown(
                    str(pdf_path),
                    use_ocr=use_ocr,
                    force_ocr=False,
                    **({"ocr_language": "por+eng"} if use_ocr else {}),
                )

    return convert


def pymupdf_markdown_converter(*, use_ocr: bool = False) -> MarkdownConverter:
    """Retorna função que inicializa o PyMuPDF4LLM somente no primeiro uso."""
    converter = None

    def convert(pdf_path: Path) -> str:
        nonlocal converter
        if converter is None:
            tessdata_path = validate_markdown_environment(require_ocr=use_ocr)
            converter = build_pymupdf_converter(tessdata_path, use_ocr=use_ocr)
        return converter(pdf_path)

    return convert


def create_markdown_atomically(
    pdf_path: Path,
    converter: MarkdownConverter,
    *,
    log_name: str,
    logger: logging.Logger,
) -> str:
    """Converte e publica Markdown completo sem sobrescrever o destino."""
    destination = markdown_output_path(pdf_path)
    if destination.exists():
        logger.warning("colisao_destino_markdown arquivo=%s", log_name)
        return "markdown_collision"

    temporary_path: Path | None = None
    try:
        logger.info("geracao_markdown_iniciada arquivo=%s", log_name)
        markdown = converter(pdf_path)
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            prefix=f".{destination.name}.",
            suffix=".tmp",
            dir=destination.parent,
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)
            temporary.write(markdown)
            temporary.flush()
            os.fsync(temporary.fileno())

        # O link é criado atomicamente e falha se outro processo tiver criado o
        # destino entre a verificação inicial e a publicação.
        os.link(temporary_path, destination)
        temporary_path.unlink()
        logger.info("markdown_criado arquivo=%s", log_name)
        return "markdown_created"
    except FileExistsError:
        logger.warning("colisao_destino_markdown arquivo=%s", log_name)
        return "markdown_collision"
    except MarkdownEnvironmentError as error:
        if error.code.startswith("tesseract_"):
            logger.error("ocr_indisponivel arquivo=%s", log_name)
        else:
            logger.error("ambiente_markdown_indisponivel arquivo=%s", log_name)
        return "markdown_failed"
    except Exception:
        # Bibliotecas de extração podem incluir conteúdo na exceção. Por arquivo,
        # registrar somente um código seguro e continuar o lote.
        logger.error("falha_geracao_markdown arquivo=%s", log_name)
        return "markdown_failed"
    finally:
        if temporary_path is not None and temporary_path.exists():
            try:
                temporary_path.unlink()
            except OSError:
                logger.error("residuo_temporario_markdown arquivo=%s", log_name)


def read_authorized_passwords(path: Path, *, limit: int = AUTHORIZED_PASSWORDS_LIMIT) -> tuple[str, ...]:
    """Lê uma lista curta de senhas autorizadas sem registrar seu conteúdo."""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as error:
        raise ValueError("arquivo_de_senhas_inexistente_ou_ilegivel") from error

    passwords: list[str] = []
    for line in lines:
        candidate = line.strip()
        if not candidate or candidate.startswith("#"):
            continue
        passwords.append(candidate)
        if len(passwords) > limit:
            raise ValueError("arquivo_de_senhas_acima_do_limite")

    if not passwords:
        raise ValueError("arquivo_de_senhas_vazio")

    return tuple(passwords)


def iter_pdfs(folder: Path, recursive: bool) -> Iterator[Path]:
    """Lista PDFs, excluindo sempre as pastas que contêm os originais movidos."""
    iterator = folder.rglob("*") if recursive else folder.iterdir()
    for item in iterator:
        if (
            item.is_file()
            and item.suffix.lower() == ".pdf"
            and ORIGINALS_DIRECTORY not in item.parts
        ):
            yield item


def remove_password(source: Path, destination: Path, password: str) -> None:
    """Salva uma cópia sem criptografia usando uma única senha já fornecida."""
    with pikepdf.open(source, password=password) as pdf:
        pdf.save(destination)

    # Preserve metadados de tempo (incluindo mtime e, quando suportado, atime)
    # somente após a cópia ter sido salva com sucesso. Isso não altera a origem.
    shutil.copystat(source, destination)

    # Confirma que a cópia é aberta sem senha antes de mover o original.
    with pikepdf.open(destination):
        pass


def is_invalid_xmp_metadata_error(error: BaseException) -> bool:
    """Identifica a mensagem conhecida de metadados XML que não são XMP."""
    return INVALID_XMP_METADATA_MESSAGE in str(error)


def inspect_pdf_protection(source: Path, log_name: str, logger: logging.Logger) -> str:
    """Verifica se o PDF exige senha sem tentar nenhuma senha fornecida."""
    try:
        with pikepdf.open(source):
            pass
    except pikepdf.PasswordError:
        return "protected"
    except (pikepdf.PdfError, OSError, ValueError, RuntimeError) as error:
        if is_invalid_xmp_metadata_error(error):
            logger.warning("metadados_xmp_invalidos arquivo=%s", log_name)
            return "ignored_invalid_xmp_metadata"
        logger.error("falha_ao_inspecionar_pdf arquivo=%s", log_name)
        return "failed_inspection"

    return "not_protected"


def safe_log_filename(filename: str) -> str:
    """Mantém o nome identificável, ocultando conteúdos entre parênteses."""
    path = Path(filename)
    redacted_stem = re.sub(r"\([^()]*\)", "(...)", path.stem)
    return f"{redacted_stem}{path.suffix}"


def process_file(
    source: Path,
    *,
    dry_run: bool,
    logger: logging.Logger,
    authorized_passwords: tuple[str, ...] = (),
    markdown_converter: MarkdownConverter | None = None,
    markdown_results: MutableMapping[str, int] | None = None,
) -> str:
    """Processa um PDF e retorna um código de resultado seguro para logs."""
    log_name = safe_log_filename(source.name)
    if dry_run:
        # Não abrir o arquivo evita inclusive possível atualização de atime.
        logger.info("simulacao_inspecao_protecao arquivo=%s", log_name)
        if markdown_converter is not None:
            logger.info("simulacao_markdown_habilitado arquivo=%s", log_name)
            if markdown_results is not None:
                markdown_results["markdown_dry_run"] = markdown_results.get("markdown_dry_run", 0) + 1
        return "dry_run"

    protection_status = inspect_pdf_protection(source, log_name, logger)
    if protection_status == "failed_inspection":
        return protection_status
    if protection_status == "ignored_invalid_xmp_metadata":
        return protection_status
    if protection_status == "not_protected":
        logger.info("ignorado_pdf_sem_senha arquivo=%s", log_name)
        if markdown_converter is not None:
            markdown_status = create_markdown_atomically(
                source, markdown_converter, log_name=log_name, logger=logger
            )
            if markdown_results is not None:
                markdown_results[markdown_status] = markdown_results.get(markdown_status, 0) + 1
        return "ignored_not_protected"

    named_candidates = extract_password_candidates(source.name)
    if not named_candidates and not authorized_passwords:
        logger.warning("arquivo_protegido_sem_senha_no_nome arquivo=%s", log_name)
        return "ignored_protected_without_password_name"

    original_directory = source.parent / ORIGINALS_DIRECTORY
    moved_original = original_directory / source.name
    if moved_original.exists():
        logger.warning("ignorado_colisao_original arquivo=%s", log_name)
        return "ignored_original_collision"

    had_destination_collision = False
    for info in reversed(named_candidates):
        destination = source.with_name(info.output_name)
        if destination.exists():
            logger.warning("ignorado_colisao_destino arquivo=%s", log_name)
            had_destination_collision = True
            continue

        password_status = try_passwords_for_destination(
            source,
            destination,
            (info.password,),
            log_name=log_name,
            logger=logger,
        )
        if password_status == "password_failed":
            continue
        if password_status != "password_matched":
            return password_status

        try:
            original_directory.mkdir(exist_ok=True)
            shutil.move(str(source), str(moved_original))
        except OSError:
            logger.error("falha_ao_mover_original arquivo=%s", log_name)
            return "failed_move"

        logger.info("copia_criada_e_original_movido arquivo=%s", log_name)
        if markdown_converter is not None:
            markdown_status = create_markdown_atomically(
                destination, markdown_converter, log_name=log_name, logger=logger
            )
            if markdown_results is not None:
                markdown_results[markdown_status] = markdown_results.get(markdown_status, 0) + 1
        return "processed"

    if authorized_passwords:
        fallback_name = named_candidates[-1].output_name if named_candidates else fallback_output_name(source.name)
        destination = source.with_name(fallback_name)
        if destination.exists():
            logger.warning("ignorado_colisao_destino arquivo=%s", log_name)
            return "ignored_destination_collision"

        password_status = try_passwords_for_destination(
            source,
            destination,
            authorized_passwords,
            log_name=log_name,
            logger=logger,
        )
        if password_status == "password_failed":
            logger.error("senha_invalida_para_credenciais_fornecidas arquivo=%s", log_name)
            return "failed_password"
        if password_status != "password_matched":
            return password_status

        try:
            original_directory.mkdir(exist_ok=True)
            shutil.move(str(source), str(moved_original))
        except OSError:
            logger.error("falha_ao_mover_original arquivo=%s", log_name)
            return "failed_move"

        logger.info("copia_criada_e_original_movido arquivo=%s", log_name)
        if markdown_converter is not None:
            markdown_status = create_markdown_atomically(
                destination, markdown_converter, log_name=log_name, logger=logger
            )
            if markdown_results is not None:
                markdown_results[markdown_status] = markdown_results.get(markdown_status, 0) + 1
        return "processed"

    if had_destination_collision:
        return "ignored_destination_collision"

    logger.error("senha_invalida_para_credenciais_fornecidas arquivo=%s", log_name)
    return "failed_password"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Remove a senha de PDFs autorizados usando senhas explicitamente fornecidas."
    )
    parser.add_argument("folder", type=Path, help="Pasta que contém os PDFs")
    parser.add_argument("--recursive", action="store_true", help="Inclui subpastas")
    parser.add_argument("--dry-run", action="store_true", help="Não altera arquivos ou diretórios")
    parser.add_argument("--log-file", type=Path, help="Arquivo opcional de log")
    parser.add_argument(
        "--authorized-passwords",
        type=Path,
        help="Arquivo opcional com lista curta de senhas autorizadas, uma por linha",
    )
    parser.add_argument(
        "--markdown",
        action="store_true",
        help="Gera Markdown localmente com PyMuPDF4LLM para todo PDF legível",
    )
    parser.add_argument(
        "-ocr",
        "--ocr",
        action="store_true",
        help="Habilita OCR seletivo na geração de Markdown (requer --markdown)",
    )
    return parser


def configure_logging(log_file: Path | None) -> logging.Logger:
    logger = logging.getLogger("pdf_remove_password")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    console = logging.StreamHandler()
    console.setFormatter(formatter)
    logger.addHandler(console)
    if log_file:
        handler = logging.FileHandler(log_file, encoding="utf-8")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.ocr and not args.markdown:
        parser.error("--ocr requer --markdown")
    folder = args.folder.expanduser()
    if not folder.is_dir():
        logger = configure_logging(None if args.dry_run else args.log_file)
        logger.error("a_pasta_informada_nao_existe_ou_nao_e_um_diretorio")
        return 2

    # Sem --log-file, o registro padrão pertence à própria pasta processada.
    # FileHandler usa modo append por padrão, preservando ocorrências anteriores.
    # Em --dry-run, não criar nem alterar arquivos de log.
    log_file = None if args.dry_run else args.log_file or folder / DEFAULT_LOG_FILENAME
    logger = configure_logging(log_file)

    authorized_passwords: tuple[str, ...] = ()
    if args.authorized_passwords:
        try:
            authorized_passwords = read_authorized_passwords(args.authorized_passwords.expanduser())
        except ValueError as error:
            logger.error("%s arquivo=%s", str(error), args.authorized_passwords)
            return 2

    markdown_converter: MarkdownConverter | None = None
    if args.markdown:
        if args.dry_run:
            # Sentinela que sinaliza a intenção sem importar o conversor nem executar OCR.
            markdown_converter = lambda _path: ""
        else:
            markdown_converter = pymupdf_markdown_converter(use_ocr=args.ocr)

    results: Counter[str] = Counter()
    markdown_results: Counter[str] = Counter()
    for source in iter_pdfs(folder, args.recursive):
        results[
            process_file(
                source,
                dry_run=args.dry_run,
                logger=logger,
                authorized_passwords=authorized_passwords,
                markdown_converter=markdown_converter,
                markdown_results=markdown_results,
            )
        ] += 1

    logger.info("resumo: %s", ", ".join(f"{key}={value}" for key, value in sorted(results.items())) or "nenhum_pdf")
    if args.markdown:
        logger.info(
            "resumo_markdown: %s",
            ", ".join(f"{key}={value}" for key, value in sorted(markdown_results.items()))
            or "nenhum_markdown",
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
