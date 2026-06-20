# AGENTS.md

## Propósito do projeto

Este projeto implementará uma ferramenta Windows em Python para remover a criptografia de PDFs que a pessoa usuária tem autorização para abrir. A senha é fornecida pelo próprio nome do arquivo, no último grupo de parênteses antes de `.pdf`.

## Requisitos por issue

- Novos requisitos e mudanças serão descritos em arquivos Markdown em `docs/issues/`, no formato `nnn-nononono.md`.
- Antes de implementar uma mudança solicitada por issue, leia o arquivo correspondente e trate-o como contexto adicional às regras deste documento.

## Regras obrigatórias

- Use `pikepdf` para abrir e salvar os PDFs.
- Antes de analisar a senha no nome ou o destino, verifique se o PDF abre sem senha; se abrir, ignore-o.
- Para um PDF protegido, tente exclusivamente textos de grupos de parênteses já existentes no nome, da direita para a esquerda; não gere, modifique ou adivinhe candidatas.
- Nunca implemente ou sugira força bruta, listas de senhas, adivinhação, tentativas múltiplas, ou qualquer descoberta de senha.
- Nunca registre, exiba ou persista senhas. Trate a senha como dado sensível transitório.
- Preserve o original até que a cópia sem senha seja salva e verificada com sucesso.
- Mova o original apenas após esse sucesso, para `originais-protegidos` dentro de sua pasta atual.
- Não sobrescreva destino, original ou log sem comportamento explícito e testado.
- `--dry-run` não pode criar, mover, renomear ou alterar arquivos e diretórios.

## Convenções de implementação

- Use `pathlib.Path` para todos os caminhos e `shutil.move` para a movimentação.
- Centralize a extração de senha e o cálculo do nome de saída em funções puras, fáceis de testar.
- A extração deve escolher somente o último grupo de parênteses antes da extensão `.pdf`, mesmo que haja texto depois dele; não interprete grupos anteriores como senha.
- Ao percorrer recursivamente, exclua diretórios `originais-protegidos`.
- Capture exceções de `pikepdf` e de E/S por arquivo, continue o lote e produza resumo final.
- Prefira escrita atômica/temporária da cópia quando a API permitir, evitando arquivos de saída parcialmente produzidos.
- Não inclua PDFs reais com senhas em versionamento ou em testes. Gere fixtures de teste localmente e descarte-as.

## Verificação antes de concluir mudanças

- Para toda mudança funcional, adicione uma entrada em `CHANGELOG.md`, na seção `Unreleased` ou em uma nova versão.
- Execute a suíte de testes relevante.
- Verifique cenários de simulação, colisão, arquivo sem padrão de senha, PDF inválido e caminho recursivo.
- Inspecione os logs/saída de teste para garantir que a senha não aparece.
- Documente qualquer comportamento que não esteja definido em `SPEC.md` antes de assumir uma política nova.
