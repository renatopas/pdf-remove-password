# Issue 004 - Gerar Markdown opcionalmente com PyMuPDF4LLM

## Contexto

A ferramenta atualmente remove a criptografia de PDFs autorizados e produz uma
cópia validada sem senha. Em alguns fluxos, também é útil obter uma representação
do conteúdo em Markdown para leitura, pesquisa ou processamento posterior.

Os PDFs podem conter texto nativo, páginas digitalizadas como imagem ou uma
combinação dos dois. Portanto, a conversão não pode presumir que todo o documento
possui texto extraível, nem aplicar OCR indiscriminadamente sobre texto nativo já
existente.

## Requisito

Adicionar uma opção explícita de linha de comando para gerar um arquivo `.md` com
o conteúdo de todo PDF legível encontrado, independentemente de ele exigir senha.

O nome recomendado da opção é:

```bash
python pdf_remove_password.py CAMINHO --markdown
```

A conversão deve usar **PyMuPDF4LLM**, com suporte a extração de texto, ordem de
leitura e tabelas. OCR deve permanecer desabilitado por padrão e ser habilitado
somente pela opção explícita `--ocr`, usada junto com `--markdown`.

Sem `--markdown`, o comportamento atual da ferramenta não deve mudar e PyMuPDF4LLM
não deve ser inicializado.

## Escopo inicial

- Para PDFs protegidos, gerar Markdown somente da cópia sem senha que tenha sido
  salva e validada com sucesso pela ferramenta.
- PDFs que já abrem sem senha devem continuar sendo ignorados pelo fluxo de
  descriptografia, mas devem gerar Markdown diretamente quando `--markdown`
  estiver ativo.
- Uma falha ao gerar Markdown não deve invalidar, apagar ou reverter uma cópia
  descriptografada já validada, nem restaurar automaticamente o original já
  movido com sucesso.
- Não alterar o PDF para adicionar camada OCR; o OCR desta funcionalidade serve
  apenas à extração usada na geração do Markdown.
- Todo o processamento deve ser local. A implementação não deve enviar PDFs,
  páginas, imagens, texto ou metadados para serviços externos.

## Origem e nome do Markdown

- Para PDF protegido, usar como entrada do PyMuPDF4LLM a cópia descriptografada,
  nunca o original protegido e nunca uma senha.
- Para PDF que abre sem senha, usar o próprio arquivo como entrada, sem analisar
  parênteses como senha, renomeá-lo ou movê-lo.
- Salvar o Markdown na mesma pasta do PDF usado como entrada.
- Usar o mesmo nome-base do PDF usado como entrada, trocando somente a extensão
  por `.md`.
- Exemplo: `Contrato (rascunho).pdf` gera `Contrato (rascunho).md`.
- Centralizar o cálculo do caminho do Markdown em função fácil de testar.
- Não sobrescrever um `.md` existente.
- Se o destino já existir, registrar colisão e preservar o arquivo existente.

## Extração de texto e OCR

- Preservar e preferir o texto nativo quando ele estiver disponível.
- Com apenas `--markdown`, desabilitar completamente o OCR no PyMuPDF4LLM e não
  exigir nem validar Tesseract.
- Aceitar `--ocr` somente junto com `--markdown`; nesse modo, permitir que
  PyMuPDF4LLM aplique OCR seletivamente a conteúdo de imagem.
- Não habilitar OCR forçado sobre o documento inteiro por padrão.
- Tratar PDFs mistos por página ou região, sem classificar necessariamente o
  documento inteiro como textual ou digitalizado.
- Configurar inicialmente OCR para português e inglês, documentando os códigos de
  idioma exigidos pelo Tesseract.
- Não implementar um detector próprio baseado apenas na quantidade total de texto
  do documento se PyMuPDF4LLM já fornecer decisão adequada no pipeline.
- Falha ou indisponibilidade do mecanismo de OCR deve ser informada sem interromper
  o processamento dos demais PDFs.

## Escrita segura e colisões

- Gerar o conteúdo em arquivo temporário na pasta de destino e publicar o `.md`
  somente depois que a conversão e a escrita terminarem com sucesso.
- Remover resíduos temporários em caso de falha, sem remover arquivos preexistentes.
- Nunca sobrescrever o PDF, o Markdown existente, o original protegido ou o log.
- Uma colisão do `.md` deve afetar apenas a geração do Markdown; não deve impedir a
  criação e validação da cópia descriptografada nem a movimentação segura do
  original definida no fluxo atual.

## Ordem do fluxo por arquivo

Quando `--markdown` estiver ativo:

1. Verificar normalmente se o PDF abre sem senha.
2. Se abrir, ignorar o fluxo de descriptografia e usar o próprio PDF para os
   passos 4-8, sem analisar senha no nome, renomear ou mover o arquivo.
3. Se for protegido, executar abertura autorizada, descriptografia, salvamento,
   validação e movimentação segura; usar a cópia descriptografada nos passos 4-8.
4. Calcular o destino `.md` a partir do PDF escolhido como entrada.
5. Se o Markdown já existir, registrar colisão e não alterá-lo.
6. Caso não exista, converter o PDF escolhido com PyMuPDF4LLM, sem OCR por padrão
   ou com OCR seletivo quando `--ocr` estiver ativo.
7. Publicar atomicamente o Markdown após a conversão terminar com sucesso.
8. Capturar falhas de conversão, OCR e E/S por arquivo, continuar o lote e incluir
   o resultado no resumo final.

Para PDFs protegidos, a conversão ocorre após a validação da cópia e a movimentação
segura do original. Para PDFs sem senha, a conversão ocorre diretamente, sem
renomear ou mover o PDF. A geração de Markdown não pode enfraquecer a garantia de
preservação do original protegido.

## Comportamento em `--dry-run`

Com `--dry-run --markdown`:

- Não inicializar o conversor nem executar OCR ou conversão integral.
- Não criar Markdown, arquivo temporário, cache, diretório ou log.
- Não baixar dados de idioma.
- Não criar, mover, renomear ou alterar PDFs e diretórios.
- Registrar somente no console que a geração de Markdown estaria habilitada e o
  destino que seria considerado, respeitando a política atual de mascaramento de
  nomes.

## Dependências e execução no Windows

- Adicionar PyMuPDF4LLM como dependência opcional associada à funcionalidade de
  Markdown, se o empacotamento adotado pelo projeto permitir extras opcionais.
- Documentar instalação, versão suportada, requisitos de execução e mecanismo de
  OCR selecionado no Windows.
- Preferir componentes que possam funcionar inteiramente de forma local.
- Definir comportamento claro quando `--markdown` for solicitado e PyMuPDF4LLM
  estiver indisponível; validar o mecanismo de OCR somente quando `--ocr` for usado.
- Não usar ou baixar modelos neurais durante o processamento. A instalação dos
  dados de idioma do Tesseract deve ser explícita e documentada.
- Avaliar e documentar impacto no tamanho da instalação, tempo de inicialização,
  memória e duração do processamento.

## Logs e resumo

Adicionar eventos sem conteúdo extraído e sem senhas para, no mínimo:

- geração de Markdown iniciada;
- Markdown criado;
- colisão de destino Markdown;
- Markdown simulado em `--dry-run`;
- OCR utilizado;
- OCR indisponível ou com falha;
- falha de conversão;
- falha de escrita ou publicação do arquivo;
- resíduo temporário não removido.

O resumo final deve distinguir PDFs descriptografados de Markdowns criados,
ignorados por colisão e com falha. Logs, erros e resumo não devem incluir senhas,
conteúdo extraído, texto reconhecido por OCR ou imagens do documento.

## Testes obrigatórios

Adicionar ou atualizar testes para cobrir:

- ausência de `--markdown`, preservando integralmente o comportamento atual;
- `--markdown` sem OCR, sem validar ou exigir Tesseract;
- rejeição de `--ocr` sem `--markdown`;
- PDF protegido com texto nativo e geração bem-sucedida do `.md`;
- PDF protegido composto somente por imagens, exigindo OCR;
- PDF misto, preservando texto nativo e usando OCR apenas onde necessário;
- documento com texto em português e em inglês;
- preservação básica de títulos, parágrafos, listas, ordem de leitura e tabelas;
- nome do Markdown derivado da cópia descriptografada;
- colisão com Markdown existente sem sobrescrita;
- escrita temporária e publicação somente após sucesso;
- remoção do temporário após falha;
- falha do PyMuPDF4LLM sem perda da cópia descriptografada;
- mecanismo de OCR ausente ou com falha, continuando o lote;
- PDF inválido e erro de E/S por arquivo;
- execução recursiva, mantendo a exclusão de `originais-protegidos`;
- PDF que já abre sem senha gerando Markdown sem ser renomeado ou movido;
- `--dry-run --markdown` sem criar arquivos, diretórios, caches ou downloads;
- resumo com contadores separados para PDF e Markdown;
- garantia de que stdout, stderr, logs, exceções capturadas e resumo não contêm
  senhas nem conteúdo do documento.

Os fixtures protegidos, digitalizados e mistos devem ser gerados localmente durante
os testes e descartados, sem versionar PDFs reais ou senhas reais.

## Documentação

Atualizar `README.md`, `SPEC.md`, `AGENTS.md` e `CHANGELOG.md` para documentar:

- a opção `--markdown`;
- que a conversão usa PyMuPDF4LLM localmente;
- o escopo abrangendo todo PDF legível, usando cópia descriptografada apenas para
  os protegidos;
- OCR desabilitado por padrão e a opção `--ocr` para habilitá-lo seletivamente com
  os idiomas configurados;
- as dependências e a preparação necessárias no Windows;
- a política de colisão e escrita temporária;
- o comportamento em `--dry-run`;
- a independência entre o resultado da descriptografia e o resultado da conversão.

## Fora de escopo

- Gerar Markdown sem a opção explícita `--markdown`.
- Usar serviços externos, APIs de OCR, LLMs ou modelos remotos.
- Resumir, traduzir, corrigir ou reescrever o conteúdo extraído.
- Extrair senhas, descobrir credenciais ou modificar a política atual de senhas.
- Garantir reprodução visual idêntica ao PDF no Markdown.
