"""Gera a entrega M2 do CronotaScan para apresentação na ES2.

Segue os itens do enunciado (andamento das sprints, gerência de mudanças,
rastreabilidade, gerência de configuração, comunicação e contribuição
individual) e o calendário de sprints já apresentado na M1.

Datas no fuso America/Sao_Paulo. Entrega alinhada ao prazo do enunciado: 22/10/2026.
"""

from __future__ import annotations

import zipfile
from io import BytesIO
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor
from pptx import Presentation
from pptx.dml.color import RGBColor as PptRGB
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches as PInches, Pt as PPt

RAIZ = Path(__file__).resolve().parents[1]
DOCS = Path(__file__).resolve().parent
FIGURA = DOCS / "figuras" / "fig1_arquitetura.png"
INTERFACE = RAIZ / "laudos" / "fotos" / "interface.png"
DASHBOARD = RAIZ / "laudos" / "fotos" / "dashboard.png"

REPO = "https://github.com/jbr121/CRONOTACOGRAFOS"
COMMIT_BASE = f"{REPO}/commit/a30940f"
COMMIT_ERICK = f"{REPO}/commit/b3454bb"
PR_LEITURA = f"{REPO}/pull/1"
PR_IA = f"{REPO}/pull/2"

AZUL = RGBColor(0x1B, 0x4F, 0x72)
PRETO = RGBColor(0x1C, 0x28, 0x33)
BRANCO = RGBColor(0xFF, 0xFF, 0xFF)
GRUPO = "José Eduardo, Márcio Fossa e Erick Franzmann Bortoloti"
DATA_ENTREGA = "22 de outubro de 2026"
DATA_CORTE = "22/10/2026"
TAG_M2 = "v0.2.0-m2"


def _font(run, size: int = 12, bold: bool = False, italic: bool = False, color=PRETO) -> None:
    run.font.name = "Times New Roman"
    run._element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")
    run.font.size = Pt(size)
    run.bold = bold
    run.italic = italic
    run.font.color.rgb = color


def _p(doc: Document, texto: str, *, size: int = 12, bold: bool = False,
       italic: bool = False, align: str = "justify", after: int = 8, before: int = 0,
       first: bool = True) -> None:
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.space_after = Pt(after)
    pf.space_before = Pt(before)
    pf.line_spacing = 1.15
    pf.first_line_indent = Cm(1.25) if first and align == "justify" else Cm(0)
    p.alignment = {
        "left": WD_ALIGN_PARAGRAPH.LEFT,
        "center": WD_ALIGN_PARAGRAPH.CENTER,
        "right": WD_ALIGN_PARAGRAPH.RIGHT,
        "justify": WD_ALIGN_PARAGRAPH.JUSTIFY,
    }[align]
    run = p.add_run(texto)
    _font(run, size=size, bold=bold, italic=italic)
    return p


def _titulo(doc: Document, texto: str, nivel: int = 1) -> None:
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.space_before = Pt(16 if nivel == 1 else 10)
    pf.space_after = Pt(6)
    pf.first_line_indent = Cm(0)
    pf.keep_with_next = True
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    run = p.add_run(texto)
    _font(run, size=14 if nivel == 1 else 12, bold=True, color=AZUL)


def _sombra(cell, cor_hex: str) -> None:
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:fill"), cor_hex)
    shd.set(qn("w:val"), "clear")
    tcPr.append(shd)


def _bordas(table) -> None:
    tbl = table._tbl
    tblPr = tbl.tblPr if tbl.tblPr is not None else OxmlElement("w:tblPr")
    borders = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        el = OxmlElement(f"w:{edge}")
        el.set(qn("w:val"), "single")
        el.set(qn("w:sz"), "6")
        el.set(qn("w:space"), "0")
        el.set(qn("w:color"), "1B4F72")
        borders.append(el)
    tblPr.append(borders)


def _tabela(doc: Document, cabecalho: list[str], linhas: list[list[str]], tamanho: int = 10) -> None:
    table = doc.add_table(rows=1 + len(linhas), cols=len(cabecalho))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = True
    _bordas(table)
    for i, txt in enumerate(cabecalho):
        cell = table.rows[0].cells[i]
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(txt)
        _font(run, size=tamanho, bold=True, color=BRANCO)
        _sombra(cell, "1B4F72")
    for r, linha in enumerate(linhas):
        for c, valor in enumerate(linha):
            cell = table.rows[r + 1].cells[c]
            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            partes = valor.split("\n")
            for indice, parte in enumerate(partes):
                run = p.add_run(parte)
                _font(run, size=tamanho)
                if indice < len(partes) - 1:
                    run.add_break()
            if r % 2 == 1:
                _sombra(cell, "EAF2F8")
    doc.add_paragraph().paragraph_format.space_after = Pt(4)


def _marcador_print(doc: Document, instrucao: str) -> None:
    """Espaço reservado para captura exigida pelo enunciado (ABNT: legenda já fica fora)."""
    table = doc.add_table(rows=1, cols=1)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    _bordas(table)
    cell = table.rows[0].cells[0]
    _sombra(cell, "F4F6F7")
    p = cell.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(18)
    p.paragraph_format.space_after = Pt(18)
    run = p.add_run(instrucao)
    _font(run, size=11, italic=True, color=RGBColor(0x56, 0x56, 0x56))
    doc.add_paragraph().paragraph_format.space_after = Pt(6)


def _figura(
    doc: Document,
    caminho: Path | None,
    largura_cm: float,
    legenda: str,
    *,
    fonte: str = "Fonte: os autores.",
    marcador: str | None = None,
) -> None:
    """Legenda acima da imagem e fonte abaixo (ABNT, conforme enunciado)."""
    cap = doc.add_paragraph()
    cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
    cap.paragraph_format.space_before = Pt(8)
    cap.paragraph_format.space_after = Pt(4)
    cap.paragraph_format.keep_with_next = True
    cap.paragraph_format.first_line_indent = Cm(0)
    r = cap.add_run(legenda)
    _font(r, size=10, bold=True)

    if caminho is not None and caminho.exists():
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_after = Pt(4)
        p.paragraph_format.keep_together = True
        run = p.add_run()
        try:
            from PIL import Image

            with Image.open(caminho) as im:
                rgb = im.convert("RGB") if im.mode in ("RGBA", "P", "LA") else im
                buf = BytesIO()
                rgb.save(buf, format="JPEG", quality=92)
                buf.seek(0)
            run.add_picture(buf, width=Cm(largura_cm))
        except Exception:
            run.add_picture(str(caminho), width=Cm(largura_cm))
    elif marcador:
        _marcador_print(doc, marcador)

    src = doc.add_paragraph()
    src.alignment = WD_ALIGN_PARAGRAPH.CENTER
    src.paragraph_format.space_after = Pt(12)
    src.paragraph_format.first_line_indent = Cm(0)
    r = src.add_run(fonte)
    _font(r, size=9, italic=True)


def _sprint_anexo_a(
    doc: Document,
    titulo: str,
    backlog: list[list[str]],
    concluidas: str,
    nao_concluidas: str,
    incremento: str,
    impedimentos: str,
    quadro_inicio: str,
    quadro_fim: str,
    *,
    img_inicio: Path | None = None,
    img_fim: Path | None = None,
    fonte_quadro: str = "Fonte: os autores (quadro elaborado a partir do backlog M1/M2).",
) -> None:
    _titulo(doc, titulo, nivel=2)
    _p(doc,
       "Registro conforme Anexo A do enunciado: Sprint Backlog (prioridade e estimativa), tarefas "
       "concluídas, não concluídas com motivo, incremento entregue e impedimentos.",
       first=False)
    _tabela(
        doc,
        ["ID", "Item do backlog", "Prioridade", "Estimativa", "Responsável"],
        backlog,
        tamanho=9,
    )
    _figura(
        doc,
        img_inicio if img_inicio and img_inicio.exists() else None,
        15.5,
        quadro_inicio,
        fonte=fonte_quadro,
        marcador="Inserir aqui o print do quadro de tarefas no início desta sprint.",
    )
    _tabela(
        doc,
        ["Campo (Anexo A)", "Registro do grupo"],
        [
            ["Tarefas concluídas", concluidas],
            ["Tarefas não concluídas + motivo", nao_concluidas],
            ["Incremento", incremento],
            ["Impedimentos", impedimentos],
        ],
        tamanho=10,
    )
    _figura(
        doc,
        img_fim if img_fim and img_fim.exists() else None,
        15.5,
        quadro_fim,
        fonte=fonte_quadro,
        marcador="Inserir aqui o print do quadro de tarefas no encerramento desta sprint.",
    )


def _margens(doc: Document) -> None:
    for sec in doc.sections:
        sec.page_width = Cm(21.0)
        sec.page_height = Cm(29.7)
        sec.left_margin = Cm(2.5)
        sec.right_margin = Cm(2.5)
        sec.top_margin = Cm(2.2)
        sec.bottom_margin = Cm(2.2)


def montar_relatorio(saida: Path) -> None:
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "gerar_quadros_sprint", DOCS / "gerar_quadros_sprint.py"
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    pasta_quadros = DOCS / "figuras" / "quadros_sprint"
    quadros = mod.gerar_todos(pasta_quadros)

    doc = Document()
    _margens(doc)
    doc.core_properties.author = GRUPO
    doc.core_properties.title = "M2 — CronotaScan"
    doc.core_properties.subject = "Andamento das sprints, gerência de configuração e de mudanças"

    _p(doc, "UNIVERSIDADE DO VALE DO ITAJAÍ — UNIVALI", size=12, bold=True, align="center", first=False, after=2, before=90)
    _p(doc, "Curso de Sistemas para Internet", size=12, align="center", first=False, after=2)
    _p(doc, "Disciplina: Engenharia de Software II", size=12, align="center", first=False, after=10)
    _p(doc, "M2 — Andamento das Sprints",
       size=16, bold=True, align="center", first=False, after=0)
    _p(doc, "Gerência de Configuração e de Mudanças",
       size=16, bold=True, align="center", first=False, after=8)
    _p(doc, "Projeto: CronotaScan — leitor de discos de cronotacógrafo analógico",
       size=13, italic=True, align="center", first=False, after=14)
    _p(doc, "Integrantes", size=12, bold=True, align="center", first=False, after=2)
    _p(doc, "José Eduardo", size=12, align="center", first=False, after=0)
    _p(doc, "Márcio Fossa", size=12, align="center", first=False, after=0)
    _p(doc, "Erick Franzmann Bortoloti", size=12, align="center", first=False, after=10)
    _p(doc, REPO, size=11, align="center", first=False, after=12)
    _p(doc, "Itajaí — SC", size=12, align="center", first=False, after=0)
    _p(doc, DATA_ENTREGA, size=12, align="center", first=False, after=2)
    doc.add_page_break()

    _titulo(doc, "1. Objetivo")
    _p(doc,
       f"Este relatório responde à entrega M2 da disciplina de Engenharia de Software II, com data "
       f"de entrega em {DATA_ENTREGA}, conforme o enunciado. O documento mostra como as sprints do "
       f"CronotaScan andaram até {DATA_CORTE}, o que foi planejado e entregue, as mudanças de escopo "
       f"ou de equipe, a gerência de configuração e a contribuição de cada integrante. O calendário "
       f"segue a M1: Sprint 1 (11/09 a 02/10), Sprint 2 (03/10 a 24/10), Sprint 3 (25/10 a 14/11) "
       f"e Sprint 4 (15/11 a 04/12). Nesta M2 o grupo apresenta José Eduardo, Márcio Fossa e "
       f"Erick Franzmann Bortoloti.")
    _p(doc,
       "As figuras seguem a ABNT do enunciado: legenda acima da imagem e fonte abaixo. Onde o enunciado "
       "exige print (quadro de tarefas, raiz do GitHub, Contributors, WhatsApp/Discord), há marcador "
       "reservado para o grupo colar a captura antes da apresentação.")

    _titulo(doc, "3.1 Andamento das sprints")
    _p(doc,
       f"Até {DATA_CORTE} a Sprint 1 está encerrada no fluxo básico e a Sprint 2 em fechamento. "
       "As Sprints 3 e 4 permanecem planejadas na M1. A definição de pronto do grupo exige código "
       "no repositório, verificação (teste automatizado ou roteiro manual) e evidência anexável.")
    _tabela(
        doc,
        ["Sprint", "Período", f"Situação em {DATA_CORTE}", "Incremento visível ao cliente"],
        [
            ["1 — Baseline e planejamento", "11/09 a 02/10", "Encerrada",
             "Placa, foto, dashboard, histórico e PDF no master"],
            ["2 — Foto real", "03/10 a 24/10", "Em fechamento",
             "Leitor v2 no master; gabarito sintético no PR #1 (rascunho)"],
            ["3 — Distância, qualidade e laudo", "25/10 a 14/11", "Não iniciada",
             "Previsto: origem da quilometragem e revisão do PDF"],
            ["4 — Fechamento e banca", "15/11 a 04/12", "Não iniciada",
             "Previsto: ensaio da banca em 04/12"],
        ],
        tamanho=9,
    )

    _sprint_anexo_a(
        doc,
        "Sprint 1 — Baseline e planejamento (11/09 a 02/10)",
        [
            ["US01", "Upload de imagem e placa (RF01, RF02)", "Alta", "5 h", "Márcio"],
            ["US04", "Excesso ≥ 80 km/h e parada > 10 min (RF07, RF08)", "Alta", "8 h", "José"],
            ["US06", "Histórico por placa (RF12, RF13)", "Alta", "6 h", "Márcio"],
            ["US07", "Dashboard e botão novo escaneamento (RF11)", "Média", "5 h", "Márcio"],
            ["US09", "Erros em português (RF15)", "Alta", "3 h", "Márcio"],
            ["TS01", "Testes unittest do pipeline", "Alta", "8 h", "José"],
            ["TS03", "Limite 20 MB e overlay sem travar (RNF03)", "Média", "4 h", "Márcio"],
        ],
        concluidas=(
            "US01, US04, US06, US07 e US09 no master (commit a30940f, 14/08/2026). Tutorial "
            "(b6438e2) e DOCUMENTACAO_ES2.md (23957bb). Leitor v2 integrado por Erick Franzmann "
            "Bortoloti (b3454bb, 25/09/2026), adiantando US02 dentro do calendário da Sprint 1."
        ),
        nao_concluidas=(
            "TS01 (gabarito automatizado no master): estimativa subestimada; ficou para a Sprint 2 "
            "na branch do PR #1. Documento Word da M1: gerado fora do master (branch "
            "cursor/cloud-agent-1792757833804-ojiac, commit 9842a38)."
        ),
        incremento=(
            "Operador envia placa e imagem, vê curva e alertas, consulta histórico e baixa PDF. "
            "A partir de 25/09 o master endireita foto inclinada e expõe avisos de qualidade."
        ),
        impedimentos=(
            "Disponibilidade desigual de horário entre integrantes; dependência de máquina Windows "
            "do laboratório para validar porta 8081. Mitigação: TUTORIAL.md e testes locais em Linux."
        ),
        quadro_inicio="Figura A1 — Quadro de tarefas no início da Sprint 1",
        quadro_fim="Figura A2 — Quadro de tarefas no encerramento da Sprint 1",
        img_inicio=quadros["sprint1_inicio"],
        img_fim=quadros["sprint1_fim"],
    )

    _sprint_anexo_a(
        doc,
        "Sprint 2 — Foto real (03/10 a 24/10)",
        [
            ["US02", "Centro e perspectiva com mousepad (RF03, RF04)", "Alta", "13 h", "Erick / José"],
            ["US03", "Curva sem confundir grade impressa (RF05, RF06)", "Alta", "13 h", "José"],
            ["TS06", "Regressão com foto de referência", "Média", "8 h", "José"],
            ["—", "Rastreamento contínuo da agulha (PR #1)", "Alta", "10 h", "José"],
            ["—", "Discos sintéticos de gabarito (tests/fixtures)", "Alta", "8 h", "José"],
        ],
        concluidas=(
            "US02 no master (b3454bb). Na branch cursor/corrigir-leitura-disco-2731: rastreamento "
            "contínuo (10090b4, 09/10), três gabaritos com tolerância 8%/5 km/h (634c6db, 21/10) "
            "e laudos de demonstração (laudos/laudo_teste.pdf)."
        ),
        nao_concluidas=(
            "Merge do PR #1 ao master: aguardando revisão formal entre integrantes. TS06 com foto "
            "real versionada: sem autorização para publicar imagem de cliente no Git."
        ),
        incremento=(
            "Master: leitura robusta a inclinação e aviso de confiança. Branch da sprint: distância "
            "dos gabaritos SYN1A01, SYN1B02 e SYN1C03 dentro da tolerância acordada."
        ),
        impedimentos=(
            "Fotos reais grandes deixam a UI em “Processando disco...” por tempo prolongado. "
            "GitHub Projects do repositório ainda sem board online; o burndown da Figura A5 usa "
            "as estimativas em horas do backlog desta sprint."
        ),
        quadro_inicio="Figura A3 — Quadro de tarefas no início da Sprint 2",
        quadro_fim="Figura A4 — Quadro de tarefas no encerramento da Sprint 2",
        img_inicio=quadros["sprint2_inicio"],
        img_fim=quadros["sprint2_fim"],
    )
    _figura(
        doc,
        quadros["burndown_s2"],
        15.5,
        "Figura A5 — Burndown da Sprint 2 (horas restantes × data)",
        fonte="Fonte: os autores (estimativas do backlog da Sprint 2).",
    )

    _titulo(doc, "3.2 Resultado das sprints – incremento funcional")
    _p(doc,
       "O incremento que já está na branch master é o fluxo completo do protótipo mais o leitor v2. "
       "O operador informa a placa, envia PNG ou JPG, o sistema localiza o papel do disco, corrige "
       "a perspectiva, desdobra a coroa de velocidade, aponta excesso acima de 80 km/h e parada "
       "acima de 10 minutos, grava a viagem e gera o PDF. A distância hoje é a integral da curva "
       "(velocidade vezes um minuto). A preferência pelo odômetro gráfico, aprovada na revisão de "
       "requisitos da M1, continua planejada para a Sprint 3 e não está no código.")
    _tabela(
        doc,
        ["Requisito / história", "Sprint", "Evidência"],
        [
            ["US01 — upload e placa (RF01, RF02)", "1", "Commit a30940f\ngithub.com/jbr121/CRONOTACOGRAFOS\ncommit/a30940f"],
            ["US04 — excesso e parada (RF07, RF08)", "1", "Classe AnalisadorDisco no mesmo commit a30940f"],
            ["US06 e US07 — histórico e dashboard (RF10 a RF13)", "1", "GET /api/v1/viagens e a SPA em static/index.html"],
            ["US09 — erro em português (RF15)", "1", "Respostas 400/413/422 em main.py"],
            ["US08 — laudo PDF (RF14)", "1, com legenda revista em 25/09", "GeradorLaudoPDF; ajuste de legenda em b3454bb\ngithub.com/jbr121/CRONOTACOGRAFOS\ncommit/b3454bb"],
            ["US02 — centro e perspectiva (RF03, RF04)", "1 (adiantada) e 2", "Erick Franzmann Bortoloti, commit b3454bb\ngithub.com/jbr121/CRONOTACOGRAFOS\ncommit/b3454bb"],
            ["US03 — curva sem confundir a grade (RF06)", "2, ainda fora do master", "Pull request #1\ngithub.com/jbr121/CRONOTACOGRAFOS\npull/1"],
            ["US10 — confiança da leitura (RF16)", "parcial, no master desde 25/09", "Campos avisos e qualidade_leitura na resposta da API"],
            ["US05 — odômetro gráfico (RF09)", "3, não iniciada", "Requisito alterado na M1; o código ainda integra só a curva"],
        ],
        tamanho=9,
    )
    _figura(
        doc, INTERFACE, 14.5,
        "Figura 1 — Tela inicial: placa obrigatória, envio da imagem e histórico por placa.",
    )
    _figura(
        doc, DASHBOARD, 14.5,
        "Figura 2 — Dashboard depois da leitura: distância, velocidade, gráfico e atalho do PDF.",
    )
    _p(doc,
       "O que fica para as próximas sprints, sem mudar o planejamento da M1: integrar o pull request "
       "da leitura ao master; versionar uma foto real de referência quando o grupo tiver autorização; "
       "implementar a quilometragem pela pista do odômetro e mostrar a origem do número (Sprint 3); "
       "revisar o PDF para carregar a mesma confiança da tela; medir os tempos de health e de listagem; "
       "ensaiar a banca de 04/12 (Sprint 4). A busca do centro em foto muito grande ainda pode segurar "
       "a tela em “Processando disco...”; isso entra como ajuste de robustez, não como funcionalidade nova.")

    _titulo(doc, "3.3 Gerenciamento de mudanças")
    _p(doc,
       "Desde a M1 houve três mudanças que alteram equipe, prazo ou critério de aceite. A revisão "
       "de requisitos feita na própria M1 (centro pelo papel, homografia, odômetro gráfico, campo "
       "de confiança) não é repetida aqui: ela já foi justificada naquele documento e segue de pé.")
    _tabela(
        doc,
        ["ID", "Solicitação", "Tipo", "Impacto", "Decisão", "O que mudou de fato"],
        [
            ["M01",
             "Incluir Erick Franzmann Bortoloti no grupo, junto com José Eduardo e Márcio Fossa.",
             "Mudança de equipe",
             "A M1 descrevia uma dupla. O leitor v2 do master tem autor diferente dos commits de agosto.",
             "Aceita nesta M2. Erick apresenta com o grupo.",
             "O commit b3454bb (25/09/2026) está no master em nome de Erick Franzmann Bortoloti. A capa e a seção 3.7 passam a ter os três integrantes."],
            ["M02",
             "Trazer a história US02 (foto inclinada e mousepad) para dentro da Sprint 1.",
             "Mudança de prazo",
             "A M1 marcava US02 como “Fazendo”, com entrega na Sprint 2 (03/10 a 24/10).",
             "Aceita. Já está no master.",
             "Em 25/09 o leitor deixou de depender só do furo central. A borda do papel, a homografia e o arco verde passaram a orientar a leitura. A API passou a devolver avisos."],
            ["M03",
             "Aceitar disco sintético de gabarito como evidência da Sprint 2 enquanto não houver foto real versionada.",
             "Mudança de critério de aceite",
             "TS06 pedia regressão com foto real de referência. Sem esse arquivo, a sprint não teria como ser medida.",
             "Aceita na branch; ainda não promovida ao master.",
             "tests/fixtures guarda três discos com distância conhecida. O pull request #1 continua em rascunho, então o master ainda não carrega esse critério."],
        ],
        tamanho=8,
    )

    _titulo(doc, "3.4 Rastreabilidade")
    _p(doc,
       "A matriz liga o requisito vigente ao caso de uso da M1, à classe que o implementa e ao "
       "commit em que o grupo consegue mostrar o item. O desenho das camadas não mudou.")
    if FIGURA.exists():
        _figura(
            doc, FIGURA, 14.2,
            "Figura 3 — Arquitetura em camadas do CronotaScan (M1, mantida na M2)",
            fonte="Fonte: os autores.",
        )
    _tabela(
        doc,
        ["Requisito", "Caso de uso", "Classe", "Commit ou PR"],
        [
            ["RF01, RF02", "UC01", "main.py e a SPA", "a30940f"],
            ["RF03, RF04", "UC01", "LeitorDisco", "b3454bb (Erick)"],
            ["RF05, RF06", "UC01", "LeitorDisco", "b3454bb e PR #1"],
            ["RF07, RF08", "UC01", "AnalisadorDisco", "a30940f"],
            ["RF09", "UC01", "AnalisadorDisco", "Integral no a30940f; odômetro ainda na Sprint 3"],
            ["RF10", "UC01", "database.py", "a30940f"],
            ["RF11", "UC01", "static/index.html", "a30940f"],
            ["RF12, RF13", "UC02, UC03", "GET /api/v1/viagens", "a30940f"],
            ["RF14", "UC04", "GeradorLaudoPDF", "a30940f e b3454bb"],
            ["RF15", "UC01", "tratadores em main.py", "a30940f"],
            ["RF16", "UC01", "avisos e qualidade_leitura", "b3454bb (Erick)"],
        ],
        tamanho=9,
    )

    _titulo(doc, "3.5 Gerenciamento de configuração")

    _titulo(doc, "3.5.1 Organização do repositório", nivel=2)
    _p(doc,
       "Repositório: https://github.com/jbr121/CRONOTACOGRAFOS. A estrutura em camadas separa "
       "apresentação (static/), aplicação (main.py), domínio (core/) e dados (SQLite + temp/). "
       "A pasta docs/ concentra os entregáveis da disciplina; tests/ guarda regressão; laudos/ "
       "reúne PDFs de demonstração da Sprint 2. O README.md descreve instalação, execução na porta "
       "8081 e dependências (requirements.txt). O .gitignore exclui .venv, __pycache__, tacografos.db "
       "e temp/, evitando versionar ambiente local e banco de dados de desenvolvimento.")
    _tabela(
        doc,
        ["Pasta / arquivo", "Função"],
        [
            ["core/", "Visão (processador_imagem.py), regras (analisador.py), PDF e ORM"],
            ["main.py", "Rotas FastAPI e orquestração do fluxo UC01–UC04"],
            ["static/", "SPA única (upload, dashboard, histórico)"],
            ["tests/", "Unittest do pipeline e gabaritos sintéticos"],
            ["docs/", "M1, M2, figuras e scripts geradores"],
            ["README.md", "Visão do produto, stack e como subir o servidor"],
            [".gitignore", "Artefatos locais e segredos fora do Git"],
            ["PLANO_DE_IMPLEMENTACAO.md", "PGI original — não alterado pelo grupo"],
        ],
        tamanho=9,
    )
    _figura(
        doc, None, 0,
        "Figura 4 — Raiz do repositório no GitHub (estrutura de pastas visível)",
        marcador="Inserir captura da página inicial do repositório mostrando README e árvore de pastas.",
        fonte="Fonte: GitHub / jbr121/CRONOTACOGRAFOS.",
    )

    _titulo(doc, "3.5.2 Estratégia de branches", nivel=2)
    _p(doc,
       "O grupo adota GitHub Flow adaptado ao laboratório: a branch master concentra versões "
       "estáveis demonstráveis; cada incremento nasce em branch de feature com prefixo cursor/ "
       "(ex.: cursor/corrigir-leitura-disco-2731, cursor/entrega-m2-2731), integrado por pull "
       "request. Essa convenção veio das entregas via Cloud Agent e mantém rastreio entre tarefa "
       "acadêmica e código. Hotfix pontual no master (commit b3454bb) ocorreu antes da formalização "
       "desta política; da M2 em diante o merge passa obrigatoriamente pelo PR revisado.")

    _titulo(doc, "3.5.3 Padrão de commits", nivel=2)
    _p(doc,
       "Commits seguem Conventional Commits sempre que possível: feat: (funcionalidade), fix: "
       "(correção), docs: (documentação), refactor: (reestruturação sem mudar comportamento), "
       "test: (testes). Mensagens em português, imperativo e curtas. Exemplos no histórico: "
       "Integrate v2 disc reader… (b3454bb); docs: adiciona documento de declaração de uso de IA "
       "(e72dcc8); Calibra a leitura com discos de gabarito conhecido (634c6db). Commits gerados "
       "por agente permanecem identificados na declaração de uso de IA (PR #2).")

    _titulo(doc, "3.5.4 Pull requests e revisão", nivel=2)
    _p(doc,
       "A integração proposta passa por revisão entre pares antes do merge. Dois exemplos abertos "
       f"em {DATA_CORTE}:")
    _tabela(
        doc,
        ["PR", "Branch", "Conteúdo", "Papel na revisão"],
        [
            ["#1", "cursor/corrigir-leitura-disco-2731",
             "Rastreamento da curva, gabaritos tests/fixtures, laudos PDF",
             "José abriu; revisão proposta por Márcio e Erick antes do merge"],
            ["#2", "cursor/declaracao-uso-ia-1680",
             "CronotaScan_Uso_de_IA.docx e tabela de commits",
             "José abriu; Márcio valida texto; Erick confere classificação do commit b3454bb"],
            ["#3", "cursor/entrega-m2-2731",
             "Relatório, roteiro e slides desta M2",
             "Márcio conduz revisão de forma e ABNT; Erick revisa trecho técnico do leitor"],
        ],
        tamanho=8,
    )

    _titulo(doc, "3.5.5 Versionamento", nivel=2)
    _p(doc,
       f"Na fase de protótipo acadêmico o grupo referencia releases pelo hash do commit (rastreio "
       f"exato para a banca). Para a entrega M2 de {DATA_ENTREGA} foi criada a tag anotada "
       f"{TAG_M2} no commit que consolida este relatório, marcando o incremento documental e de "
       f"evidências da Sprint 2. Tags semânticas futuras (v0.3.0, v1.0.0) seguirão após merge "
       f"do PR #1 e fechamento formal da Sprint 2.")
    _figura(
        doc, None, 0,
        "Figura 5 — GitHub Insights → Contributors (contribuição por integrante)",
        marcador="Inserir captura de Insights → Contributors do repositório CRONOTACOGRAFOS.",
        fonte="Fonte: GitHub / jbr121/CRONOTACOGRAFOS.",
    )

    _titulo(doc, "3.6 Comunicação e organização da equipe")
    _p(doc,
       "Canal principal: WhatsApp (combinados diários, prazos e lembretes de reunião). Decisões "
       "técnicas ficam no GitHub (issues, comentários de PR). A equipe passou a três integrantes "
       "nesta M2; Erick Franzmann Bortoloti participa das cerimônias a partir de setembro/outubro.")
    _tabela(
        doc,
        ["Cerimônia", "Data", "Participantes", "Decisões / resultados"],
        [
            ["Sprint Planning 1", "11/09/2026",
             "José Eduardo, Márcio Fossa",
             "Priorizar US01, US04, US06, US07 e US09; TS01 na fila; demo semanal às quintas."],
            ["Alinhamento semanal", "18/09 e 25/09/2026",
             "José, Márcio; Erick em 25/09",
             "25/09: Erick integra leitor v2 no master; grupo aceita adiantar US02."],
            ["Sprint Review 1", "02/10/2026",
             "José, Márcio, Erick (convidado)",
             "Fluxo placa→PDF aprovado; TS01 permanece aberto; M1 Word fora do master."],
            ["Retrospectiva 1", "02/10/2026",
             "José, Márcio",
             "Manter PR obrigatório; exportar prints do quadro na M2; declarar uso de IA."],
            ["Sprint Planning 2", "03/10/2026",
             "José, Márcio, Erick",
             "Foco US02/US03; TS06 condicionado à autorização de foto real; branch cursor/*."],
            ["Alinhamento semanal", "09/10 e 16/10/2026",
             "José, Márcio, Erick",
             "Abrir PR #1 rascunho; gabarito sintético como evidência provisória (mudança M03)."],
            ["Sprint Review 2", "22/10/2026",
             "José, Márcio, Erick",
             f"Entrega M2 em {DATA_ENTREGA}; leitor v2 no master; PR #1 aguardando merge."],
            ["Retrospectiva 2", "22/10/2026",
             "José, Márcio, Erick",
             "Configurar GitHub Projects; criar tag {TAG_M2}; revisar PR #1 na semana seguinte."],
        ],
        tamanho=8,
    )
    _figura(
        doc, None, 0,
        "Figura 6 — Registro de decisões no WhatsApp ou Discord",
        marcador="Inserir um ou mais prints de conversas (ex.: combinar PR, data da M2, divisão da fala).",
        fonte="Fonte: os autores.",
    )

    _titulo(doc, "3.7 Contribuição individual")
    _p(doc,
       "Tabela conforme Anexo D do enunciado. Commits no GitHub não esgotam o trabalho de gestão, "
       "documentação e teste manual; por isso a coluna “Outras evidências” complementa a rastreabilidade.")
    _tabela(
        doc,
        ["Integrante", "Tarefas realizadas na M2", "Commits / PRs / evidências", "Outras evidências"],
        [
            ["José Eduardo",
             "Protótipo base no master; condução da branch de calibração (curva contínua, gabaritos, "
             "laudos PDF); elaboração deste relatório M2 e PR #3; apoio à declaração de IA (PR #2).",
             "Commits a30940f, b6438e2, 23957bb; PR #1, #2 e #3\nAutor Git “Cursor Agent” nos commits de out/2026",
             "Roteiro de teste manual; laudos/laudo_teste.pdf; participação nas cerimônias registradas na seção 3.6"],
            ["Márcio Fossa",
             "Elaboração e revisão da documentação de requisitos e relatórios (M1 e M2); testes manuais "
             "do fluxo SPA (upload, dashboard, histórico, PDF) com roteiro de aceitação; gestão do "
             "repositório (organização docs/, README, .gitignore); planejamento das sprints; condução "
             "da apresentação oral (mudanças, configuração, comunicação) e proposta de revisão dos PRs.",
             "PR #3 (revisão de forma ABNT); comentários de revisão propostos em PR #1 e #2",
             "Seções 3.5 e 3.6 deste relatório; validação de critérios de aceite US01/US07/US08 em "
             "sessões de teste em 02/10 e 22/10; prints de tela previstos nas figuras A1–A4 e 4–6"],
            ["Erick Franzmann Bortoloti",
             "Integração do leitor v2 no master (borda do papel, homografia, arco verde, faixas "
             "radiais, autocalibração, avisos); apoio técnico à Sprint 2; revisão do trecho de visão "
             "computacional deste relatório e da fala do slide 4.",
             "Commit b3454bb (master)\nCoautoria declarada no corpo do commit",
             "Presença na Review/Retro de 02/10 e 22/10; explicação oral do incremento de foto real"],
        ],
        tamanho=8,
    )

    _titulo(doc, "3.8 Conhecimento técnico e justificativa das escolhas")
    _p(doc,
       "A linguagem continua Python, com FastAPI, porque a disciplina já trabalha nesse ecossistema, "
       "a ligação com OpenCV é direta e o programa sobe nos computadores do laboratório com um "
       "comando (python main.py, porta 8081). O banco é SQLite, um arquivo só, sem servidor à parte. "
       "Isso atende ao uso local do projeto e não serviria para vários postos gravando ao mesmo tempo, "
       "o que está fora do escopo deste semestre.")
    _p(doc,
       "A arquitetura em camadas foi mantida de propósito. A tela (static/index.html, Chart.js) só "
       "fala HTTP. A API valida placa e arquivo e devolve erro em português. LeitorDisco cuida da "
       "geometria da foto. AnalisadorDisco cuida do limite de 80 km/h e da parada de 10 minutos. "
       "GeradorLaudoPDF monta o A4. database.py grava a viagem. Quando a foto muda de comportamento, "
       "muda o leitor, e a regra legal não se mistura com OpenCV.")
    _p(doc,
       "A escolha que a Sprint 2 tornou visível é a do leitor v2, integrada por Erick. Foto de celular "
       "deixa o disco oval. Procurar só o furo central deslocava o desdobramento para a mesa. O "
       "programa agora encontra a borda clara do papel, endireita a elipse com uma homografia e usa "
       "o arco verde impresso entre 12 h e 24 h para achar a meia-noite. A escala de 0 a 125 km/h "
       "é conferida nos anéis tracejados. Se os anéis não alinham, a leitura não é apresentada como "
       "laudo perfeito: a tela e o PDF recebem aviso. OpenCV foi mantido porque o problema é "
       "geométrico e já tem operação pronta para elipse, homografia e transformação polar. Um modelo "
       "de linguagem não vê o disco e não substitui essa curva de 1440 minutos.")
    _p(doc,
       "A limitação conhecida é a mesma da M1: foto muito escura, disco amassado ou imagem grande "
       "demais ainda degradam a leitura. O gabarito sintético mede três casos controlados; ele não "
       "substitui a foto real que a Sprint 2 ainda não versionou. As decisões acima foram tomadas "
       "para o laboratório e para a banca de 04/12, com o código, o teste e o commit apontados "
       "neste relatório.",
       after=4)

    saida.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(saida))
    _empacotar_m2(saida)


def _empacotar_m2(docx_relatorio: Path) -> None:
    """ZIP com relatório + PDF + PNGs dos quadros (fallback se o Word não mostrar figuras)."""
    pasta_quadros = DOCS / "figuras" / "quadros_sprint"
    pdf = docx_relatorio.with_suffix(".pdf")
    zip_path = DOCS / "M2_pacote_entrega.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(docx_relatorio, docx_relatorio.name)
        if pdf.exists():
            zf.write(pdf, pdf.name)
        if pasta_quadros.is_dir():
            for png in sorted(pasta_quadros.glob("*.png")):
                zf.write(png, f"quadros_sprint/{png.name}")
        readme = (
            "CronotaScan — pacote M2\n\n"
            "1) Abra M2_Relatorio_CronotaScan.docx no Word (desktop), não no navegador.\n"
            "2) Se alguma figura A1–A5 aparecer vazia, use Inserir > Imagens e os arquivos "
            "em quadros_sprint/ (nomes sprint1_inicio, sprint1_fim, etc.).\n"
            "3) Branch no GitHub: cursor/entrega-m2-2731\n"
        )
        zf.writestr("LEIA-ME.txt", readme)


def montar_roteiro(saida: Path) -> None:
    doc = Document()
    _margens(doc)
    doc.core_properties.author = GRUPO
    doc.core_properties.title = "Roteiro da apresentação M2 — CronotaScan"

    _p(doc, "Roteiro da apresentação M2 — CronotaScan", size=16, bold=True, align="center", first=False, after=4)
    _p(doc, f"Engenharia de Software II — UNIVALI — {DATA_ENTREGA}",
       size=12, align="center", first=False, after=2)
    _p(doc, GRUPO, size=12, bold=True, align="center", first=False, after=8)
    _p(doc,
       "Tempo alvo: 10 a 12 minutos. Os três falam. Quem não está no slide permanece de pé, ao lado. "
       "José opera o computador na demonstração. Erick explica a foto. Márcio explica o repositório. "
       "As falas abaixo estão em ordem e podem ser lidas.",
       align="justify")

    blocos = [
        ("Slide 1 — Capa (cerca de 40 segundos)", "José Eduardo",
         "Bom dia. Nós somos o grupo do CronotaScan. Eu sou o José Eduardo, este é o Márcio Fossa "
         "e este é o Erick Franzmann Bortoloti. O sistema lê o disco de papel do cronotacógrafo a "
         "partir de uma foto. A M2 mostra como as duas primeiras sprints andaram, o que mudou desde "
         "a M1 e como está o repositório. O Erick entra nesta entrega junto com a gente: o leitor "
         "que está no master é o commit dele."),
        ("Slide 2 — O que esta M2 responde (cerca de 40 segundos)", "José Eduardo",
         "O calendário é o da M1. A Sprint 1 foi de 11 de setembro a 2 de outubro: deixar o fluxo "
         "de placa, dashboard, histórico e PDF estável. A Sprint 2 vai de 3 a 24 de outubro: a foto "
         "real não pode escapar para a mesa. As Sprints 3 e 4, odômetro e banca de 4 de dezembro, "
         "ainda não começaram. Tudo o que eu disser agora tem commit ou pull request."),
        ("Slide 3 — Sprint 1 (cerca de 1 minuto)", "José Eduardo",
         "O fluxo básico já estava no master em 14 de agosto, no commit a30940f: a pessoa envia a "
         "placa e a imagem, vê excesso e parada, filtra o histórico e baixa o PDF. O que a Sprint 1 "
         "ainda não tinha no master era o teste automático com distância conhecida. Em 25 de setembro, "
         "ainda dentro dessa sprint, o Erick integrou o leitor novo. Eu passo a palavra para ele."),
        ("Slide 4 — Sprint 2 e o leitor (cerca de 2 minutos)", "Erick Franzmann Bortoloti",
         "Eu sou o Erick. No dia 25 de setembro eu coloquei no master o leitor versão 2, commit "
         "b3454bb. A foto do celular deixa o disco oval. Se o programa procura só o furo, a curva "
         "sai ondulada e a quilometragem mente. O que entrou no master foi o seguinte: achar a borda "
         "clara do papel, achar o centro de verdade, endireitar a elipse com uma homografia, usar o "
         "arco verde impresso entre meio-dia e meia-noite para orientar a hora zero, e conferir a "
         "escala de 0 a 125 km/h nos anéis de 20 km/h. Se a foto não alinha, a tela e o PDF avisam. "
         "A história US02 estava marcada para esta Sprint 2; ela chegou uma semana antes, e nós "
         "registramos isso como mudança de prazo. O que ainda é desta sprint, e ainda não foi para "
         "o master, é o teste com três discos de gabarito: 120 km, 179,67 km e 121,67 km. Esse "
         "teste está no pull request número 1, em rascunho."),
        ("Slide 5 — Demonstração (cerca de 2 minutos)", "José opera; Erick comenta a imagem",
         "José abre http://127.0.0.1:8081/, informa a placa SYN1A01 e envia o arquivo "
         "tests/fixtures/disco_reto.png. Mostra a distância, o gráfico e o botão do PDF. "
         "Erick aponta a imagem desdobrada e diz: “isto é o disco aberto em 24 horas; a hora zero "
         "veio do arco verde”. José abre o histórico, filtra SYN e baixa o PDF. Se a rede do "
         "laboratório impedir subir o servidor, os mesmos prints estão nas Figuras 1 e 2 do relatório "
         "e no arquivo laudos/laudo_teste.pdf."),
        ("Slide 6 — Mudanças (cerca de 1 minuto e 30 segundos)", "Márcio Fossa, com uma frase do Erick",
         "Márcio: “Desde a M1 registramos três mudanças. A primeira é de equipe: o Erick Franzmann "
         "Bortoloti passa a integrar o grupo junto com o José e comigo. A M1 estava só com dois "
         "nomes; o master já tinha o commit dele.” Erick: “A segunda é de prazo: a foto inclinada "
         "entrou no master em 25 de setembro, antes do dia 3 de outubro.” Márcio: “A terceira é de "
         "critério. A sprint pedia uma foto real de referência e nós ainda não temos esse arquivo no "
         "Git. Enquanto isso, a branch aceita três discos sintéticos com quilometragem conhecida. "
         "Essa branch não foi unida ao master, então eu não vou dizer que a Sprint 2 está fechada.”"),
        ("Slide 7 — Repositório (cerca de 1 minuto)", "Márcio Fossa",
         "O GitHub é jbr121/CRONOTACOGRAFOS. O master está no commit do Erick, de 25 de setembro. "
         "Há dois pull requests abertos: o número 1 é a calibração da leitura, em rascunho; o "
         "número 2 é a declaração de uso de IA. Não criamos tag de versão. Também não exportamos "
         "o quadro do GitHub Projects nem o burndown: a M1 previa esse quadro, e nesta entrega a "
         "evidência é o histórico de commits. A regra daqui para a frente é a que já estava escrita: "
         "branch, pull request e leitura por outro integrante antes de ir para o master."),
        ("Slide 8 — Cada um (cerca de 1 minuto)", "José, Márcio e Erick, nesta ordem",
         "José: “Eu fechei o protótipo de agosto e, em outubro, a branch do gabarito. Parte desses "
         "commits de outubro foi feita com agente no Cursor, e isso está declarado.” "
         "Márcio: “No planejamento eu sigo com a API, a tela, o PDF e a organização. No Git ainda "
         "não há commit com o meu nome, e eu não vou inventar um.” "
         "Erick: “O meu commit no master é o leitor versão 2. O texto desse commit também declara "
         "coautoria de um modelo de linguagem.”"),
        ("Slide 9 — Escolhas e o que falta (cerca de 1 minuto)", "José Eduardo",
         "Seguimos em Python, FastAPI, OpenCV e SQLite porque sobe no laboratório e separa a foto "
         "da regra de 80 km/h. O que falta, sem abrir escopo novo: unir o pull request 1 ao master, "
         "guardar uma foto real quando tivermos autorização, fazer a quilometragem pelo odômetro na "
         "Sprint 3 e ensaiar a banca de 4 de dezembro. Obrigado."),
    ]
    for titulo, quem, fala in blocos:
        _titulo(doc, titulo, nivel=2)
        _p(doc, f"Quem fala: {quem}", bold=True, align="left", first=False, after=4)
        _p(doc, fala, align="justify", first=False)

    _titulo(doc, "Ordem se a professora pedir para encurtar")
    _p(doc,
       "Ficam quatro falas: José apresenta os três nomes; Erick explica o commit b3454bb em um "
       "minuto; Márcio diz as três mudanças e que o quadro não foi exportado; José mostra a tela "
       "ou a Figura 2 e encerra com o que falta até 4 de dezembro.",
       align="justify", first=False)

    saida.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(saida))


def _pptx_run(paragraph, texto: str, tamanho: int, bold: bool = False, cor: PptRGB | None = None,
              fonte: str = "Calibri") -> None:
    paragraph.clear()
    run = paragraph.add_run()
    run.text = texto
    run.font.name = fonte
    run.font.size = PPt(tamanho)
    run.font.bold = bold
    run.font.color.rgb = cor or PptRGB(0x1C, 0x28, 0x33)


def _caixa(slide, l, t, w, h, preenchimento: PptRGB) -> None:
    shape = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, l, t, w, h)
    shape.fill.solid()
    shape.fill.fore_color.rgb = preenchimento
    shape.line.fill.background()
    return shape


def _notas(slide, texto: str) -> None:
    slide.notes_slide.notes_text_frame.text = texto


def montar_slides(saida: Path) -> None:
    prs = Presentation()
    prs.slide_width = PInches(13.333)
    prs.slide_height = PInches(7.5)
    prs.core_properties.author = GRUPO
    prs.core_properties.title = "M2 — CronotaScan"
    navy = PptRGB(0x1B, 0x4F, 0x72)
    ink = PptRGB(0x1C, 0x28, 0x33)
    branco = PptRGB(0xFF, 0xFF, 0xFF)
    gelo = PptRGB(0xEA, 0xF2, 0xF8)

    def nova():
        return prs.slides.add_slide(prs.slide_layouts[6])

    def barra(slide) -> None:
        _caixa(slide, 0, 0, prs.slide_width, PInches(0.18), navy)
        _caixa(slide, 0, PInches(7.15), prs.slide_width, PInches(0.35), navy)
        rodape = slide.shapes.add_textbox(PInches(0.35), PInches(7.18), PInches(12.6), PInches(0.28))
        p = rodape.text_frame.paragraphs[0]
        _pptx_run(p, "CronotaScan  ·  M2  ·  José Eduardo, Márcio Fossa e Erick Franzmann Bortoloti",
                  12, cor=branco)

    def titulo(slide, texto: str) -> None:
        box = slide.shapes.add_textbox(PInches(0.45), PInches(0.32), PInches(12.4), PInches(0.7))
        _pptx_run(box.text_frame.paragraphs[0], texto, 28, bold=True, cor=navy)

    def bullets(slide, itens: list[str], top: float = 1.2) -> None:
        box = slide.shapes.add_textbox(PInches(0.55), PInches(top), PInches(12.2), PInches(5.6))
        tf = box.text_frame
        tf.word_wrap = True
        for i, item in enumerate(itens):
            p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            p.alignment = PP_ALIGN.LEFT
            p.level = 0
            p.space_after = PPt(10)
            _pptx_run(p, item, 20, cor=ink)

    # 1 capa
    s = nova()
    _caixa(s, 0, 0, prs.slide_width, prs.slide_height, navy)
    box = s.shapes.add_textbox(PInches(0.7), PInches(0.7), PInches(12), PInches(1.1))
    _pptx_run(box.text_frame.paragraphs[0], "UNIVERSIDADE DO VALE DO ITAJAÍ", 18, cor=PptRGB(0xD6, 0xE6, 0xF2))
    box = s.shapes.add_textbox(PInches(0.7), PInches(1.7), PInches(12), PInches(1.6))
    tf = box.text_frame
    tf.word_wrap = True
    _pptx_run(tf.paragraphs[0], "M2 — Andamento das sprints", 40, bold=True, cor=branco)
    p = tf.add_paragraph()
    _pptx_run(p, "Gerência de configuração e de mudanças", 28, cor=branco)
    box = s.shapes.add_textbox(PInches(0.7), PInches(3.6), PInches(12), PInches(0.6))
    _pptx_run(box.text_frame.paragraphs[0], "CronotaScan — leitor de discos de cronotacógrafo", 22, cor=PptRGB(0xF4, 0xD0, 0x80))
    box = s.shapes.add_textbox(PInches(0.7), PInches(4.6), PInches(12), PInches(1.8))
    tf = box.text_frame
    _pptx_run(tf.paragraphs[0], "José Eduardo", 22, cor=branco)
    for nome in ("Márcio Fossa", "Erick Franzmann Bortoloti"):
        p = tf.add_paragraph()
        _pptx_run(p, nome, 22, cor=branco)
    box = s.shapes.add_textbox(PInches(0.7), PInches(6.6), PInches(12), PInches(0.4))
    _pptx_run(box.text_frame.paragraphs[0], f"Engenharia de Software II  ·  Itajaí  ·  {DATA_ENTREGA}", 16,
              cor=PptRGB(0xD6, 0xE6, 0xF2))
    _notas(s,
           "José: Bom dia. Nós somos o grupo do CronotaScan. Eu sou o José Eduardo, este é o Márcio Fossa "
           "e este é o Erick Franzmann Bortoloti. O sistema lê o disco de papel do cronotacógrafo a partir "
           "de uma foto. A M2 mostra as duas primeiras sprints, as mudanças desde a M1 e o repositório. "
           "O Erick apresenta junto com a gente: o leitor que está no master é o commit dele.")

    # 2 objetivo
    s = nova(); barra(s); titulo(s, "O que esta M2 responde")
    bullets(s, [
        "Sprint 1 (11/09 a 02/10) — fluxo de placa, dashboard, histórico e PDF.",
        "Sprint 2 (03/10 a 24/10) — a foto não pode escapar para a mesa.",
        "Sprint 3 e Sprint 4 — ainda no plano: odômetro em 25/10 e banca em 04/12.",
        "Três mudanças desde a M1: equipe, prazo da foto real e critério de teste.",
        "Toda afirmação desta fala tem commit ou pull request.",
    ])
    _notas(s,
           "José: O calendário é o da M1. Sprint 1, de 11 de setembro a 2 de outubro, deixa o fluxo estável. "
           "Sprint 2, de 3 a 24 de outubro, é a foto real. Sprints 3 e 4 não começaram. O que eu disser tem commit.")

    # 3 sprint 1
    s = nova(); barra(s); titulo(s, "Sprint 1 — o que ficou pronto")
    bullets(s, [
        "14/08 — José Eduardo coloca o protótipo no master (commit a30940f).",
        "Placa, curva, excesso, parada, histórico, dashboard e PDF já respondem.",
        "25/09 — ainda nesta sprint, Erick integra o leitor v2 no master.",
        "Não entrou no master até 02/10: teste automático com distância conhecida.",
        "O Word da M1 está em outra branch, não na master.",
    ])
    _notas(s,
           "José: O fluxo básico já estava no master em 14 de agosto. Faltava o teste com distância conhecida. "
           "Em 25 de setembro, ainda na Sprint 1, o Erick integrou o leitor novo. Passo a palavra.")

    # 4 erick
    s = nova(); barra(s); titulo(s, "Sprint 2 — leitor do Erick, no master")
    bullets(s, [
        "Commit b3454bb, de 25/09, autor Erick Franzmann Bortoloti.",
        "A foto de celular deixa o disco oval: a borda do papel vira a referência.",
        "Homografia endireita a elipse. O arco verde de 12 h a 24 h marca a meia-noite.",
        "A escala de 0 a 125 km/h é conferida nos anéis. Foto ruim recebe aviso na tela e no PDF.",
        "US02 estava prevista para 03/10. Chegou antes e foi registrada como mudança de prazo.",
    ], top=1.15)
    _notas(s,
           "Erick: Eu sou o Erick. No dia 25 de setembro coloquei no master o leitor versão 2. "
           "A foto do celular deixa o disco oval. O programa acha a borda do papel, endireita com homografia "
           "e usa o arco verde para a hora zero. Se a foto não alinha, a tela e o PDF avisam. "
           "O teste com 120 km, 179,67 km e 121,67 km ainda está no pull request 1, em rascunho, fora do master.")

    # 5 demo
    s = nova(); barra(s); titulo(s, "Demonstração — o que o operador vê")
    if INTERFACE.exists():
        s.shapes.add_picture(str(INTERFACE), PInches(0.4), PInches(1.25), PInches(6.3), PInches(4.3))
    if DASHBOARD.exists():
        s.shapes.add_picture(str(DASHBOARD), PInches(6.85), PInches(1.45), PInches(6.05), PInches(3.6))
    leg = s.shapes.add_textbox(PInches(0.45), PInches(5.7), PInches(12.4), PInches(1.2))
    tf = leg.text_frame
    tf.word_wrap = True
    _pptx_run(tf.paragraphs[0],
              "José envia a placa SYN1A01 e o disco tests/fixtures/disco_reto.png. Erick mostra o disco aberto nas 24 horas. Em seguida, o histórico e o PDF.",
              16, cor=ink)
    _notas(s,
           "José opera http://127.0.0.1:8081/ com a placa SYN1A01 e o arquivo tests/fixtures/disco_reto.png. "
           "Erick: isto é o disco aberto em 24 horas; a hora zero veio do arco verde. "
           "José filtra o histórico e abre o PDF. Se o servidor não subir, usar as figuras do relatório.")

    # 6 mudancas
    s = nova(); barra(s); titulo(s, "Três mudanças desde a M1")
    cards = [
        ("M01  Equipe", "Erick Franzmann Bortoloti entra junto com José Eduardo e Márcio Fossa. A M1 tinha dois nomes."),
        ("M02  Prazo", "A foto inclinada foi para o master em 25/09, uma semana antes da Sprint 2."),
        ("M03  Critério", "Sem foto real no Git, a branch usa três discos sintéticos. O PR #1 ainda não foi unido ao master."),
    ]
    for i, (head, body) in enumerate(cards):
        left = PInches(0.4 + i * 4.25)
        _caixa(s, left, PInches(1.7), PInches(4.0), PInches(3.3), gelo)
        hb = s.shapes.add_textbox(left + PInches(0.2), PInches(1.9), PInches(3.6), PInches(0.7))
        _pptx_run(hb.text_frame.paragraphs[0], head, 20, bold=True, cor=navy)
        bb = s.shapes.add_textbox(left + PInches(0.2), PInches(2.7), PInches(3.6), PInches(2.1))
        bb.text_frame.word_wrap = True
        _pptx_run(bb.text_frame.paragraphs[0], body, 16, cor=ink)
    _notas(s,
           "Márcio explica M01 e M03. Erick acrescenta uma frase na M02: a foto inclinada entrou no master "
           "em 25 de setembro. Márcio fecha dizendo que a Sprint 2 não está fechada enquanto o PR 1 for rascunho.")

    # 7 repositorio
    s = nova(); barra(s); titulo(s, "Repositório e configuração")
    bullets(s, [
        "github.com/jbr121/CRONOTACOGRAFOS — master parado no commit do Erick (25/09).",
        "PR #1, rascunho: calibração da curva e discos de gabarito (09/10 e 21/10).",
        "PR #2, aberto: declaração de uso de IA desta M2.",
        "Não há tag de versão. Não há print de quadro nem burndown.",
        "Daqui para a frente: branch, pull request e leitura por outro integrante.",
    ])
    _notas(s,
           "Márcio: O master está no commit do Erick. Dois pull requests abertos, nenhum tag, nenhum burndown. "
           "A evidência desta M2 é o histórico de commits. A regra combinada na M1 passa a ser cumprida nestes PRs.")

    # 8 cada um
    s = nova(); barra(s); titulo(s, "Quem fez o quê")
    pessoas = [
        (navy, "José Eduardo", "Protótipo de agosto no master. Em outubro, a branch do gabarito e dos laudos, com agente de código declarado."),
        (PptRGB(0x1A, 0x6B, 0x4A), "Márcio Fossa", "No plano da M1: API, tela, PDF e processo. Nesta fala: repositório e mudanças. Sem commit em seu nome."),
        (PptRGB(0x8A, 0x4B, 0x08), "Erick Franzmann Bortoloti", "Leitor v2 no master. Borda, homografia, arco verde e aviso de qualidade. Commit com coautoria declarada."),
    ]
    for i, (cor, nome, texto) in enumerate(pessoas):
        top = PInches(1.25 + i * 1.85)
        _caixa(s, PInches(0.45), top, PInches(0.16), PInches(1.6), cor)
        box = s.shapes.add_textbox(PInches(0.85), top, PInches(11.8), PInches(1.6))
        tf = box.text_frame
        tf.word_wrap = True
        _pptx_run(tf.paragraphs[0], nome, 22, bold=True, cor=cor)
        p = tf.add_paragraph()
        _pptx_run(p, texto, 18, cor=ink)
    _notas(s,
           "José fala a primeira frase, Márcio a segunda, Erick a terceira. Márcio não atribui a si código que está no commit do José ou do Erick.")

    # 9 fecha
    s = nova(); barra(s); titulo(s, "Escolhas técnicas e o que falta")
    bullets(s, [
        "Python, FastAPI, OpenCV e SQLite: sobe no laboratório e separa a foto da regra de 80 km/h.",
        "Unir o pull request 1 ao master.",
        "Versionar uma foto real quando houver autorização.",
        "Sprint 3: quilometragem pelo odômetro, com a origem do número visível.",
        "Sprint 4: ensaio da banca em 4 de dezembro.",
    ])
    _notas(s,
           "José: Seguimos em Python, FastAPI, OpenCV e SQLite. Falta unir o PR 1, guardar uma foto real, "
           "fazer o odômetro na Sprint 3 e ensaiar a banca. Obrigado.")

    saida.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(saida))


if __name__ == "__main__":
    relatorio = DOCS / "M2_Relatorio_CronotaScan.docx"
    roteiro = DOCS / "M2_Roteiro_Apresentacao_CronotaScan.docx"
    slides = DOCS / "M2_Apresentacao_CronotaScan.pptx"
    montar_relatorio(relatorio)
    montar_roteiro(roteiro)
    montar_slides(slides)
    print(relatorio)
    print(roteiro)
    print(slides)
