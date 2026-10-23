"""PDF curto para decorar a apresentação oral da M2 — CronotaScan."""

from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import ListFlowable, ListItem, PageBreak, Paragraph, SimpleDocTemplate, Spacer

DOCS = Path(__file__).resolve().parent
SAIDA = DOCS / "M2_Resumo_Para_Apresentacao.pdf"
GRUPO = "José Eduardo · Márcio Fossa · Erick Franzmann Bortoloti"
DATA = "22 de outubro de 2026"
TAG = "v0.2.0-m2"
REPO = "github.com/jbr121/CRONOTACOGRAFOS"


def _estilos():
    base = getSampleStyleSheet()
    return {
        "titulo": ParagraphStyle(
            "titulo",
            parent=base["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=18,
            textColor=colors.HexColor("#1B4F72"),
            spaceAfter=10,
            alignment=TA_CENTER,
        ),
        "sub": ParagraphStyle(
            "sub",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=11,
            textColor=colors.HexColor("#444444"),
            alignment=TA_CENTER,
            spaceAfter=14,
        ),
        "secao": ParagraphStyle(
            "secao",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=13,
            textColor=colors.HexColor("#1B4F72"),
            spaceBefore=12,
            spaceAfter=6,
        ),
        "quem": ParagraphStyle(
            "quem",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=11,
            textColor=colors.HexColor("#0E6655"),
            spaceAfter=4,
        ),
        "fala": ParagraphStyle(
            "fala",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=11,
            leading=15,
            alignment=TA_JUSTIFY,
            spaceAfter=8,
        ),
        "bullet": ParagraphStyle(
            "bullet",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=10.5,
            leading=14,
            leftIndent=12,
        ),
        "cola": ParagraphStyle(
            "cola",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=10,
            leading=13,
            textColor=colors.HexColor("#1C2833"),
        ),
    }


def _bullets(itens: list[str], estilo) -> ListFlowable:
    return ListFlowable(
        [ListItem(Paragraph(t, estilo), leftIndent=6) for t in itens],
        bulletType="bullet",
        start="•",
    )


def gerar(destino: Path = SAIDA) -> Path:
    est = _estilos()
    doc = SimpleDocTemplate(
        str(destino),
        pagesize=A4,
        leftMargin=2.2 * cm,
        rightMargin=2.2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
        title="Resumo M2 — CronotaScan",
        author=GRUPO,
    )
    story: list = []

    story.append(Paragraph("CronotaScan — resumo para apresentação M2", est["titulo"]))
    story.append(Paragraph("Engenharia de Software II · UNIVALI · Itajaí", est["sub"]))
    story.append(Paragraph(GRUPO, est["sub"]))
    story.append(Paragraph(f"Entrega {DATA} · ~10–12 minutos", est["sub"]))
    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph("Como usar este PDF", est["secao"]))
    story.append(
        Paragraph(
            "Cada bloco é uma fala. Quem aparece em verde na frase “Quem fala” deve decorar aquele "
            "trecho. José opera o PC na demo. Se faltar tempo, use só a última página (cola rápida).",
            est["fala"],
        )
    )
    story.append(PageBreak())

    blocos = [
        (
            "1. Abertura (~40 s)",
            "José Eduardo",
            "Bom dia. Somos o grupo do CronotaScan: eu, José Eduardo, o Márcio Fossa e o "
            "Erick Franzmann Bortoloti. O sistema lê o disco de papel do cronotacógrafo a partir "
            "de uma foto. A M2 mostra como as sprints andaram, as mudanças desde a M1 e como "
            "organizamos o repositório. O leitor que está no master é o commit do Erick.",
        ),
        (
            "2. O que a M2 responde (~40 s)",
            "José Eduardo",
            "Sprint 1: de 11 de setembro a 2 de outubro — fluxo de placa, dashboard, histórico e PDF. "
            "Sprint 2: de 3 a 24 de outubro — foto real sem escapar para a mesa. Sprints 3 e 4 "
            "ainda vêm: odômetro e banca em 4 de dezembro. Tudo que falamos tem commit ou pull request.",
        ),
        (
            "3. Sprint 1 (~1 min)",
            "José Eduardo",
            "Em 14 de agosto o master já tinha upload, análise, histórico e PDF — commit a30940f. "
            "Faltava teste automático com distância conhecida. Em 25 de setembro o Erick integrou "
            "o leitor novo, ainda dentro da Sprint 1. Passo a palavra para ele.",
        ),
        (
            "4. Leitor v2 — Erick (~2 min)",
            "Erick Franzmann Bortoloti",
            "No dia 25 de setembro integrei o leitor versão 2 no master, commit b3454bb. Foto de "
            "celular deixa o disco oval; se o programa procura só o furo, a curva mente. Entrou: "
            "borda do papel, homografia, arco verde das 12h às 24h para a meia-noite, escala nos "
            "anéis de 20 km/h e aviso se a foto é ruim. O teste com três discos de gabarito está "
            "no pull request 1, ainda em rascunho.",
        ),
        (
            "5. Demonstração (~2 min)",
            "José opera · Erick comenta",
            "Abrir localhost 8081, placa SYN1A01, arquivo tests/fixtures/disco_reto.png. Mostrar "
            "distância, gráfico e PDF. Erick: “Isto é o disco aberto em 24 horas; a hora zero veio "
            "do arco verde.” Se o servidor não subir, usar o PDF laudo_teste ou as figuras do relatório.",
        ),
        (
            "6. Três mudanças (~1,5 min)",
            "Márcio Fossa (+ frase do Erick)",
            "Márcio: Erick entrou oficialmente no grupo nesta M2. Erick: a foto inclinada entrou "
            "no master uma semana antes da Sprint 2. Márcio: sem foto real no Git usamos três discos "
            "sintéticos; o PR 1 ainda não foi para o master — a Sprint 2 não está 100% fechada.",
        ),
        (
            "7. Repositório (~1 min)",
            "Márcio Fossa",
            f"Repositório {REPO}. Master no commit do Erick. PR 1 calibração, PR 2 uso de IA, PR 3 "
            f"esta M2. Tag {TAG}. Daqui para frente: branch, pull request e revisão antes do merge.",
        ),
        (
            "8. Cada integrante (~1 min)",
            "José, Márcio e Erick",
            "José: protótipo de agosto e branch do gabarito em outubro, com agente declarado. "
            "Márcio: documentação M1/M2, testes manuais da tela, planejamento e condução da fala. "
            "Erick: commit b3454bb — leitor v2 no master.",
        ),
        (
            "9. Fechamento (~1 min)",
            "José Eduardo",
            "Stack: Python, FastAPI, OpenCV, SQLite — roda no laboratório. Falta: merge do PR 1, "
            "foto real autorizada, odômetro na Sprint 3 e ensaio da banca. Obrigado.",
        ),
    ]

    for titulo, quem, fala in blocos:
        story.append(Paragraph(titulo, est["secao"]))
        story.append(Paragraph(f"Quem fala: {quem}", est["quem"]))
        story.append(Paragraph(fala, est["fala"]))

    story.append(PageBreak())
    story.append(Paragraph("Cola rápida — decorar números e nomes", est["titulo"]))
    story.append(Spacer(1, 0.2 * cm))
    cola = [
        f"Grupo: José Eduardo, Márcio Fossa, Erick Franzmann Bortoloti.",
        "Produto: CronotaScan — foto do disco → curva → alertas → histórico → PDF.",
        "Sprint 1: 11/09–02/10 · Sprint 2: 03/10–24/10 · Banca: 04/12.",
        "Commit base: a30940f (14/08) — fluxo completo no master.",
        "Commit Erick: b3454bb (25/09) — leitor v2, homografia, arco verde.",
        "PR #1: calibração + gabaritos (rascunho) · PR #2: IA · PR #3: M2.",
        f"Tag: {TAG} · Porta: 8081 · Demo: placa SYN1A01, disco_reto.png.",
        "Mudanças M01 equipe · M02 prazo US02 · M03 gabarito sintético.",
        "Regras: excesso > 80 km/h · parada > 10 min · distância = integral da curva (odômetro na S3).",
        "Cerimônias: WhatsApp no dia a dia · GitHub nos PRs · review semanal.",
    ]
    story.append(_bullets(cola, est["cola"]))

    story.append(Spacer(1, 0.4 * cm))
    story.append(Paragraph("Versão curta (5 minutos)", est["secao"]))
    story.append(
        _bullets(
            [
                "José: apresenta os três + objetivo M2.",
                "Erick: 1 minuto no b3454bb (oval → homografia → arco verde).",
                "José: demo SYN1A01 ou figura do relatório.",
                "Márcio: três mudanças + PRs + tag.",
                "José: o que falta até dezembro. Obrigado.",
            ],
            est["bullet"],
        )
    )

    destino.parent.mkdir(parents=True, exist_ok=True)
    doc.build(story)
    return destino


if __name__ == "__main__":
    caminho = gerar()
    print(caminho)
