# PDF Remove Password

Ferramenta de linha de comando para criar cópias sem senha de PDFs que você está autorizado a abrir. Ela usa **somente** a senha já presente no nome do arquivo e nunca tenta adivinhar, descobrir ou fazer força bruta de senhas.

## Convenção de nomes

A senha é o último conteúdo entre parênteses antes da extensão `.pdf`, mesmo que haja outros caracteres entre o parêntese de fechamento e a extensão. A cópia recebe o mesmo nome sem esse grupo.

```text
Contrato (rascunho) (Senha123).pdf  ->  Contrato (rascunho).pdf
Contrato (Senha123) - cópia.pdf     ->  Contrato - cópia.pdf
```

Antes de interpretar o nome, o programa verifica se o PDF realmente exige senha. PDFs que abrem sem senha são ignorados imediatamente, mesmo que possuam texto entre parênteses no nome. A senha não é escrita nos logs; para arquivos reconhecidos, o log substitui seu conteúdo por `(...)`, preservando a indicação de que o nome continha senha.

Se um PDF protegido não contém senha no nome, o programa não tenta adivinhar a senha: registra o aviso `arquivo_protegido_sem_senha_no_nome` e continua o lote.

PDFs que apresentarem o erro conhecido de metadados `Metadata seems to be XML but not XMP` são ignorados com o aviso `metadados_xmp_invalidos`; o lote continua e o original não é alterado.

Quando há mais de um grupo de parênteses, as candidatas são testadas da direita para a esquerda, usando somente os textos já presentes no próprio nome. Isso permite processar nomes como `arquivo(senha)(1).pdf`: primeiro `1` é tentado; se falhar, `senha` é usada e a saída será `arquivo(1).pdf`.

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
```

Por padrão, cada execução grava seus eventos em `remove-senha-pdf.log` dentro da pasta processada. Se esse arquivo já existir, as novas ocorrências são adicionadas ao final. Use `--log-file` para escolher outro local ou nome.

Depois de gerar e verificar a cópia sem senha, o programa move o original para a subpasta `originais-protegidos`. O original não é movido se a cópia falhar. Destinos existentes não são sobrescritos.

A cópia preserva a data e a hora de modificação do PDF original. Quando o sistema de arquivos permitir, a data/hora de acesso também é preservada. Essa cópia de metadados ocorre apenas depois que o novo PDF é salvo com sucesso e não altera o arquivo original.

`--dry-run` apenas informa as ações planejadas: não cria, move, renomeia ou altera nenhum arquivo.

## Testes

```powershell
python -m pytest
```
