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
- Parâmetro `--authorized-passwords` para lista curta de senhas autorizadas como fallback explícito.

### Changed

- PDFs são verificados sem senha antes de interpretar o nome; os que não exigem senha são ignorados.
- Erro conhecido de metadados XML inválidos para XMP é registrado como aviso e o PDF afetado é ignorado sem interromper o lote.
- A senha pode ser obtida de qualquer grupo de parênteses já existente no nome antes de `.pdf`, mesmo se houver texto depois dele.
- Para nomes com vários grupos de parênteses, as candidatas explícitas são tentadas da direita para a esquerda, preservando sufixos como `(1)` quando outro grupo anterior for a senha correta.
- Logs identificam o arquivo com conteúdos entre parênteses ocultos como `(...)`, sem revelar senhas.
- Em `--dry-run`, a ferramenta registra eventos apenas no console e não cria arquivo de log.

### Security

- Não há força bruta, adivinhação ou geração de senhas: somente textos já presentes em grupos de parênteses no nome do arquivo e uma lista curta explicitamente fornecida pela pessoa usuária podem ser usados.
- Senhas da lista autorizada não são exibidas, registradas ou persistidas pela ferramenta.
