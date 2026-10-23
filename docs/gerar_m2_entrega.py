"""Gera a entrega M2 do CronotaScan para apresentação na ES2.

Segue os itens do enunciado (andamento das sprints, gerência de mudanças,
rastreabilidade, gerência de configuração, comunicação e contribuição
individual) e o calendário de sprints já apresentado na M1.

Datas no fuso America/Sao_Paulo. Evidências conferidas no Git em 23/10/2026.
"""

from __future__ import annotations

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


def _figura(doc: Document, caminho: Path, largura_cm: float, legenda: str) -> None:
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(6)
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.keep_together = True
    run = p.add_run()
    run.add_picture(str(caminho), width=Cm(largura_cm))
    cap = doc.add_paragraph()
    cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
    cap.paragraph_format.space_after = Pt(10)
    cap.paragraph_format.first_line_indent = Cm(0)
    r = cap.add_run(legenda)
    _font(r, size=10, italic=True)


def _margens(doc: Document) -> None:
    for sec in doc.sections:
        sec.page_width = Cm(21.0)
        sec.page_height = Cm(29.7)
        sec.left_margin = Cm(2.5)
        sec.right_margin = Cm(2.5)
        sec.top_margin = Cm(2.2)
        sec.bottom_margin = Cm(2.2)


def montar_relatorio(saida: Path) -> None:
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
    _p(doc, "23 de outubro de 2026", size=12, align="center", first=False, after=2)
    doc.add_page_break()

    _titulo(doc, "1. Objetivo")
    _p(doc,
       "Este relatório responde à entrega M2 da disciplina: mostrar como as sprints do CronotaScan "
       "andaram até 23 de outubro de 2026, o que foi planejado e o que foi entregue, quais mudanças "
       "de escopo ou de equipe foram aceitas, como o repositório está organizado e o que cada "
       "integrante fez. O calendário é o mesmo apresentado na M1: Sprint 1 de 11/09 a 02/10 "
       "(baseline e planejamento), Sprint 2 de 03/10 a 24/10 (foto real), Sprint 3 de 25/10 a 14/11 "
       "(distância, qualidade e laudo) e Sprint 4 de 15/11 a 04/12 (fechamento e banca). "
       "A M1 registrava dois integrantes. Nesta M2 o grupo apresenta três pessoas: José Eduardo, "
       "Márcio Fossa e Erick Franzmann Bortoloti.")
    _p(doc,
       "Cada afirmação abaixo aponta o commit ou o pull request em que ela pode ser conferida. "
       "Onde a evidência pedida no enunciado não existe (print do quadro ou gráfico de burndown), "
       "o texto diz isso com clareza, em vez de descrever um quadro que não foi exportado.")

    _titulo(doc, "3.1 Andamento das sprints")
    _p(doc,
       "Até esta data fecharam-se os fatos da Sprint 1 e está em fechamento a Sprint 2, cujo prazo "
       "vai até 24/10. As Sprints 3 e 4 permanecem como foram planejadas na M1 e ainda não começaram. "
       "A definição de pronto combinada na M1 continua valendo: código no repositório, comportamento "
       "conferido e evidência anexável. Programar sem integrar na branch principal não conta como "
       "incremento do master.")
    _tabela(
        doc,
        ["Sprint", "Período", "Situação em 23/10/2026", "Incremento que o cliente já vê"],
        [
            ["1 — Baseline e planejamento", "11/09 a 02/10", "Encerrada no fluxo básico",
             "Placa, foto, dashboard, histórico e PDF no master"],
            ["2 — Foto real", "03/10 a 24/10", "Em fechamento",
             "Leitor v2 já no master; gabarito sintético ainda só na branch do PR #1"],
            ["3 — Distância, qualidade e laudo", "25/10 a 14/11", "Não iniciada",
             "Previsto: origem da quilometragem e revisão do PDF"],
            ["4 — Fechamento e banca", "15/11 a 04/12", "Não iniciada",
             "Previsto: tutorial da banca e ensaio em 04/12"],
        ],
        tamanho=9,
    )

    _titulo(doc, "Sprint 1 — Baseline e planejamento (11/09 a 02/10)", nivel=2)
    _tabela(
        doc,
        ["Campo pedido no enunciado", "Registro do grupo"],
        [
            ["Objetivo",
             "Ambiente estável e fluxo placa → dashboard → histórico reproduzível na máquina da equipe. Histórias da M1: US01, US04, US06, US07, US09, TS01 e TS03."],
            ["Planejado",
             "Upload com placa, excesso de 80 km/h e parada acima de 10 min, histórico por placa, dashboard com novo escaneamento, mensagem de erro em português, testes do pipeline e limite de upload."],
            ["Concluído",
             "O master já tinha esse fluxo em 14/08/2026, no commit a30940f de José Eduardo (jbr121): FastAPI, SPA, SQLite, AnalisadorDisco e GeradorLaudoPDF. No mesmo dia entraram o tutorial de laboratório (b6438e2) e a documentação complementar de ES2 (23957bb). Em 25/09, ainda dentro do calendário da Sprint 1, Erick Franzmann Bortoloti integrou o leitor v2 no master (b3454bb)."],
            ["Não concluído / motivo",
             "O unittest com disco de gabarito (TS01) não estava no master ao fim de 02/10. O documento Word da M1 também não está na branch master: ele foi gerado na branch cursor/cloud-agent-1792757833804-ojiac (commit 9842a38, de 23/10)."],
            ["Incremento",
             "Um operador consegue enviar placa e imagem, ver a curva, gravar a viagem, filtrar o histórico e baixar o PDF. A partir de 25/09 o master também endireita a foto do disco."],
        ],
        tamanho=10,
    )

    _titulo(doc, "Sprint 2 — Foto real (03/10 a 24/10)", nivel=2)
    _tabela(
        doc,
        ["Campo pedido no enunciado", "Registro do grupo"],
        [
            ["Objetivo",
             "O desdobramento polar não pode escapar para a mesa, e a madrugada não pode aparecer como excesso falso. Histórias da M1: US02 (centro e perspectiva), US03 (curva sem a grade impressa virar velocidade) e TS06 (foto real de referência)."],
            ["Planejado",
             "Disco encontrado mesmo com mousepad e foto inclinada; curva de 24 h em km/h; roteiro de regressão com uma foto real quando houver autorização para versioná-la."],
            ["Concluído",
             "US02 chegou ao master antes do início oficial da sprint, no commit b3454bb de Erick Franzmann Bortoloti: borda elíptica do papel, homografia, meia-noite pelo arco verde de 12 h a 24 h, faixas de velocidade e de atividade, autocalibração pelos anéis de 20 km/h e avisos de qualidade na API, na tela e no PDF. Na sprint propriamente dita, a branch cursor/corrigir-leitura-disco-2731 (pull request #1, ainda em rascunho) passou a rastrear a agulha de forma contínua (commit 10090b4, 09/10) e a conferir três discos sintéticos de gabarito (commit 634c6db, 21/10): 120 km em velocidade constante, 179,67 km em rampa e 121,67 km com uma lacuna de 4 minutos. A tolerância do teste é 8% na distância e 5 km/h na velocidade máxima."],
            ["Não concluído / motivo",
             "O pull request #1 não foi integrado ao master, então o gabarito ainda não é incremento da linha principal. Não há foto real de cliente no repositório, e por isso o critério da M1 (“foto de referência não gera excesso à 00:02”) segue aberto. O quadro de tarefas e o burndown não foram exportados."],
            ["Incremento",
             "No master, a foto inclinada deixa de ser lida como elipse torta e o laudo avisa quando a leitura não é confiável. Na branch da sprint, a distância dos três discos de gabarito fica dentro da tolerância, e há um PDF de demonstração das telas (laudos/laudo_teste.pdf)."],
        ],
        tamanho=10,
    )
    _p(doc,
       "O enunciado pede também o print do quadro no início e no fim de cada sprint e, se houver, o "
       "burndown. O grupo combinou na M1 usar GitHub Projects, com as colunas A Fazer, Fazendo, "
       "Em Teste e Pronto. Esse quadro não foi criado no repositório e não há gráfico de burndown "
       "para anexar. A evidência usada nesta M2 é o histórico de commits e os dois pull requests abertos.")

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
        _figura(doc, FIGURA, 14.2, "Figura 3 — Arquitetura em camadas já apresentada na M1 e mantida nesta entrega.")
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
    _p(doc,
       "O repositório é https://github.com/jbr121/CRONOTACOGRAFOS. A pasta core/ guarda visão, "
       "regras, banco e PDF. main.py expõe a API. static/ é a interface. tests/ guarda os testes. "
       "docs/ passa a guardar os documentos da disciplina, inclusive este relatório. laudos/ guarda "
       "os PDFs de demonstração produzidos na Sprint 2. O plano do Projeto Integrador "
       "(PLANO_DE_IMPLEMENTACAO.md) não foi reescrito.")
    _p(doc,
       "A branch master está no commit b3454bb, de 25/09/2026, feito por Erick Franzmann Bortoloti. "
       "Há duas linhas de trabalho abertas. A branch cursor/corrigir-leitura-disco-2731 contém a "
       "calibração da curva e os laudos de demonstração; o pull request #1 foi aberto em 09/10/2026 "
       "e segue como rascunho. A branch cursor/declaracao-uso-ia-1680 contém a declaração de uso de "
       "IA pedida junto da M2; o pull request #2 está aberto. A branch "
       "cursor/cloud-agent-1792757833804-ojiac guarda a M1, a Lean Inception e a definição do PGI, "
       "e também ainda não foi unida ao master.")
    _p(doc,
       "O repositório ainda não recebeu tag de versão. A referência usada na apresentação "
       "é o hash do commit. A regra combinada na M1 — branch por história e revisão do outro "
       "integrante antes do merge — não foi seguida à risca neste período: o leitor v2 entrou no "
       "master pelo commit direto de Erick, e os pull requests de outubro ainda não tiveram revisão "
       "registrada em comentário. O grupo mantém a regra daqui para a frente e usa estes dois PRs "
       "como o lugar em que a revisão passa a ficar escrita.")

    _titulo(doc, "3.6 Comunicação e organização da equipe")
    _p(doc,
       "O dia a dia continua como a M1 descreveu: combinados pelo WhatsApp e decisão técnica no "
       "GitHub, ao lado do código. A reunião curta da semana serve para dizer o objetivo, o "
       "impedimento e fazer uma demonstração de poucos minutos. A partir desta M2 a equipe deixa "
       "de ser uma dupla. José Eduardo, Márcio Fossa e Erick Franzmann Bortoloti apresentam juntos.")
    _p(doc,
       "O quadro previsto tem as colunas A Fazer, Fazendo, Em Teste e Pronto, com um responsável "
       "em cada item. Como o GitHub Projects não foi aberto, o responsável abaixo é o que a M1 "
       "já tinha atribuído, corrigido pelo que o Git registra de fato.")
    _tabela(
        doc,
        ["Integrante", "Responsabilidade na equipe", "O que o Git mostra até 23/10"],
        [
            ["José Eduardo (jbr121)",
             "Visão, testes e documentação de disciplina, como na M1.",
             "Commits a30940f, b6438e2 e 23957bb no master. Direção da branch de calibração (PR #1) e da declaração de uso de IA (PR #2)."],
            ["Márcio Fossa",
             "Aplicação, interface, laudo e condução do processo, como na M1.",
             "Nenhum commit está assinado com o nome dele. Na apresentação desta M2 ele conduz mudanças, configuração e comunicação."],
            ["Erick Franzmann Bortoloti (ErickFbort)",
             "Integração do leitor de foto real, junto com José na visão computacional.",
             "Commit b3454bb no master, em 25/09/2026. O texto do commit declara coautoria do modelo Claude Opus 5.5."],
        ],
        tamanho=9,
    )

    _titulo(doc, "3.7 Contribuição individual")
    _p(doc,
       "A tabela atende ao pedido de contribuição individual da M2. Os links são os mesmos que a "
       "professora pode abrir no GitHub. Trabalho feito com agente de código está identificado, "
       "para não ser apresentado como digitação manual.")
    _tabela(
        doc,
        ["Integrante", "O que fez nesta M2", "Evidência"],
        [
            ["José Eduardo",
             "Manteve o protótipo de agosto (upload, análise, histórico, PDF, tutorial e documentação de ES2). Em outubro conduziu a correção do rastreio da agulha, os três discos de gabarito e os PDFs que explicam as telas. Esses commits de outubro têm autor Git “Cursor Agent”.",
             "github.com/jbr121/CRONOTACOGRAFOS\ncommit/a30940f\npull/1\npull/2"],
            ["Márcio Fossa",
             "Permanece responsável, no planejamento da M1, pela API, pela interface, pelo laudo e pelo quadro. Nesta apresentação explica o repositório, os pull requests e a forma como o grupo se organiza. Não há commit em seu nome para vincular.",
             "Seção 6 da M1 e seções 3.5 e 3.6 deste relatório."],
            ["Erick Franzmann Bortoloti",
             "Reescreveu o leitor e integrou a versão 2 no master: borda do papel, centro real, homografia, arco verde, faixas radiais, autocalibração e avisos de qualidade. Esse é o incremento de foto real que a Sprint 2 precisava mostrar.",
             "github.com/jbr121/CRONOTACOGRAFOS\ncommit/b3454bb"],
        ],
        tamanho=9,
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


def montar_roteiro(saida: Path) -> None:
    doc = Document()
    _margens(doc)
    doc.core_properties.author = GRUPO
    doc.core_properties.title = "Roteiro da apresentação M2 — CronotaScan"

    _p(doc, "Roteiro da apresentação M2 — CronotaScan", size=16, bold=True, align="center", first=False, after=4)
    _p(doc, "Engenharia de Software II — UNIVALI — 23 de outubro de 2026",
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
    _pptx_run(box.text_frame.paragraphs[0], "Engenharia de Software II  ·  Itajaí  ·  23 de outubro de 2026", 16,
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
