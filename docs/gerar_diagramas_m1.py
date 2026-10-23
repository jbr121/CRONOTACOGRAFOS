"""Diagramas PNG para o documento M1 (arquitetura, casos de uso, sequência, classes)."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Circle, Ellipse, Rectangle
from matplotlib.lines import Line2D

PASTA = Path(__file__).resolve().parent / "figuras"
AZUL = "#1B4F72"
AZUL_CLARO = "#D4E6F1"
CINZA = "#F4F6F7"
BORDA = "#1C2833"
TEXTO = "#1C2833"
VERDE = "#196F3D"
LARANJA = "#B9770E"


def _setup(ax, xlim, ylim) -> None:
    ax.set_xlim(*xlim)
    ax.set_ylim(*ylim)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_facecolor("white")


def _caixa(ax, x, y, w, h, texto, fc=AZUL_CLARO, ec=AZUL, size=9, weight="bold") -> None:
    box = FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0.02,rounding_size=0.08",
        linewidth=1.4, edgecolor=ec, facecolor=fc, zorder=2,
    )
    ax.add_patch(box)
    ax.text(
        x + w / 2, y + h / 2, texto, ha="center", va="center",
        fontsize=size, color=TEXTO, weight=weight, zorder=3,
        wrap=True, family="DejaVu Sans",
    )


def gerar_arquitetura(caminho: Path) -> None:
    fig, ax = plt.subplots(figsize=(10.5, 7.2), dpi=160)
    _setup(ax, (0, 10.5), (0, 7.2))
    ax.set_title("Figura 1 — Arquitetura em camadas do CronotaScan", fontsize=12, pad=8, color=AZUL)

    camadas = [
        (0.4, 5.7, 9.7, 1.2, "Apresentação\nSPA  —  static/index.html  (upload, dashboard, histórico, PDF)", "#EAF2F8"),
        (0.4, 4.15, 9.7, 1.2, "Aplicação\nFastAPI  —  main.py  (rotas, validação, orquestração, erros)", "#D5F5E3"),
        (0.4, 2.15, 9.7, 1.7, "", "#FCF3CF"),
        (0.4, 0.35, 9.7, 1.5, "", "#FADBD8"),
    ]
    for args in camadas:
        _caixa(ax, *args[:4], args[4] if args[4] else " ", fc=args[5], size=9)

    ax.text(5.25, 3.65, "Domínio", ha="center", fontsize=10, weight="bold", color=AZUL)
    _caixa(ax, 0.7, 2.35, 2.8, 1.15, "LeitorDisco\nprocessador_imagem.py", fc="#FDEBD0", size=8)
    _caixa(ax, 3.75, 2.35, 2.8, 1.15, "AnalisadorDisco\nanalisador.py", fc="#FDEBD0", size=8)
    _caixa(ax, 6.8, 2.35, 2.9, 1.15, "GeradorLaudoPDF\ngerador_pdf.py", fc="#FDEBD0", size=8)

    ax.text(5.25, 1.6, "Dados", ha="center", fontsize=10, weight="bold", color=AZUL)
    _caixa(ax, 1.1, 0.5, 3.6, 0.95, "SQLite  tacografos.db\ndatabase.py", fc="#F5B7B1", size=8)
    _caixa(ax, 5.6, 0.5, 3.8, 0.95, "Arquivos  temp/\nimagens desdobradas", fc="#F5B7B1", size=8)

    for y0, y1 in ((5.7, 5.35), (4.15, 3.85), (2.15, 1.85)):
        ax.annotate("", xy=(5.25, y1), xytext=(5.25, y0),
                    arrowprops=dict(arrowstyle="-|>", color=AZUL, lw=1.6))

    fig.tight_layout()
    fig.savefig(caminho, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def gerar_casos_de_uso(caminho: Path) -> None:
    fig, ax = plt.subplots(figsize=(10.2, 6.8), dpi=160)
    _setup(ax, (0, 10.2), (0, 6.8))
    ax.set_title("Figura 2 — Diagrama de casos de uso", fontsize=12, pad=8, color=AZUL)

    sistema = FancyBboxPatch(
        (2.6, 0.45), 6.9, 5.9,
        boxstyle="round,pad=0.04,rounding_size=0.12",
        linewidth=1.5, edgecolor=AZUL, facecolor="#FBFCFC", linestyle="--",
    )
    ax.add_patch(sistema)
    ax.text(6.05, 6.1, "CronotaScan", ha="center", fontsize=11, weight="bold", color=AZUL)

    # Ator
    ax.add_patch(Circle((1.15, 4.35), 0.28, fill=False, lw=1.6, edgecolor=BORDA))
    ax.plot([1.15, 1.15], [4.07, 3.15], color=BORDA, lw=1.6)
    ax.plot([0.75, 1.55], [3.7, 3.7], color=BORDA, lw=1.6)
    ax.plot([1.15, 0.8], [3.15, 2.55], color=BORDA, lw=1.6)
    ax.plot([1.15, 1.5], [3.15, 2.55], color=BORDA, lw=1.6)
    ax.text(1.15, 2.15, "Operador\nde frota", ha="center", fontsize=9, weight="bold")

    casos = [
        (6.05, 5.25, "UC01 Processar disco"),
        (6.05, 4.15, "UC02 Consultar histórico"),
        (6.05, 3.05, "UC03 Ver detalhe da viagem"),
        (6.05, 1.95, "UC04 Gerar laudo PDF"),
        (6.05, 0.95, "UC05 Limpar / novo scan"),
    ]
    for cx, cy, nome in casos:
        e = Ellipse((cx, cy), 4.4, 0.78, facecolor=AZUL_CLARO, edgecolor=AZUL, lw=1.4)
        ax.add_patch(e)
        ax.text(cx, cy, nome, ha="center", va="center", fontsize=9, color=TEXTO)

    for cy in (5.25, 4.15, 3.05, 1.95, 0.95):
        ax.annotate("", xy=(3.85, cy), xytext=(1.55, 3.6),
                    arrowprops=dict(arrowstyle="-", color=AZUL, lw=1.1))

    ax.annotate("", xy=(6.05, 2.32), xytext=(6.05, 2.68),
                arrowprops=dict(arrowstyle="-|>", color=VERDE, lw=1.3))
    ax.text(8.35, 2.48, "<<include>>", fontsize=7, color=VERDE)

    fig.tight_layout()
    fig.savefig(caminho, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def gerar_sequencia_uc01(caminho: Path) -> None:
    fig, ax = plt.subplots(figsize=(11.2, 8.0), dpi=160)
    ax.set_xlim(0, 11.2)
    ax.set_ylim(0, 8.0)
    ax.axis("off")
    ax.set_title("Figura 3 — Diagrama de sequência (UC01 Processar disco)", fontsize=12, pad=8, color=AZUL)

    lifelines = [
        (1.0, "Operador"),
        (3.1, "SPA"),
        (5.2, "FastAPI"),
        (7.3, "LeitorDisco"),
        (9.5, "Analisador\n+ SQLite"),
    ]
    y_top, y_bot = 7.15, 0.55
    for x, nome in lifelines:
        ax.add_patch(FancyBboxPatch((x - 0.75, 7.15), 1.5, 0.7,
                                    boxstyle="round,pad=0.02,rounding_size=0.06",
                                    fc=AZUL_CLARO, ec=AZUL, lw=1.3))
        ax.text(x, 7.5, nome, ha="center", va="center", fontsize=8, weight="bold")
        ax.plot([x, x], [y_top, y_bot], color="#7F8C8D", lw=1.0, ls="--")

    mensagens = [
        (6.85, 1.0, 3.1, "1. placa + imagem", False),
        (6.35, 3.1, 5.2, "2. POST /upload-disco/", False),
        (5.85, 5.2, 7.3, "3. processar(bytes)", False),
        (5.35, 7.3, 5.2, "4. ResultadoProcessamento", True),
        (4.85, 5.2, 7.3, "5. extrair_curva_velocidade()", False),
        (4.35, 7.3, 5.2, "6. curva tempo × km/h", True),
        (3.85, 5.2, 9.5, "7. analisar_infracoes(curva)", False),
        (3.35, 9.5, 5.2, "8. resumo + infrações", True),
        (2.85, 5.2, 9.5, "9. INSERT viagem + infrações", False),
        (2.35, 9.5, 5.2, "10. viagem_id", True),
        (1.85, 5.2, 3.1, "11. JSON (dashboard)", True),
        (1.35, 3.1, 1.0, "12. métricas, gráfico e alertas", True),
    ]
    for y, x1, x2, texto, retorno in mensagens:
        estilo = "dashed" if retorno else "solid"
        ax.annotate(
            "", xy=(x2, y), xytext=(x1, y),
            arrowprops=dict(arrowstyle="-|>", color=AZUL if not retorno else VERDE, lw=1.2, ls=estilo),
        )
        xm = (x1 + x2) / 2
        ax.text(xm, y + 0.12, texto, ha="center", fontsize=7.2, color=TEXTO)

    fig.tight_layout()
    fig.savefig(caminho, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def _classe(ax, x, y, w, h, titulo, attrs, ops, header_fc=AZUL) -> None:
    ax.add_patch(Rectangle((x, y), w, h, facecolor="white", edgecolor=BORDA, lw=1.2))
    cab = 0.42
    ax.add_patch(Rectangle((x, y + h - cab), w, cab, facecolor=header_fc, edgecolor=BORDA, lw=1.2))
    ax.text(x + w / 2, y + h - cab / 2, titulo, ha="center", va="center",
            fontsize=8, color="white", weight="bold")
    corpo = "\n".join(attrs + ["—"] + ops)
    ax.text(x + 0.08, y + h - cab - 0.08, corpo, ha="left", va="top",
            fontsize=6.6, family="DejaVu Sans", color=TEXTO)


def gerar_classes(caminho: Path) -> None:
    fig, ax = plt.subplots(figsize=(12.2, 8.4), dpi=160)
    _setup(ax, (0, 12.2), (0, 8.4))
    ax.set_title("Figura 4 — Diagrama de classes de especificação", fontsize=12, pad=8, color=AZUL)

    _classe(
        ax, 0.2, 4.7, 3.85, 3.4, "LeitorDisco",
        ["- fracao_raio_min: float", "- velocidade_maxima_kmh: int"],
        ["+ processar(bytes): Resultado", "+ extrair_curva_velocidade()",
         "+ salvar_imagem_desdobrada()", "+ avaliar_qualidade()"],
    )
    _classe(
        ax, 4.85, 5.7, 3.5, 2.4, "ResultadoProcessamento",
        ["+ imagem_desdobrada", "+ mascara_grade",
         "+ distancia_odometro_km", "+ nitidez"],
        ["+ carrega o resultado do polar"],
        header_fc="#1A5276",
    )
    _classe(
        ax, 8.95, 5.9, 3.05, 2.2, "CirculoDetectado",
        ["+ centro_x: int", "+ centro_y: int", "+ raio: int"],
        ["+ ancora o warpPolar"],
        header_fc="#1A5276",
    )
    _classe(
        ax, 4.85, 2.85, 3.5, 2.35, "AnalisadorDisco",
        ["- limite_velocidade_kmh: float", "- minutos_parada: int = 10"],
        ["+ analisar_infracoes(curva)", "- detectar_excessos()/paradas()"],
        header_fc=VERDE,
    )
    _classe(
        ax, 8.7, 2.85, 3.3, 2.35, "GeradorLaudoPDF",
        ["- limite_velocidade_kmh: float"],
        ["+ gerar_pdf_viagem(...): bytes"],
        header_fc=LARANJA,
    )
    _classe(
        ax, 0.2, 0.25, 5.4, 2.15, "LeituraViagem",
        ["+ id, placa_veiculo, data_processamento",
         "+ distancia_total_km, velocidade_maxima",
         "+ confianca_leitura, origem_distancia"],
        ["1  ——  *  Infracao  (cascade)"],
        header_fc="#6C3483",
    )
    _classe(
        ax, 6.5, 0.25, 5.5, 2.15, "Infracao",
        ["+ id, viagem_id, tipo_infracao",
         "+ hora_inicio, hora_fim, velocidade_registrada"],
        ["excesso_velocidade | parada_prolongada"],
        header_fc="#6C3483",
    )

    ax.annotate("", xy=(4.85, 6.85), xytext=(4.05, 6.85),
                arrowprops=dict(arrowstyle="-|>", color=AZUL, lw=1.3))
    ax.text(4.45, 7.05, "produz", fontsize=7.5, color=AZUL, ha="center")

    ax.annotate("", xy=(8.95, 7.0), xytext=(8.35, 7.0),
                arrowprops=dict(arrowstyle="-|>", color=AZUL, lw=1.3))
    ax.text(8.65, 7.2, "contém", fontsize=7.5, color=AZUL, ha="center")

    ax.annotate("", xy=(6.6, 5.2), xytext=(6.6, 5.7),
                arrowprops=dict(arrowstyle="-|>", color=AZUL, lw=1.3))
    ax.text(7.55, 5.38, "alimenta", fontsize=7.5, color=AZUL, ha="center")

    ax.annotate("", xy=(6.5, 1.32), xytext=(5.6, 1.32),
                arrowprops=dict(arrowstyle="-", color=AZUL, lw=1.3))
    ax.text(5.7, 1.5, "1", fontsize=8, color=AZUL)
    ax.text(6.35, 1.5, "*", fontsize=8, color=AZUL)

    ax.annotate("", xy=(9.3, 2.4), xytext=(9.3, 2.85),
                arrowprops=dict(arrowstyle="-|>", color=LARANJA, lw=1.3))
    ax.text(9.55, 2.58, "lê", fontsize=7.5, color=LARANJA)

    fig.tight_layout()
    fig.savefig(caminho, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def gerar_todos() -> dict[str, Path]:
    PASTA.mkdir(parents=True, exist_ok=True)
    caminhos = {
        "arquitetura": PASTA / "fig1_arquitetura.png",
        "casos_uso": PASTA / "fig2_casos_uso.png",
        "sequencia": PASTA / "fig3_sequencia_uc01.png",
        "classes": PASTA / "fig4_classes.png",
    }
    gerar_arquitetura(caminhos["arquitetura"])
    gerar_casos_de_uso(caminhos["casos_uso"])
    gerar_sequencia_uc01(caminhos["sequencia"])
    gerar_classes(caminhos["classes"])
    return caminhos


if __name__ == "__main__":
    gerados = gerar_todos()
    for nome, path in gerados.items():
        print(nome, path)
