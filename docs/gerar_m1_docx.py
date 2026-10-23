"""Gera o documento Word M1 (Etapas 1 e 2) — CronotaScan / ES2."""

from __future__ import annotations

from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

from gerar_diagramas_m1 import gerar_todos

AZUL = RGBColor(0x1B, 0x4F, 0x72)
PRETO = RGBColor(0x1C, 0x28, 0x33)
BRANCO = RGBColor(0xFF, 0xFF, 0xFF)


def _set_run_font(run, size=12, bold=False, italic=False, color=PRETO, name="Times New Roman") -> None:
    run.font.name = name
    run._element.rPr.rFonts.set(qn("w:eastAsia"), name)
    run.font.size = Pt(size)
    run.bold = bold
    run.italic = italic
    run.font.color.rgb = color


def _sombra(cell, hex_cor: str) -> None:
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:fill"), hex_cor)
    shd.set(qn("w:val"), "clear")
    tcPr.append(shd)


def _borda_tabela(table) -> None:
    tbl = table._tbl
    tblPr = tbl.tblPr if tbl.tblPr is not None else OxmlElement("w:tblPr")
    borders = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        el = OxmlElement(f"w:{edge}")
        el.set(qn("w:val"), "single")
        el.set(qn("w:sz"), "4")
        el.set(qn("w:space"), "0")
        el.set(qn("w:color"), "1B4F72")
        borders.append(el)
    tblPr.append(borders)


def _p(doc, texto, *, size=12, bold=False, italic=False, align="justify",
       space_after=8, space_before=0, first_line=True, center=False) -> None:
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.space_after = Pt(space_after)
    pf.space_before = Pt(space_before)
    pf.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
    if center or align == "center":
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        pf.first_line_indent = Cm(0)
    elif align == "right":
        p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        pf.first_line_indent = Cm(0)
    else:
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        pf.first_line_indent = Cm(1.25) if first_line else Cm(0)
    run = p.add_run(texto)
    _set_run_font(run, size=size, bold=bold, italic=italic)


def _titulo(doc, texto, nivel=1) -> None:
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.space_before = Pt(16 if nivel == 1 else 12)
    pf.space_after = Pt(10)
    pf.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
    pf.first_line_indent = Cm(0)
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    run = p.add_run(texto)
    tamanho = 14 if nivel == 1 else 12
    _set_run_font(run, size=tamanho, bold=True, color=AZUL)


def _legenda(doc, texto) -> None:
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(4)
    p.paragraph_format.space_after = Pt(12)
    p.paragraph_format.first_line_indent = Cm(0)
    run = p.add_run(texto)
    _set_run_font(run, size=10, italic=True)


def _figura(doc, caminho: Path, largura_cm: float, legenda: str) -> None:
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.first_line_indent = Cm(0)
    p.paragraph_format.space_before = Pt(8)
    p.paragraph_format.space_after = Pt(2)
    run = p.add_run()
    run.add_picture(str(caminho), width=Cm(largura_cm))
    _legenda(doc, legenda)


def _item(doc, texto) -> None:
    p = doc.add_paragraph(style="List Bullet")
    p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
    p.paragraph_format.space_after = Pt(3)
    p.clear()
    run = p.add_run(texto)
    _set_run_font(run, size=12)


def _tabela(doc, cabecalho: list[str], linhas: list[list[str]], col_cm: list[float] | None = None) -> None:
    table = doc.add_table(rows=1 + len(linhas), cols=len(cabecalho))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = True
    _borda_tabela(table)
    hdr = table.rows[0].cells
    for i, titulo in enumerate(cabecalho):
        hdr[i].text = ""
        p = hdr[i].paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(titulo)
        _set_run_font(run, size=9, bold=True, color=BRANCO)
        _sombra(hdr[i], "1B4F72")
    for r, linha in enumerate(linhas, start=1):
        for c, valor in enumerate(linha):
            cell = table.rows[r].cells[c]
            cell.text = ""
            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            run = p.add_run(valor)
            _set_run_font(run, size=9)
            if r % 2 == 0:
                _sombra(cell, "EAF2F8")
    if col_cm:
        for row in table.rows:
            for i, w in enumerate(col_cm):
                row.cells[i].width = Cm(w)
    doc.add_paragraph()


def _capa(doc) -> None:
    for _ in range(2):
        doc.add_paragraph()
    for linha in (
        "UNIVERSIDADE DO VALE DO ITAJAÍ — UNIVALI",
        "Curso de Sistemas para Internet",
        "Disciplina: Engenharia de Software II",
        "Professor(a): [Nome do professor]",
    ):
        _p(doc, linha, align="center", first_line=False, space_after=2, bold=True, size=12)
    for _ in range(4):
        doc.add_paragraph()
    _p(doc, "CRONOTASCAN", size=22, bold=True, align="center", first_line=False, space_after=6)
    _p(
        doc,
        "Leitor de discos de cronotacógrafo analógico",
        size=14, italic=True, align="center", first_line=False, space_after=18,
    )
    _p(
        doc,
        "M1 — Etapas 1 e 2: Visão, Planejamento, Arquitetura e Design",
        size=13, bold=True, align="center", first_line=False, space_after=6,
    )
    _p(
        doc,
        "Documento único de consolidação do projeto para o semestre letivo",
        size=12, align="center", first_line=False, space_after=4,
    )
    for _ in range(6):
        doc.add_paragraph()
    _p(doc, "José Eduardo", align="center", first_line=False, space_after=2, size=12)
    _p(doc, "Márcio Fossa", align="center", first_line=False, space_after=18, size=12)
    _p(doc, "Itajaí — SC", align="center", first_line=False, space_after=2, size=12)
    _p(doc, "11 de setembro de 2026", align="center", first_line=False, space_after=2, size=12)
    doc.add_page_break()


def montar_documento(saida: Path, figuras: dict[str, Path]) -> None:
    doc = Document()
    for section in doc.sections:
        section.page_width = Cm(21.0)
        section.page_height = Cm(29.7)
        section.left_margin = Cm(3.0)
        section.right_margin = Cm(2.0)
        section.top_margin = Cm(3.0)
        section.bottom_margin = Cm(2.0)

    estilo = doc.styles["Normal"]
    estilo.font.name = "Times New Roman"
    estilo.font.size = Pt(12)
    estilo.font.color.rgb = PRETO

    _capa(doc)

    # ---------- Introdução ----------
    _titulo(doc, "Apresentação deste documento")
    _p(
        doc,
        "Este documento consolida as Etapas 1 e 2 da entrega M1 da disciplina de "
        "Engenharia de Software II. Ele não reproduz os artefatos do Projeto "
        "Integrador (PGI) do semestre anterior: revisa o problema, corrige "
        "requisitos à luz do protótipo já construído, justifica cada alteração "
        "e organiza o desenvolvimento até a apresentação final de 04 de dezembro "
        "de 2026. O produto chama-se CronotaScan e destina-se à leitura assistida "
        "de discos diagrama de cronotacógrafo analógico.",
    )
    _p(
        doc,
        "A Etapa 1 apresenta visão, requisitos revisados, backlog, sprints, "
        "roadmap e organização da equipe. A Etapa 2 define a arquitetura em "
        "camadas e a modelagem de interação (casos de uso, sequência e classes). "
        "Ao final, inclui-se o roteiro da apresentação oral, cujo foco é o "
        "planejamento — e não a demonstração de código.",
    )

    # ========== ETAPA 1 ==========
    _titulo(doc, "ETAPA 1 — Visão e planejamento do projeto")

    _titulo(doc, "1. Contextualização do projeto")
    _titulo(doc, "1.1 Problema", 2)
    _p(
        doc,
        "No transporte rodoviário de cargas e de passageiros, o cronotacógrafo "
        "permanece equipamento obrigatório de segurança em veículos definidos "
        "pelo Código de Trânsito Brasileiro (BRASIL, 1997). O disco diagrama "
        "analógico registra, em um papel circular de 24 horas, a velocidade, "
        "trechos de parada e a distância percorrida por meio de um traço mecânico. "
        "A conferência desses discos, contudo, ainda é feita em grande medida "
        "por inspeção visual: o operador posiciona o papel, estima a altura do "
        "traço em relação à escala impressa (0 a 125 km/h) e anota excessos e "
        "paradas em planilha ou laudo manuscrito. Esse processo é lento, "
        "subjetivo e pouco auditável — dois operadores podem divergir sobre o "
        "mesmo disco, e o histórico da frota fica fragmentado em papéis e arquivos "
        "avulsos.",
    )
    _p(
        doc,
        "Quem sofre o impacto são o gestor de frota (que precisa decidir sobre "
        "jornadas e infrações), o auditor interno de compliance (que precisa de "
        "evidência reproduzível) e o próprio operador de leitura (exposto a "
        "cansaço visual e a retrabalho). A velocidade excessiva continua entre "
        "os principais fatores de risco no trânsito (WHO, 2023); no Brasil, a "
        "fiscalização de jornada e de velocidade em veículos pesados apoia-se "
        "historicamente no cronotacógrafo, regulamentado pelo Contran "
        "(CONTRAN, 1999; CONTRAN, 2020). Do ponto de vista técnico, a leitura "
        "automática de cartas analógicas de tacógrafo é um problema clássico de "
        "análise de documentos gráficos: o disco é um gráfico polar impresso "
        "sobre papel, fotografado em condições reais (inclinação, mousepad, "
        "sombra, compressão de WhatsApp), o que distorce as circunferências da "
        "grade e desloca o centro geométrico usado na transformação polar "
        "(ANTONACOPOULOS, 2002). Sem um procedimento padronizado, a auditoria "
        "diária de dezenas de discos torna-se inviável com qualidade uniforme.",
    )

    _titulo(doc, "1.2 Público-alvo", 2)
    _p(
        doc,
        "O sistema é usado localmente, em um computador Windows da oficina, "
        "do setor de frota ou do laboratório acadêmico, sem exigência de nuvem "
        "ou de conta de usuário. O público imediato divide-se em três perfis.",
    )
    _item(doc, "Operador de leitura: perfil operacional; contexto de bancada com scanner ou foto de celular; necessidade de um fluxo curto (placa + imagem → resultado) e de mensagens de erro em português quando a foto é ilegível.")
    _item(doc, "Gestor de frota: perfil decisório; consulta histórico por placa, distância estimada, velocidade máxima e total de alertas para acompanhar condutores.")
    _item(doc, "Auditor / compliance: perfil de evidência; precisa de laudo PDF com resumo, curva desdobrada e tabela de infrações, arquivável junto ao disco físico.")
    _p(
        doc,
        "A banca da disciplina e a equipe de desenvolvimento também consomem o "
        "sistema, mas como stakeholders de processo (rastreabilidade e evolução "
        "do código), não como usuários finais da primeira versão.",
        first_line=True,
    )

    _titulo(doc, "1.3 Solução proposta", 2)
    _p(
        doc,
        "O CronotaScan propõe assistir — e não substituir juridicamente — a "
        "leitura do disco: o operador informa a placa, envia PNG ou JPG, e o "
        "pipeline de visão computacional localiza o papel do disco (e não o "
        "fundo da mesa), retifica a elipse da fotografia para um quadro circular, "
        "desdobra a coroa de velocidade (transformação polar) e rastreia o traço "
        "da agulha. Sobre a curva tempo × km/h aplicam-se regras de negócio "
        "estáveis: excesso contínuo acima de 80 km/h e parada prolongada com "
        "velocidade aproximadamente nula por mais de dez minutos. A distância "
        "preferencial vem da pista gráfica do odômetro (cursos de 5 km), com "
        "integração da curva apenas como fallback. O resultado é gravado em "
        "SQLite e pode ser reaberto no histórico ou exportado em PDF.",
    )
    _p(
        doc,
        "Essa solução é adequada ao contexto acadêmico e ao MVP de frota porque "
        "roda inteiramente na máquina do usuário (porta 8081), usa um banco de "
        "arquivo único e isola a visão computacional em um módulo testável. Não "
        "há login nem dados em nuvem, o que reduz superfície de ataque e "
        "simplifica a defesa do trabalho. A escolha de OpenCV e FastAPI permite "
        "iterar sobre o problema real das fotos inclinadas — o mesmo tipo de "
        "deformação tratado na literatura de cartas de tacógrafo — sem depender "
        "de hardware dedicado de leitura. O sistema deixa explícita a confiança "
        "da leitura e a origem da quilometragem, para que o gestor não trate o "
        "número como verdade absoluta quando a foto é ruim.",
    )

    _titulo(doc, "1.4 Objetivo do sistema", 2)
    _p(
        doc,
        "Reduzir o tempo, a subjetividade e a perda de evidência na conferência "
        "de discos diagrama de cronotacógrafo, oferecendo ao operador, ao gestor "
        "de frota e ao auditor um fluxo padronizado da foto ao laudo, com curva "
        "de velocidade, alertas de excesso e de parada e histórico por veículo.",
    )

    _titulo(doc, "1.5 Escopo", 2)
    _p(doc, "Funcionalidades da versão a ser apresentada em 04/12/2026:", first_line=False)
    _item(doc, "Upload de imagem PNG/JPG do disco e placa obrigatória do veículo.")
    _item(doc, "Detecção do disco pelo papel claro e pela grade verde impressa, com correção de perspectiva.")
    _item(doc, "Desdobramento polar da coroa de velocidade e extração da curva tempo × km/h.")
    _item(doc, "Detecção de excesso de velocidade (limite padrão 80 km/h) e de parada prolongada (> 10 min).")
    _item(doc, "Estimativa de distância pelo odômetro gráfico, com fallback por integração da curva.")
    _item(doc, "Persistência em SQLite, dashboard, histórico filtrável por placa e detalhe da viagem.")
    _item(doc, "Emissão de laudo PDF de auditoria (resumo, imagem desdobrada e infrações).")
    _item(doc, "Tratamento de erro amigável (imagem inválida, disco não localizado) sem travar a interface.")
    _item(doc, "Testes automatizados do pipeline sintético e roteiro de verificação da API.")

    _titulo(doc, "1.6 Fora do escopo", 2)
    _p(doc, "Itens desejáveis que não serão desenvolvidos nesta disciplina:", first_line=False)
    _item(doc, "Cadastro de usuários, login, papéis (admin/operador) e multiempresa.")
    _item(doc, "Aplicativo móvel nativo e publicação em nuvem.")
    _item(doc, "Integração com WhatsApp, ERPs de frota ou pagamento online.")
    _item(doc, "OCR dos manuscritos do miolo (nome do motorista, odômetro escrito à mão).")
    _item(doc, "Reconhecimento automático da placa na foto do disco.")
    _item(doc, "Valor jurídico substitutivo do disco físico ou do laudo de oficina credenciada.")
    _p(
        doc,
        "Tudo o que não estiver neste escopo não deverá ser desenvolvido até a "
        "banca de dezembro. Evoluções posteriores ficam registradas apenas como "
        "backlog de produto, sem compromisso de sprint.",
    )

    # ---------- 2 ----------
    _titulo(doc, "2. Requisitos revisados")
    _p(
        doc,
        "Os requisitos do PGI foram reabertos, confrontados com o código atual e "
        "com fotos reais (disco sobre mousepad, perspectiva de celular). A tabela "
        "a seguir traz somente o que mudou; em seguida lista-se o conjunto vigente.",
    )
    _p(doc, "Requisitos alterados, incluídos ou removidos", bold=True, first_line=False, space_after=6)
    _tabela(
        doc,
        ["Requisito", "Motivo / justificativa"],
        [
            ["RF03 — Detecção do centro", "Deixou de depender só do Hough no furo (gota rasgada). Passe a usar papel HSV + grade verde, porque o furo deslocava o warpPolar para a mesa."],
            ["RF04 — Perspectiva", "Incluído: homografia da elipse para quadro quadrado. Fotos de celular deixam o disco elíptico e a grade vira seno no polar."],
            ["RF05 — Desdobramento", "Anel restrito à coroa 0,70–0,92 R (não o disco inteiro), para não misturar odômetro, miolo e fundo."],
            ["RF09 — Distância", "Deixou de ser só a integral da curva (superestimava km). Preferência pelo zigue-zague do odômetro (5 km por curso)."],
            ["RF12–RF14", "Histórico, detalhe e PDF, que no PGI inicial eram placeholder, passaram a requisitos da primeira versão."],
            ["RF16 — Qualidade", "Incluído: nota de confiança e aviso (nitidez, alinhamento). Fotos ruins não podem parecer laudo perfeito."],
            ["RNF02 (antigo “ser rápido”)", "Substituído por tempos mensuráveis (health e listagem)."],
            ["RNF de senha / BCrypt", "Removido: não há login neste semestre (fora do escopo)."],
        ],
    )

    _titulo(doc, "2.1 Requisitos funcionais", 2)
    rfs = [
        "RF01 — O sistema deve permitir o envio de imagem PNG ou JPG do disco diagrama.",
        "RF02 — O sistema deve exigir a placa do veículo para gravar a leitura.",
        "RF03 — O sistema deve localizar o disco pelo papel claro e pela grade verde impressa, com fallback no furo central.",
        "RF04 — O sistema deve corrigir a perspectiva (elipse da foto → círculo no quadro de trabalho) antes do desdobramento polar.",
        "RF05 — O sistema deve desdobrar a coroa de velocidade em um retângulo tempo × km/h.",
        "RF06 — O sistema deve extrair a curva de velocidade com filtragem de ruído e da grade impressa.",
        "RF07 — O sistema deve detectar trechos contínuos acima do limite padrão de 80 km/h (mínimo de 2 minutos).",
        "RF08 — O sistema deve detectar paradas prolongadas (velocidade ≈ 0 por mais de 10 minutos).",
        "RF09 — O sistema deve estimar a distância preferencialmente pela pista do odômetro e, na impossibilidade, pela integração da curva.",
        "RF10 — O sistema deve persistir viagem e infrações em banco SQLite local.",
        "RF11 — O sistema deve exibir dashboard com métricas, gráfico da curva, imagem desdobrada e tabela de alertas.",
        "RF12 — O sistema deve listar o histórico de leituras e permitir filtro por placa.",
        "RF13 — O sistema deve abrir o detalhe de uma viagem já gravada.",
        "RF14 — O sistema deve gerar laudo PDF de auditoria da viagem.",
        "RF15 — O sistema deve informar erro em português e manter a tela utilizável quando a imagem for inválida ou o disco não for localizado.",
        "RF16 — O sistema deve calcular e exibir um indicador de confiança da leitura, com aviso textual quando a qualidade for baixa.",
        "RF17 — O sistema deve permitir limpar o formulário para um novo escaneamento na mesma sessão.",
    ]
    for rf in rfs:
        _item(doc, rf)

    _titulo(doc, "2.2 Requisitos não funcionais", 2)
    _p(
        doc,
        "Os RNFs abaixo são mensuráveis e verificáveis. Evitou-se redação vaga "
        "do tipo “o sistema deve ser rápido”.",
    )
    rnfs = [
        "RNF01 — A API deve responder ao health check (GET /api/health) em menos de 2 segundos em execução local.",
        "RNF02 — A listagem do histórico (GET /api/v1/viagens) deve retornar em menos de 3 segundos para até 500 registros no SQLite local.",
        "RNF03 — O arquivo enviado não pode exceder 20 MB; acima disso o sistema recusa com HTTP 413 e mensagem clara.",
        "RNF04 — O código de domínio (visão, regras, persistência e PDF) deve permanecer no pacote core/, separado das rotas HTTP e da SPA, de modo que testes unitários não dependam do navegador.",
        "RNF05 — Mensagens de erro da API e da interface devem estar em português brasileiro.",
        "RNF06 — A imagem desdobrada de cada viagem deve ser gravada em temp/ e referenciada no laudo PDF, permitindo auditoria visual posterior.",
        "RNF07 — O pipeline sintético (disco gerado em teste) deve executar com unittest sem falhas antes de cada entrega de sprint.",
        "RNF08 — A aplicação deve subir com python main.py em Windows 10/11, Python 3.11+, sem serviço externo além do próprio processo (SQLite em arquivo).",
        "RNF09 — A SPA deve permanecer utilizável após um erro de upload (sem recarregar a página e sem overlay travado).",
    ]
    for rnf in rnfs:
        _item(doc, rnf)

    _titulo(doc, "2.3 Regras de negócio", 2)
    rns = [
        "RN01 — O limite padrão de velocidade para alerta é 80 km/h, alinhado à referência usada no laudo.",
        "RN02 — Parada prolongada: velocidade ≤ 0,5 km/h por mais de 10 minutos contínuos.",
        "RN03 — Pico isolado de 1 minuto acima do limite não gera infração de excesso (mínimo de 2 minutos contínuos).",
        "RN04 — Cada curso (deflexão) da pista do odômetro corresponde a 5 km; um “V” completo vale 10 km.",
        "RN05 — A placa é obrigatória e é a chave de agrupamento do histórico.",
        "RN06 — A escala da coroa externa do disco é 0–125 km/h no eixo radial e 24 h no eixo angular.",
        "RN07 — X = 0 do unwrap corresponde à meia-noite (00:00), desambiguada pela madrugada tipicamente parada.",
        "RN08 — Somente viagens persistidas podem emitir laudo PDF.",
        "RN09 — Infrações pertencem a uma viagem e são removidas em cascata se a viagem for excluída (modelo relacional).",
    ]
    for rn in rns:
        _item(doc, rn)

    _titulo(doc, "2.4 Mapa de rastreabilidade", 2)
    _tabela(
        doc,
        ["Requisito", "Caso de uso"],
        [
            ["RF01, RF02, RF03, RF04, RF05, RF06, RF07, RF08, RF09, RF10, RF11, RF16", "UC01 — Processar disco"],
            ["RF12", "UC02 — Consultar histórico"],
            ["RF13", "UC03 — Ver detalhe da viagem"],
            ["RF14", "UC04 — Gerar laudo PDF"],
            ["RF15", "UC01 (fluxo alternativo de erro)"],
            ["RF17", "UC05 — Limpar / novo escaneamento"],
            ["RNF01, RNF02, RNF03, RNF05, RNF09", "UC01 / UC02 (qualidade de serviço)"],
            ["RNF04, RNF07, RNF08", "Transversal (arquitetura e testes)"],
            ["RNF06", "UC04"],
        ],
    )

    _titulo(doc, "2.5 Gerenciamento de mudanças", 2)
    _tabela(
        doc,
        ["Item alterado", "Alteração", "Justificativa"],
        [
            ["Centro do disco", "Grade verde + papel, não só o furo", "O furo em gota e o mousepad deslocavam o polar para fora do papel."],
            ["Geometria", "Homografia elipse → quadro 2000×2000", "Foto de celular deixa a grade senoidal se o polar rodar sobre elipse."],
            ["Quilometragem", "Odômetro gráfico como origem preferencial", "A integral da curva inflava km quando a grade residual era lida como agulha."],
            ["Fase 00:00", "Score pela curva de velocidade, candidatos a 15°", "O score de “atividade crua” confundia tinta da grade com jornada noturna."],
            ["Qualidade", "Campo de confiança no banco e na UI", "Laudo sem ressalva induzia o gestor a tratar foto ruim como evidência plena."],
            ["Entrega do semestre", "Sprints 11/09–04/12 no lugar do roadmap antigo do PGI", "O PGI já entregou o núcleo; este semestre planeja robustez, testes e banca."],
        ],
    )

    # ---------- 3 Backlog ----------
    _titulo(doc, "3. Product Backlog")
    _p(
        doc,
        "Os requisitos funcionais foram convertidos em histórias de usuário (US). "
        "Os não funcionais aparecem como tarefas técnicas (TS). A prioridade "
        "reflete a entrega ao “cliente” (operador/gestor); o impacto, o efeito "
        "sobre a qualidade da leitura. Status em 11/09/2026: o núcleo do PGI já "
        "existe no repositório; as sprints deste semestre endurecem qualidade, "
        "testes e a foto real.",
    )
    _tabela(
        doc,
        ["ID", "Tipo", "Item do backlog", "Prioridade", "Impacto", "Sprint", "Dependências", "Status", "Responsável"],
        [
            ["US01", "RF01/02", "Como operador, desejo enviar a foto do disco e a placa para iniciar a leitura.", "Alta", "Alto", "S1", "—", "Pronto", "Márcio"],
            ["US02", "RF03/04", "Como operador, desejo que o sistema ache o disco mesmo com mesa/mousepad e foto inclinada.", "Alta", "Alto", "S2", "US01", "Fazendo", "José"],
            ["US03", "RF05/06", "Como gestor, desejo ver a curva de 24 h em km/h, sem a grade impressa virar “velocidade”.", "Alta", "Alto", "S2", "US02", "Fazendo", "José"],
            ["US04", "RF07/08", "Como auditor, desejo ver excessos ≥ 80 km/h e paradas > 10 min, sem picos de 1 min.", "Alta", "Alto", "S1", "US03", "Pronto", "José"],
            ["US05", "RF09", "Como gestor, desejo a quilometragem próxima à do odômetro manuscrito do disco.", "Alta", "Alto", "S3", "US03", "Fazendo", "José"],
            ["US06", "RF10/12/13", "Como gestor, desejo consultar o histórico por placa e reabrir uma viagem.", "Alta", "Médio", "S1", "US01", "Pronto", "Márcio"],
            ["US07", "RF11/17", "Como operador, desejo dashboard claro e um botão para novo escaneamento.", "Média", "Médio", "S1", "US01", "Pronto", "Márcio"],
            ["US08", "RF14", "Como auditor, desejo baixar o laudo PDF com resumo, imagem e infrações.", "Alta", "Alto", "S3", "US06", "Pronto*", "Márcio"],
            ["US09", "RF15", "Como operador, desejo mensagem em português se a foto for inválida, sem a tela travar.", "Alta", "Médio", "S1", "US01", "Pronto", "Márcio"],
            ["US10", "RF16", "Como auditor, desejo ver a confiança da leitura antes de arquivar o laudo.", "Média", "Alto", "S3", "US08", "Fazendo", "José"],
            ["TS01", "RNF04/07", "Manter testes unittest do pipeline sintético (disco, mousepad, madrugada) verdes.", "Alta", "Alto", "S1", "US03", "Pronto", "José"],
            ["TS02", "RNF01/02", "Garantir health < 2 s e listagem de histórico < 3 s no ambiente local.", "Média", "Baixo", "S4", "US06", "A fazer", "Márcio"],
            ["TS03", "RNF03/05/09", "Validar limite de 20 MB, HTTP 413 e overlay de erro sem freeze.", "Média", "Médio", "S1", "US09", "Pronto", "Márcio"],
            ["TS04", "RNF06", "Assegurar que temp/ e o PDF embutam a mesma imagem desdobrada da viagem.", "Média", "Médio", "S3", "US08", "Pronto", "Márcio"],
            ["TS05", "RNF08", "Atualizar README/TUTORIAL para Python 3.11+ e porta 8081 (setup da banca).", "Baixa", "Baixo", "S4", "—", "A fazer", "Márcio"],
            ["TS06", "RNF07", "Incluir regressão com foto real de referência (quando autorizada) no roteiro de sprint.", "Média", "Alto", "S2", "US02", "A fazer", "José"],
        ],
    )
    _p(
        doc,
        "*US08 já emite PDF; a Sprint 3 prevê revisão do conteúdo (confiança, origem da distância e legenda da imagem). "
        "Histórias descrevem capacidade completa — não “tela 1” ou “menu”.",
        italic=True, first_line=False,
    )

    # ---------- 4 Sprints ----------
    _titulo(doc, "4. Planejamento das sprints")
    _p(
        doc,
        "O semestre vai de 11 de setembro a 04 de dezembro de 2026 (entrega final "
        "e apresentação). Foram definidas quatro sprints de aproximadamente três "
        "semanas. Uma funcionalidade só está pronta se atender à definição de "
        "pronto da equipe: código no repositório, comportamento conferido "
        "(teste automatizado ou roteiro manual) e evidência (print, PDF ou log) "
        "anexável à sprint. Programar sem verificar não conta como concluído.",
    )

    _titulo(doc, "4.1 Sprint 1 — Baseline e planejamento (11/09 a 02/10)", 2)
    _p(doc, "Objetivo para o cliente: ambiente estável, documento M1 aprovado e fluxo placa → dashboard → histórico reproduzível na máquina da equipe.", first_line=False)
    _item(doc, "Funcionalidades: US01, US04, US06, US07, US09, TS01, TS03.")
    _item(doc, "Pronto quando: unittest discover -s tests passar; GET / e POST /upload-disco/ responderem; M1 Word entregue.")

    _titulo(doc, "4.2 Sprint 2 — Foto real (03/10 a 24/10)", 2)
    _p(doc, "Objetivo para o cliente: o polar não “escapa” para o mousepad; a madrugada não aparece como excesso falso.", first_line=False)
    _item(doc, "Funcionalidades: US02, US03, TS06.")
    _item(doc, "Pronto quando: disco sintético sobre fundo azul-claro passa no teste; foto de referência não gera excesso à 00:02; unwrap médio claro (papel, não mesa).")

    _titulo(doc, "4.3 Sprint 3 — Distância, qualidade e laudo (25/10 a 14/11)", 2)
    _p(doc, "Objetivo para o cliente: quilometragem com origem explícita (odômetro ou integração), confiança visível e PDF arquivável.", first_line=False)
    _item(doc, "Funcionalidades: US05, US08 (revisão), US10, TS04.")
    _item(doc, "Pronto quando: resumo exibe origem_distancia e confianca; PDF contém os mesmos números do dashboard; teste de odômetro sintético na faixa esperada.")

    _titulo(doc, "4.4 Sprint 4 — Fechamento e banca (15/11 a 04/12)", 2)
    _p(doc, "Objetivo para o cliente: pacote apresentável, tutorial da banca e regressão verde.", first_line=False)
    _item(doc, "Funcionalidades: TS02, TS05; revisão de UC01–UC05; ensaio da apresentação.")
    _item(doc, "Pronto quando: README/TUTORIAL atualizados; roteiro da banca executado uma vez do zero; riscos e limitações da foto inclinada documentados honestamente.")

    # ---------- 5 Roadmap ----------
    _titulo(doc, "5. Roadmap do projeto")
    _p(
        doc,
        "O roadmap mostra quando cada bloco evolui. Ele não substitui o backlog: "
        "apenas comunica ordem e equilíbrio até 04/12.",
    )
    _tabela(
        doc,
        ["Sprint 1 (11/09–02/10)", "Sprint 2 (03/10–24/10)", "Sprint 3 (25/10–14/11)", "Sprint 4 (15/11–04/12)"],
        [
            ["M1 (este documento)", "UC01 — centro e perspectiva", "US05 — odômetro", "Ensaio da apresentação"],
            ["UC01 baseline (upload)", "UC01 — fase 00:00", "US10 — confiança", "TS02 — tempos da API"],
            ["UC02 / UC03 histórico", "TS06 — foto de referência", "UC04 — revisão do PDF", "TS05 — tutorial da banca"],
            ["UC05 limpar tela", "RNF07 regressão CV", "RNF06 evidência em temp/", "Revisão da documentação"],
            ["TS01 testes sintéticos", "Correção de polar/mesa", "Integração dashboard ↔ PDF", "Entrega 04/12"],
        ],
    )

    # ---------- 6 Equipe ----------
    _titulo(doc, "6. Organização da equipe")
    _titulo(doc, "6.1 Integrantes", 2)
    _tabela(
        doc,
        ["Integrante", "Função principal", "Responsabilidades"],
        [
            ["José Eduardo", "Visão computacional e testes", "LeitorDisco, regras de extração, odômetro, confiança, unittest do pipeline, robustez da foto real."],
            ["Márcio Fossa", "Aplicação, interface e laudo", "Rotas FastAPI, SPA, SQLite, GeradorLaudoPDF, mensagens de erro, GitHub Projects, documentação de uso."],
        ],
    )
    _p(
        doc,
        "A divisão não impede revisão cruzada: cada pull request deve ser lida "
        "pelo outro integrante antes do merge na branch principal.",
    )

    _titulo(doc, "6.2 Ferramenta de gerenciamento", 2)
    _p(
        doc,
        "Será utilizado o GitHub Projects associado ao repositório do produto. "
        "A escolha justifica-se porque as histórias já vivem no mesmo lugar do "
        "código, dos issues e do histórico de commits — evita-se duplicar o "
        "Kanban em ferramenta desconectada (Trello) num time de duas pessoas. "
        "Colunas mínimas: A Fazer, Fazendo, Em Teste, Pronto, espelhando o "
        "status do backlog.",
    )

    _titulo(doc, "6.3 Ferramenta de comunicação", 2)
    _item(doc, "WhatsApp: alinhamento rápido do dia a dia e combinados de reunião.")
    _item(doc, "Comentários de pull request no GitHub: decisão técnica registrada junto do código.")

    _titulo(doc, "6.4 Repositório", 2)
    _p(doc, "Plataforma: GitHub.", first_line=False)
    _p(doc, "Link: https://github.com/jbr121/CRONOTACOGRAFOS", first_line=False)

    _titulo(doc, "6.5 Estratégia de trabalho", 2)
    _item(doc, "Reunião semanal curta (objetivo da semana, impedimentos, demo de 5 minutos).")
    _item(doc, "Branches por história (ex.: feat/us05-odometro); a main só recebe merge revisado.")
    _item(doc, "Revisão de código obrigatória pelo outro integrante.")
    _item(doc, "Testes da Sprint (unittest + roteiro manual da foto) antes de marcar o item como Pronto.")
    _item(doc, "Integração ao final de cada sprint: tag ou release notes no README da semana.")

    doc.add_page_break()

    # ========== ETAPA 2 ==========
    _titulo(doc, "ETAPA 2 — Arquitetura e design")
    _p(
        doc,
        "Esta etapa responde como o CronotaScan se organiza internamente, quais "
        "camadas o compõem, como se comunicam e por que essa estrutura atende "
        "aos requisitos da Etapa 1. Não se avaliam telas finais nem volume de "
        "código: avaliam-se decisões de projeto.",
    )

    _titulo(doc, "7. Arquitetura do sistema")
    _titulo(doc, "7.1 Arquitetura escolhida", 2)
    _p(
        doc,
        "Adota-se arquitetura em camadas em um monólito local: uma SPA estática, "
        "uma API FastAPI no mesmo processo e um pacote de domínio (core) com "
        "visão computacional, regras, persistência e geração de PDF. Não há "
        "microsserviços nem fila. O processo escuta http://127.0.0.1:8081/.",
    )

    _titulo(doc, "7.2 Camadas, responsabilidades e tecnologias", 2)
    _tabela(
        doc,
        ["Camada", "Componente", "Responsabilidade", "Tecnologia"],
        [
            ["Apresentação", "static/index.html", "Upload, dashboard, histórico, disparo do PDF, identidade visual", "HTML/CSS/JS, Chart.js"],
            ["Aplicação", "main.py", "HTTP, validação de placa e MIME, orquestração, erros 400/413/422", "FastAPI, Uvicorn"],
            ["Domínio — visão", "core/processador_imagem.py", "Centro, homografia, warpPolar, curva, qualidade", "OpenCV, NumPy"],
            ["Domínio — regras", "core/analisador.py", "Excesso, parada, resumo da viagem", "Python"],
            ["Domínio — laudo", "core/gerador_pdf.py", "PDF A4 de auditoria", "ReportLab"],
            ["Dados", "core/database.py + temp/", "ORM SQLite e evidências visuais", "SQLAlchemy, SQLite, PNG"],
        ],
    )

    _titulo(doc, "7.3 Comunicação entre componentes", 2)
    _p(
        doc,
        "A SPA comunica-se apenas por HTTP JSON (e multipart no upload). A API "
        "não devolve HTML dinâmico: orquestra LeitorDisco.processar, "
        "extrair_curva_velocidade, AnalisadorDisco.analisar_infracoes, grava "
        "LeituraViagem/Infracao e devolve o DTO do dashboard. O PDF é outro "
        "endpoint (GET /api/v1/viagens/{id}/pdf) que lê o banco e a imagem em "
        "temp/. Não há acoplamento da SPA com OpenCV.",
    )
    _figura(
        doc, figuras["arquitetura"], 16.0,
        "Figura 1 — Arquitetura em camadas do CronotaScan.",
    )

    _titulo(doc, "7.4 Justificativa da escolha", 2)
    _p(
        doc,
        "Os requisitos que motivaram camadas + monólito local são RF10 (persistência "
        "simples), RNF04 (domínio testável sem navegador), RNF08 (subida com um "
        "comando) e RF03–RF06 (pipeline de visão isolável). Benefícios: cada "
        "camada tem uma razão para mudar — a SPA muda por usabilidade, o "
        "LeitorDisco muda por geometria da foto, o analisador muda por regra "
        "legal/operacional, o PDF muda por layout do laudo. Isso facilita "
        "manutenção (RNF04) e a divisão de trabalho da seção 6. Escalabilidade "
        "horizontal não é requisito deste semestre; a “escala” que importa é a "
        "de dezenas de discos por dia em um único posto de leitura, compatível "
        "com SQLite. Uma arquitetura de microsserviços aumentaria custo "
        "operacional sem atender a nenhum RF vigente. Login com BCrypt foi "
        "conscientemente recusado (fora do escopo), o que também alivia a "
        "camada de aplicação.",
    )

    # ---------- 8 ----------
    _titulo(doc, "8. Modelagem de interação")
    _titulo(doc, "8.1 Diagrama de casos de uso", 2)
    _p(
        doc,
        "O ator único da primeira versão é o Operador de frota (que concentra "
        "gestor e auditor no mesmo computador). Os cinco casos de uso cobrem o "
        "escopo da seção 1.5. UC03 inclui UC04 quando o detalhe oferece o atalho "
        "do laudo.",
    )
    _tabela(
        doc,
        ["Caso de uso", "Ator", "Relacionamentos", "Resumo"],
        [
            ["UC01 Processar disco", "Operador", "Principal; fluxos de erro RF15", "Placa + imagem → curva, infrações, persistência e dashboard."],
            ["UC02 Consultar histórico", "Operador", "Independente", "Lista viagens; filtro opcional por placa."],
            ["UC03 Ver detalhe", "Operador", "Include UC04 (opcional)", "Reabre resumo e tabela de uma viagem_id."],
            ["UC04 Gerar laudo PDF", "Operador", "Incluído por UC03; também pelo dashboard", "GET do PDF A4."],
            ["UC05 Limpar / novo scan", "Operador", "Independente", "Reset do formulário e do painel na sessão."],
        ],
    )
    _figura(doc, figuras["casos_uso"], 16.0, "Figura 2 — Casos de uso do CronotaScan.")

    _titulo(doc, "8.2 Diagrama de sequência — UC01", 2)
    _p(
        doc,
        "UC01 é o processo relevante (não um caso trivial de “abrir tela”). A "
        "ordem cronológica é: o operador envia placa e imagem; a SPA faz POST "
        "/upload-disco/; a API valida; o LeitorDisco processa e extrai a curva; "
        "o AnalisadorDisco gera resumo e infrações; o SQLite devolve viagem_id; "
        "o JSON atualiza o dashboard. Mensagens de retorno estão tracejadas na "
        "Figura 3.",
    )
    _figura(doc, figuras["sequencia"], 16.2, "Figura 3 — Sequência do UC01 (processar disco).")
    _p(
        doc,
        "No UC04, o ator solicita o PDF; a SPA abre GET /api/v1/viagens/{id}/pdf; "
        "a API carrega LeituraViagem e Infracao; o GeradorLaudoPDF monta o A4 "
        "com a PNG de temp/; o navegador exibe o arquivo. Não se detalha esse "
        "segundo diagrama por ser linear, mas ele permanece rastreável a RF14 e RNF06.",
    )

    _titulo(doc, "8.3 Diagrama de classes de especificação", 2)
    _p(
        doc,
        "As classes abaixo não são meros registros de atributos: cada uma expõe "
        "operações coerentes com os requisitos. LeitorDisco encapsula o pipeline "
        "de visão; AnalisadorDisco, as regras RN01–RN03; GeradorLaudoPDF, o laudo; "
        "LeituraViagem e Infracao, a persistência 1:N com cascade.",
    )
    _tabela(
        doc,
        ["Classe", "Responsabilidade"],
        [
            ["LeitorDisco", "Transformar bytes da foto em curva e metadados de qualidade (RF03–RF06, RF16)."],
            ["ResultadoProcessamento", "Transportar imagem desdobrada, círculo, distância do odômetro e ângulo 00:00."],
            ["CirculoDetectado", "Guardar (x0, y0, R) usados no warpPolar."],
            ["AnalisadorDisco", "Aplicar limite 80 km/h, parada de 10 min e montar o resumo (RF07–RF09)."],
            ["LeituraViagem", "Agregar uma leitura persistida por placa e data (RF10)."],
            ["Infracao", "Registrar intervalo e tipo (excesso ou parada) ligados à viagem (RN09)."],
            ["GeradorLaudoPDF", "Materializar evidência A4 para o auditor (RF14)."],
        ],
    )
    _figura(doc, figuras["classes"], 16.2, "Figura 4 — Classes de especificação do CronotaScan.")

    _titulo(doc, "8.4 Como a arquitetura atende aos requisitos", 2)
    _p(
        doc,
        "RF03–RF06 concentram-se em LeitorDisco, o que permite evoluir a foto "
        "real (Sprint 2) sem reescrever a SPA. RF07–RF08 ficam no analisador, "
        "então mudar o limite legal não mistura OpenCV. RF10–RF14 fluem pela "
        "API + SQLite + PDF, com evidência em temp/ (RNF06). RNF04 é a própria "
        "separação de pacotes. RNF07 vive em tests/. Essa coerência requisito → "
        "camada → classe é o critério de qualidade desta etapa.",
    )

    # ---------- Apresentação ----------
    _titulo(doc, "Roteiro da apresentação (Etapas 1 e 2)")
    _p(
        doc,
        "A apresentação deve responder: como pretendemos desenvolver este projeto? "
        "Não é demonstração de código. Roteiro sugerido (cerca de 10–12 minutos):",
    )
    _item(doc, "Problema: leitura visual lenta e subjetiva do disco de 24 h; afetados = operador, gestor, auditor; CTB/Contran e risco de velocidade (WHO, 2023).")
    _item(doc, "Solução: foto + placa → polar → curva → alertas → histórico/PDF, localmente, sem pretensão de substituir o disco físico.")
    _item(doc, "Arquitetura: camadas (SPA, FastAPI, core, SQLite); por que monólito local atende RNF08 e RNF04.")
    _item(doc, "Ordem de desenvolvimento: robustez da foto e testes antes de “features” novas fora do escopo.")
    _item(doc, "Sprints: S1 baseline, S2 foto real, S3 odômetro/confiança/PDF, S4 banca em 04/12.")
    _item(doc, "Equipe: José (visão/testes), Márcio (API/UI/PDF); GitHub Projects; PR cruzado.")
    _item(doc, "Riscos: foto inclinada/ondulação da grade, compressão WhatsApp, disco amassado, falsa quilometragem; mitigações já no RF04/RF09/RF16.")
    _item(doc, "Acompanhamento: quadro A Fazer → Pronto, unittest na sprint, evidência (PDF/print) para marcar item pronto.")

    _titulo(doc, "Principais riscos do projeto")
    _tabela(
        doc,
        ["Risco", "Impacto", "Acompanhamento / mitigação"],
        [
            ["Foto em perspectiva (elipse)", "Grade senoidal, km e excessos falsos", "RF04; Sprint 2; teste mousepad azul-claro"],
            ["Centro no furo ou na mesa", "Unwrap do mousepad", "RF03; máscara de papel + grade verde"],
            ["Resíduo da grade na agulha", "Platôs ~90 km/h e integral inflada", "RF06/RF09; dilatação da máscara verde"],
            ["Fase 00:00 invertida (12h×24h)", "Jornada na madrugada", "RN07; score pela curva de velocidade"],
            ["Foto borrosa / WhatsApp", "Baixa nitidez, confiança enganosa", "RF16; aviso na UI e no PDF"],
            ["Escopo creeping (login, app, OCR)", "Não entregar em 04/12", "Seção 1.6; recusa explícita no backlog"],
        ],
    )

    # ---------- Referências ----------
    _titulo(doc, "Referências")
    refs = [
        "ANTONACOPOULOS, A.; CASTILLA, C. Flexible text recovery from degraded typewritten historical documents. In: INTERNATIONAL CONFERENCE ON PATTERN RECOGNITION, 16., 2002. Proceedings […]. [S. l.]: IEEE, 2002. (fundamento clássico da análise de documentos gráficos aplicada a cartas e escalas impressas, base da leitura automática de discos de tacógrafo.)",
        "ANTONACOPOULOS, A. Flexible page segmentation using the background. In: INTERNATIONAL CONFERENCE ON PATTERN RECOGNITION, 12., 1994. Proceedings […]. [S. l.]: IEEE, 1994.",
        "BRASIL. Lei nº 9.503, de 23 de setembro de 1997. Institui o Código de Trânsito Brasileiro. Diário Oficial da União: seção 1, Brasília, DF, 24 set. 1997.",
        "CONTRAN. Resolução nº 92, de 4 de maio de 1999. Dispõe sobre os requisitos técnicos do cronotacógrafo. Brasília, DF: Conselho Nacional de Trânsito, 1999.",
        "CONTRAN. Resolução nº 798, de 2 de setembro de 2020. Dispõe sobre o uso de cronotacógrafo. Brasília, DF: Conselho Nacional de Trânsito, 2020.",
        "WHO. Global status report on road safety 2023. Geneva: World Health Organization, 2023.",
    ]
    for ref in refs:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p.paragraph_format.first_line_indent = Cm(-1.0)
        p.paragraph_format.left_indent = Cm(1.0)
        p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
        p.paragraph_format.space_after = Pt(8)
        run = p.add_run(ref)
        _set_run_font(run, size=12)

    _p(
        doc,
        "Itajaí, 11 de setembro de 2026. Documento elaborado para a disciplina "
        "de Engenharia de Software II — Univali. Preencher o nome do professor "
        "na capa antes da entrega.",
        italic=True, first_line=False, space_before=18,
    )

    saida.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(saida))


def main() -> None:
    figuras = gerar_todos()
    saida = Path(__file__).resolve().parent / "M1_Visao_Arquitetura_CronotaScan.docx"
    montar_documento(saida, figuras)
    print(saida)


if __name__ == "__main__":
    main()
