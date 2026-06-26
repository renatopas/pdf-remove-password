from pdf_remove_password import extract_password_and_output_name, extract_password_candidates


def test_uses_last_parentheses_group_as_password() -> None:
    result = extract_password_and_output_name("Contrato (rascunho) (Senha123).pdf")

    assert result is not None
    assert result.password == "Senha123"
    assert result.output_name == "Contrato (rascunho).pdf"


def test_removes_whitespace_before_password_group() -> None:
    result = extract_password_and_output_name("Relatorio   (abc).PDF")

    assert result is not None
    assert result.password == "abc"
    assert result.output_name == "Relatorio.PDF"


def test_extracts_last_group_even_when_text_follows_it_before_extension() -> None:
    result = extract_password_and_output_name("Contrato (rascunho) (Senha123) - copia.pdf")

    assert result is not None
    assert result.password == "Senha123"
    assert result.output_name == "Contrato (rascunho) - copia.pdf"


def test_handles_files_without_a_final_group_or_pdf_extension() -> None:
    assert extract_password_and_output_name("Contrato.pdf") is None
    assert extract_password_and_output_name("Contrato (senha).pdf.bak") is None


def test_returns_none_for_empty_password_group() -> None:
    assert extract_password_and_output_name("Contrato ().pdf") is None


def test_extracts_all_non_empty_parentheses_groups_with_outputs() -> None:
    candidates = extract_password_candidates("arquivo (abc) (senha)(2).pdf")

    assert [(item.password, item.output_name) for item in candidates] == [
        ("abc", "arquivo (senha)(2).pdf"),
        ("senha", "arquivo (abc) (2).pdf"),
        ("2", "arquivo (abc) (senha).pdf"),
    ]
