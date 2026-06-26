# Especificação — Removedor de Senha de PDFs

## Objetivo

Aplicativo Windows em Python que processa PDFs para os quais a pessoa usuária já possui autorização e senha. A senha preferencial é lida do nome do arquivo; opcionalmente, a pessoa usuária pode informar uma lista curta de senhas autorizadas para fallback. O programa nunca tenta descobrir, adivinhar ou gerar senhas.

## Escopo funcional

- Receber uma pasta de entrada como argumento.
- Processar apenas arquivos cuja extensão seja `.pdf`, sem distinção entre maiúsculas e minúsculas.
- Por padrão, examinar apenas a pasta indicada. Com uma opção de linha de comando, incluir subpastas.
- Considerar como senha o conteúdo do **último** conjunto de parênteses antes da extensão `.pdf`, ainda que existam outros caracteres entre o parêntese de fechamento e a extensão.
  - Exemplo: `Contrato (rascunho) (Senha123).pdf` usa `Senha123`.
  - Exemplos sem senha extraível: `Contrato.pdf`, grupos finais vazios e nomes sem pares de parênteses válidos.
- Abrir o PDF com `pikepdf` usando a senha extraída do nome e, se necessário, as senhas da lista curta autorizada.
- Gerar uma cópia descriptografada na mesma pasta do arquivo de origem, retirando do nome o conjunto final de parênteses que contém a senha.
  - Exemplo: `Contrato (rascunho) (Senha123).pdf` gera `Contrato (rascunho).pdf`.
- Quando a senha vier somente da lista autorizada e não houver senha no nome, gerar a cópia com o sufixo `-sem-senha`.
  - Exemplo: `Contrato.pdf` gera `Contrato-sem-senha.pdf`.
- Depois que a cópia for criada e validada com sucesso, mover o PDF original para uma subpasta da própria pasta de origem. O nome padrão da subpasta será `originais-protegidos`.
- Nunca sobrescrever um arquivo existente. Em colisões de nome, registrar o fato e pular o arquivo.
- Não modificar o conteúdo nem o nome do original antes de uma cópia descriptografada válida existir.

## Limites de segurança e uso

- O programa destina-se exclusivamente a PDFs que a pessoa usuária está autorizada a abrir.
- Não implementar força bruta, dicionários, consulta externa, nem qualquer mecanismo de descoberta de senha.
- Para cada arquivo protegido, as únicas tentativas permitidas são a senha do último grupo de parênteses antes de `.pdf` e as senhas de uma lista curta explicitamente fornecida pela pessoa usuária. Não gerar nem modificar candidatas.
- A lista curta deve ter no máximo 10 senhas válidas, uma por linha. Linhas vazias e comentários iniciados por `#` são ignorados.
- Nunca incluir senhas nos logs, mensagens de erro, relatórios ou nomes de saída.

## Interface de linha de comando proposta

```text
pdf-remove-password PASTA [--recursive] [--dry-run] [--log-file CAMINHO] [--authorized-passwords CAMINHO]
```

- `PASTA`: diretório a processar.
- `--recursive`: inclui subpastas; deve ignorar a subpasta `originais-protegidos` para não reprocessar originais movidos.
- `--dry-run`: simula todas as ações; não cria PDFs, não cria pastas, não cria logs e não move arquivos.
- `--log-file CAMINHO`: destino opcional para log persistente; sem essa opção, registrar em `remove-senha-pdf.log` dentro da pasta processada. Em `--dry-run`, registrar somente no console.
- `--authorized-passwords CAMINHO`: arquivo opcional de texto com lista curta de senhas autorizadas, uma por linha.

## Fluxo por arquivo

1. Localizar PDFs de acordo com o modo recursivo escolhido.
2. Ignorar arquivos já situados em uma pasta `originais-protegidos`.
3. Fora de `--dry-run`, tentar abrir o PDF sem senha para verificar se ele é protegido.
4. Se ele abrir sem senha, registrá-lo como ignorado e não analisar o nome nem o destino.
5. Se for protegido, extrair a senha pelo último grupo entre parênteses antes de `.pdf`.
6. Se não houver senha válida no nome e não houver lista autorizada, registrar `arquivo_protegido_sem_senha_no_nome`.
7. Calcular o nome de saída removendo somente esse último grupo e espaços adjacentes apropriados. Se não houver senha no nome e a lista autorizada for usada, adicionar o sufixo `-sem-senha`.
8. Se o destino já existir, registrar `ignorado_colisao_destino`.
9. Em `--dry-run`, registrar a inspeção planejada, sem alterar o disco.
10. Abrir com `pikepdf` usando primeiro a senha extraída do nome, quando existir. Se ela falhar ou não existir, tentar as senhas autorizadas na ordem do arquivo.
11. Parar no primeiro sucesso, salvar a cópia sem criptografia e confirmar que o arquivo foi criado.
12. Somente então criar a subpasta de originais, se necessário, e mover o PDF de origem para ela.
13. Em qualquer falha, registrar o erro sem revelar a senha e manter o original no local.

## Dependências e compatibilidade

- Python suportado pelo projeto.
- `pikepdf` para abertura e salvamento dos PDFs.
- APIs padrão para caminhos, movimentação e logs (`pathlib`, `shutil`, `logging`, `argparse`).
- Alvo: Windows; os caminhos devem ser tratados por `pathlib`, sem concatenação manual de separadores.

## Logs

Cada evento deve ter nível, caminho do arquivo e resultado, sem a senha. Eventos mínimos: descoberta, ignorado sem senha, colisão, simulação, cópia criada, original movido, falha ao abrir, falha ao salvar e falha ao mover. Ao final, emitir um resumo com contadores por resultado.

## Critérios de aceitação e testes

- Testar extração do último grupo de parênteses, inclusive múltiplos grupos, espaços, extensão em maiúsculas e casos inválidos.
- Testar a formação do nome de saída, garantindo a remoção de apenas o grupo de senha.
- Testar modo não recursivo e `--recursive`, incluindo a exclusão de `originais-protegidos`.
- Testar `--dry-run` para confirmar que nenhum arquivo ou diretório é alterado.
- Testar sucesso: a cópia abre sem senha e o original é movido somente após o salvamento bem-sucedido.
- Testar leitura da lista autorizada, limite de 10 senhas, comentários, linhas vazias, lista ausente, lista vazia e lista acima do limite.
- Testar fallback quando não há senha no nome e quando a senha do nome não funciona.
- Testar que `--dry-run` com lista autorizada não cria PDF, pasta, log nem move original.
- Testar falha de senha/PDF corrompido: nenhum original é movido.
- Testar colisão de destino: nenhum arquivo é sobrescrito nem movido.
- Testar que logs e exceções capturadas não contêm a senha.
