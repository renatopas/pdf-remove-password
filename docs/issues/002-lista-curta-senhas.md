# Issue 002 - Lista curta de senhas autorizadas

## Contexto

Hoje a ferramenta tenta remover a criptografia usando a senha informada no último grupo de parênteses antes da extensão `.pdf`.

Há casos legítimos em que a senha não está no nome do arquivo, ou em que a senha presente no nome está incorreta. Para esses casos, a pessoa usuária precisa poder fornecer uma lista curta de senhas conhecidas e autorizadas para o lote.

## Requisito

Adicionar suporte a um arquivo opcional de senhas autorizadas, informado por parâmetro de linha de comando:

```bash
python pdf_remove_password.py CAMINHO --authorized-passwords SENHAS.txt
```

O nome recomendado do parâmetro é `--authorized-passwords`.

## Formato do arquivo

- Arquivo de texto simples.
- Uma senha por linha.
- Linhas vazias devem ser ignoradas.
- Linhas cujo primeiro caractere não branco seja `#` devem ser tratadas como comentário e ignoradas.
- A ordem das senhas deve ser preservada.
- A ferramenta não deve modificar, criar, copiar, salvar ou reformatar esse arquivo.

Exemplo:

```text
# senhas autorizadas para este lote
senha1
senha2
senha3
```

## Ordem de tentativa

Para cada PDF protegido:

1. Verificar antes se o PDF abre sem senha. Se abrir, ignorar o arquivo.
2. Tentar a senha extraída do último grupo de parênteses antes de `.pdf`, quando existir.
3. Se a senha do nome não existir ou não funcionar, tentar as senhas do arquivo `--authorized-passwords`, na ordem informada.
4. Parar no primeiro sucesso.
5. Se nenhuma senha funcionar, registrar apenas que o arquivo não pôde ser aberto com as credenciais fornecidas, sem revelar valores.

## Limites e segurança

- A lista deve ter limite explícito de tamanho. O limite inicial recomendado é 10 senhas válidas, depois de ignorar linhas vazias e comentários.
- Se o arquivo tiver mais senhas válidas que o limite, a execução deve falhar antes de processar PDFs.
- A ferramenta não pode gerar, derivar, modificar, combinar, baixar ou adivinhar senhas.
- A ferramenta não pode implementar dicionários, listas públicas, heurísticas, mutações ou força bruta.
- A ferramenta nunca deve imprimir, registrar, persistir ou expor as senhas lidas.
- Mensagens de erro, resumo final, logs e modo `--dry-run` não podem conter senhas.
- O caminho do arquivo de senhas pode aparecer em mensagens, mas o conteúdo nunca.

## Comportamento em `--dry-run`

Em modo `--dry-run`:

- Não criar, mover, renomear, salvar ou alterar arquivos e diretórios.
- Pode validar se o arquivo informado em `--authorized-passwords` existe e é legível.
- Pode validar o limite de quantidade de senhas.
- Não deve imprimir as senhas.
- Não deve tentar salvar cópia sem senha nem mover originais.

## Erros esperados

A implementação deve tratar, com mensagem clara e sem vazamento de senha:

- Arquivo de senhas inexistente.
- Arquivo de senhas ilegível.
- Arquivo de senhas vazio após ignorar comentários e linhas vazias.
- Arquivo com mais senhas válidas que o limite.
- PDF cujo nome não tem senha e cuja lista não abre o arquivo.
- PDF cuja senha do nome falha e cuja lista também falha.

## Testes obrigatórios

Adicionar ou atualizar testes para cobrir:

- Leitura de lista com linhas vazias e comentários.
- Preservação da ordem das senhas.
- Rejeição de lista acima do limite.
- Lista ausente.
- Lista vazia.
- Fallback quando não há senha no nome.
- Fallback quando a senha do nome não funciona.
- Parada no primeiro sucesso.
- Garantia de que nenhuma senha aparece em stdout, stderr, logs, exceções capturadas ou resumo final.
- `--dry-run` com `--authorized-passwords` sem criar, mover, salvar ou alterar arquivos.

## Documentação

Atualizar `README.md`, `SPEC.md` e `CHANGELOG.md` para documentar:

- O parâmetro `--authorized-passwords`.
- O formato do arquivo.
- O limite de senhas.
- A ordem de tentativa.
- As garantias de não exibição e não persistência das senhas.
