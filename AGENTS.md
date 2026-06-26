# AGENTS.md

## Propósito do projeto

Este projeto implementará uma ferramenta Windows em Python para remover a criptografia de PDFs que a pessoa usuária tem autorização para abrir. As senhas preferenciais são fornecidas pelo próprio nome do arquivo, em grupos de parênteses existentes antes de `.pdf`. Opcionalmente, a pessoa usuária pode fornecer uma lista curta de senhas autorizadas como fallback explícito.

## Requisitos por issue

- Novos requisitos e mudanças serão descritos em arquivos Markdown em `docs/issues/`, no formato `nnn-nononono.md`.
- Antes de implementar uma mudança solicitada por issue, leia o arquivo correspondente e trate-o como contexto adicional às regras deste documento.

## Regras obrigatórias

- Use `pikepdf` para abrir e salvar os PDFs.
- Antes de analisar a senha no nome ou o destino, verifique se o PDF abre sem senha; se abrir, ignore-o.
- Para um PDF protegido, tente primeiro os textos dos grupos de parênteses já existentes no nome, da direita para a esquerda; se nenhum deles existir ou abrir o PDF, use somente a lista curta de senhas explicitamente fornecida pela pessoa usuária.
- A lista de senhas deve ser pequena, finita, mantida manualmente pela pessoa usuária, usada apenas por opção explícita e nunca gerada, expandida, derivada, modificada ou baixada pela ferramenta.
- Nunca implemente ou sugira força bruta, listas públicas de senhas, dicionários, mutações, adivinhação, heurísticas, variações automáticas, tentativas ilimitadas, ou qualquer descoberta de senha.
- Nunca registre, exiba ou persista senhas pela ferramenta. A lista, quando usada, deve ser lida como entrada sensível fornecida pela pessoa usuária; a ferramenta não deve criar, salvar, completar, copiar, imprimir ou incluir essas senhas em logs, erros ou resumos.
- Preserve o original até que a cópia sem senha seja salva e verificada com sucesso.
- Mova o original apenas após esse sucesso, para `originais-protegidos` dentro de sua pasta atual.
- Não sobrescreva destino, original ou log sem comportamento explícito e testado.
- `--dry-run` não pode criar, mover, renomear ou alterar arquivos e diretórios.

## Convenções de implementação

- Use `pathlib.Path` para todos os caminhos e `shutil.move` para a movimentação.
- Centralize a extração da senha do nome, a leitura controlada da lista curta de senhas e o cálculo do nome de saída em funções fáceis de testar.
- A extração do nome deve escolher somente textos de grupos de parênteses já existentes antes da extensão `.pdf`, mesmo que haja texto depois deles; tente-os da direita para a esquerda e não gere variações.
- A lista curta de senhas deve preservar a ordem informada pela pessoa usuária, ignorar linhas vazias e comentários, ter limite explícito de tamanho, e parar no primeiro sucesso.
- Ao percorrer recursivamente, exclua diretórios `originais-protegidos`.
- Capture exceções de `pikepdf` e de E/S por arquivo, continue o lote e produza resumo final.
- Prefira escrita atômica/temporária da cópia quando a API permitir, evitando arquivos de saída parcialmente produzidos.
- Não inclua PDFs reais com senhas em versionamento ou em testes. Gere fixtures de teste localmente e descarte-as.

## Verificação antes de concluir mudanças

- Para toda mudança funcional, adicione uma entrada em `CHANGELOG.md`, na seção `Unreleased` ou em uma nova versão.
- Execute a suíte de testes relevante.
- Verifique cenários de simulação, colisão, arquivo sem padrão de senha, PDF inválido e caminho recursivo.
- Verifique cenários de fallback com lista curta, incluindo lista ausente, vazia, acima do limite, sem sucesso e com sucesso.
- Inspecione os logs/saída de teste para garantir que nenhuma senha aparece.
- Documente qualquer comportamento que não esteja definido em `SPEC.md` antes de assumir uma política nova.
