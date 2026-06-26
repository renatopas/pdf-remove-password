"""Remove a senha de PDFs autorizados, usando senhas explicitamente fornecidas."""

from __future__ import annotations

import argparse
import logging
import re
import shutil
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

import pikepdf


ORIGINALS_DIRECTORY = "originais-protegidos"
DEFAULT_LOG_FILENAME = "remove-senha-pdf.log"
INVALID_XMP_METADATA_MESSAGE = "Metadata seems to be XML but not XMP"
AUTHORIZED_PASSWORDS_LIMIT = 10
FALLBACK_OUTPUT_SUFFIX = "-sem-senha"


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
) -> str:
    """Processa um PDF e retorna um código de resultado seguro para logs."""
    log_name = safe_log_filename(source.name)
    if dry_run:
        # Não abrir o arquivo evita inclusive possível atualização de atime.
        logger.info("simulacao_inspecao_protecao arquivo=%s", log_name)
        return "dry_run"

    protection_status = inspect_pdf_protection(source, log_name, logger)
    if protection_status == "failed_inspection":
        return protection_status
    if protection_status == "ignored_invalid_xmp_metadata":
        return protection_status
    if protection_status == "not_protected":
        logger.info("ignorado_pdf_sem_senha arquivo=%s", log_name)
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
    args = build_parser().parse_args(argv)
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

    results: Counter[str] = Counter()
    for source in iter_pdfs(folder, args.recursive):
        results[
            process_file(
                source,
                dry_run=args.dry_run,
                logger=logger,
                authorized_passwords=authorized_passwords,
            )
        ] += 1

    logger.info("resumo: %s", ", ".join(f"{key}={value}" for key, value in sorted(results.items())) or "nenhum_pdf")
    return 0


if __name__ == "__main__":
    sys.exit(main())
