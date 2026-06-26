# Issue 003 - Testar todos os grupos de parênteses do nome

## Contexto

Alguns PDFs podem ter mais de um grupo de parênteses no nome. Um caso comum no Windows é o gerenciador de arquivos adicionar um sufixo numérico para evitar duplicidade:

```text
arquivo (senha)(1).pdf
```

Nesse exemplo, `(1)` não é a senha. Ele é apenas um sufixo automático de nome duplicado. Se a ferramenta considerar apenas o último grupo de parênteses antes de `.pdf`, ela tentará `1`, falhará, e não chegará à senha real em `(senha)`.

## Requisito

Para PDFs protegidos, a ferramenta deve considerar todos os grupos de parênteses existentes no nome do arquivo como senhas candidatas explícitas, testando da direita para a esquerda.

Isso deve continuar restrito ao conteúdo já presente no nome do arquivo:

- não gerar senhas;
- não derivar variações;
- não modificar candidatas;
- não usar heurísticas;
- não usar força bruta;
- não usar listas públicas ou dicionários.

## Ordem de tentativa

Para cada PDF protegido:

1. Verificar antes se o PDF abre sem senha. Se abrir, ignorar o arquivo.
2. Extrair todos os grupos de parênteses não vazios no nome base do arquivo.
3. Tentar os grupos extraídos da direita para a esquerda.
4. Parar no primeiro grupo que abrir o PDF com sucesso.
5. Se nenhum grupo do nome funcionar, usar a lista curta de `--authorized-passwords`, quando informada, conforme a issue 002.
6. Se nenhuma credencial fornecida funcionar, registrar falha sem revelar valores.

Exemplo:

```text
arquivo (senha)(1).pdf
```

Ordem de tentativa:

1. `1`
2. `senha`

Se `senha` funcionar, a saída deve remover apenas o grupo que funcionou:

```text
arquivo (1).pdf
```

## Nome de saída

Quando uma senha candidata do nome funcionar:

- remover somente o grupo de parênteses que continha a senha bem-sucedida;
- preservar os demais grupos;
- preservar sufixos como `(1)`;
- ajustar espaços adjacentes como já ocorre hoje;
- nunca incluir a senha no nome de saída.

Exemplos esperados:

```text
arquivo (senha)(1).pdf              -> arquivo (1).pdf
contrato (rascunho) (senha).pdf     -> contrato (rascunho).pdf
contrato (senha) - copia.pdf        -> contrato - copia.pdf
arquivo (abc) (senha)(2).pdf        -> arquivo (abc) (2).pdf
```

Quando nenhuma senha do nome funcionar e a senha vier da lista autorizada, manter a regra da issue 002 para nome de saída.

## Colisões de destino

A ferramenta não pode sobrescrever arquivos existentes.

Para cada candidata do nome:

- calcular o destino correspondente à remoção daquele grupo;
- se o destino já existir, registrar colisão para aquela candidata sem revelar a senha;
- continuar para a próxima candidata, se houver;
- se todas as candidatas possíveis forem bloqueadas por colisão ou falha, manter o original no lugar.

## Logs e segurança

- Nunca registrar, imprimir ou persistir qualquer senha candidata.
- Logs devem continuar mascarando conteúdos entre parênteses no nome do arquivo.
- Mensagens de erro devem indicar apenas o resultado, como senha inválida ou colisão, sem valores.
- O resumo final não pode conter senhas.

## Testes obrigatórios

Adicionar ou atualizar testes para cobrir:

- `arquivo (senha)(1).pdf`, em que `(1)` falha e `(senha)` funciona.
- Preservação do sufixo `(1)` no nome de saída.
- Múltiplos grupos, garantindo tentativa da direita para a esquerda.
- Remoção somente do grupo que funcionou.
- Grupos vazios ignorados.
- Caso em que nenhum grupo do nome funciona e a lista `--authorized-passwords` é usada.
- Caso em que nenhum grupo do nome funciona e não há lista autorizada.
- Colisão de destino em uma candidata, continuando para outra candidata possível.
- Garantia de que nenhuma senha candidata aparece em stdout, stderr, logs, exceções capturadas ou resumo final.
- `--dry-run` sem criar, mover, salvar ou alterar arquivos e diretórios.

## Documentação

Atualizar `AGENTS.md`, `README.md`, `SPEC.md` e `CHANGELOG.md` para documentar:

- que todos os grupos de parênteses do nome são candidatos explícitos;
- que a ordem é da direita para a esquerda;
- que sufixos como `(1)` são preservados se outro grupo anterior for a senha correta;
- que isso não autoriza geração, modificação, derivação ou descoberta de senhas.
