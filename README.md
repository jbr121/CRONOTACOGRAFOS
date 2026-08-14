# CronotaScan — Leitor de Discos de Cronotacógrafo Analógico

Protótipo do **Projeto Integrador (PGI)** — Curso de Sistemas para Internet (Univali).

O CronotaScan realiza a leitura visual de discos diagrama de cronotacógrafo analógico por visão computacional (OpenCV), detecta excessos de velocidade e paradas prolongadas, persiste o histórico em SQLite e gera laudos PDF de auditoria.

---

## Requisitos

- Windows 10/11 (testado)
- Python 3.11+
- Navegador moderno (Chrome, Edge ou Firefox)

---

## Instalação rápida (passo a passo)

Abra o **PowerShell** na pasta do projeto:

```powershell
cd E:\CRONOTACOGRAFOS
```

### 1. Criar e ativar o ambiente virtual

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Se aparecer erro de política de execução:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
.\.venv\Scripts\Activate.ps1
```

### 2. Instalar as dependências

```powershell
python -m pip install -r requirements.txt
```

Principais bibliotecas: FastAPI, Uvicorn, OpenCV, NumPy, Pandas, SQLAlchemy, ReportLab.

### 3. Executar a aplicação

```powershell
python main.py
```

Aguarde a mensagem:

```text
Uvicorn running on http://127.0.0.1:8081
```

### 4. Abrir a interface

No navegador, acesse:

**http://127.0.0.1:8081/**

Documentação Swagger da API: **http://127.0.0.1:8081/docs**  
Health check: **http://127.0.0.1:8081/api/health**

> **Porta:** o CronotaScan usa **8081** por padrão, para poder rodar junto com outro software na **8080**.  
> Para mudar: `$env:PORT=8090` e depois `python main.py`.

---

## Como testar (roteiro para a banca)

1. Informe a **placa** do veículo (ex.: `ABC-1234`).
2. Selecione a **imagem** do disco (PNG/JPG) e clique em **Upload do Disco**.
3. Aguarde o processamento (overlay de carregamento).
4. Confira no dashboard:
   - distância estimada, velocidades e total de infrações;
   - gráfico Chart.js da curva;
   - imagem desdobrada (debug);
   - tabela de excessos/paradas.
5. No **Histórico de leituras**, use **Filtrar**, **Ver Detalhes** e **PDF**.
6. Clique em **Gerar Laudo PDF** para abrir o laudo em nova aba.
7. Use **Limpar / Novo Escaneamento** para reiniciar o formulário.

### Teste de falha controlada (robustez)

Envie uma foto sem disco / muito escura / cortada. O sistema deve responder com mensagem clara em português (ex.: impossibilidade de localizar o centro) e **não travar** a tela.

---

## Estrutura do projeto

```text
CRONOTACOGRAFOS/
├── main.py                      # API FastAPI + handlers de erro
├── requirements.txt
├── README.md
├── PLANO_DE_IMPLEMENTACAO.md
├── tacografos.db                # SQLite (criado automaticamente)
├── temp/                        # Imagens desdobradas / PDFs de teste
├── static/
│   └── index.html               # SPA (dashboard)
└── core/
    ├── processador_imagem.py    # OpenCV — LeitorDisco
    ├── analisador.py            # Regras de negócio
    ├── database.py              # SQLAlchemy / SQLite
    └── gerador_pdf.py           # Laudos PDF (ReportLab)
```

---

## Endpoints principais

| Método | Rota | Descrição |
| --- | --- | --- |
| `GET` | `/` | Interface SPA |
| `GET` | `/api/health` | Status da API |
| `POST` | `/upload-disco/` | Processa disco + placa e grava no banco |
| `GET` | `/api/v1/viagens` | Lista histórico (`?placa=` opcional) |
| `GET` | `/api/v1/viagens/{id}` | Detalhe da viagem |
| `GET` | `/api/v1/viagens/{id}/pdf` | Laudo PDF de auditoria |

---

## Manutenção rápida

**Parar o servidor:** `Ctrl + C` no terminal.

**Reiniciar o banco (apaga o histórico):**

```powershell
# com o servidor parado
Remove-Item E:\CRONOTACOGRAFOS\tacografos.db -Force
python main.py
```

**Limpar imagens de debug:**

```powershell
Remove-Item E:\CRONOTACOGRAFOS\temp\* -Force -ErrorAction SilentlyContinue
```

---

## Observações para a apresentação

- O protótipo prioriza **escaneamentos bem iluminados e centralizados**.
- A distância é uma **estimativa** por integração velocidade × tempo.
- O histórico e os laudos PDF apoiam a auditoria de frota; a validação final é do gestor/auditor.
- Detalhes de arquitetura e roadmap: consulte [`PLANO_DE_IMPLEMENTACAO.md`](PLANO_DE_IMPLEMENTACAO.md).

---

*CronotaScan — PGI Univali — Sistemas para Internet*
