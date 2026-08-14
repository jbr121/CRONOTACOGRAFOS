# Tutorial — Como rodar o CronotaScan (PC da Univali)

Guia rápido para subir o sistema do zero em outro computador Windows.
Tempo estimado: **5 a 15 minutos** (depende da internet).

Repositório: [https://github.com/jbr121/CRONOTACOGRAFOS](https://github.com/jbr121/CRONOTACOGRAFOS)

---

## Antes de sair de casa (checklist)

Leve no **pendrive** (plano B se a internet falhar):

- [ ] Pasta do projeto **sem** a pasta `.venv`
- [ ] 2 ou 3 fotos boas de disco (PNG/JPG, disco inteiro, bem iluminado)
- [ ] Este tutorial (arquivo `TUTORIAL.md` ou impresso)

No celular, salve também o link do GitHub.

---

## Parte 1 — Conferir o PC da Univali

1. Abra o **PowerShell** (Windows + S → digite `PowerShell` → Enter).
2. Digite os dois comandos:

```powershell
python --version
git --version
```

**O que precisa aparecer:**

- Python **3.11** ou maior (ex.: `Python 3.11.9`)
- Git (ex.: `git version 2.xx`)

**Se `python` não funcionar**, tente:

```powershell
py --version
```

A partir daí, troque `python` por `py` em todos os comandos.

**Se não tiver Python ou Git:** peça no laboratório ou use o ZIP (Parte 2, opção B).

---

## Parte 2 — Baixar o projeto

### Opção A — Git (recomendada)

```powershell
cd $env:USERPROFILE\Desktop
git clone https://github.com/jbr121/CRONOTACOGRAFOS.git
cd CRONOTACOGRAFOS
```

### Opção B — ZIP (sem Git)

1. Abra no navegador: [https://github.com/jbr121/CRONOTACOGRAFOS](https://github.com/jbr121/CRONOTACOGRAFOS)
2. Clique em **Code** (verde) → **Download ZIP**
3. Extraia na **Área de Trabalho**
4. No PowerShell:

```powershell
cd $env:USERPROFILE\Desktop
cd CRONOTACOGRAFOS-master
```

> Se a pasta extraída tiver outro nome, use o nome que aparecer.

### Opção C — Pendrive

Copie a pasta `CRONOTACOGRAFOS` para a Área de Trabalho e:

```powershell
cd $env:USERPROFILE\Desktop\CRONOTACOGRAFOS
```

---

## Parte 3 — Criar o ambiente virtual

Ainda **dentro da pasta do projeto**:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**Deu certo?** O início da linha fica assim: `(.venv)`

### Erro de política de execução

Se aparecer algo como `não é permitido carregar porque a execução de scripts está desabilitada`:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
.\.venv\Scripts\Activate.ps1
```

Aceite com `S` se perguntar.

---

## Parte 4 — Instalar as bibliotecas

Com o `(.venv)` ativo:

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Espere terminar. O OpenCV costuma demorar mais.

**Deu certo?** A última linha não deve ser um erro vermelho. Você pode conferir com:

```powershell
python -c "import fastapi, cv2, sqlalchemy, reportlab; print('OK')"
```

Tem que imprimir `OK`.

---

## Parte 5 — Ligar o sistema

```powershell
python main.py
```

Espere aparecer:

```text
Uvicorn running on http://127.0.0.1:8081
```

**Não feche essa janela do PowerShell.** Ela é o servidor.

---

## Parte 6 — Abrir no navegador

1. Abra o Chrome ou Edge.
2. Digite na barra de endereço:

```text
http://127.0.0.1:8081/
```

3. A tela **Galaxy Pro / CronotaScan** deve aparecer (fundo escuro, logo, campo de placa).

Se a página não atualizar, use **Ctrl + Shift + R**.

---

## Parte 7 — Como usar (demo)

1. **Placa do veículo** — exemplo: `ABC-1234`
2. **Arquivo do disco** — escolha a foto PNG/JPG
3. Clique em **Analisar Disco**
4. Espere o overlay “Processando disco...”
5. Confira:
   - cards de distância, velocidades e infrações
   - gráfico da curva
   - imagem desdobrada
   - tabela de alertas
6. Clique em **Gerar Laudo PDF** (abre em nova aba)
7. No **Histórico**, use **Detalhes** e **PDF**

Para limpar a tela e começar outra leitura: botão **Limpar**.

Para **parar** o servidor: volte no PowerShell e pressione **Ctrl + C**.

---

## Problemas comuns

### Porta 8081 ocupada

```powershell
$env:PORT=8090
python main.py
```

Abra então: **http://127.0.0.1:8090/**

### `ModuleNotFoundError` (fastapi, cv2, sqlalchemy...)

O ambiente virtual não está ativo. Rode de novo:

```powershell
cd $env:USERPROFILE\Desktop\CRONOTACOGRAFOS
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python main.py
```

### `Não foi possível localizar o centro do disco`

A foto está ruim para o algoritmo. Use outra com:

- disco **inteiro** no enquadramento
- boa luz, sem sombra forte
- papel o mais reto possível (evite foto muito de lado)

### Tela antiga / “não mudou nada”

**Ctrl + Shift + R** no navegador, ou abra uma aba anônima (**Ctrl + Shift + N**).

### Sem internet no laboratório

Use o **pendrive** (Parte 2, opção C).  
Se as bibliotecas ainda não estiverem instaladas nesse PC, o `pip install` **precisa** de internet. Nesse caso, peça rede ou rode no seu notebook.

---

## Comando único (depois que já instalou uma vez)

Na próxima vez no **mesmo PC**:

```powershell
cd $env:USERPROFILE\Desktop\CRONOTACOGRAFOS
.\.venv\Scripts\Activate.ps1
python main.py
```

Abra: **http://127.0.0.1:8081/**

---

*CronotaScan — Galaxy Pro — PGI Univali*
