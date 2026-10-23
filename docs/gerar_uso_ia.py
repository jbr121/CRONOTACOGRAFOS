"""
Gera o documento Word com declaração completa de uso de IA no projeto CronotaScan.
Inclui histórico de commits com hash, data, autor e descrição.
"""

from __future__ import annotations

from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt, RGBColor, Cm
from docx.oxml.ns import qn
from docx.oxml import OxmlElement


SAIDA = Path(__file__).resolve().parent / "CronotaScan_Uso_de_IA.docx"

REPOSITORIO = "https://github.com/jbr121/CRONOTACOGRAFOS"

# Histórico completo de commits (hash, data, autor, mensagem, o que fez, envolveu IA?)
COMMITS = [
    {
        "hash": "a30940f",
        "data": "14/08/2026 16:00",
        "autor": "José Eduardo (jbr121)",
        "mensagem": "Initial commit: CronotaScan PGI Univali",
        "descricao": "Estrutura inicial do projeto: FastAPI, banco SQLite, front-end SPA e pipeline básico de leitura.",
        "ia": False,
    },
    {
        "hash": "b6438e2",
        "data": "14/08/2026 16:30",
        "autor": "José Eduardo (jbr121)",
        "mensagem": "Add tutorial for running CronotaScan on Univali lab PCs.",
        "descricao": "Tutorial passo a passo para rodar o sistema nos computadores do laboratório da UNIVALI.",
        "ia": False,
    },
    {
        "hash": "23957bb",
        "data": "14/08/2026 16:32",
        "autor": "José Eduardo (jbr121)",
        "mensagem": "Add ES2 complementary documentation without changing existing PGI plan.",
        "descricao": "Documentação complementar de Engenharia de Software II sem alterar o plano PGI existente.",
        "ia": False,
    },
    {
        "hash": "b3454bb",
        "data": "25/09/2026 20:48",
        "autor": "Erick Franzmann Bortoloti + Claude Opus 5.5 (IA)",
        "mensagem": "Integrate v2 disc reader with perspective correction and validation",
        "descricao": (
            "Reformulação completa do pipeline OpenCV (1125 linhas alteradas): detecção da borda "
            "do disco como elipse, homografia para correção de perspectiva (elipse → círculo), "
            "orientação pelo arco verde 12h–24h, autocalibração pelos anéis de 20 km/h impressos, "
            "leitura da barra de atividade para filtrar minutos parados. "
            "Co-Authored-By: Claude Opus 5.5 (Anthropic)."
        ),
        "ia": True,
    },
    {
        "hash": "10090b4",
        "data": "09/10/2026 18:46",
        "autor": "Cursor Agent (IA) + José Eduardo",
        "mensagem": "Corrige rastreamento da curva do disco",
        "descricao": (
            "Correção de bugs no rastreamento da agulha de velocidade: ajuste das faixas radiais, "
            "remoção de impressão fixa do disco (linhas tracejadas confundidas com agulha) e "
            "criação dos primeiros testes unitários automatizados (tests/test_processador_imagem.py, 79 linhas)."
        ),
        "ia": True,
    },
    {
        "hash": "634c6db",
        "data": "21/10/2026 11:13",
        "autor": "Cursor Agent (IA) + José Eduardo",
        "mensagem": "Calibra a leitura com discos de gabarito conhecido",
        "descricao": (
            "Calibração com discos reais: zera minutos parados quando a barra de atividade está visível, "
            "preserva trechos longos de velocidade constante, reconhece o arco verde mesmo com perspectiva. "
            "Adição de fixtures (discos sintéticos reto, inclinado e com lacuna) e "
            "testes automatizados com gabarito JSON (tests/test_fixtures_disco.py)."
        ),
        "ia": True,
    },
    {
        "hash": "920e257",
        "data": "21/10/2026 11:24",
        "autor": "Cursor Agent (IA) + José Eduardo",
        "mensagem": "Gera laudo PDF dos discos de gabarito",
        "descricao": "Geração do laudo PDF de auditoria com os resultados dos discos de gabarito para validação do pipeline.",
        "ia": True,
    },
    {
        "hash": "b6abd2f",
        "data": "21/10/2026 11:27",
        "autor": "Cursor Agent (IA) + José Eduardo",
        "mensagem": "Inclui a interface e o dashboard no laudo PDF",
        "descricao": "Inserção de capturas de tela da interface web e do dashboard de infrações no laudo PDF para evidência visual.",
        "ia": True,
    },
    {
        "hash": "306196e",
        "data": "21/10/2026 11:39",
        "autor": "Cursor Agent (IA) + José Eduardo",
        "mensagem": "Gera o PDF com a explicação das telas e funções",
        "descricao": "Criação do PDF explicativo de todas as telas e funções do sistema CronotaScan (laudos/explicacao_telas_e_funcoes.pdf).",
        "ia": True,
    },
    {
        "hash": "00aac9a",
        "data": "21/10/2026 11:43",
        "autor": "Cursor Agent (IA) + José Eduardo",
        "mensagem": "Adiciona laudo teste com as imagens do CronotaScan",
        "descricao": "Laudo de teste completo com imagens do sistema incluídas para apresentação à professora (laudos/laudo_teste.pdf).",
        "ia": True,
    },
    {
        "hash": "8b438ca",
        "data": "21/10/2026 11:49",
        "autor": "Cursor Agent (IA) + José Eduardo",
        "mensagem": "Reescreve o laudo teste com a explicação de cada tela e função",
        "descricao": "Revisão completa do laudo de teste: cada tela e função do sistema descrita individualmente com clareza para a banca.",
        "ia": True,
    },
    {
        "hash": "9842a38",
        "data": "23/10/2026 09:17",
        "autor": "José Eduardo (jbr121)",
        "mensagem": "Cursor: Apply local changes for cloud agent",
        "descricao": "Sincronização de alterações locais com o agente na nuvem do Cursor.",
        "ia": False,
    },
    {
        "hash": "e72dcc8",
        "data": "23/10/2026 12:20",
        "autor": "Cursor Agent (IA)",
        "mensagem": "docs: adiciona documento de declaração de uso de IA (para entrega M2)",
        "descricao": "Criação deste próprio documento de declaração de uso de IA, conforme solicitado pela professora.",
        "ia": True,
    },
]


def _set_cell_bg(cell, hex_color: str) -> None:
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_color)
    tcPr.append(shd)


def _cell_text(cell, texto: str, negrito: bool = False, tamanho: int = 10, cor: str | None = None) -> None:
    cell.text = ""
    p = cell.paragraphs[0]
    run = p.add_run(texto)
    run.bold = negrito
    run.font.size = Pt(tamanho)
    if cor:
        r, g, b = int(cor[0:2], 16), int(cor[2:4], 16), int(cor[4:6], 16)
        run.font.color.rgb = RGBColor(r, g, b)
    p.paragraph_format.space_after = Pt(0)


def paragrafo(doc: Document, texto: str, negrito: bool = False, tamanho: int = 12, centralizado: bool = False) -> None:
    p = doc.add_paragraph()
    run = p.add_run(texto)
    run.bold = negrito
    run.font.size = Pt(tamanho)
    p.paragraph_format.space_after = Pt(6)
    if centralizado:
        p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    else:
        p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY


def titulo_secao(doc: Document, texto: str) -> None:
    h = doc.add_heading(texto, level=2)
    h.paragraph_format.space_before = Pt(14)
    h.paragraph_format.space_after = Pt(6)


def item_lista(doc: Document, texto: str) -> None:
    p = doc.add_paragraph(style="List Bullet")
    p.add_run(texto).font.size = Pt(12)
    p.paragraph_format.space_after = Pt(4)


def main() -> None:
    doc = Document()

    # Margens ABNT
    for section in doc.sections:
        section.top_margin    = Cm(3)
        section.bottom_margin = Cm(2)
        section.left_margin   = Cm(3)
        section.right_margin  = Cm(2)

    # ── Capa ────────────────────────────────────────────────────────────────
    titulo = doc.add_heading("Declaração de Uso de Inteligência Artificial", 0)
    titulo.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    titulo.paragraph_format.space_after = Pt(4)

    for linha in [
        "Projeto Integrador — CronotaScan",
        "Disciplina: Engenharia de Software II",
        "Universidade do Vale do Itajaí — UNIVALI",
        "Grupo: José Eduardo, Márcio Fossa, Erick",
        "Data de entrega: Outubro de 2026",
    ]:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(linha)
        r.font.size = Pt(12)
        r.bold = ("Grupo" in linha or "Projeto" in linha)
        p.paragraph_format.space_after = Pt(2)

    paragrafo(doc, f"Repositório GitHub: {REPOSITORIO}", tamanho=11, centralizado=True)
    doc.add_paragraph()

    # ── 1. Apresentação ──────────────────────────────────────────────────────
    titulo_secao(doc, "1. Apresentação")
    paragrafo(doc,
        "Em conformidade com a política de transparência acadêmica da UNIVALI, este documento "
        "descreve de forma detalhada todos os pontos do projeto CronotaScan em que ferramentas "
        "de Inteligência Artificial Generativa (IAG) foram utilizadas como suporte ao "
        "desenvolvimento. Inclui o histórico completo de commits do repositório GitHub, "
        "identificando quais foram realizados com auxílio da IA e quais foram feitos "
        "exclusivamente pela equipe."
    )
    paragrafo(doc,
        "O uso de IA não substituiu o raciocínio crítico da equipe: todas as sugestões geradas "
        "foram revisadas, adaptadas e validadas pelos integrantes antes de serem incorporadas. "
        "A equipe se responsabiliza integralmente pelo conteúdo entregue."
    )

    # ── 2. Ferramenta utilizada ──────────────────────────────────────────────
    titulo_secao(doc, "2. Ferramenta de IA Utilizada")
    paragrafo(doc,
        "Ferramenta: Cursor (https://cursor.com) — ambiente de desenvolvimento integrado com IA."
    )
    item_lista(doc, "Modelo de IA: Claude Opus 5.5 / Claude Sonnet 4.6 (Anthropic)")
    item_lista(doc, "Modo: Cloud Agent — o assistente lê, edita e faz commit de arquivos do projeto sob supervisão do desenvolvedor")
    item_lista(doc, 'Identificação nos commits: o autor aparece como "Cursor Agent" ou como "Co-Authored-By: Claude Opus 5.5"')
    paragrafo(doc,
        'Cada commit feito com IA é identificado claramente no histórico do GitHub com o autor '
        '"Cursor Agent" ou com a linha Co-Authored-By. Os commits feitos somente pela equipe '
        'têm como autor o nome do integrante (jbr121 = José Eduardo, ErickFbort = Erick).'
    )

    # ── 3. Histórico de commits ──────────────────────────────────────────────
    titulo_secao(doc, "3. Histórico Completo de Commits")
    paragrafo(doc,
        f"O repositório está em: {REPOSITORIO}\n"
        "A tabela abaixo lista todos os commits em ordem cronológica. Commits com fundo "
        "amarelo envolveram o uso de IA; commits com fundo branco foram feitos exclusivamente "
        "pela equipe."
    )

    # Cabeçalho da tabela
    tabela = doc.add_table(rows=1, cols=4)
    tabela.style = "Table Grid"
    tabela.autofit = False

    # Larguras das colunas
    larguras = [Cm(2.2), Cm(3.5), Cm(3.5), Cm(8.8)]
    for i, col in enumerate(tabela.columns):
        for cell in col.cells:
            cell.width = larguras[i]

    cab = tabela.rows[0].cells
    for idx, titulo_col in enumerate(["Hash", "Data / Autor", "Mensagem do Commit", "O que foi feito"]):
        _set_cell_bg(cab[idx], "1F3864")
        _cell_text(cab[idx], titulo_col, negrito=True, tamanho=10, cor="FFFFFF")

    for commit in COMMITS:
        linha = tabela.add_row().cells
        bg = "FFF2CC" if commit["ia"] else "FFFFFF"
        _set_cell_bg(linha[0], bg)
        _set_cell_bg(linha[1], bg)
        _set_cell_bg(linha[2], bg)
        _set_cell_bg(linha[3], bg)
        _cell_text(linha[0], commit["hash"], tamanho=9)
        _cell_text(linha[1], f"{commit['data']}\n{commit['autor']}", tamanho=9)
        _cell_text(linha[2], commit["mensagem"], negrito=True, tamanho=9)
        _cell_text(linha[3], commit["descricao"], tamanho=9)

    doc.add_paragraph()
    p = doc.add_paragraph()
    r = p.add_run("Legenda: ")
    r.bold = True
    r.font.size = Pt(10)
    p.add_run("Fundo ").font.size = Pt(10)
    r2 = p.add_run("amarelo")
    r2.font.size = Pt(10)
    r2.bold = True
    p.add_run(" = commit com auxílio de IA.  Fundo ").font.size = Pt(10)
    r3 = p.add_run("branco")
    r3.font.size = Pt(10)
    r3.bold = True
    p.add_run(" = commit somente da equipe.").font.size = Pt(10)

    doc.add_paragraph()

    # ── 4. Detalhamento por área ─────────────────────────────────────────────
    titulo_secao(doc, "4. Detalhamento do Uso de IA por Área do Projeto")

    doc.add_heading("4.1 Pipeline de Visão Computacional (core/processador_imagem.py)", level=3)
    paragrafo(doc,
        "A parte mais complexa do sistema é o pipeline OpenCV que transforma a foto do disco "
        "analógico em uma curva de velocidade × tempo. A IA foi utilizada para:"
    )
    item_lista(doc, "Propor o uso de cv2.fitEllipse para detectar a borda do disco mesmo em fotos inclinadas.")
    item_lista(doc, "Desenvolver a homografia que corrige a perspectiva da foto (elipse → círculo perfeito).")
    item_lista(doc, "Sugerir cv2.warpPolar para o desdobramento polar (disco circular → imagem retangular).")
    item_lista(doc, "Criar a lógica de máscara HSV para isolar o papel branco do disco e ignorar o mousepad colorido de fundo.")
    item_lista(doc, "Implementar a autocalibração pelos anéis tracejados impressos (20, 40, 60, 80, 100 km/h).")
    item_lista(doc, "Criar a detecção da barra de atividade para ler velocidade somente nos minutos em que o caminhão está em movimento.")
    item_lista(doc, "Implementar a orientação pelo arco verde 12h–24h impresso na borda do disco.")
    paragrafo(doc,
        "Commits relacionados: b3454bb (25/09/2026), 10090b4 (09/10/2026), 634c6db (21/10/2026). "
        "Em todos, a equipe revisou o código gerado, ajustou os parâmetros com fotos reais dos "
        "discos e validou os resultados manualmente."
    )

    doc.add_heading("4.2 Testes Automatizados", level=3)
    paragrafo(doc,
        "Os testes unitários e de fixtures foram elaborados com suporte da IA:"
    )
    item_lista(doc, "tests/test_processador_imagem.py — testes do pipeline principal (commit 10090b4).")
    item_lista(doc, "tests/discos_sinteticos.py — geração de discos sintéticos com OpenCV (reto, inclinado, com lacuna).")
    item_lista(doc, "tests/test_fixtures_disco.py — comparação de resultados com gabarito JSON (commit 634c6db).")
    paragrafo(doc,
        "A equipe definiu os cenários e critérios de aceite; a IA traduziu esses cenários em código."
    )

    doc.add_heading("4.3 Laudos e PDFs", level=3)
    item_lista(doc, "laudos/laudo_discos_gabarito.pdf — laudo dos discos de gabarito (commit 920e257).")
    item_lista(doc, "laudos/explicacao_telas_e_funcoes.pdf — PDF com todas as telas e funções (commit 306196e).")
    item_lista(doc, "laudos/laudo_teste.pdf — laudo completo com imagens do sistema (commits 00aac9a e 8b438ca).")

    doc.add_heading("4.4 Documentação Acadêmica", level=3)
    paragrafo(doc,
        "A IA auxiliou na redação e formatação dos seguintes documentos entregues na disciplina:"
    )
    item_lista(doc, "M1 — Visão, Arquitetura e Planejamento do CronotaScan (Word + diagramas UML em PNG).")
    item_lista(doc, "Lean Inception — Visão do produto, É/Não é / Faz/Não faz e 3 objetivos principais.")
    item_lista(doc, "Definição do Projeto Integrador (PGI) — escopo, cronograma e riscos.")
    item_lista(doc, "Atividade de Testes (partes 1 e 2) — respostas às questões teóricas em linguagem simples.")
    item_lista(doc, "M2 — Relatório de progresso e roteiro de apresentação oral.")
    item_lista(doc, "Este documento — Declaração de Uso de IA (commit e72dcc8, 23/10/2026).")

    # ── 5. O que NÃO foi feito pela IA ──────────────────────────────────────
    titulo_secao(doc, "5. O Que NÃO Foi Feito pela IA")
    item_lista(doc, "Coleta e digitalização das fotos reais de discos de cronotacógrafo.")
    item_lista(doc, "Definição dos requisitos funcionais junto ao orientador/professor.")
    item_lista(doc, "Validação dos resultados do pipeline contra laudos reais (comparação manual de km e velocidade).")
    item_lista(doc, "Decisões de arquitetura: escolha de FastAPI, SQLite, SPA HTML/JS puro.")
    item_lista(doc, "Apresentação oral do projeto para a banca.")
    item_lista(doc, "Estrutura inicial do projeto (commit a30940f — Initial commit, feito exclusivamente pela equipe).")

    # ── 6. Resumo estatístico ────────────────────────────────────────────────
    titulo_secao(doc, "6. Resumo Estatístico")

    total = len(COMMITS)
    com_ia = sum(1 for c in COMMITS if c["ia"])
    sem_ia = total - com_ia

    tabela2 = doc.add_table(rows=4, cols=2)
    tabela2.style = "Table Grid"
    dados = [
        ("Total de commits no repositório", str(total)),
        ("Commits com auxílio de IA (fundo amarelo)", str(com_ia)),
        ("Commits somente da equipe (fundo branco)", str(sem_ia)),
        ("Repositório GitHub", REPOSITORIO),
    ]
    for i, (chave, valor) in enumerate(dados):
        linha = tabela2.rows[i].cells
        _cell_text(linha[0], chave, negrito=True, tamanho=11)
        _cell_text(linha[1], valor, tamanho=11)

    doc.add_paragraph()

    # ── 7. Assinaturas ───────────────────────────────────────────────────────
    titulo_secao(doc, "7. Declaração e Assinaturas")
    paragrafo(doc,
        "Os abaixo assinados declaram que as informações acima são verdadeiras e que "
        "o uso da IA foi realizado de forma ética, transparente e sob supervisão da equipe, "
        "em conformidade com as diretrizes da UNIVALI para projetos integradores."
    )

    doc.add_paragraph()
    for nome in ["José Eduardo", "Márcio Fossa", "Erick Franzmann Bortoloti"]:
        p = doc.add_paragraph()
        p.add_run("_" * 55).font.size = Pt(11)
        doc.add_paragraph().add_run(nome).font.size = Pt(11)
        doc.add_paragraph()

    doc.save(str(SAIDA))
    print(f"Documento salvo em: {SAIDA}")
    print(f"Commits listados: {total}  |  Com IA: {com_ia}  |  Sem IA: {sem_ia}")


if __name__ == "__main__":
    main()
