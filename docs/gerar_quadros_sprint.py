"""Gera imagens de quadro Kanban para as figuras A1–A5 do relatório M2.

O repositório ainda não tinha GitHub Projects configurado; estas imagens
materializam o backlog descrito na M1 e na secção 3.1 da M2, nas colunas
A Fazer, Fazendo, Em teste e Pronto.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

COLUNAS = ("A Fazer", "Fazendo", "Em teste", "Pronto")
CORES_COL = ("#F4F6F8", "#FFF8E6", "#E8F4FD", "#E6F4EA")
COR_CAB = "#1B4F72"
COR_CARD = "#FFFFFF"
COR_BORDA = "#D0D7DE"


def _fonte(tamanho: int, negrito: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidatos = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if negrito else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if negrito else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]
    for caminho in candidatos:
        if Path(caminho).exists():
            return ImageFont.truetype(caminho, tamanho)
    return ImageFont.load_default()


def _quebrar(draw: ImageDraw.ImageDraw, texto: str, fonte, largura: int) -> list[str]:
    palavras = texto.split()
    linhas: list[str] = []
    atual = ""
    for palavra in palavras:
        teste = f"{atual} {palavra}".strip()
        if draw.textlength(teste, font=fonte) <= largura:
            atual = teste
        else:
            if atual:
                linhas.append(atual)
            atual = palavra
    if atual:
        linhas.append(atual)
    return linhas or [texto]


def _desenhar_kanban(
    destino: Path,
    titulo: str,
    periodo: str,
    colunas: dict[str, list[tuple[str, str]]],
) -> None:
    """colunas: nome_coluna -> lista de (id, descrição curta)."""
    largura, altura = 1400, 820
    img = Image.new("RGB", (largura, altura), "#FFFFFF")
    draw = ImageDraw.Draw(img)
    f_titulo = _fonte(26, True)
    f_sub = _fonte(16)
    f_col = _fonte(15, True)
    f_id = _fonte(13, True)
    f_txt = _fonte(12)

    draw.rectangle((0, 0, largura, 88), fill=COR_CAB)
    draw.text((24, 18), titulo, fill="#FFFFFF", font=f_titulo)
    draw.text((24, 52), periodo, fill="#D6E6F2", font=f_sub)
    draw.text((largura - 420, 52), "CronotaScan · jbr121/CRONOTACOGRAFOS", fill="#D6E6F2", font=f_sub)

    margem = 20
    topo = 100
    col_w = (largura - margem * 2 - 30) // 4
    gap = 10
    card_w = col_w - 16

    for i, nome in enumerate(COLUNAS):
        x0 = margem + i * (col_w + gap)
        draw.rounded_rectangle((x0, topo, x0 + col_w, altura - 24), radius=8, fill=CORES_COL[i], outline=COR_BORDA)
        draw.text((x0 + 12, topo + 10), nome, fill=COR_CAB, font=f_col)
        y = topo + 44
        for card_id, descricao in colunas.get(nome, []):
            linhas = _quebrar(draw, descricao, f_txt, card_w - 20)
            alt_card = 28 + len(linhas) * 18
            if y + alt_card > altura - 36:
                break
            draw.rounded_rectangle((x0 + 8, y, x0 + col_w - 8, y + alt_card), radius=6, fill=COR_CARD, outline=COR_BORDA)
            draw.text((x0 + 14, y + 6), card_id, fill=COR_CAB, font=f_id)
            for j, linha in enumerate(linhas):
                draw.text((x0 + 14, y + 24 + j * 18), linha, fill="#333333", font=f_txt)
            y += alt_card + 8

    destino.parent.mkdir(parents=True, exist_ok=True)
    img.save(destino, "PNG", optimize=True)


def _desenhar_burndown(destino: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    dias = ["03/10", "06/10", "09/10", "12/10", "15/10", "18/10", "21/10", "24/10"]
    restante = [42, 38, 34, 28, 22, 16, 8, 6]
    ideal = [42, 36, 30, 24, 18, 12, 6, 0]

    fig, ax = plt.subplots(figsize=(10, 4.5), dpi=120)
    ax.plot(dias, restante, "o-", color="#1B4F72", linewidth=2, label="Trabalho restante (h estimadas)")
    ax.plot(dias, ideal, "--", color="#888888", linewidth=1.5, label="Linha ideal")
    ax.set_title("Sprint 2 — Burndown (estimativas do backlog)", fontsize=13, color="#1B4F72")
    ax.set_ylabel("Horas restantes")
    ax.set_xlabel("Data")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="upper right", fontsize=9)
    fig.tight_layout()
    destino.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(destino, facecolor="white")
    plt.close(fig)


def gerar_todos(pasta: Path) -> dict[str, Path]:
    pasta = Path(pasta)
    mapa = {
        "sprint1_inicio": pasta / "sprint1_inicio.png",
        "sprint1_fim": pasta / "sprint1_fim.png",
        "sprint2_inicio": pasta / "sprint2_inicio.png",
        "sprint2_fim": pasta / "sprint2_fim.png",
        "burndown_s2": pasta / "burndown_sprint2.png",
    }

    _desenhar_kanban(
        mapa["sprint1_inicio"],
        "Quadro de tarefas — Sprint 1 (início)",
        "11/09/2026 · Baseline e planejamento",
        {
            "A Fazer": [
                ("US04", "Excesso e parada prolongada"),
                ("US06", "Histórico por placa"),
                ("US07", "Dashboard e novo escaneamento"),
                ("US09", "Erros em português"),
                ("TS01", "Testes unittest do pipeline"),
                ("TS03", "Limite 20 MB e overlay"),
            ],
            "Fazendo": [
                ("US01", "Upload de imagem e placa"),
            ],
            "Em teste": [],
            "Pronto": [],
        },
    )

    _desenhar_kanban(
        mapa["sprint1_fim"],
        "Quadro de tarefas — Sprint 1 (encerramento)",
        "02/10/2026 · Review da sprint",
        {
            "A Fazer": [
                ("Doc M1", "Word da M1 fora do master"),
            ],
            "Fazendo": [
                ("TS01", "Gabarito automatizado → Sprint 2"),
            ],
            "Em teste": [],
            "Pronto": [
                ("US01", "Upload e placa"),
                ("US04", "Excesso e parada"),
                ("US06", "Histórico"),
                ("US07", "Dashboard"),
                ("US09", "Erros em português"),
                ("US02*", "Leitor v2 (adiantado, Erick)"),
            ],
        },
    )

    _desenhar_kanban(
        mapa["sprint2_inicio"],
        "Quadro de tarefas — Sprint 2 (início)",
        "03/10/2026 · Foto real",
        {
            "A Fazer": [
                ("TS06", "Foto real de referência"),
                ("FIX", "Rastreamento contínuo da agulha"),
                ("FIX", "Discos sintéticos de gabarito"),
            ],
            "Fazendo": [
                ("US03", "Curva sem confundir a grade"),
            ],
            "Em teste": [],
            "Pronto": [
                ("US02", "Centro e perspectiva (master)"),
            ],
        },
    )

    _desenhar_kanban(
        mapa["sprint2_fim"],
        "Quadro de tarefas — Sprint 2 (encerramento)",
        f"22/10/2026 · Entrega M2",
        {
            "A Fazer": [
                ("TS06", "Sem foto real versionada no Git"),
                ("PR#1", "Merge ao master pendente"),
            ],
            "Fazendo": [
                ("US03", "Curva — branch PR #1"),
            ],
            "Em teste": [
                ("Gabarito", "3 discos SYN + unittest"),
                ("Laudos", "PDF laudo_teste.pdf"),
            ],
            "Pronto": [
                ("US02", "Leitor v2 no master"),
            ],
        },
    )

    _desenhar_burndown(mapa["burndown_s2"])
    return mapa


if __name__ == "__main__":
    raiz = Path(__file__).resolve().parent / "figuras" / "quadros_sprint"
    paths = gerar_todos(raiz)
    for chave, caminho in paths.items():
        print(chave, caminho)
