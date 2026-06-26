# PDF Remove Password

Ferramenta de linha de comando para criar cópias sem senha de PDFs que você está autorizado a abrir. Ela usa a senha já presente no nome do arquivo e, opcionalmente, uma lista curta de senhas autorizadas. Ela nunca tenta adivinhar, descobrir ou fazer força bruta de senhas.

## Convenção de nomes

A senha é o último conteúdo entre parênteses antes da extensão `.pdf`, mesmo que haja outros caracteres entre o parêntese de fechamento e a extensão. A cópia recebe o mesmo nome sem esse grupo.

```text
Contrato (rascunho) (Senha123).pdf  ->  Contrato (rascunho).pdf
Contrato (Senha123) - cópia.pdf     ->  Contrato - cópia.pdf
```

Antes de interpretar o nome, o programa verifica se o PDF realmente exige senha. PDFs que abrem sem senha são ignorados imediatamente, mesmo que possuam texto entre parênteses no nome. A senha não é escrita nos logs; para arquivos reconhecidos, o log substitui seu conteúdo por `(...)`, preservando a indicação de que o nome continha senha.

Se um PDF protegido não contém senha no nome e nenhuma lista autorizada foi informada, o programa não tenta adivinhar a senha: registra o aviso `arquivo_protegido_sem_senha_no_nome` e continua o lote.

PDFs que apresentarem o erro conhecido de metadados `Metadata seems to be XML but not XMP` são ignorados com o aviso `metadados_xmp_invalidos`; o lote continua e o original não é alterado.

Quando há mais de um grupo de parênteses, somente o último grupo é usado como senha do nome.

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

Para cada PDF protegido, a senha do nome é tentada primeiro. Se ela não existir ou não funcionar, a lista curta é usada como fallback. Quando não há senha no nome, a cópia sem senha recebe o sufixo `-sem-senha`, por exemplo `Documento.pdf` gera `Documento-sem-senha.pdf`.

## Instalação

Requer Python e `pikepdf`.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## Uso

```powershell
python .\pdf_remove_password.py "C:\PDFs"
python .\pdf_remove_password.py "C:\PDFs" --recursive
python .\pdf_remove_password.py "C:\PDFs" --dry-run --log-file .\processamento.log
python .\pdf_remove_password.py "C:\PDFs" --authorized-passwords .\senhas.txt
```

Por padrão, cada execução grava seus eventos em `remove-senha-pdf.log` dentro da pasta processada. Se esse arquivo já existir, as novas ocorrências são adicionadas ao final. Use `--log-file` para escolher outro local ou nome.

Depois de gerar e verificar a cópia sem senha, o programa move o original para a subpasta `originais-protegidos`. O original não é movido se a cópia falhar. Destinos existentes não são sobrescritos.

A cópia preserva a data e a hora de modificação do PDF original. Quando o sistema de arquivos permitir, a data/hora de acesso também é preservada. Essa cópia de metadados ocorre apenas depois que o novo PDF é salvo com sucesso e não altera o arquivo original.

`--dry-run` apenas informa as ações planejadas: não cria, move, renomeia ou altera nenhum arquivo. Em simulação, os eventos são registrados apenas no console, sem criar arquivo de log.

## Testes

```powershell
python -m pytest
```
