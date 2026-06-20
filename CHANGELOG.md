# Changelog

Este arquivo registra mudanças funcionais relevantes do projeto.

## Unreleased

### Added

- Ferramenta de linha de comando para processar PDFs autorizados com `pikepdf`.
- Processamento opcional de subpastas, modo `--dry-run`, logs e resumo de resultados.
- Geração obrigatória do log padrão `remove-senha-pdf.log` na pasta processada, com acréscimo ao arquivo existente.
- Cópia sem senha com preservação de data/hora de modificação e, quando suportado, de acesso.
- Movimentação segura do original para `originais-protegidos` somente após a cópia validada.
- Testes automatizados para nomes, metadados e cenários de proteção por senha.

### Changed

- PDFs são verificados sem senha antes de interpretar o nome; os que não exigem senha são ignorados.
- A senha pode ser obtida do último grupo de parênteses antes de `.pdf`, mesmo se houver texto depois dele.
- Para nomes com vários grupos de parênteses, as candidatas explícitas são tentadas da direita para a esquerda, cobrindo sufixos do Windows como `(1)`.
- Logs identificam o arquivo com conteúdos entre parênteses ocultos como `(...)`, sem revelar senhas.

### Security

- Não há força bruta, adivinhação ou geração de senhas: somente textos explicitamente presentes no nome do arquivo podem ser usados.
