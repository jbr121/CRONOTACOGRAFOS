"""
Gera a declaração de uso de IA do CronotaScan a partir do histórico real do Git.

Datas no fuso America/Sao_Paulo (UTC-3).
Commits conferidos em 23/10/2026 contra o repositório jbr121/CRONOTACOGRAFOS.
"""

from __future__ import annotations

from pathlib import Path

from docx import Document
from docx.enum.section import WD_ORIENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor


SAIDA = Path(__file__).resolve().parent / "CronotaScan_Uso_de_IA.docx"
REPOSITORIO = "https://github.com/jbr121/CRONOTACOGRAFOS"

# Ordem cronológica. "ia" segue o que o Git registra (autor Cursor Agent,
# Co-Authored-By de modelo, ou mensagem explícita de cloud agent).
COMMITS = [
    {
        "hash": "a30940f",
        "data": "14/08/2026 16:00",
        "autor": "José Eduardo (jbr121)",
        "branch": "master",
        "mensagem": "Initial commit: CronotaScan PGI Univali",
        "descricao": (
            "Estrutura inicial feita pela equipe: FastAPI, SQLite, interface e pipeline básico. "
            "Não há coautoria de IA neste commit."
        ),
        "ia": False,
    },
    {
        "hash": "b6438e2",
        "data": "14/08/2026 16:30",
        "autor": "José Eduardo (jbr121)",
        "branch": "master",
        "mensagem": "Add tutorial for running CronotaScan on Univali lab PCs.",
        "descricao": "Tutorial para rodar o sistema nos computadores do laboratório da UNIVALI. Sem coautoria de IA.",
        "ia": False,
    },
    {
        "hash": "23957bb",
        "data": "14/08/2026 16:32",
        "autor": "José Eduardo (jbr121)",
        "branch": "master",
        "mensagem": "Add ES2 complementary documentation without changing existing PGI plan.",
        "descricao": "Documentação complementar de Engenharia de Software II. Sem coautoria de IA.",
        "ia": False,
    },
    {
        "hash": "b3454bb",
        "data": "25/09/2026 20:48",
        "autor": "Erick Franzmann Bortoloti",
        "branch": "master",
        "mensagem": "Integrate v2 disc reader with perspective correction and validation",
        "descricao": (
            "Reescrita do leitor em core/processador_imagem.py (494 linhas adicionadas, 647 removidas), "
            "mais ajustes em main.py, static/index.html e core/gerador_pdf.py. "
            "O corpo do commit declara Co-Authored-By: Claude Opus 5.5 (Anthropic). "
            "Conteúdo: borda do disco como elipse, homografia, arco verde 12h–24h, "
            "faixas radiais de velocidade e atividade, autocalibração pelos anéis de 20 km/h."
        ),
        "ia": True,
    },
    {
        "hash": "10090b4",
        "data": "09/10/2026 15:46",
        "autor": "Cursor Agent; coautor José Eduardo",
        "branch": "cursor/corrigir-leitura-disco-2731",
        "mensagem": "Corrige rastreamento da curva do disco",
        "descricao": (
            "Autor Git: Cursor Agent. Altera core/processador_imagem.py e cria "
            "tests/test_processador_imagem.py. Esta branch ainda não foi unida ao master."
        ),
        "ia": True,
    },
    {
        "hash": "634c6db",
        "data": "21/10/2026 08:13",
        "autor": "Cursor Agent; coautor José Eduardo",
        "branch": "cursor/corrigir-leitura-disco-2731",
        "mensagem": "Calibra a leitura com discos de gabarito conhecido",
        "descricao": (
            "Zera minutos parados quando a barra de atividade é visível, preserva trechos "
            "longos de velocidade constante e ajusta o arco verde. Inclui fixtures sintéticos "
            "e tests/test_fixtures_disco.py."
        ),
        "ia": True,
    },
    {
        "hash": "920e257",
        "data": "21/10/2026 08:24",
        "autor": "Cursor Agent; coautor José Eduardo",
        "branch": "cursor/corrigir-leitura-disco-2731",
        "mensagem": "Gera laudo PDF dos discos de gabarito",
        "descricao": "Cria laudos/laudo_discos_gabarito.pdf com o resultado dos discos de gabarito.",
        "ia": True,
    },
    {
        "hash": "b6abd2f",
        "data": "21/10/2026 08:27",
        "autor": "Cursor Agent; coautor José Eduardo",
        "branch": "cursor/corrigir-leitura-disco-2731",
        "mensagem": "Inclui a interface e o dashboard no laudo PDF",
        "descricao": "Inclui laudos/fotos/interface.png e laudos/fotos/dashboard.png no laudo PDF.",
        "ia": True,
    },
    {
        "hash": "306196e",
        "data": "21/10/2026 08:39",
        "autor": "Cursor Agent; coautor José Eduardo",
        "branch": "cursor/corrigir-leitura-disco-2731",
        "mensagem": "Gera o PDF com a explicação das telas e funções",
        "descricao": "Cria laudos/explicacao_telas_e_funcoes.pdf.",
        "ia": True,
    },
    {
        "hash": "00aac9a",
        "data": "21/10/2026 08:43",
        "autor": "Cursor Agent; coautor José Eduardo",
        "branch": "cursor/corrigir-leitura-disco-2731",
        "mensagem": "Adiciona laudo teste com as imagens do CronotaScan",
        "descricao": "Cria laudos/laudo_teste.pdf.",
        "ia": True,
    },
    {
        "hash": "8b438ca",
        "data": "21/10/2026 08:49",
        "autor": "Cursor Agent; coautor José Eduardo",
        "branch": "cursor/corrigir-leitura-disco-2731",
        "mensagem": "Reescreve o laudo teste com a explicação de cada tela e função",
        "descricao": "Reescreve laudos/laudo_teste.pdf descrevendo cada tela e função.",
        "ia": True,
    },
    {
        "hash": "9842a38",
        "data": "23/10/2026 09:17",
        "autor": "José Eduardo (jbr121), aplicando o Cloud Agent",
        "branch": "cursor/cloud-agent-1792757833804-ojiac",
        "mensagem": "Cursor: Apply local changes for cloud agent",
        "descricao": (
            "Commit feito por José Eduardo com a mensagem padrão do Cursor ao aplicar o agente. "
            "36 arquivos, +5143/−253. Entra aqui o código de visão, testes e os documentos da disciplina "
            "gerados com o agente: M1, Lean Inception, Definição do PGI, respostas das atividades de testes, "
            "relatório e roteiro do M2, mais os scripts docs/gerar_*.py. "
            "Esta branch sai do commit 23957bb e ainda não está no master."
        ),
        "ia": True,
    },
    {
        "hash": "e72dcc8",
        "data": "23/10/2026 09:20",
        "autor": "Cursor Agent; coautor José Eduardo",
        "branch": "cursor/declaracao-uso-ia-1680",
        "mensagem": "docs: adiciona documento de declaração de uso de IA (para entrega M2)",
        "descricao": "Primeira versão deste documento e do script docs/gerar_uso_ia.py.",
        "ia": True,
    },
    {
        "hash": "c392737",
        "data": "23/10/2026 09:23",
        "autor": "Cursor Agent; coautor José Eduardo",
        "branch": "cursor/declaracao-uso-ia-1680",
        "mensagem": "docs: reescreve declaração de uso de IA com tabela completa de commits",
        "descricao": (
            "Segunda versão deste documento. Ainda trazia horários em UTC e classificava o commit "
            "9842a38 como se não tivesse IA."
        ),
        "ia": True,
    },
]


def _sombrear(celula, hex_cor: str) -> None:
    tc_pr = celula._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_cor)
    tc_pr.append(shd)


def _texto(celula, texto: str, negrito: bool = False, tamanho: int = 9, cor: str | None = None) -> None:
    celula.text = ""
    paragrafo = celula.paragraphs[0]
    partes = texto.split("\n")
    for indice, parte in enumerate(partes):
        run = paragrafo.add_run(parte)
        run.bold = negrito
        run.font.size = Pt(tamanho)
        run.font.name = "Times New Roman"
        if cor:
            run.font.color.rgb = RGBColor(int(cor[0:2], 16), int(cor[2:4], 16), int(cor[4:6], 16))
        if indice < len(partes) - 1:
            run.add_break()
    paragrafo.paragraph_format.space_after = Pt(0)
    paragrafo.paragraph_format.space_before = Pt(0)


def paragrafo(doc: Document, texto: str, tamanho: int = 12, negrito: bool = False, centro: bool = False) -> None:
    p = doc.add_paragraph()
    run = p.add_run(texto)
    run.bold = negrito
    run.font.size = Pt(tamanho)
    run.font.name = "Times New Roman"
    p.paragraph_format.space_after = Pt(6)
    p.paragraph_format.line_spacing = 1.15
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER if centro else WD_ALIGN_PARAGRAPH.JUSTIFY


def secao(doc: Document, texto: str) -> None:
    titulo = doc.add_heading(texto, level=2)
    titulo.paragraph_format.space_before = Pt(12)
    titulo.paragraph_format.space_after = Pt(6)


def item(doc: Document, texto: str) -> None:
    p = doc.add_paragraph(style="List Bullet")
    run = p.add_run(texto)
    run.font.size = Pt(12)
    run.font.name = "Times New Roman"
    p.paragraph_format.space_after = Pt(3)


def main() -> None:
    doc = Document()
    for section in doc.sections:
        section.orientation = WD_ORIENT.PORTRAIT
        section.page_width = Cm(21.0)
        section.page_height = Cm(29.7)
        section.top_margin = Cm(3)
        section.bottom_margin = Cm(2)
        section.left_margin = Cm(3)
        section.right_margin = Cm(2)

    titulo = doc.add_heading("Declaração de Uso de Inteligência Artificial", 0)
    titulo.alignment = WD_ALIGN_PARAGRAPH.CENTER

    for linha, destaque in (
        ("Projeto Integrador — CronotaScan", True),
        ("Disciplina: Engenharia de Software II", False),
        ("Universidade do Vale do Itajaí — UNIVALI", False),
        ("Grupo: José Eduardo, Márcio Fossa e Erick Franzmann Bortoloti", True),
        ("Outubro de 2026", False),
    ):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(linha)
        run.bold = destaque
        run.font.size = Pt(12)
        run.font.name = "Times New Roman"
        p.paragraph_format.space_after = Pt(2)

    paragrafo(doc, "Repositório: " + REPOSITORIO, tamanho=11, centro=True)

    secao(doc, "1. O que este documento declara")
    paragrafo(
        doc,
        "Este texto informa onde a equipe usou inteligência artificial generativa no CronotaScan "
        "e lista todos os commits existentes no GitHub até 23/10/2026, inclusive os que estão em "
        "branches e ainda não foram unidos ao master. Os dados foram lidos do Git (autor, data com "
        "fuso, mensagem e arquivos). Horários abaixo estão no fuso de São Paulo (UTC−3).",
    )
    paragrafo(
        doc,
        "A equipe revisou o que o agente escreveu antes de incorporar. A responsabilidade pelo "
        "conteúdo entregue é do grupo.",
    )

    secao(doc, "2. Ferramenta")
    item(doc, "Ferramenta: Cursor (https://cursor.com), modo Cloud Agent.")
    item(
        doc,
        "O único commit que nomeia o modelo é o b3454bb: Co-Authored-By Claude Opus 5.5 (Anthropic).",
    )
    item(
        doc,
        "Nos demais commits de agente, o Git registra o autor como Cursor Agent e José Eduardo como "
        "Co-authored-by. O nome do modelo não foi gravado nesses commits, então ele não é inventado aqui.",
    )
    item(
        doc,
        "Este arquivo (docs/CronotaScan_Uso_de_IA.docx) e o script docs/gerar_uso_ia.py foram "
        "redigidos pelo Cloud Agent do Cursor, a pedido da equipe, para a entrega do M2.",
    )

    secao(doc, "3. Commits do repositório")
    paragrafo(
        doc,
        "São 14 commits no total, em quatro linhas de histórico. Fundo amarelo: o Git mostra uso de IA "
        "ou a mensagem diz que o commit aplica o cloud agent. Fundo branco: commit só da equipe.",
    )
    paragrafo(
        doc,
        "Márcio Fossa integra o grupo e assina esta declaração. Até esta data ele não aparece como "
        "autor de commit no repositório.",
    )

    colunas = ("Hash", "Data (São Paulo) e autor", "Branch e mensagem", "O que o commit contém")
    larguras = (Cm(2.0), Cm(3.6), Cm(4.2), Cm(6.2))
    tabela = doc.add_table(rows=1, cols=4)
    tabela.style = "Table Grid"
    tabela.autofit = False
    cabecalho = tabela.rows[0].cells
    for indice, titulo_coluna in enumerate(colunas):
        cabecalho[indice].width = larguras[indice]
        _sombrear(cabecalho[indice], "1F3864")
        _texto(cabecalho[indice], titulo_coluna, negrito=True, tamanho=9, cor="FFFFFF")

    for commit in COMMITS:
        celulas = tabela.add_row().cells
        fundo = "FFF2CC" if commit["ia"] else "FFFFFF"
        valores = (
            commit["hash"],
            commit["data"] + "\n" + commit["autor"],
            commit["branch"] + "\n" + commit["mensagem"],
            commit["descricao"],
        )
        for indice, valor in enumerate(valores):
            celulas[indice].width = larguras[indice]
            _sombrear(celulas[indice], fundo)
            _texto(celulas[indice], valor, negrito=(indice == 0), tamanho=8)

    doc.add_paragraph()
    paragrafo(
        doc,
        "Legenda: fundo amarelo = commit com IA registrada no Git ou com a mensagem de aplicação "
        "do cloud agent. Fundo branco = commit somente da equipe.",
        tamanho=11,
    )

    secao(doc, "4. Onde a IA entrou, com o commit correspondente")

    doc.add_heading("4.1 Leitura do disco", level=3)
    item(
        doc,
        "b3454bb (master, 25/09/2026): leitor v2 com elipse, homografia, arco verde e autocalibração. "
        "Modelo declarado: Claude Opus 5.5. Autor humano: Erick.",
    )
    item(
        doc,
        "10090b4 e 634c6db (branch cursor/corrigir-leitura-disco-2731): correção do rastreamento da "
        "curva e calibração com discos de gabarito. Autor Git: Cursor Agent.",
    )

    doc.add_heading("4.2 Testes", level=3)
    item(doc, "10090b4 cria tests/test_processador_imagem.py.")
    item(doc, "634c6db cria os discos sintéticos, o gabarito JSON e tests/test_fixtures_disco.py.")
    item(
        doc,
        "9842a38 cria tests/test_pipeline.py e tests/test_analisador.py na branch do cloud agent.",
    )

    doc.add_heading("4.3 Laudos em PDF", level=3)
    item(doc, "920e257, b6abd2f, 306196e, 00aac9a e 8b438ca geram e reescrevem os PDFs em laudos/.")
    paragrafo(
        doc,
        "Esses arquivos estão na branch cursor/corrigir-leitura-disco-2731. Eles não estão no master.",
    )

    doc.add_heading("4.4 Documentos da disciplina", level=3)
    paragrafo(
        doc,
        "Os documentos pedidos na disciplina foram gerados com o Cloud Agent e entraram no Git no "
        "commit 9842a38, branch cursor/cloud-agent-1792757833804-ojiac, em 23/10/2026 às 09:17 "
        "(horário de São Paulo). Não estão no master.",
    )
    item(doc, "docs/M1_Visao_Arquitetura_CronotaScan.docx e docs/gerar_m1_docx.py, com as figuras em docs/figuras/.")
    item(doc, "docs/Lean_Inception_CronotaScan.docx e docs/gerar_lean_inception.py.")
    item(doc, "docs/Definicao_Projeto_Integrador_CronotaScan.docx e docs/gerar_definicao_pgi.py.")
    item(doc, "docs/Respostas_Atividade_Testes.docx, a versão em linguagem simples e a parte 2, com os scripts gerar_respostas_testes.py.")
    item(doc, "docs/M2_Relatorio_CronotaScan.docx, docs/M2_Roteiro_Apresentacao_CronotaScan.docx e docs/gerar_m2_relatorio.py.")
    item(doc, "Este documento: commits e72dcc8 e c392737, branch cursor/declaracao-uso-ia-1680.")

    secao(doc, "5. O que a equipe fez sem IA")
    item(doc, "Commits a30940f, b6438e2 e 23957bb: base do projeto, tutorial de laboratório e documentação de ES2.")
    item(doc, "Escolha da arquitetura (FastAPI, SQLite e página única) e dos requisitos com o professor.")
    item(doc, "Fotos reais dos discos e a conferência manual do que o programa leu.")
    item(doc, "Apresentação oral. Márcio Fossa participa do grupo mesmo sem commit no GitHub.")

    secao(doc, "6. Números")
    total = len(COMMITS)
    com_ia = sum(1 for commit in COMMITS if commit["ia"])
    sem_ia = total - com_ia
    resumo = doc.add_table(rows=5, cols=2)
    resumo.style = "Table Grid"
    linhas_resumo = (
        ("Commits no GitHub até 23/10/2026", str(total)),
        ("Com IA registrada ou aplicação do cloud agent", str(com_ia)),
        ("Somente da equipe", str(sem_ia)),
        ("Branches além do master", "cursor/corrigir-leitura-disco-2731; cursor/cloud-agent-1792757833804-ojiac; cursor/declaracao-uso-ia-1680"),
        ("Repositório", REPOSITORIO),
    )
    for indice, (chave, valor) in enumerate(linhas_resumo):
        _texto(resumo.rows[indice].cells[0], chave, negrito=True, tamanho=10)
        _texto(resumo.rows[indice].cells[1], valor, tamanho=10)

    doc.add_paragraph()
    secao(doc, "7. Declaração")
    paragrafo(
        doc,
        "A correção desta declaração (datas no horário de São Paulo, branch de cada commit e o "
        "9842a38 marcado como uso de IA) entra no commit seguinte ao c392737, com a mensagem "
        "docs: corrige datas, branches e classificação de IA na declaração.",
    )
    paragrafo(
        doc,
        "Declaramos que a tabela acima corresponde ao histórico do GitHub na data desta entrega "
        "e que o uso de IA foi supervisionado pela equipe.",
    )
    doc.add_paragraph()
    for nome in ("José Eduardo", "Márcio Fossa", "Erick Franzmann Bortoloti"):
        p = doc.add_paragraph()
        run = p.add_run("_" * 48)
        run.font.size = Pt(12)
        run.font.name = "Times New Roman"
        p2 = doc.add_paragraph()
        run2 = p2.add_run(nome)
        run2.font.size = Pt(12)
        run2.font.name = "Times New Roman"
        doc.add_paragraph()

    doc.save(str(SAIDA))
    print(f"Documento salvo em: {SAIDA}")
    print(f"Commits: {total} | com IA: {com_ia} | sem IA: {sem_ia}")


if __name__ == "__main__":
    main()
