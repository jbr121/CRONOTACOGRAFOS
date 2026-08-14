"""
Geração de laudos oficiais de auditoria em PDF (Sprint 4 — CronotaScan).

Utiliza ReportLab (platypus) para montar um documento A4 formal
a partir dos dados persistidos de uma viagem e suas infrações.
"""

from __future__ import annotations

import io
from datetime import datetime
from pathlib import Path
from typing import Sequence

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from core.database import Infracao, LeituraViagem

# Limite de referência exibido no laudo (alinhado ao AnalisadorDisco / main.py)
LIMITE_VELOCIDADE_LAUDO_KMH: float = 80.0


class GeradorLaudoPDF:
    """Monta o PDF de auditoria de cronotacógrafo a partir dos models do banco."""

    def __init__(self, limite_velocidade_kmh: float = LIMITE_VELOCIDADE_LAUDO_KMH) -> None:
        self.limite_velocidade_kmh = limite_velocidade_kmh
        self._estilos = self._criar_estilos()

    def gerar_pdf_viagem(
        self,
        viagem: LeituraViagem,
        infracoes: Sequence[Infracao],
        caminho_imagem_desdobrada: str | None = None,
    ) -> bytes:
        """
        Gera o laudo em memória e devolve os bytes do PDF.

        Parâmetros:
        - viagem: registro LeituraViagem
        - infracoes: lista de Infracao associadas
        - caminho_imagem_desdobrada: PNG opcional do warpPolar (ignorado se inválido)
        """
        buffer = io.BytesIO()
        documento = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=1.8 * cm,
            rightMargin=1.8 * cm,
            topMargin=1.6 * cm,
            bottomMargin=1.6 * cm,
            title=f"Laudo CronotaScan — {viagem.placa_veiculo}",
            author="CronotaScan",
        )

        elementos: list[object] = []
        elementos.extend(self._bloco_cabecalho(viagem))
        elementos.append(Spacer(1, 8 * mm))
        elementos.extend(self._bloco_resumo(viagem, len(infracoes)))
        elementos.append(Spacer(1, 8 * mm))
        elementos.extend(self._bloco_imagem(caminho_imagem_desdobrada))
        elementos.append(Spacer(1, 6 * mm))
        elementos.extend(self._bloco_infracoes(infracoes))
        elementos.append(Spacer(1, 14 * mm))
        elementos.extend(self._bloco_rodape())

        documento.build(elementos)  # type: ignore[arg-type]
        return buffer.getvalue()

    def _criar_estilos(self) -> dict[str, ParagraphStyle]:
        base = getSampleStyleSheet()
        return {
            "titulo": ParagraphStyle(
                "TituloLaudo",
                parent=base["Heading1"],
                fontName="Helvetica-Bold",
                fontSize=13,
                leading=16,
                alignment=TA_CENTER,
                textColor=colors.HexColor("#1e3a54"),
                spaceAfter=4,
            ),
            "subtitulo": ParagraphStyle(
                "SubtituloLaudo",
                parent=base["Normal"],
                fontName="Helvetica",
                fontSize=9,
                alignment=TA_CENTER,
                textColor=colors.HexColor("#5b6b7c"),
                spaceAfter=8,
            ),
            "secao": ParagraphStyle(
                "SecaoLaudo",
                parent=base["Heading2"],
                fontName="Helvetica-Bold",
                fontSize=11,
                textColor=colors.HexColor("#0f7a6c"),
                spaceBefore=4,
                spaceAfter=6,
            ),
            "corpo": ParagraphStyle(
                "CorpoLaudo",
                parent=base["Normal"],
                fontName="Helvetica",
                fontSize=9,
                leading=12,
                alignment=TA_LEFT,
            ),
            "ok": ParagraphStyle(
                "MsgOk",
                parent=base["Normal"],
                fontName="Helvetica-Bold",
                fontSize=10,
                textColor=colors.HexColor("#1b7a3d"),
                alignment=TA_CENTER,
                spaceBefore=6,
                spaceAfter=6,
            ),
            "rodape": ParagraphStyle(
                "RodapeLaudo",
                parent=base["Normal"],
                fontName="Helvetica",
                fontSize=8,
                leading=11,
                alignment=TA_JUSTIFY,
                textColor=colors.HexColor("#333333"),
            ),
            "assinatura": ParagraphStyle(
                "Assinatura",
                parent=base["Normal"],
                fontName="Helvetica",
                fontSize=9,
                alignment=TA_CENTER,
                spaceBefore=4,
            ),
            "celula": ParagraphStyle(
                "Celula",
                parent=base["Normal"],
                fontName="Helvetica",
                fontSize=8,
                leading=10,
            ),
        }

    def _bloco_cabecalho(self, viagem: LeituraViagem) -> list[object]:
        data_relatorio = datetime.now().strftime("%d/%m/%Y %H:%M")
        data_proc = viagem.data_processamento
        if isinstance(data_proc, datetime):
            data_proc_fmt = data_proc.strftime("%d/%m/%Y %H:%M:%S")
        else:
            data_proc_fmt = str(data_proc)

        return [
            Paragraph(
                "LAUDO DE AUDITORIA DE CRONOTACÓGRAFO — CRONOTASCAN",
                self._estilos["titulo"],
            ),
            Paragraph(
                f"Relatório gerado em {data_relatorio}",
                self._estilos["subtitulo"],
            ),
            self._tabela_dados(
                [
                    ["Placa do veículo", str(viagem.placa_veiculo)],
                    ["ID da viagem", str(viagem.id)],
                    ["Data do processamento", data_proc_fmt],
                ]
            ),
        ]

    def _bloco_resumo(self, viagem: LeituraViagem, total_infracoes: int) -> list[object]:
        return [
            Paragraph("1. Resumo operacional", self._estilos["secao"]),
            self._tabela_dados(
                [
                    [
                        "Distância total estimada (km)",
                        f"{float(viagem.distancia_total_km):.2f}",
                    ],
                    [
                        "Velocidade máxima registrada (km/h)",
                        f"{float(viagem.velocidade_maxima):.1f}",
                    ],
                    ["Total de infrações detectadas", str(total_infracoes)],
                    [
                        "Limite de velocidade de referência (km/h)",
                        f"{self.limite_velocidade_kmh:.1f}",
                    ],
                ]
            ),
        ]

    def _bloco_imagem(self, caminho_imagem: str | None) -> list[object]:
        elementos: list[object] = [
            Paragraph("2. Comprovação visual (disco desdobrado)", self._estilos["secao"]),
        ]

        if not caminho_imagem:
            elementos.append(
                Paragraph(
                    "Imagem desdobrada não disponível para este laudo "
                    "(arquivo temporário ausente ou não vinculado à viagem).",
                    self._estilos["corpo"],
                )
            )
            return elementos

        caminho = Path(caminho_imagem)
        if not caminho.is_file():
            elementos.append(
                Paragraph(
                    f"Arquivo de imagem não encontrado: {caminho.name}",
                    self._estilos["corpo"],
                )
            )
            return elementos

        try:
            # Mantém proporção da imagem dentro da largura útil (~16 cm)
            imagem = Image(str(caminho))
            largura_max = 16 * cm
            altura_max = 5.5 * cm
            fator = min(
                largura_max / float(imagem.imageWidth),
                altura_max / float(imagem.imageHeight),
            )
            imagem.drawWidth = float(imagem.imageWidth) * fator
            imagem.drawHeight = float(imagem.imageHeight) * fator
            imagem.hAlign = "CENTER"
            elementos.append(imagem)
            elementos.append(
                Paragraph(
                    "Figura: transformação polar→cartesiana (eixo X ≈ 24 h; "
                    "eixo Y ≈ 0–120 km/h).",
                    self._estilos["subtitulo"],
                )
            )
        except Exception:  # noqa: BLE001 — não quebra o laudo se a imagem falhar
            elementos.append(
                Paragraph(
                    "Não foi possível incorporar a imagem desdobrada ao PDF.",
                    self._estilos["corpo"],
                )
            )

        return elementos

    def _bloco_infracoes(self, infracoes: Sequence[Infracao]) -> list[object]:
        elementos: list[object] = [
            Paragraph("3. Infrações e eventos detectados", self._estilos["secao"]),
        ]

        if not infracoes:
            elementos.append(
                Paragraph(
                    "Nenhuma infração registrada no período.",
                    self._estilos["ok"],
                )
            )
            return elementos

        cabecalho = [
            Paragraph("<b>Tipo de evento</b>", self._estilos["celula"]),
            Paragraph("<b>Início</b>", self._estilos["celula"]),
            Paragraph("<b>Fim</b>", self._estilos["celula"]),
            Paragraph("<b>Vel. máx. (km/h)</b>", self._estilos["celula"]),
            Paragraph("<b>Status / Limite</b>", self._estilos["celula"]),
        ]
        dados: list[list[object]] = [cabecalho]

        for item in infracoes:
            tipo = str(item.tipo_infracao)
            if tipo == "excesso_velocidade":
                rotulo = "Excesso de velocidade"
                vel = (
                    f"{float(item.velocidade_registrada):.1f}"
                    if item.velocidade_registrada is not None
                    else "—"
                )
                status = f"Acima do limite ({self.limite_velocidade_kmh:.0f} km/h)"
            else:
                rotulo = "Parada prolongada"
                vel = "0.0"
                status = "Parado > 10 min"

            dados.append(
                [
                    Paragraph(rotulo, self._estilos["celula"]),
                    Paragraph(str(item.hora_inicio), self._estilos["celula"]),
                    Paragraph(str(item.hora_fim), self._estilos["celula"]),
                    Paragraph(vel, self._estilos["celula"]),
                    Paragraph(status, self._estilos["celula"]),
                ]
            )

        tabela = Table(
            dados,
            colWidths=[4.2 * cm, 2.2 * cm, 2.2 * cm, 3.0 * cm, 4.8 * cm],
            repeatRows=1,
        )
        tabela.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e3a54")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#f7f9fb")),
                    ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#d5dee8")),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 4),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    (
                        "ROWBACKGROUNDS",
                        (0, 1),
                        (-1, -1),
                        [colors.HexColor("#ffffff"), colors.HexColor("#f3f6f9")],
                    ),
                ]
            )
        )
        elementos.append(tabela)
        return elementos

    def _bloco_rodape(self) -> list[object]:
        return [
            Paragraph("4. Responsabilidade técnica e assinatura", self._estilos["secao"]),
            Paragraph(
                "Este laudo foi gerado automaticamente pelo protótipo CronotaScan "
                "com base em visão computacional sobre o disco diagrama de "
                "cronotacógrafo analógico. Os valores de distância e velocidade são "
                "estimativas derivadas da imagem digitalizada e destinam-se a apoio "
                "à auditoria de frota. A validação final permanece sob "
                "responsabilidade do Gestor de Frota / Auditor técnico.",
                self._estilos["rodape"],
            ),
            Spacer(1, 18 * mm),
            Paragraph("________________________________________", self._estilos["assinatura"]),
            Paragraph(
                "Assinatura do Gestor de Frota / Auditor",
                self._estilos["assinatura"],
            ),
            Spacer(1, 4 * mm),
            Paragraph(
                "Nome / registro: ______________________________________",
                self._estilos["assinatura"],
            ),
        ]

    def _tabela_dados(self, linhas: list[list[str]]) -> Table:
        """Tabela simples rótulo × valor para cabeçalho e resumo."""
        dados = [
            [
                Paragraph(f"<b>{rotulo}</b>", self._estilos["celula"]),
                Paragraph(valor, self._estilos["celula"]),
            ]
            for rotulo, valor in linhas
        ]
        tabela = Table(dados, colWidths=[9 * cm, 7.4 * cm])
        tabela.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#eef3f7")),
                    ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#d5dee8")),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        return tabela
