# PDF Remove Password

Ferramenta de linha de comando para criar cópias sem senha de PDFs que você está autorizado a abrir. Ela usa a senha já presente no nome do arquivo e, opcionalmente, uma lista curta de senhas autorizadas. Ela nunca tenta adivinhar, descobrir ou fazer força bruta de senhas.

## Convenção de nomes

As senhas candidatas são os conteúdos não vazios entre parênteses no nome do arquivo. A ferramenta tenta esses grupos da direita para a esquerda, usando somente textos já presentes no nome. A cópia recebe o mesmo nome sem o grupo que abriu o PDF.

```text
Contrato (rascunho) (Senha123).pdf  ->  Contrato (rascunho).pdf
Contrato (Senha123) - cópia.pdf     ->  Contrato - cópia.pdf
arquivo (Senha123)(1).pdf           ->  arquivo (1).pdf
```

Antes de interpretar o nome, o programa verifica se o PDF realmente exige senha. PDFs que abrem sem senha são ignorados imediatamente pelo fluxo de descriptografia, mesmo que possuam texto entre parênteses no nome. Com `--markdown`, eles ainda são convertidos diretamente. A senha não é escrita nos logs; para arquivos reconhecidos, o log substitui seu conteúdo por `(...)`, preservando a indicação de que o nome continha senha.

Se um PDF protegido não contém senha no nome e nenhuma lista autorizada foi informada, o programa não tenta adivinhar a senha: registra o aviso `arquivo_protegido_sem_senha_no_nome` e continua o lote.

PDFs que apresentarem o erro conhecido de metadados `Metadata seems to be XML but not XMP` são ignorados com o aviso `metadados_xmp_invalidos`; o lote continua e o original não é alterado.

Quando há mais de um grupo de parênteses, todos são candidatos explícitos. Isso cobre sufixos como `(1)`, comuns em arquivos duplicados no Windows: a ferramenta tenta `1`, depois tenta o grupo anterior, e preserva o sufixo se outro grupo for a senha correta.

## Lista curta de senhas autorizadas

Opcionalmente, informe um arquivo com senhas conhecidas e autorizadas para o lote:

```powershell
python .\pdf_remove_password.py "C:\PDFs" --authorized-passwords .\senhas.txt
```

Formato do arquivo:

```text
# senhas autorizadas para este lote
senha1
senha2
senha3
```

Regras:

- uma senha por linha;
- linhas vazias e comentários iniciados por `#` são ignorados;
- o limite é de 10 senhas válidas;
- a ordem do arquivo é preservada;
- a ferramenta para no primeiro sucesso;
- nenhuma senha é escrita em logs, erros, resumos ou saída de simulação.

Para cada PDF protegido, as senhas do nome são tentadas primeiro, da direita para a esquerda. Se nenhuma existir ou funcionar, a lista curta é usada como fallback. Quando não há senha no nome, a cópia sem senha recebe o sufixo `-sem-senha`, por exemplo `Documento.pdf` gera `Documento-sem-senha.pdf`.

## Instalação

Requer Python e `pikepdf`.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

### Instalação opcional para Markdown

A geração de Markdown usa PyMuPDF4LLM localmente, sem OCR por padrão. Ela não faz
parte da instalação básica:

```powershell
python -m pip install -r requirements-markdown.txt
```

O Tesseract é necessário somente para usar `--ocr`. Nesse caso, instale-o para
Windows, coloque o executável no `PATH` e instale os dados dos idiomas português
(`por`) e inglês (`eng`). Quando necessário, configure `TESSDATA_PREFIX` para a
pasta `tessdata` da instalação.

O instalador do Tesseract para Windows utilizado no desenvolvimento e nos testes
foi obtido na página da [UB Mannheim](https://github.com/UB-Mannheim/tesseract/wiki).

PyMuPDF4LLM não exige modelos neurais, GPU, PyTorch ou serviços externos. Quando
explicitamente habilitado, OCR torna páginas digitalizadas mais lentas que páginas
com texto nativo e é aplicado seletivamente.

## Uso

```powershell
python .\pdf_remove_password.py "C:\PDFs"
python .\pdf_remove_password.py "C:\PDFs" --recursive
python .\pdf_remove_password.py "C:\PDFs" --dry-run --log-file .\processamento.log
python .\pdf_remove_password.py "C:\PDFs" --authorized-passwords .\senhas.txt
python .\pdf_remove_password.py "C:\PDFs" --markdown
python .\pdf_remove_password.py "C:\PDFs" --markdown --ocr
```

Por padrão, cada execução grava seus eventos em `remove-senha-pdf.log` dentro da pasta processada. Se esse arquivo já existir, as novas ocorrências são adicionadas ao final. Use `--log-file` para escolher outro local ou nome.

Depois de gerar e verificar a cópia sem senha, o programa move o original para a subpasta `originais-protegidos`. O original não é movido se a cópia falhar. Destinos existentes não são sobrescritos.

A cópia preserva a data e a hora de modificação do PDF original. Quando o sistema de arquivos permitir, a data/hora de acesso também é preservada. Essa cópia de metadados ocorre apenas depois que o novo PDF é salvo com sucesso e não altera o arquivo original.

`--dry-run` apenas informa as ações planejadas: não cria, move, renomeia ou altera nenhum arquivo. Em simulação, os eventos são registrados apenas no console, sem criar arquivo de log.

## Markdown opcional

Com `--markdown`, todo PDF legível gera um `.md` de mesmo nome-base na mesma pasta.
Por exemplo, `Contrato.pdf` gera `Contrato.md`. Para PDFs protegidos, a conversão
usa a cópia descriptografada criada e validada. PDFs que já abrem sem senha
continuam sendo ignorados pelo fluxo de descriptografia, mas são convertidos
diretamente para Markdown.

Por padrão, `--markdown` usa apenas a camada textual existente e não inicializa o
Tesseract. Use também `--ocr` somente quando desejar reconhecimento seletivo de
conteúdo de imagem. OCR de página inteira não é forçado; os idiomas configurados
são português e inglês e o processamento ocorre inteiramente no computador local.

O Markdown é escrito primeiro em arquivo temporário e publicado somente depois de
completo. Um `.md` existente nunca é sobrescrito. Se a conversão, o OCR ou a
escrita falhar, o lote continua e a cópia descriptografada permanece válida; o
erro não desfaz a movimentação segura do original.

Se PyMuPDF4LLM estiver indisponível, a ferramenta registra a falha do Markdown por
arquivo e continua o lote. A disponibilidade do Tesseract só é verificada quando
`--ocr` é informado.

Em `--dry-run --markdown`, o conversor não é importado, OCR não é inicializado e
nenhum arquivo, cache ou diretório é criado.

## Testes

```powershell
python -m pytest
```
