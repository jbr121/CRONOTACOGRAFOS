"""
Processador de imagem para discos de cronotacógrafo analógico.

Fluxo principal:
1. Decodificar a imagem colorida (BGR) e equalizar (CLAHE)
2. Localizar o disco pelo papel claro + furo em gota (não pela mesa/mousepad)
3. Homografia da elipse → quadro quadrado centrado; só então warpPolar
4. Alinhar 00:00 pela ponta do furo mecânico em gota
5. Recortar a coroa de velocidade (≈ 0.70–0.92 R) e desdobrar polar → cartesiana
6. Estimar distância pela pista intermediária (zigue-zague do odômetro)
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Final, TypedDict

import cv2
import numpy as np
from numpy.typing import NDArray


# Constantes do domínio do cronotacógrafo (disco analógico padrão)
HORAS_NO_DIA: Final[int] = 24
MINUTOS_NO_DIA: Final[int] = HORAS_NO_DIA * 60
VELOCIDADE_MAXIMA_KMH: Final[int] = 125  # pista externa impressa 0–125 km/h

# Resolução padrão do desdobramento
LARGURA_PADRAO_PX: Final[int] = 1440  # 24 h * 60 min → 1 px ≈ 1 minuto
ALTURA_PADRAO_PX: Final[int] = 480    # faixa de velocidade 0–125 km/h

# Layout padrão EC/Kienzle (Antonacopoulos 2002; Fleetco):
#   miolo       — manuscritos do motorista
#   anel interno — odômetro (cursos de 5 km; um “V” completo = 10 km)
#   anel médio  — atividade (modo de trabalho)
#   anel externo — velocidade 0–125 km/h
FRACAO_RAIO_MIN_VELOCIDADE: Final[float] = 0.70
FRACAO_RAIO_MAX_VELOCIDADE: Final[float] = 0.92
FRACAO_RAIO_MIN_ODOMETRO: Final[float] = 0.32
FRACAO_RAIO_MAX_ODOMETRO: Final[float] = 0.52
# Segunda hipótese (discos em que o zigue-zague fica mais para fora)
FRACAO_RAIO_MIN_ODOMETRO_ALT: Final[float] = 0.52
FRACAO_RAIO_MAX_ODOMETRO_ALT: Final[float] = 0.68
# r_max nunca alcança a borda física do papel (fundo da mesa / recorte)
FRACAO_RMAX_VS_PAPEL: Final[float] = 0.92
FRACAO_MASCARA_PAPEL: Final[float] = 0.92
LADO_QUADRO_PX: Final[int] = 2000
# Raio do disco no quadro retificado (margem branca nas bordas)
FRACAO_RAIO_NO_QUADRO: Final[float] = 0.46
# Topo da imagem desdobrada = raio externo; ignora a vinheta preta da borda
MARGEM_Y_BORDA_EXTERNA: Final[float] = 0.08
# Costura polar (00:00 / 24:00): minutos branqueados em cada ponta do eixo X
MINUTOS_COSTURA_POLAR: Final[int] = 18

# Um “V” completo (ida+volta) = 10 km; cada deflexão = 5 km
KM_POR_CICLO_ODOMETRO: Final[float] = 10.0
KM_POR_DEFLEXAO_ODOMETRO: Final[float] = 5.0

# Rastreamento da agulha: caminhão não salta 0→125 km/h em 1 minuto
SALTO_MAXIMO_KMH_POR_MINUTO: Final[float] = 12.0
# Componentes da máscara mais estreitos que isto (minutos) são dígitos/sujeira
LARGURA_MINIMA_TRACO_PX: Final[int] = 16

# Critérios para aceitar um traço de estilete na coluna
CONTRASTE_MINIMO_TRACO: Final[int] = 28
PIXEIS_ESCUROS_MINIMOS: Final[int] = 4

# Faixa HSV do verde impresso do disco (grade/escala de velocidade).
# H no OpenCV vai de 0 a 179; o verde do papel varia entre esverdeado e oliva.
VERDE_HSV_BAIXO: Final[tuple[int, int, int]] = (30, 20, 20)
VERDE_HSV_ALTO: Final[tuple[int, int, int]] = (95, 255, 255)
# Grade pontilhada (20/40/60/80 km/h): saturação mais alta, sem o mousepad.
GRADE_VERDE_HSV_BAIXO: Final[tuple[int, int, int]] = (35, 40, 40)
GRADE_VERDE_HSV_ALTO: Final[tuple[int, int, int]] = (85, 255, 255)
# ~10% dos discos EC são vermelhos ou azuis (Antonacopoulos)
VERMELHO_HSV_BAIXO1: Final[tuple[int, int, int]] = (0, 40, 40)
VERMELHO_HSV_ALTO1: Final[tuple[int, int, int]] = (10, 255, 255)
VERMELHO_HSV_BAIXO2: Final[tuple[int, int, int]] = (170, 40, 40)
VERMELHO_HSV_ALTO2: Final[tuple[int, int, int]] = (179, 255, 255)
AZUL_HSV_BAIXO: Final[tuple[int, int, int]] = (100, 40, 40)
AZUL_HSV_ALTO: Final[tuple[int, int, int]] = (130, 255, 255)
FRACAO_MINIMA_VERDE: Final[float] = 0.004
# Variância do Laplaciano abaixo disto → foto borrada (só aviso, não bloqueia)
NITIDEZ_MINIMA: Final[float] = 45.0
# Fotos de celular 4K+ são redimensionadas: Hough e polar ficam mais estáveis
MAX_LADO_PROCESSAMENTO_PX: Final[int] = 1800

# CLAHE (equalização adaptativa) — normaliza sombras e reflexos do papel brilhante
CLAHE_CLIP_LIMIT: Final[float] = 2.0
CLAHE_TILE_GRID: Final[tuple[int, int]] = (8, 8)

# Correção de perspectiva: rejeita só elipses absurdas (mesa, blob)
RAZAO_ELIPSE_MINIMA: Final[float] = 1.03
RAZAO_ELIPSE_MAXIMA: Final[float] = 2.20

# Pasta de debug na raiz do projeto
RAIZ_PROJETO: Final[Path] = Path(__file__).resolve().parent.parent
PASTA_TEMP: Final[Path] = RAIZ_PROJETO / "temp"


class PontoVelocidade(TypedDict):
    """Um ponto da curva: hora do dia + velocidade estimada."""
    hora: str
    velocidade_kmh: float


@dataclass(frozen=True, slots=True)
class CirculoDetectado:
    """Representa o furo central encontrado na imagem."""
    centro_x: int
    centro_y: int
    raio: int


@dataclass(frozen=True, slots=True)
class ResultadoProcessamento:
    """Saída consolidada do pipeline de leitura do disco."""
    imagem_cinza: NDArray[np.uint8]
    circulo: CirculoDetectado
    imagem_desdobrada: NDArray[np.uint8]
    largura_px: int
    altura_px: int
    mascara_grade_desdobrada: NDArray[np.uint8] | None = None
    distancia_odometro_km: float | None = None
    ciclos_odometro: int = 0
    angulo_zero_graus: float = 0.0
    nitidez: float = 0.0
    alinhamento_gota: bool = False


class ErroProcessamentoDisco(Exception):
    """Erro de domínio genérico no processamento do disco."""


class ImagemInvalidaError(ErroProcessamentoDisco):
    """Imagem ausente, corrompida ou em formato não suportado."""


class FuroNaoEncontradoError(ErroProcessamentoDisco):
    """Não foi possível localizar o furo central com HoughCircles."""


class LeitorDisco:
    """
    Classe responsável por transformar um escaneamento circular
    em uma representação retangular (tempo × velocidade).
    """

    def __init__(
        self,
        largura_desdobramento: int = LARGURA_PADRAO_PX,
        altura_desdobramento: int = ALTURA_PADRAO_PX,
        velocidade_maxima_kmh: int = VELOCIDADE_MAXIMA_KMH,
        fracao_raio_min: float = FRACAO_RAIO_MIN_VELOCIDADE,
        fracao_raio_max: float = FRACAO_RAIO_MAX_VELOCIDADE,
        fracao_odometro_min: float = FRACAO_RAIO_MIN_ODOMETRO,
        fracao_odometro_max: float = FRACAO_RAIO_MAX_ODOMETRO,
        km_por_ciclo_odometro: float = KM_POR_CICLO_ODOMETRO,
    ) -> None:
        if largura_desdobramento <= 0 or altura_desdobramento <= 0:
            raise ValueError("As dimensões do desdobramento devem ser positivas.")
        if velocidade_maxima_kmh <= 0:
            raise ValueError("A velocidade máxima deve ser positiva.")
        if not (0.0 < fracao_raio_min < fracao_raio_max <= 1.0):
            raise ValueError("As frações de raio devem obedecer: 0 < min < max <= 1.")
        if not (0.0 < fracao_odometro_min < fracao_odometro_max <= 1.0):
            raise ValueError("As frações do odômetro devem obedecer: 0 < min < max <= 1.")
        if km_por_ciclo_odometro <= 0:
            raise ValueError("km_por_ciclo_odometro deve ser positivo.")

        self.largura_desdobramento = largura_desdobramento
        self.altura_desdobramento = altura_desdobramento
        self.velocidade_maxima_kmh = velocidade_maxima_kmh
        self.fracao_raio_min = fracao_raio_min
        self.fracao_raio_max = fracao_raio_max
        self.fracao_odometro_min = fracao_odometro_min
        self.fracao_odometro_max = fracao_odometro_max
        self.km_por_ciclo_odometro = km_por_ciclo_odometro

    def _decodificar_bgr(self, dados_imagem: bytes) -> NDArray[np.uint8]:
        """Decodifica os bytes recebidos em uma imagem colorida (BGR) validada."""
        if not dados_imagem:
            raise ImagemInvalidaError("Arquivo de imagem vazio. Selecione um PNG ou JPG válido.")

        imagem_bgr = self._bytes_para_bgr(dados_imagem)
        if imagem_bgr is None or imagem_bgr.size == 0 or min(imagem_bgr.shape[:2]) < 50:
            raise ImagemInvalidaError("A imagem é muito pequena ou inválida.")

        return self._limitar_tamanho(imagem_bgr)

    def _bytes_para_bgr(self, dados_imagem: bytes) -> NDArray[np.uint8] | None:
        """
        Decodifica com Pillow (respeita EXIF de celular) e cai no OpenCV se falhar.
        """
        try:
            from PIL import Image, ImageOps

            with Image.open(BytesIO(dados_imagem)) as pil:
                pil = ImageOps.exif_transpose(pil)
                rgb = np.array(pil.convert("RGB"))
            if rgb.ndim != 3 or rgb.shape[2] < 3:
                raise ValueError("RGB inválido")
            return cv2.cvtColor(rgb[:, :, :3], cv2.COLOR_RGB2BGR)
        except Exception:
            try:
                buffer = np.frombuffer(dados_imagem, dtype=np.uint8)
                return cv2.imdecode(buffer, cv2.IMREAD_COLOR)
            except Exception as erro:
                raise ImagemInvalidaError("Falha ao ler o arquivo de imagem.") from erro

    def _limitar_tamanho(self, imagem_bgr: NDArray[np.uint8]) -> NDArray[np.uint8]:
        """Reduz fotos enormes para um lado máximo — acelera e estabiliza o Hough."""
        altura, largura = imagem_bgr.shape[:2]
        maior = max(altura, largura)
        if maior <= MAX_LADO_PROCESSAMENTO_PX:
            return imagem_bgr
        escala = MAX_LADO_PROCESSAMENTO_PX / float(maior)
        novo = (max(1, int(round(largura * escala))), max(1, int(round(altura * escala))))
        return cv2.resize(imagem_bgr, novo, interpolation=cv2.INTER_AREA)

    def carregar_imagem_cinza(self, dados_imagem: bytes) -> NDArray[np.uint8]:
        """Compatibilidade: decodifica e converte diretamente para escala de cinza."""
        return cv2.cvtColor(self._decodificar_bgr(dados_imagem), cv2.COLOR_BGR2GRAY)

    def _equalizar_iluminacao(
        self,
        imagem_cinza: NDArray[np.uint8],
    ) -> NDArray[np.uint8]:
        """
        Equalização adaptativa de contraste (CLAHE).

        Por quê: fotos do mesmo disco variam muito com luz/ângulo. Sombras
        "apagam" o traço do estilete e reflexos "estouram" o papel. O CLAHE
        normaliza o brilho por regiões (tiles), preservando o contraste local
        do traço sem estourar a imagem inteira como faria uma equalização global.
        Isto reduz drasticamente a instabilidade entre fotos diferentes.
        """
        clahe = cv2.createCLAHE(
            clipLimit=CLAHE_CLIP_LIMIT,
            tileGridSize=CLAHE_TILE_GRID,
        )
        return clahe.apply(imagem_cinza)

    def _mascara_verde(
        self,
        imagem_bgr: NDArray[np.uint8],
    ) -> NDArray[np.uint8] | None:
        """Compatibilidade: devolve a máscara da grade impressa (verde/vermelho/azul)."""
        return self._mascara_grade_impressa(imagem_bgr)

    def _mascara_grade_impressa(
        self,
        imagem_bgr: NDArray[np.uint8],
    ) -> NDArray[np.uint8] | None:
        """
        Isola o gabarito impresso (verde na maioria; vermelho/azul em ~10%).

        HSV separa matiz de brilho, então a máscara sobrevive a variação de luz.
        """
        if imagem_bgr is None or imagem_bgr.ndim != 3:
            return None

        hsv = cv2.cvtColor(imagem_bgr, cv2.COLOR_BGR2HSV)
        faixas = (
            (VERDE_HSV_BAIXO, VERDE_HSV_ALTO),
            (VERMELHO_HSV_BAIXO1, VERMELHO_HSV_ALTO1),
            (VERMELHO_HSV_BAIXO2, VERMELHO_HSV_ALTO2),
            (AZUL_HSV_BAIXO, AZUL_HSV_ALTO),
        )
        mascara = np.zeros(hsv.shape[:2], dtype=np.uint8)
        for baixo, alto in faixas:
            mascara = cv2.bitwise_or(
                mascara,
                cv2.inRange(hsv, np.array(baixo, dtype=np.uint8), np.array(alto, dtype=np.uint8)),
            )

        nucleo = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        mascara = cv2.morphologyEx(mascara, cv2.MORPH_CLOSE, nucleo, iterations=1)
        return mascara

    def _mascara_somente_verde(
        self,
        imagem_bgr: NDArray[np.uint8],
    ) -> NDArray[np.uint8] | None:
        """Tinta verde da grade pontilhada (HSV rígido — sem azul do mousepad)."""
        if imagem_bgr is None or imagem_bgr.ndim != 3:
            return None
        hsv = cv2.cvtColor(imagem_bgr, cv2.COLOR_BGR2HSV)
        mascara = cv2.inRange(
            hsv,
            np.array(GRADE_VERDE_HSV_BAIXO, dtype=np.uint8),
            np.array(GRADE_VERDE_HSV_ALTO, dtype=np.uint8),
        )
        if float((mascara > 0).mean()) < 0.002:
            mascara = cv2.inRange(
                hsv,
                np.array(VERDE_HSV_BAIXO, dtype=np.uint8),
                np.array(VERDE_HSV_ALTO, dtype=np.uint8),
            )
        nucleo = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        return cv2.morphologyEx(mascara, cv2.MORPH_CLOSE, nucleo, iterations=1)

    def _mascara_papel_hsv(self, imagem_bgr: NDArray[np.uint8]) -> NDArray[np.uint8]:
        """
        Papel branco/creme do disco.

        Mousepad azul-claro (V alto, S médio, H azul) passava na faixa larga
        V>=130/S<=90 e virava o 'disco'. Aqui: quase branco OU creme esverdeado,
        nunca matiz azul saturado.
        """
        hsv = cv2.cvtColor(imagem_bgr, cv2.COLOR_BGR2HSV)
        branco = cv2.inRange(
            hsv,
            np.array((0, 0, 168), dtype=np.uint8),
            np.array((180, 40, 255), dtype=np.uint8),
        )
        creme = cv2.inRange(
            hsv,
            np.array((8, 0, 155), dtype=np.uint8),
            np.array((85, 50, 255), dtype=np.uint8),
        )
        mascara = cv2.bitwise_or(branco, creme)
        azul = cv2.inRange(
            hsv,
            np.array((90, 30, 0), dtype=np.uint8),
            np.array((140, 255, 255), dtype=np.uint8),
        )
        mascara[azul > 0] = 0
        nucleo = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (11, 11))
        mascara = cv2.morphologyEx(mascara, cv2.MORPH_CLOSE, nucleo, iterations=2)
        mascara = cv2.morphologyEx(mascara, cv2.MORPH_OPEN, nucleo, iterations=1)
        return mascara

    def _tem_miolo_escuro(
        self,
        imagem_cinza: NDArray[np.uint8],
        centro_x: float,
        centro_y: float,
        raio: float,
    ) -> bool:
        """O disco real tem furo em gota escuro no miolo; o mousepad não."""
        if raio < 30:
            return False
        altura, largura = imagem_cinza.shape[:2]
        cx, cy = int(round(centro_x)), int(round(centro_y))
        r_miolo = max(6, int(round(raio * 0.12)))
        x0, y0 = max(0, cx - r_miolo), max(0, cy - r_miolo)
        x1, y1 = min(largura, cx + r_miolo), min(altura, cy + r_miolo)
        if x1 - x0 < 4 or y1 - y0 < 4:
            return False
        miolo = float(imagem_cinza[y0:y1, x0:x1].mean())
        ys, xs = np.ogrid[0:altura, 0:largura]
        dist = np.sqrt((xs - centro_x) ** 2 + (ys - centro_y) ** 2)
        anel = (dist >= raio * 0.28) & (dist <= raio * 0.50)
        if not np.any(anel):
            return False
        papel = float(imagem_cinza[anel].mean())
        return miolo + 22.0 < papel

    def _contorno_mais_proximo_do_circulo(
        self,
        mascara: NDArray[np.uint8],
        circulo: CirculoDetectado,
    ) -> NDArray[np.int32] | None:
        contornos, _ = cv2.findContours(mascara, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contornos:
            return None
        melhor = None
        melhor_dist = float("inf")
        for contorno in contornos:
            if len(contorno) < 5:
                continue
            (cx, cy), raio = cv2.minEnclosingCircle(contorno)
            dist = abs(cx - circulo.centro_x) + abs(cy - circulo.centro_y) + abs(raio - circulo.raio)
            if dist < melhor_dist:
                melhor_dist = dist
                melhor = contorno
        return melhor

    def _localizar_disco_por_papel(
        self,
        imagem_bgr: NDArray[np.uint8],
        imagem_cinza: NDArray[np.uint8],
    ) -> CirculoDetectado | None:
        """
        Maior blob de papel claro que contém o furo em gota.

        Evita travar no mousepad (linhas/RGB) que o verde ou o maior
        contorno adaptativo pegavam como se fossem o disco.
        """
        if imagem_bgr is None or imagem_bgr.ndim != 3:
            return None
        mascara = self._mascara_papel_hsv(imagem_bgr)
        contornos, _ = cv2.findContours(mascara, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contornos:
            return None
        altura, largura = imagem_cinza.shape[:2]
        area_img = float(altura * largura)
        candidatos = sorted(contornos, key=cv2.contourArea, reverse=True)
        melhor: CirculoDetectado | None = None
        melhor_area = 0.0
        for contorno in candidatos[:8]:
            area = float(cv2.contourArea(contorno))
            if area < area_img * 0.04:
                break
            if area > area_img * 0.90:
                continue
            if len(contorno) < 5:
                continue
            (cx, cy), raio_enc = cv2.minEnclosingCircle(contorno)
            if raio_enc < 40.0:
                continue
            preenchimento = area / (np.pi * raio_enc * raio_enc)
            if preenchimento < 0.68:
                continue
            if raio_enc > min(altura, largura) * 0.55:
                continue
            if not self._tem_miolo_escuro(imagem_cinza, cx, cy, raio_enc):
                continue
            pontos = contorno.reshape(-1, 2).astype(np.float64)
            dist = np.sqrt((pontos[:, 0] - cx) ** 2 + (pontos[:, 1] - cy) ** 2)
            raio = float(np.percentile(dist, 99.0))
            raio = min(raio, raio_enc)
            if area > melhor_area:
                melhor_area = area
                melhor = CirculoDetectado(
                    centro_x=int(round(cx)),
                    centro_y=int(round(cy)),
                    raio=int(round(raio)),
                )
        return melhor

    def _raio_papel_a_partir_do_furo(
        self,
        imagem_bgr: NDArray[np.uint8],
        furo: CirculoDetectado,
    ) -> int | None:
        """Do miolo, caminha no papel claro até a borda do disco."""
        mascara = self._mascara_papel_hsv(imagem_bgr)
        fracao = float((mascara > 0).mean())
        if fracao > 0.85:
            return None
        altura, largura = mascara.shape[:2]
        cx, cy = int(furo.centro_x), int(furo.centro_y)
        if not (0 <= cx < largura and 0 <= cy < altura):
            return None
        r0 = max(8, int(furo.raio) * 2)
        r1 = int(min(cx, cy, largura - cx - 1, altura - cy - 1))
        if r1 <= r0 + 10:
            return None
        raios: list[int] = []
        for k in range(72):
            ang = (2.0 * np.pi * k) / 72.0
            coss, seno = float(np.cos(ang)), float(np.sin(ang))
            ultimo = None
            for raio in range(r0, r1):
                x = int(round(cx + raio * coss))
                y = int(round(cy + raio * seno))
                if not (0 <= x < largura and 0 <= y < altura):
                    break
                if mascara[y, x] > 0:
                    ultimo = raio
                elif ultimo is not None and raio > ultimo + 6:
                    break
            if ultimo is not None:
                raios.append(ultimo)
        if len(raios) < 24:
            return None
        return int(round(float(np.median(np.array(raios, dtype=np.float64)))))

    def detectar_centro(
        self,
        imagem_bgr: NDArray[np.uint8],
        imagem_cinza: NDArray[np.uint8],
        mascara_verde: NDArray[np.uint8] | None = None,
    ) -> CirculoDetectado:
        """
        Centro/raio do PAPEL do disco, ancorado no furo em gota.

        A grade verde só entra se o centroide cair dentro do papel claro —
        senão um mousepad RGB vira o “disco” e o warpPolar desdobra a mesa.
        """
        disco = self._localizar_disco_por_papel(imagem_bgr, imagem_cinza)
        if disco is not None:
            return disco

        mascara_papel = None
        fracao_papel = 0.0
        if imagem_bgr is not None and imagem_bgr.ndim == 3:
            mascara_papel = self._mascara_papel_hsv(imagem_bgr)
            fracao_papel = float((mascara_papel > 0).mean())
        fundo_estudio = fracao_papel > 0.85
        lado_min = min(imagem_cinza.shape[:2])

        if not fundo_estudio and imagem_bgr is not None and imagem_bgr.ndim == 3:
            try:
                furo = self.encontrar_furo_central(imagem_cinza)
            except FuroNaoEncontradoError:
                furo = None
            if furo is not None:
                raio_papel = self._raio_papel_a_partir_do_furo(imagem_bgr, furo)
                if (
                    raio_papel is not None
                    and raio_papel > max(40, furo.raio * 4)
                    and raio_papel <= lado_min * 0.55
                ):
                    return CirculoDetectado(
                        centro_x=furo.centro_x,
                        centro_y=furo.centro_y,
                        raio=raio_papel,
                    )

        centro_verde = self.encontrar_centro_pela_grade_verde(imagem_bgr, None)
        if centro_verde is not None and centro_verde.raio <= lado_min * 0.55:
            if fundo_estudio or mascara_papel is None:
                return centro_verde
            cx, cy = centro_verde.centro_x, centro_verde.centro_y
            altura, largura = mascara_papel.shape[:2]
            if 0 <= cy < altura and 0 <= cx < largura and mascara_papel[cy, cx] > 0:
                return centro_verde

        if centro_verde is not None and fundo_estudio:
            return centro_verde
        return self.encontrar_furo_central(imagem_cinza)

    def encontrar_centro_pela_grade_verde(
        self,
        imagem_bgr: NDArray[np.uint8],
        mascara_verde: NDArray[np.uint8] | None = None,
    ) -> CirculoDetectado | None:
        """
        Usa a tinta verde impressa (círculos de escala) como referência absoluta.

        Por que isto corrige a ondulação:
        - O furo físico (formato pera) fica levemente deslocado do centro da
          impressão. A grade verde é concêntrica e simétrica, então o centroide
          da máscara verde coincide com o centro real da escala de velocidade.
        - O raio é refinado com cv2.minEnclosingCircle sobre os pontos verdes,
          que cerca a escala completa independentemente de pequenas assimetrias.

        Retorna None se não houver verde suficiente (deixa o fallback assumir).
        """
        if imagem_bgr is None or imagem_bgr.ndim != 3:
            return None

        altura, largura = imagem_bgr.shape[:2]
        mascara = self._mascara_somente_verde(imagem_bgr)
        if mascara is None:
            mascara = mascara_verde if mascara_verde is not None else self._mascara_verde(imagem_bgr)
        if mascara is None:
            return None

        ys, xs = np.nonzero(mascara)
        total_pixels = altura * largura
        if xs.size < max(50, int(total_pixels * FRACAO_MINIMA_VERDE)):
            return None

        # Verde ocupando quase tudo → provavelmente fundo verde, não a grade
        if xs.size > total_pixels * 0.6:
            return None

        # 1ª estimativa do centro: centroide de toda a máscara verde
        cx = float(xs.mean())
        cy = float(ys.mean())

        # Refino: recalcula o centroide considerando só o anel externo da grade
        # (reduz o peso de manuscritos/carimbos verdes no miolo)
        distancias = np.sqrt((xs - cx) ** 2 + (ys - cy) ** 2)
        raio_externo = float(np.percentile(distancias, 98))
        if raio_externo <= 1.0:
            return None

        anel = distancias >= (raio_externo * 0.55)
        if int(np.count_nonzero(anel)) >= 50:
            cx = float(xs[anel].mean())
            cy = float(ys[anel].mean())

        # Raio absoluto: menor círculo que envolve toda a tinta verde
        pontos = np.column_stack((xs, ys)).astype(np.float32)
        (_, _), raio_menor_circulo = cv2.minEnclosingCircle(pontos)
        # Combina percentil (robusto a outliers) com o círculo envolvente
        distancias = np.sqrt((xs - cx) ** 2 + (ys - cy) ** 2)
        raio_p98 = float(np.percentile(distancias, 98))
        raio_externo = float(min(raio_menor_circulo, raio_p98 * 1.05))

        centro_x = int(round(cx))
        centro_y = int(round(cy))
        raio = int(round(raio_externo))

        if not (0 <= centro_x < largura and 0 <= centro_y < altura):
            return None
        if raio <= 5:
            return None

        return CirculoDetectado(centro_x=centro_x, centro_y=centro_y, raio=raio)

    def _contorno_papel(
        self,
        imagem_cinza: NDArray[np.uint8],
    ) -> NDArray[np.int32] | None:
        """Maior contorno do disco (papel claro × mesa escura)."""
        if imagem_cinza.size == 0 or min(imagem_cinza.shape[:2]) < 40:
            return None
        suavizada = cv2.GaussianBlur(imagem_cinza, (7, 7), 0)
        binaria = cv2.adaptiveThreshold(
            suavizada,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            11,
            2,
        )
        if float(binaria.mean()) < 127.0:
            binaria = cv2.bitwise_not(binaria)
        nucleo = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (11, 11))
        binaria = cv2.morphologyEx(binaria, cv2.MORPH_CLOSE, nucleo, iterations=3)
        contornos, _ = cv2.findContours(binaria, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contornos:
            _, otsu = cv2.threshold(suavizada, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            if float(otsu.mean()) < 127.0:
                otsu = cv2.bitwise_not(otsu)
            otsu = cv2.morphologyEx(otsu, cv2.MORPH_CLOSE, nucleo, iterations=2)
            contornos, _ = cv2.findContours(otsu, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if not contornos:
                return None
        maior = max(contornos, key=cv2.contourArea)
        area_img = float(imagem_cinza.shape[0] * imagem_cinza.shape[1])
        if cv2.contourArea(maior) < area_img * 0.08:
            return None
        return maior

    def _circulo_do_papel(
        self,
        imagem_cinza: NDArray[np.uint8],
        imagem_bgr: NDArray[np.uint8] | None = None,
    ) -> CirculoDetectado | None:
        """Centro e raio do PAPEL (não da grade verde, que desloca o warpPolar)."""
        if imagem_bgr is not None and imagem_bgr.ndim == 3:
            disco = self._localizar_disco_por_papel(imagem_bgr, imagem_cinza)
            if disco is not None:
                return disco
        if float(np.mean(imagem_cinza)) > 200.0:
            return None
        contorno = self._contorno_papel(imagem_cinza)
        if contorno is None or len(contorno) < 5:
            return None
        area = float(cv2.contourArea(contorno))
        area_img = float(imagem_cinza.shape[0] * imagem_cinza.shape[1])
        if area > area_img * 0.90:
            return None
        (cx, cy), raio = cv2.minEnclosingCircle(contorno)
        if raio < 40:
            return None
        preenchimento = area / (np.pi * raio * raio)
        if preenchimento < 0.68:
            return None
        if raio > min(imagem_cinza.shape[:2]) * 0.55:
            return None
        if not self._tem_miolo_escuro(imagem_cinza, cx, cy, raio):
            return None
        return CirculoDetectado(
            centro_x=int(round(cx)),
            centro_y=int(round(cy)),
            raio=int(round(raio)),
        )

    def _enquadrar_disco(
        self,
        imagem: NDArray[np.uint8],
        circulo: CirculoDetectado,
        lado: int = LADO_QUADRO_PX,
    ) -> tuple[NDArray[np.uint8], CirculoDetectado]:
        """Recorta um quadrado só com o disco e redimensiona (ex.: 2000×2000)."""
        raio = max(int(circulo.raio), 24)
        margem = max(4, int(round(raio * 0.03)))
        metade = raio + margem
        lado_src = max(2 * metade, 32)
        if imagem.ndim == 3:
            canvas = np.full((lado_src, lado_src, imagem.shape[2]), 255, dtype=np.uint8)
        else:
            canvas = np.full((lado_src, lado_src), 255, dtype=np.uint8)

        x0 = int(circulo.centro_x) - metade
        y0 = int(circulo.centro_y) - metade
        x1 = x0 + lado_src
        y1 = y0 + lado_src
        altura, largura = imagem.shape[:2]
        xs0, ys0 = max(0, x0), max(0, y0)
        xs1, ys1 = min(largura, x1), min(altura, y1)
        xd0, yd0 = xs0 - x0, ys0 - y0
        xd1, yd1 = xd0 + (xs1 - xs0), yd0 + (ys1 - ys0)
        if xs1 > xs0 and ys1 > ys0:
            canvas[yd0:yd1, xd0:xd1] = imagem[ys0:ys1, xs0:xs1]

        quadro = cv2.resize(canvas, (lado, lado), interpolation=cv2.INTER_AREA)
        escala = lado / float(lado_src)
        novo = CirculoDetectado(
            centro_x=lado // 2,
            centro_y=lado // 2,
            raio=max(8, int(round(raio * escala))),
        )
        return quadro, novo

    def _elipse_da_grade_verde(
        self,
        imagem_bgr: NDArray[np.uint8],
        circulo: CirculoDetectado | None = None,
    ) -> tuple[tuple[float, float], tuple[float, float], float] | None:
        """Elipse das circunferências verdes — a que o polar precisa circularizar."""
        mascara = self._mascara_somente_verde(imagem_bgr)
        if mascara is None:
            return None
        ys, xs = np.nonzero(mascara)
        if xs.size < 80:
            return None
        pts = np.column_stack((xs, ys)).astype(np.float32)
        if circulo is not None:
            dist = np.sqrt(
                (pts[:, 0] - float(circulo.centro_x)) ** 2
                + (pts[:, 1] - float(circulo.centro_y)) ** 2
            )
            raio_ref = max(float(circulo.raio), 1.0)
            anel = (dist >= raio_ref * 0.62) & (dist <= raio_ref * 1.02)
            if int(np.count_nonzero(anel)) >= 80:
                pts = pts[anel]
        if pts.shape[0] < 5:
            return None
        try:
            (cx, cy), eixos, angulo = cv2.fitEllipse(pts)
        except cv2.error:
            return None
        if min(eixos) < 20:
            return None
        return (float(cx), float(cy)), (float(eixos[0]), float(eixos[1])), float(angulo)

    def _elipse_por_raio_verde(
        self,
        imagem_bgr: NDArray[np.uint8],
        circulo: CirculoDetectado,
    ) -> tuple[tuple[float, float], tuple[float, float], float] | None:
        """
        Elipse pelos raios da tinta verde (1 ponto/°).

        fitEllipse em todos os pixels verdes inclui traços radiais (24h) e distorce;
        aqui só entra o contorno externo de cada raio no anel de velocidade.
        """
        mascara = self._mascara_somente_verde(imagem_bgr)
        if mascara is None:
            return None
        base = self._centro_hough_circunferencias_verdes(imagem_bgr, circulo) or circulo
        cx0, cy0 = float(base.centro_x), float(base.centro_y)
        raio_ref = max(float(circulo.raio), 24.0)
        altura, largura = mascara.shape[:2]
        pts: list[list[float]] = []
        for deg in range(360):
            th = np.deg2rad(float(deg))
            cth, sth = float(np.cos(th)), float(np.sin(th))
            for r in range(int(raio_ref * 0.65), int(raio_ref * 0.98)):
                x = int(round(cx0 + r * cth))
                y = int(round(cy0 + r * sth))
                if 0 <= x < largura and 0 <= y < altura and mascara[y, x] > 0:
                    pts.append([float(x), float(y)])
                    break
        if len(pts) < 60:
            return None
        arr = np.asarray(pts, dtype=np.float32)
        try:
            (cx, cy), eixos, angulo = cv2.fitEllipse(arr)
        except cv2.error:
            return None
        if min(eixos) < 20:
            return None
        return (float(cx), float(cy)), (float(eixos[0]), float(eixos[1])), float(angulo)

    def _score_elipse_pos_homografia(
        self,
        imagem_bgr: NDArray[np.uint8],
        elipse: tuple[tuple[float, float], tuple[float, float], float],
        lado: int = LADO_QUADRO_PX,
    ) -> float:
        """Ondulação da grade após homografia + busca grossa de centro (menor = melhor)."""
        convertido = self._homografia_elipse_para_quadro(elipse, lado)
        if convertido is None:
            return 1e9
        homografia, circulo = convertido
        warped = cv2.warpPerspective(
            imagem_bgr,
            homografia,
            (int(lado), int(lado)),
            flags=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=(255, 255, 255),
        )
        mascara = self._mascara_somente_verde(warped)
        if mascara is None:
            return 1e9
        r_min = float(circulo.raio) * FRACAO_RAIO_MIN_VELOCIDADE
        r_max = float(circulo.raio) * FRACAO_RAIO_MAX_VELOCIDADE
        melhor = 1e9
        for dx in range(-40, 41, 8):
            for dy in range(-40, 41, 8):
                cand = CirculoDetectado(
                    centro_x=circulo.centro_x + dx,
                    centro_y=circulo.centro_y + dy,
                    raio=circulo.raio,
                )
                desdobrada = self._desdobrar_anel(
                    mascara, cand, r_min, r_max, largura_px=480, altura_px=160,
                )
                melhor = min(melhor, self._score_ondulacao_grade(desdobrada))
        return float(melhor)

    def _escolher_elipse_perspectiva(
        self,
        imagem_bgr: NDArray[np.uint8],
        circulo: CirculoDetectado,
        lado: int = LADO_QUADRO_PX,
    ) -> tuple[tuple[float, float], tuple[float, float], float] | None:
        """Testa elipse do papel, da grade e por raio; fica com a de menor ondulação."""
        candidatos: list[tuple[tuple[float, float], tuple[float, float], float]] = []
        vistos: set[tuple[float, float, float, float, float]] = set()

        def registrar(
            el: tuple[tuple[float, float], tuple[float, float], float] | None,
        ) -> None:
            if el is None:
                return
            (cx, cy), (ew, eh), ang = el
            chave = (
                round(cx, 1), round(cy, 1),
                round(ew, 1), round(eh, 1), round(ang, 1),
            )
            if chave in vistos:
                return
            vistos.add(chave)
            candidatos.append(el)

        registrar(self._elipse_do_papel(imagem_bgr))
        registrar(self._elipse_da_grade_verde(imagem_bgr, circulo))
        registrar(self._elipse_por_raio_verde(imagem_bgr, circulo))

        if not candidatos:
            return None
        melhor = candidatos[0]
        melhor_score = self._score_elipse_pos_homografia(imagem_bgr, melhor, lado)
        for el in candidatos[1:]:
            score = self._score_elipse_pos_homografia(imagem_bgr, el, lado)
            if score < melhor_score:
                melhor_score = score
                melhor = el
        return melhor

    def _elipse_do_papel(
        self,
        imagem: NDArray[np.uint8],
    ) -> tuple[tuple[float, float], tuple[float, float], float] | None:
        """Elipse do papel (HSV + furo) para a homografia — não a da mesa."""
        if imagem.ndim == 3:
            cinza = cv2.cvtColor(imagem, cv2.COLOR_BGR2GRAY)
            disco = self._localizar_disco_por_papel(imagem, cinza)
            if disco is not None:
                contorno = self._contorno_mais_proximo_do_circulo(
                    self._mascara_papel_hsv(imagem), disco,
                )
                if contorno is not None and len(contorno) >= 5:
                    (cx, cy), eixos, angulo = cv2.fitEllipse(contorno)
                    return (float(cx), float(cy)), (float(eixos[0]), float(eixos[1])), float(angulo)
            cinza_para_fallback = cinza
        else:
            cinza_para_fallback = imagem

        maior = self._contorno_papel(cinza_para_fallback)
        if maior is None or len(maior) < 5:
            return None
        area = float(cv2.contourArea(maior))
        area_img = float(cinza_para_fallback.shape[0] * cinza_para_fallback.shape[1])
        if area > area_img * 0.90:
            return None
        (ecx, ecy), raio = cv2.minEnclosingCircle(maior)
        if raio < 40 or area / (np.pi * raio * raio) < 0.68:
            return None
        if raio > min(cinza_para_fallback.shape[:2]) * 0.55:
            return None
        if not self._tem_miolo_escuro(cinza_para_fallback, ecx, ecy, raio):
            return None
        (cx, cy), eixos, angulo = cv2.fitEllipse(maior)
        return (float(cx), float(cy)), (float(eixos[0]), float(eixos[1])), float(angulo)

    def _homografia_elipse_para_quadro(
        self,
        elipse: tuple[tuple[float, float], tuple[float, float], float],
        lado: int = LADO_QUADRO_PX,
    ) -> tuple[NDArray[np.float32], CirculoDetectado] | None:
        """
        4 extremos da elipse → círculo centrado em (lado/2, lado/2).

        Polar em cima de elipse vira seno; esta homografia deixa a grade
        horizontal. Preserva a orientação (o eixo 12h–24h não gira).
        """
        (cx, cy), (eixo_w, eixo_h), angulo = elipse
        semi_a = float(eixo_w) / 2.0
        semi_b = float(eixo_h) / 2.0
        if semi_a <= 2.0 or semi_b <= 2.0:
            return None
        razao = max(semi_a, semi_b) / min(semi_a, semi_b)
        if razao < RAZAO_ELIPSE_MINIMA or razao > RAZAO_ELIPSE_MAXIMA:
            return None

        theta = np.deg2rad(float(angulo))
        ux, uy = float(np.cos(theta)), float(np.sin(theta))
        vx, vy = -uy, ux
        cx_d = float(lado) / 2.0
        cy_d = float(lado) / 2.0
        raio = float(lado) * FRACAO_RAIO_NO_QUADRO
        origem = np.array(
            [
                [cx + semi_a * ux, cy + semi_a * uy],
                [cx - semi_a * ux, cy - semi_a * uy],
                [cx + semi_b * vx, cy + semi_b * vy],
                [cx - semi_b * vx, cy - semi_b * vy],
            ],
            dtype=np.float32,
        )
        destino = np.array(
            [
                [cx_d + raio * ux, cy_d + raio * uy],
                [cx_d - raio * ux, cy_d - raio * uy],
                [cx_d + raio * vx, cy_d + raio * vy],
                [cx_d - raio * vx, cy_d - raio * vy],
            ],
            dtype=np.float32,
        )
        try:
            homografia = cv2.getPerspectiveTransform(origem, destino)
        except cv2.error:
            return None
        circulo = CirculoDetectado(
            centro_x=int(lado) // 2,
            centro_y=int(lado) // 2,
            raio=max(8, int(round(raio))),
        )
        return homografia.astype(np.float32), circulo

    def _homografia_elipse_circulo(
        self,
        elipse: tuple[tuple[float, float], tuple[float, float], float],
    ) -> tuple[NDArray[np.float32], CirculoDetectado] | None:
        """Compatibilidade: retifica para o quadro quadrado padrão."""
        return self._homografia_elipse_para_quadro(elipse, LADO_QUADRO_PX)

    def corrigir_perspectiva(
        self,
        imagem: NDArray[np.uint8],
        circulo: CirculoDetectado,
        mascara_verde: NDArray[np.uint8] | None,
        lado: int = LADO_QUADRO_PX,
    ) -> tuple[NDArray[np.uint8], CirculoDetectado, NDArray[np.float32] | None]:
        """
        Elipse da foto de celular → círculo num quadrado (centro = lado/2).

        warpPolar só depois desta retificação; senão a grade vira seno.
        """
        if imagem.ndim == 3:
            elipse = self._escolher_elipse_perspectiva(imagem, circulo, lado)
        else:
            elipse = self._elipse_do_papel(imagem)

        if elipse is None:
            return imagem, circulo, None

        convertido = self._homografia_elipse_para_quadro(elipse, lado)
        if convertido is None:
            return imagem, circulo, None
        homografia, circulo_novo = convertido

        borda: int | tuple[int, ...] = 255 if imagem.ndim == 2 else (255, 255, 255)
        corrigida = cv2.warpPerspective(
            imagem,
            homografia,
            (int(lado), int(lado)),
            flags=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=borda,
        )
        return corrigida, circulo_novo, homografia

    def encontrar_furo_central(
        self,
        imagem_cinza: NDArray[np.uint8],
    ) -> CirculoDetectado:
        if imagem_cinza is None or imagem_cinza.ndim != 2:
            raise ImagemInvalidaError("A imagem deve estar em escala de cinza.")

        altura, largura = imagem_cinza.shape
        menor_lado = min(altura, largura)
        suavizada = cv2.GaussianBlur(imagem_cinza, (9, 9), 2)

        raio_minimo = max(10, menor_lado // 40)
        raio_maximo = max(raio_minimo + 1, menor_lado // 8)

        candidatos: NDArray[np.int_] | None = None
        for param2 in (30, 22, 16):
            circulos = cv2.HoughCircles(
                image=suavizada,
                method=cv2.HOUGH_GRADIENT,
                dp=1.2,
                minDist=max(1, menor_lado // 4),
                param1=100,
                param2=param2,
                minRadius=raio_minimo,
                maxRadius=raio_maximo,
            )
            if circulos is not None:
                candidatos = np.round(circulos[0]).astype(int)
                break

        if candidatos is None or len(candidatos) == 0:
            raise FuroNaoEncontradoError("Não foi possível localizar o centro do disco.")

        centro_imagem_x = largura / 2.0
        centro_imagem_y = altura / 2.0
        melhor = min(
            candidatos,
            key=lambda c: (float(c[0]) - centro_imagem_x) ** 2
            + (float(c[1]) - centro_imagem_y) ** 2,
        )

        centro_hough_x = int(melhor[0])
        centro_hough_y = int(melhor[1])
        raio_hough = int(melhor[2])

        # Refina o centro para furo em formato de pera
        refinado = self._refinar_centro_por_contornos(
            imagem_cinza,
            centro_hough_x,
            centro_hough_y,
            raio_hough,
        )
        if refinado is not None:
            centro_x, centro_y, raio = refinado
        else:
            centro_x, centro_y, raio = centro_hough_x, centro_hough_y, raio_hough

        return CirculoDetectado(centro_x=centro_x, centro_y=centro_y, raio=raio)

    def _refinar_centro_por_contornos(
        self,
        imagem_cinza: NDArray[np.uint8],
        centro_x: int,
        centro_y: int,
        raio: int,
    ) -> tuple[int, int, int] | None:
        altura, largura = imagem_cinza.shape
        margem = max(int(raio * 2.8), 24)
        x0 = max(0, centro_x - margem)
        y0 = max(0, centro_y - margem)
        x1 = min(largura, centro_x + margem)
        y1 = min(altura, centro_y + margem)

        roi = imagem_cinza[y0:y1, x0:x1]
        if roi.size == 0 or min(roi.shape) < 10:
            return None

        suavizada = cv2.GaussianBlur(roi, (5, 5), 0)
        _, binaria = cv2.threshold(
            suavizada,
            0,
            255,
            cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU,
        )

        nucleo = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        binaria = cv2.morphologyEx(binaria, cv2.MORPH_OPEN, nucleo, iterations=1)
        binaria = cv2.morphologyEx(binaria, cv2.MORPH_CLOSE, nucleo, iterations=2)

        contornos, _ = cv2.findContours(
            binaria,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE,
        )
        if not contornos:
            return None

        area_min = max(40.0, float(np.pi * (raio * 0.35) ** 2))
        area_max = float(np.pi * (raio * 2.8) ** 2)
        cx_local = float(centro_x - x0)
        cy_local = float(centro_y - y0)

        melhor_contorno = None
        melhor_score = float("inf")

        for contorno in contornos:
            area = float(cv2.contourArea(contorno))
            if area < area_min or area > area_max:
                continue

            momentos = cv2.moments(contorno)
            if momentos["m00"] == 0:
                continue

            mx = float(momentos["m10"] / momentos["m00"])
            my = float(momentos["m01"] / momentos["m00"])
            dist2 = (mx - cx_local) ** 2 + (my - cy_local) ** 2

            score = dist2 / max(area, 1.0)
            if score < melhor_score:
                melhor_score = score
                melhor_contorno = contorno

        if melhor_contorno is None:
            return None

        momentos = cv2.moments(melhor_contorno)
        if momentos["m00"] == 0:
            return None

        centro_ref_x = int(round(momentos["m10"] / momentos["m00"] + x0))
        centro_ref_y = int(round(momentos["m01"] / momentos["m00"] + y0))

        area = float(cv2.contourArea(melhor_contorno))
        raio_equiv = int(max(1, round(np.sqrt(area / np.pi))))

        if not (0 <= centro_ref_x < largura and 0 <= centro_ref_y < altura):
            return None

        return centro_ref_x, centro_ref_y, raio_equiv

    def _raio_disco_util(
        self,
        imagem: NDArray[np.uint8],
        circulo: CirculoDetectado,
    ) -> float:
        """Raio máximo que cabe na imagem a partir do centro detectado."""
        altura, largura = imagem.shape[:2]
        distancias_borda = (
            circulo.centro_x,
            circulo.centro_y,
            largura - circulo.centro_x - 1,
            altura - circulo.centro_y - 1,
        )
        raio_borda = float(max(1, min(distancias_borda)))
        raio_disco = float(circulo.raio) if circulo.raio > 0 else raio_borda
        return min(raio_disco, raio_borda)

    def _raio_papel(
        self,
        imagem_cinza: NDArray[np.uint8],
        circulo: CirculoDetectado,
    ) -> float:
        """
        Raio da circunferência do papel (antes do fundo da mesa).

        Percorre o perfil radial de brilho: o disco é claro; a mesa/recorte é
        escuro. O último anel ainda claro é a borda do papel.
        """
        altura, largura = imagem_cinza.shape[:2]
        cx = float(circulo.centro_x)
        cy = float(circulo.centro_y)
        r_img = self._raio_disco_util(imagem_cinza, circulo)
        r_lim = float(max(r_img, float(circulo.raio)))
        r_lim = min(
            r_lim * 1.20,
            float(min(cx, cy, largura - cx - 1.0, altura - cy - 1.0)),
        )
        r_lim = max(r_lim, 8.0)

        n_bins = 80
        ys, xs = np.ogrid[0:altura, 0:largura]
        dist = np.sqrt((xs.astype(np.float64) - cx) ** 2 + (ys.astype(np.float64) - cy) ** 2)
        hist = np.zeros(n_bins, dtype=np.float64)
        for i in range(n_bins):
            r0 = (i / n_bins) * r_lim
            r1 = ((i + 1) / n_bins) * r_lim
            faixa = (dist >= r0) & (dist < r1)
            if not np.any(faixa):
                hist[i] = 0.0
            else:
                hist[i] = float(imagem_cinza[faixa].mean())

        i_miolo = max(2, int(n_bins * 0.18))
        i_meio = max(i_miolo + 1, int(n_bins * 0.55))
        papel = float(np.median(hist[i_miolo:i_meio]))
        if papel < 40.0:
            return r_img

        limiar = max(papel * 0.58, 70.0)
        i_borda = i_meio
        for i in range(n_bins - 2, i_meio, -1):
            if hist[i] >= limiar:
                i_borda = i
                break

        raio = ((i_borda + 1) / n_bins) * r_lim
        return float(np.clip(raio, max(8.0, float(circulo.raio) * 0.80), r_lim))

    def _mascarar_fundo_fora_do_papel(
        self,
        imagem: NDArray[np.uint8],
        circulo: CirculoDetectado,
        raio_papel: float,
        preenchimento: int = 255,
    ) -> NDArray[np.uint8]:
        """
        Zera (na prática: pinta de papel claro) tudo fora do disco.

        Importante: o fundo da foto é PRETO. Se entrar no warpPolar, o
        rastreamento trata a borda como agulha em 125 km/h. Por isso o
        preenchimento é branco/papel, nunca zero.
        """
        mascara = np.zeros(imagem.shape[:2], dtype=np.uint8)
        raio = max(1, int(round(raio_papel * FRACAO_MASCARA_PAPEL)))
        cv2.circle(
            mascara,
            (int(circulo.centro_x), int(circulo.centro_y)),
            raio,
            255,
            thickness=-1,
        )
        saida = imagem.copy()
        saida[mascara == 0] = preenchimento
        return saida

    def _calcular_raios_anel_velocidade(
        self,
        imagem_cinza: NDArray[np.uint8],
        circulo: CirculoDetectado,
        mascara_verde: NDArray[np.uint8] | None = None,
        raio_papel: float | None = None,
    ) -> tuple[float, float]:
        """
        r_min / r_max da pista EXTERNA de velocidade.

        Isola só a coroa 0–125 km/h. r_max fica estritamente dentro do papel
        para a borda preta da mesa não entrar na amostragem.
        """
        raio_disco = self._raio_disco_util(imagem_cinza, circulo)
        if raio_papel is not None and raio_papel > 8.0:
            raio_ref = min(raio_disco, float(raio_papel))
        else:
            raio_ref = raio_disco
        teto = raio_ref * FRACAO_RMAX_VS_PAPEL

        min_radius = raio_ref * self.fracao_raio_min
        max_radius = min(raio_ref * self.fracao_raio_max, teto)
        # Coroa fixa 0.70–0.92 R: a máscara verde do mousepad deslocava o anel.

        min_radius = max(1.0, min_radius)
        max_radius = max(min_radius + 1.0, max_radius)
        return float(min_radius), float(max_radius)

    def _raios_pista_externa_por_verde(
        self,
        mascara_verde: NDArray[np.uint8],
        circulo: CirculoDetectado,
        raio_disco: float,
    ) -> tuple[float, float] | None:
        """Localiza a coroa verde mais externa (escala de velocidade)."""
        ys, xs = np.nonzero(mascara_verde)
        if xs.size < 80:
            return None

        dist = np.sqrt(
            (xs.astype(np.float64) - float(circulo.centro_x)) ** 2
            + (ys.astype(np.float64) - float(circulo.centro_y)) ** 2
        )
        n_bins = 64
        hist, bordas = np.histogram(dist, bins=n_bins, range=(0.0, max(raio_disco, 1.0)))
        if hist.size < 8:
            return None

        kernel = np.ones(5, dtype=np.float64) / 5.0
        suave = np.convolve(hist.astype(np.float64), kernel, mode="same")
        i0 = int(n_bins * 0.58)
        trecho = suave[i0:]
        if trecho.size == 0:
            return None
        limiar = max(float(trecho.max()) * 0.22, 1.0)
        ativos = np.flatnonzero(trecho >= limiar)
        if ativos.size == 0:
            return None

        i_min = int(i0 + ativos[0])
        i_max = int(i0 + ativos[-1])
        r_min = float(bordas[i_min])
        r_max = float(bordas[min(i_max + 1, len(bordas) - 1)])

        r_min = max(r_min, raio_disco * self.fracao_raio_min * 0.92)
        r_max = min(max(r_max, r_min + 8.0), raio_disco * FRACAO_RMAX_VS_PAPEL)
        if r_max - r_min < 8.0:
            return None
        return r_min, r_max

    def _desdobrar_anel(
        self,
        imagem: NDArray[np.uint8],
        circulo: CirculoDetectado,
        min_radius: float,
        max_radius: float,
        largura_px: int | None = None,
        altura_px: int | None = None,
    ) -> NDArray[np.uint8]:
        """warpPolar de um anel [min_radius, max_radius] → retângulo tempo × raio."""
        largura = int(largura_px or self.largura_desdobramento)
        altura = int(altura_px or self.altura_desdobramento)
        centro = (float(circulo.centro_x), float(circulo.centro_y))
        max_radius = max(float(max_radius), float(min_radius) + 1.0)

        polar = cv2.warpPolar(
            src=imagem,
            dsize=(altura, largura),
            center=centro,
            maxRadius=max_radius,
            flags=cv2.WARP_POLAR_LINEAR + cv2.INTER_LINEAR,
        )

        colunas = polar.shape[1]
        col_inicio = int(round((min_radius / max_radius) * (colunas - 1)))
        col_inicio = max(0, min(col_inicio, colunas - 2))
        polar_anel = polar[:, col_inicio:]

        polar_anel = cv2.resize(
            polar_anel,
            (altura, largura),
            interpolation=cv2.INTER_AREA,
        )

        retangular = cv2.rotate(polar_anel, cv2.ROTATE_90_COUNTERCLOCKWISE)
        retangular = cv2.flip(retangular, 0)
        return retangular

    def _score_ondulacao_grade(self, mascara_desdobrada: NDArray[np.uint8]) -> float:
        """Desvio do centróide da grade no tempo: 0 = linhas 100% horizontais."""
        img = mascara_desdobrada.astype(np.float64)
        if img.ndim == 3:
            img = img.mean(axis=2)
        if img.size == 0:
            return 1e9
        altura, largura = img.shape[:2]
        col_sum = img.sum(axis=0)
        if float(col_sum.max()) < 1.0:
            return 1e9
        ys = np.arange(altura, dtype=np.float64)[:, None]
        centroides = (img * ys).sum(axis=0) / np.maximum(col_sum, 1.0)
        validos = col_sum > (0.015 * float(altura) * 255.0)
        if int(np.count_nonzero(validos)) < max(12, largura // 10):
            return 1e9
        return float(np.std(centroides[validos]))

    def _endireitar_grade_no_linear(
        self,
        imagem_desdobrada: NDArray[np.uint8],
        mascara_grade: NDArray[np.uint8] | None,
    ) -> tuple[NDArray[np.uint8], NDArray[np.uint8] | None]:
        """
        Corrige inclinação residual por correlação cruzada iterativa.

        O centróide único é instável com várias linhas (20/40/60/...). Aqui cada
        coluna é alinhada ao perfil médio iterativamente — converge para linhas
        horizontais, alinhando a máscara da grade à grade real e permitindo
        que a remoção da grade (no rastreamento da agulha) funcione.
        """
        if mascara_grade is None or mascara_grade.ndim != 2:
            return imagem_desdobrada, mascara_grade
        if imagem_desdobrada.shape[:2] != mascara_grade.shape[:2]:
            return imagem_desdobrada, mascara_grade
        if self._score_ondulacao_grade(mascara_grade) < 1e9:
            return imagem_desdobrada, mascara_grade

        img = mascara_grade.astype(np.float64)
        altura, largura = img.shape[:2]
        col_sum = img.sum(axis=0)
        if float(col_sum.max()) < 1.0:
            return imagem_desdobrada, mascara_grade
        validas = col_sum > (0.012 * float(altura) * 255.0)
        if int(np.count_nonzero(validas)) < max(24, largura // 8):
            return imagem_desdobrada, mascara_grade

        max_shift = int(min(altura // 3, 80))
        acumulado = np.zeros(largura, dtype=np.float64)

        def perfil_deslocada(arr: NDArray[np.float64], shifts: NDArray[np.float64]) -> NDArray[np.float64]:
            out = np.zeros_like(arr)
            for x in range(largura):
                out[:, x] = np.roll(arr[:, x], int(round(shifts[x])))
            return out

        for _ in range(4):
            deslocada = perfil_deslocada(img, acumulado)
            ref = deslocada[:, validas].mean(axis=1)
            ref = ref - float(ref.mean())
            ref_norm = float(np.sqrt((ref * ref).sum())) + 1e-9
            novo_shift = np.zeros(largura, dtype=np.float64)
            for x in range(largura):
                if not validas[x]:
                    novo_shift[x] = novo_shift[max(0, x - 1)]
                    continue
                col = deslocada[:, x] - float(deslocada[:, x].mean())
                col_norm = float(np.sqrt((col * col).sum())) + 1e-9
                melhor_shift, melhor_corr = 0, -1e9
                for dy in range(-max_shift, max_shift + 1):
                    rolada = np.roll(col, dy)
                    corr = float((rolada * ref).sum()) / (col_norm * ref_norm)
                    if corr > melhor_corr:
                        melhor_corr = corr
                        melhor_shift = dy
                novo_shift[x] = float(melhor_shift)
            acumulado = acumulado + novo_shift

        kernel = np.ones(11, dtype=np.float64) / 11.0
        desloc_suave = np.convolve(acumulado, kernel, mode="same")
        limite = max(4.0, float(altura) * 0.12)
        desloc_suave = np.clip(desloc_suave, -limite, limite)
        desloc_i = np.round(desloc_suave).astype(np.int32)

        saida_img = imagem_desdobrada.copy()
        saida_mask = mascara_grade.copy()
        for x in range(largura):
            dy = int(desloc_i[x])
            if dy == 0:
                continue
            saida_img[:, x] = np.roll(saida_img[:, x], dy, axis=0)
            saida_mask[:, x] = np.roll(saida_mask[:, x], dy, axis=0)
        return saida_img, saida_mask

    def _centro_hough_circunferencias_verdes(
        self,
        imagem_bgr: NDArray[np.uint8],
        circulo: CirculoDetectado,
    ) -> CirculoDetectado | None:
        """
        Centro das circunferências verdes impressas (não o bounding box do papel).

        Várias coroas 0.70–0.98 R devem compartilhar o mesmo (x0, y0); a mediana
        desses centros é a âncora do warpPolar.
        """
        mascara = self._mascara_somente_verde(imagem_bgr)
        if mascara is None:
            return None
        raio = max(int(circulo.raio), 24)
        suavizada = cv2.GaussianBlur(mascara, (5, 5), 0)
        achados: NDArray[np.float64] | None = None
        metodos: list[int] = [cv2.HOUGH_GRADIENT]
        if hasattr(cv2, "HOUGH_GRADIENT_ALT"):
            metodos.insert(0, int(cv2.HOUGH_GRADIENT_ALT))
        for metodo in metodos:
            if metodo == cv2.HOUGH_GRADIENT:
                lista_param2: tuple[float, ...] = (28.0, 20.0, 14.0, 10.0)
            else:
                lista_param2 = (0.85, 0.7, 0.55)
            for param2 in lista_param2:
                kwargs = dict(
                    image=suavizada,
                    method=metodo,
                    dp=1.2,
                    minDist=max(6, raio // 24),
                    param1=80,
                    param2=param2,
                    minRadius=max(8, int(raio * 0.68)),
                    maxRadius=max(10, int(raio * 0.98)),
                )
                try:
                    circulos = cv2.HoughCircles(**kwargs)
                except cv2.error:
                    continue
                if circulos is not None and len(circulos[0]) >= 2:
                    achados = circulos[0].astype(np.float64)
                    break
            if achados is not None:
                break
        if achados is None:
            return None
        dist = np.sqrt(
            (achados[:, 0] - float(circulo.centro_x)) ** 2
            + (achados[:, 1] - float(circulo.centro_y)) ** 2
        )
        ok = dist <= float(raio) * 0.08
        if int(np.count_nonzero(ok)) < 2:
            return None
        sel = achados[ok]
        return CirculoDetectado(
            centro_x=int(round(float(np.median(sel[:, 0])))),
            centro_y=int(round(float(np.median(sel[:, 1])))),
            raio=circulo.raio,
        )

    def _refinar_centro_por_grade_verde(
        self,
        imagem_bgr: NDArray[np.uint8],
        circulo: CirculoDetectado,
    ) -> CirculoDetectado:
        """Busca (x0,y0) que deixa 20/40/60/80 km/h horizontais no unwrap."""
        mascara = self._mascara_somente_verde(imagem_bgr)
        if mascara is None or float((mascara > 0).mean()) < 0.002:
            return circulo
        base = self._centro_hough_circunferencias_verdes(imagem_bgr, circulo) or circulo
        r_min = float(circulo.raio) * FRACAO_RAIO_MIN_VELOCIDADE
        r_max = float(circulo.raio) * FRACAO_RAIO_MAX_VELOCIDADE

        def avaliar(cx: int, cy: int) -> float:
            cand = CirculoDetectado(centro_x=cx, centro_y=cy, raio=circulo.raio)
            desdobrada = self._desdobrar_anel(
                mascara, cand, r_min, r_max, largura_px=720, altura_px=240,
            )
            return self._score_ondulacao_grade(desdobrada)

        melhor_x, melhor_y = base.centro_x, base.centro_y
        melhor_s = avaliar(melhor_x, melhor_y)
        for passo, raio_busca in ((8, 48), (4, 20), (2, 8), (1, 3)):
            origem_x, origem_y = melhor_x, melhor_y
            for dy in range(-raio_busca, raio_busca + 1, passo):
                for dx in range(-raio_busca, raio_busca + 1, passo):
                    if dx == 0 and dy == 0:
                        continue
                    score = avaliar(origem_x + dx, origem_y + dy)
                    if score < melhor_s:
                        melhor_s = score
                        melhor_x = origem_x + dx
                        melhor_y = origem_y + dy
        return CirculoDetectado(centro_x=melhor_x, centro_y=melhor_y, raio=circulo.raio)

    def _separar_grade_hsv_linear(
        self,
        imagem_bgr_linear: NDArray[np.uint8],
    ) -> tuple[NDArray[np.uint8], NDArray[np.uint8]]:
        """Figura 2 em cinza (grade visível) + máscara HSV da tinta verde."""
        hsv = cv2.cvtColor(imagem_bgr_linear, cv2.COLOR_BGR2HSV)
        mascara = cv2.inRange(
            hsv,
            np.array(GRADE_VERDE_HSV_BAIXO, dtype=np.uint8),
            np.array(GRADE_VERDE_HSV_ALTO, dtype=np.uint8),
        )
        cinza = cv2.cvtColor(imagem_bgr_linear, cv2.COLOR_BGR2GRAY)
        return cinza, mascara

    def desdobrar_disco(
        self,
        imagem_cinza: NDArray[np.uint8],
        circulo: CirculoDetectado,
        mascara_verde: NDArray[np.uint8] | None = None,
    ) -> NDArray[np.uint8]:
        min_radius, max_radius = self._calcular_raios_anel_velocidade(
            imagem_cinza,
            circulo,
            mascara_verde,
        )
        return self._desdobrar_anel(imagem_cinza, circulo, min_radius, max_radius)

    def _rotacionar_em_torno(
        self,
        imagem: NDArray[np.uint8],
        circulo: CirculoDetectado,
        angulo_graus: float,
        borda: int | tuple[int, ...] = 255,
    ) -> NDArray[np.uint8]:
        """Rotaciona em torno do centro do disco (ângulo OpenCV: anti-horário +)."""
        centro = (float(circulo.centro_x), float(circulo.centro_y))
        altura, largura = imagem.shape[:2]
        matriz = cv2.getRotationMatrix2D(centro, float(angulo_graus), 1.0)
        if imagem.ndim == 3:
            valor: int | tuple[int, ...] = (255, 255, 255) if isinstance(borda, int) else borda
        else:
            valor = int(borda) if isinstance(borda, (int, float)) else 255
        return cv2.warpAffine(
            imagem,
            matriz,
            (largura, altura),
            flags=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=valor,
        )

    def _angulo_ponta_gota(
        self,
        imagem_cinza: NDArray[np.uint8],
        circulo: CirculoDetectado,
    ) -> float | None:
        """
        Ângulo (graus) da ponta do furo em gota, no sistema do warpPolar.

        warpPolar usa θ = atan2(y - cy, x - cx): 0° = eixo +X (direita).
        O eixo maior do furo em gota coincide com o eixo 12h–24h do disco
        (Antonacopoulos, 2002). A ponta mais afastada do centroide aponta
        para um dos polos; alinhamos com +X e refinamos pelas marcas da borda.
        """
        altura, largura = imagem_cinza.shape[:2]
        raio_busca = max(18, int(circulo.raio * 0.22))
        x0 = max(0, circulo.centro_x - raio_busca)
        y0 = max(0, circulo.centro_y - raio_busca)
        x1 = min(largura, circulo.centro_x + raio_busca)
        y1 = min(altura, circulo.centro_y + raio_busca)
        roi = imagem_cinza[y0:y1, x0:x1]
        if roi.size == 0 or min(roi.shape) < 12:
            return None

        suavizada = cv2.GaussianBlur(roi, (5, 5), 0)
        _, binaria = cv2.threshold(
            suavizada, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU,
        )
        nucleo = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        binaria = cv2.morphologyEx(binaria, cv2.MORPH_OPEN, nucleo, iterations=1)
        binaria = cv2.morphologyEx(binaria, cv2.MORPH_CLOSE, nucleo, iterations=2)

        contornos, _ = cv2.findContours(binaria, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contornos:
            return None

        cx_local = float(circulo.centro_x - x0)
        cy_local = float(circulo.centro_y - y0)
        area_min = 40.0
        area_max = float(np.pi * (raio_busca * 0.95) ** 2)

        melhor = None
        melhor_score = float("inf")
        for contorno in contornos:
            area = float(cv2.contourArea(contorno))
            if area < area_min or area > area_max:
                continue
            momentos = cv2.moments(contorno)
            if momentos["m00"] == 0:
                continue
            mx = float(momentos["m10"] / momentos["m00"])
            my = float(momentos["m01"] / momentos["m00"])
            dist2 = (mx - cx_local) ** 2 + (my - cy_local) ** 2
            score = dist2 / max(area, 1.0)
            if score < melhor_score:
                melhor_score = score
                melhor = contorno

        if melhor is None:
            return None

        momentos = cv2.moments(melhor)
        if momentos["m00"] == 0:
            return None
        mx = float(momentos["m10"] / momentos["m00"])
        my = float(momentos["m01"] / momentos["m00"])

        pts = melhor.reshape(-1, 2).astype(np.float64)
        d2 = (pts[:, 0] - mx) ** 2 + (pts[:, 1] - my) ** 2
        ponta = pts[int(np.argmax(d2))]
        raio_eq = float(np.sqrt(max(float(cv2.contourArea(melhor)), 1.0) / np.pi))
        alongamento = float(np.sqrt(d2.max()) / max(raio_eq, 1.0))
        if alongamento < 1.12:
            return None

        dx = float(ponta[0] - mx)
        dy = float(ponta[1] - my)
        return float(np.degrees(np.arctan2(dy, dx)))

    def _angulos_eixo_entalhe(
        self,
        imagem_cinza: NDArray[np.uint8],
        circulo: CirculoDetectado,
    ) -> list[float]:
        """
        Eixo maior do furo-guia (gota/trapézio): 12h–24h.

        minAreaRect é mais estável que o pixel mais afastado (canto a 45°).
        Devolve os dois polos (ponta e cauda), ponta primeiro se houver.
        """
        ponta = self._angulo_ponta_gota(imagem_cinza, circulo)
        altura, largura = imagem_cinza.shape[:2]
        raio_busca = max(18, int(circulo.raio * 0.22))
        x0 = max(0, circulo.centro_x - raio_busca)
        y0 = max(0, circulo.centro_y - raio_busca)
        x1 = min(largura, circulo.centro_x + raio_busca)
        y1 = min(altura, circulo.centro_y + raio_busca)
        roi = imagem_cinza[y0:y1, x0:x1]
        if roi.size == 0 or min(roi.shape) < 12:
            return [ponta] if ponta is not None else []

        suavizada = cv2.GaussianBlur(roi, (5, 5), 0)
        _, binaria = cv2.threshold(
            suavizada, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU,
        )
        nucleo = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        binaria = cv2.morphologyEx(binaria, cv2.MORPH_CLOSE, nucleo, iterations=2)
        contornos, _ = cv2.findContours(binaria, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contornos:
            return [ponta] if ponta is not None else []

        melhor = max(contornos, key=cv2.contourArea)
        if len(melhor) < 5:
            return [ponta] if ponta is not None else []

        (_cx, _cy), (eixo_w, eixo_h), angulo_rect = cv2.minAreaRect(melhor)
        if eixo_w < eixo_h:
            eixo = float(angulo_rect) + 90.0
        else:
            eixo = float(angulo_rect)
        polo_a = eixo % 360.0
        polo_b = (eixo + 180.0) % 360.0

        def dist_circ(a: float, b: float) -> float:
            return abs((a - b + 180.0) % 360.0 - 180.0)

        if ponta is not None:
            if dist_circ(ponta, polo_a) <= dist_circ(ponta, polo_b):
                return [polo_a, polo_b]
            return [polo_b, polo_a]
        return [polo_a, polo_b]

    def _angulo_marca_24h(
        self,
        imagem_cinza: NDArray[np.uint8],
        circulo: CirculoDetectado,
        raio_papel: float,
    ) -> float | None:
        """
        Âncora 00:00/24h: linha radial impressa (mais longa/escura que os ticks).

        Amostra 720 raios. Tick de hora vive só na borda; a marca das 24h
        atravessa o anel externo. score = energia_borda × energia_raio.
        """
        if raio_papel < 16.0:
            return None
        altura, largura = imagem_cinza.shape[:2]
        cx = float(circulo.centro_x)
        cy = float(circulo.centro_y)
        n_ang = 720
        imgf = imagem_cinza.astype(np.float64)

        def energia_faixa(r0: float, r1: float, n_r: int) -> NDArray[np.float64]:
            rs = np.linspace(r0, r1, n_r)
            out = np.zeros(n_ang, dtype=np.float64)
            for i in range(n_ang):
                theta = (i / n_ang) * 2.0 * np.pi
                cth, sth = np.cos(theta), np.sin(theta)
                xs = np.clip((cx + rs * cth).round().astype(np.int32), 0, largura - 1)
                ys = np.clip((cy + rs * sth).round().astype(np.int32), 0, altura - 1)
                out[i] = 255.0 - float(imgf[ys, xs].mean())
            return out

        borda = energia_faixa(raio_papel * 0.86, raio_papel * 0.96, 28)
        raio = energia_faixa(raio_papel * 0.52, raio_papel * 0.84, 36)
        kernel = np.ones(9, dtype=np.float64) / 9.0

        def suave(sinal: NDArray[np.float64]) -> NDArray[np.float64]:
            pad = np.concatenate([sinal[-12:], sinal, sinal[:12]])
            return np.convolve(pad, kernel, mode="same")[12:12 + n_ang]

        borda_s = suave(borda)
        raio_s = suave(raio)
        b_max = float(borda_s.max())
        r_max = float(raio_s.max())
        if b_max < 4.0 and r_max < 4.0:
            return None

        b_n = borda_s / max(b_max, 1e-6)
        r_n = raio_s / max(r_max, 1e-6)
        score = b_n * (0.35 + 0.65 * r_n)
        pico = int(np.argmax(score))
        if float(score[pico]) < 0.18:
            return None
        return float((pico / n_ang) * 360.0)

    def _score_fase_madrugada(
        self,
        imagem_bgr: NDArray[np.uint8],
        circulo: CirculoDetectado,
        raio_papel: float,
        angulo_graus: float,
    ) -> float:
        """
        Quanto a fase deixa a madrugada (16h–05h) parada e o dia (08h–16h) em movimento.

        A grade verde é apagada no linear para não contar como jornada.
        """
        r_min = raio_papel * FRACAO_RAIO_MIN_VELOCIDADE
        r_max = raio_papel * FRACAO_RAIO_MAX_VELOCIDADE
        rot = self._rotacionar_em_torno(
            imagem_bgr, circulo, angulo_graus, borda=(255, 255, 255),
        )
        unwrap_bgr = self._desdobrar_anel(
            rot, circulo, r_min, r_max, largura_px=360, altura_px=120,
        )
        cinza, mascara = self._separar_grade_hsv_linear(unwrap_bgr)
        cinza = cinza.copy()
        cinza[mascara > 0] = 255
        mediana = float(np.median(cinza))
        atividade = (cinza.astype(np.float64) < (mediana - 22.0)).mean(axis=0)
        n = int(atividade.size)
        if n < 24:
            return -1e9
        i8 = int(round(8.0 / 24.0 * n))
        i16 = int(round(16.0 / 24.0 * n))
        i5 = int(round(5.0 / 24.0 * n))
        noite = np.concatenate([atividade[i16:], atividade[:i5]])
        dia = atividade[i8:i16]
        if noite.size == 0 or dia.size == 0:
            return -1e9
        return float(dia.mean() - noite.mean())

    def _score_fase_por_velocidade(
        self,
        imagem_bgr: NDArray[np.uint8],
        circulo: CirculoDetectado,
        raio_papel: float,
        angulo_graus: float,
    ) -> float:
        """
        Score de fase pela curva de velocidade extraída (não por atividade crua).

        No ângulo certo: madrugada (00–05 e 18–24) parada (v≈0) e dia (08–16)
        em movimento. O score de atividade era enganado pelo resíduo da grade
        ondulada; este usa a agulha rastreada como o laudo final.
        """
        r_min = raio_papel * FRACAO_RAIO_MIN_VELOCIDADE
        r_max = raio_papel * FRACAO_RAIO_MAX_VELOCIDADE
        rot = self._rotacionar_em_torno(
            imagem_bgr, circulo, angulo_graus, borda=(255, 255, 255),
        )
        unwrap_bgr = self._desdobrar_anel(
            rot, circulo, r_min, r_max, largura_px=720, altura_px=240,
        )
        cinza, mascara = self._separar_grade_hsv_linear(unwrap_bgr)
        preparada = self._preparar_imagem_para_traco(cinza, mascara_grade=mascara)
        altura, largura = preparada.shape[:2]
        if altura < 4 or largura < 24:
            return -1e9
        y_corte = max(1, int(round(altura * MARGEM_Y_BORDA_EXTERNA)))
        denom_y = max(altura - 1, 1)
        velocidades: list[float] = []
        for x in range(largura):
            coluna = preparada[:, x]
            trecho = coluna[y_corte:]
            if trecho.size == 0:
                velocidades.append(0.0)
                continue
            y = int(np.argmin(trecho)) + y_corte
            if not self._coluna_tem_traco_valido(coluna, y):
                velocidades.append(0.0)
                continue
            fracao = 1.0 - (float(y) / denom_y)
            velocidades.append(max(0.0, min(fracao, 1.0)) * float(self.velocidade_maxima_kmh))
        arr = np.asarray(velocidades, dtype=np.float64)
        n = int(arr.size)
        if n < 24:
            return -1e9
        i5 = int(round(5.0 / 24.0 * n))
        i8 = int(round(8.0 / 24.0 * n))
        i16 = int(round(16.0 / 24.0 * n))
        i18 = int(round(18.0 / 24.0 * n))
        noite = np.concatenate([arr[:i5], arr[i18:]])
        dia = arr[i8:i16]
        if noite.size == 0 or dia.size == 0:
            return -1e9
        # Penaliza movimento noturno forte (fase errada deixa madrugada a 60 km/h).
        pena_noite = float(np.maximum(noite - 12.0, 0.0).mean())
        return float(dia.mean()) - 3.0 * pena_noite

    def _angulos_unicos(self, angulos: list[float], tol: float = 10.0) -> list[float]:
        unicos: list[float] = []
        for angulo in angulos:
            a = float(angulo) % 360.0
            if any(abs((a - u + 180.0) % 360.0 - 180.0) <= tol for u in unicos):
                continue
            unicos.append(a)
        return unicos

    def _angulo_zero_temporal(
        self,
        imagem_cinza: NDArray[np.uint8],
        circulo: CirculoDetectado,
        raio_papel: float,
        imagem_bgr: NDArray[np.uint8] | None = None,
    ) -> tuple[float | None, bool]:
        """
        X=0 = marco 00:00. Desambigua 12h vs 24h pela madrugada parada (16h–05h).
        """
        eixos = self._angulos_eixo_entalhe(imagem_cinza, circulo)
        marca = self._angulo_marca_24h(imagem_cinza, circulo, raio_papel)
        candidatos: list[float] = []
        if marca is not None:
            candidatos.append(float(marca))
            candidatos.append((float(marca) + 180.0) % 360.0)
        candidatos.extend(float(e) for e in eixos)
        candidatos.extend((0.0, 90.0, 180.0, 270.0))
        # Grade fina a cada 15° — em fotos baixa-resolução a marca/entalhe falha,
        # e a fase correta pode estar num ângulo não cardinal (ex.: 105°).
        candidatos.extend(float(a) for a in range(0, 360, 15))
        candidatos = self._angulos_unicos(candidatos)
        if not candidatos:
            return None, False

        base_fase = imagem_bgr if imagem_bgr is not None and imagem_bgr.ndim == 3 else None
        if base_fase is None:
            base_fase = cv2.cvtColor(imagem_cinza, cv2.COLOR_GRAY2BGR)

        # Score primário pela curva de velocidade (robusto ao resíduo da grade).
        melhor_angulo = candidatos[0]
        melhor_score = -1e9
        for angulo in candidatos:
            score = self._score_fase_por_velocidade(
                base_fase, circulo, raio_papel, angulo,
            )
            if score > melhor_score:
                melhor_score = score
                melhor_angulo = angulo
        return float(melhor_angulo), True

    def _estimar_distancia_odometro(
        self,
        imagem_cinza: NDArray[np.uint8],
        circulo: CirculoDetectado,
        raio_disco: float,
        r_min_vel: float,
        imagem_bgr: NDArray[np.uint8] | None = None,
    ) -> tuple[float | None, int]:
        """
        Conta o zigue-zague da pista de distância (anel interno).

        Literatura Kienzle/Fleetco: cada curso (deflexão) = 5 km; um “V”
        completo (ida+volta) = 10 km. Testa dois anéis e fica com o de
        maior amplitude (layout varia um pouco entre fabricantes).
        """
        candidatos = (
            (raio_disco * self.fracao_odometro_min, raio_disco * self.fracao_odometro_max),
            (
                raio_disco * FRACAO_RAIO_MIN_ODOMETRO_ALT,
                min(raio_disco * FRACAO_RAIO_MAX_ODOMETRO_ALT, r_min_vel * 0.98),
            ),
        )

        melhor: tuple[float, int, float] | None = None  # dist, ciclos, amplitude
        for r_min_odo, r_max_odo in candidatos:
            if r_max_odo - r_min_odo < 6.0:
                continue
            medido = self._contar_ziguezague(
                imagem_cinza, circulo, r_min_odo, r_max_odo, imagem_bgr=imagem_bgr,
            )
            if medido is None:
                continue
            dist, ciclos, amplitude = medido
            if melhor is None or amplitude > melhor[2]:
                melhor = (dist, ciclos, amplitude)

        if melhor is None:
            return None, 0
        return melhor[0], melhor[1]

    def _contar_ziguezague(
        self,
        imagem_cinza: NDArray[np.uint8],
        circulo: CirculoDetectado,
        r_min: float,
        r_max: float,
        imagem_bgr: NDArray[np.uint8] | None = None,
    ) -> tuple[float, int, float] | None:
        if imagem_bgr is not None and imagem_bgr.ndim == 3:
            anel_bgr = self._desdobrar_anel(imagem_bgr, circulo, r_min, r_max)
            anel, mascara_grade = self._separar_grade_hsv_linear(anel_bgr)
            anel = anel.copy()
            anel[mascara_grade > 0] = 255
        else:
            anel = self._desdobrar_anel(imagem_cinza, circulo, r_min, r_max)
        if anel.ndim != 2 or anel.shape[1] < 32:
            return None
        # Mesa/mousepad é escuro; o odômetro gráfico vive no papel claro
        if float(anel.mean()) < 100.0:
            return None

        suavizada = cv2.GaussianBlur(anel, (5, 5), 0)
        ys = np.argmin(suavizada, axis=0).astype(np.float64)
        if ys.size < 16:
            return None

        janela = 7
        kernel = np.ones(janela, dtype=np.float64) / float(janela)
        ys = np.convolve(ys, kernel, mode="same")
        ys = ys - float(np.mean(ys))
        amplitude = float(np.std(ys))
        altura_anel = float(anel.shape[0])
        amplitude_min = max(3.5, altura_anel * 0.07)
        if amplitude < amplitude_min:
            return None

        sinais = np.sign(ys)
        sinais[sinais == 0] = 1
        cruzamentos_brutos = np.where(sinais[1:] * sinais[:-1] < 0)[0] + 1
        if cruzamentos_brutos.size <= 0:
            return None
        if cruzamentos_brutos.size > 36 and amplitude < altura_anel * 0.14:
            min_dist = max(24, int(round(anel.shape[1] / 28.0)))
            cruzamentos_lista: list[int] = []
            ultimo = -min_dist
            for idx in cruzamentos_brutos:
                if int(idx) - ultimo >= min_dist:
                    cruzamentos_lista.append(int(idx))
                    ultimo = int(idx)
            cruzamentos = len(cruzamentos_lista)
        else:
            cruzamentos = int(cruzamentos_brutos.size)
        if cruzamentos <= 0 or cruzamentos > 72:
            return None
        if amplitude > altura_anel * 0.40:
            return None
        # 1 cruzamento (ida ou volta) = 5 km — evita arredondar 9,6 V para 8×10 km
        distancia = float(cruzamentos * KM_POR_DEFLEXAO_ODOMETRO)
        ciclos = max(1, int(round(cruzamentos / 2.0)))
        return distancia, ciclos, amplitude

    def _alinhar_marcas_hora(
        self,
        imagem_cinza: NDArray[np.uint8],
        circulo: CirculoDetectado,
        imagem_desdobrada: NDArray[np.uint8],
        mascara_grade: NDArray[np.uint8] | None,
        raio_papel: float | None = None,
    ) -> tuple[NDArray[np.uint8], NDArray[np.uint8] | None]:
        """
        Coloca x=0 na marca impressa 24h/00:00 (não no tick de hora mais próximo
        de um θ=0 já errado — isso deixava o laudo ~3 h atrasado).
        """
        raio = float(raio_papel) if raio_papel and raio_papel > 8.0 else self._raio_disco_util(
            imagem_cinza, circulo,
        )
        ticks = self._desdobrar_anel(imagem_cinza, circulo, raio * 0.86, raio * 0.96)
        raios = self._desdobrar_anel(imagem_cinza, circulo, raio * 0.52, raio * 0.84)
        if ticks.ndim != 2 or ticks.shape[1] < 48:
            return imagem_desdobrada, mascara_grade

        def perfil_escuro(img: NDArray[np.uint8]) -> NDArray[np.float64]:
            sinal = (255.0 - img.astype(np.float64)).mean(axis=0)
            kernel = np.ones(9, dtype=np.float64) / 9.0
            return np.convolve(sinal, kernel, mode="same")

        e_tick = perfil_escuro(ticks)
        n = int(e_tick.shape[0])
        e_raio_raw = perfil_escuro(raios)
        if e_raio_raw.size == n:
            e_raio = e_raio_raw
        else:
            e_raio = np.interp(
                np.linspace(0.0, 1.0, n),
                np.linspace(0.0, 1.0, int(e_raio_raw.size)),
                e_raio_raw,
            )

        t_max = float(e_tick.max())
        r_max = float(e_raio.max())
        if t_max < 1.0:
            return imagem_desdobrada, mascara_grade

        t_n = e_tick / max(t_max, 1e-6)
        r_n = e_raio / max(r_max, 1e-6)
        score = t_n * (0.35 + 0.65 * r_n)
        # Refina ±2 h em torno do θ=0 (gota/madrugada). Argmax global pegava a mesa.
        janela = max(8, n // 12)
        trecho = np.concatenate([score[-janela:], score[: janela + 1]])
        pico_local = int(np.argmax(trecho))
        if float(trecho[pico_local]) < 0.16:
            return imagem_desdobrada, mascara_grade
        offset = pico_local - janela
        if offset == 0:
            return imagem_desdobrada, mascara_grade

        desdobrada = np.roll(imagem_desdobrada, -int(offset), axis=1)
        mask2 = (
            np.roll(mascara_grade, -int(offset), axis=1)
            if mascara_grade is not None
            else None
        )
        return desdobrada, mask2

    def _alinhar_fase_por_parada(
        self,
        imagem_desdobrada: NDArray[np.uint8],
        mascara_grade: NDArray[np.uint8] | None,
    ) -> tuple[NDArray[np.uint8], NDArray[np.uint8] | None]:
        """
        Se a meia-noite caiu no meio da jornada, vira 12 h (12h vs 24h invertidos).
        A parada longa da madrugada deve cobrir o X=0.
        """
        altura, largura = imagem_desdobrada.shape[:2]
        if largura < 48:
            return imagem_desdobrada, mascara_grade
        trabalho = imagem_desdobrada.copy()
        if mascara_grade is not None and mascara_grade.shape == trabalho.shape:
            trabalho[mascara_grade > 0] = 255
        mediana = float(np.median(trabalho))
        atividade = (trabalho.astype(np.float64) < (mediana - 22.0)).mean(axis=0)
        parado = atividade < max(0.05, float(np.median(atividade)) * 0.5)
        n = int(parado.size)
        estendido = np.concatenate([parado, parado])
        melhor_ini, melhor_len = 0, 0
        i = 0
        while i < estendido.size:
            if not bool(estendido[i]):
                i += 1
                continue
            j = i
            while j < estendido.size and bool(estendido[j]):
                j += 1
            comprimento = j - i
            if comprimento > melhor_len:
                melhor_len = comprimento
                melhor_ini = i
            i = j
        if melhor_len < n // 6:
            return imagem_desdobrada, mascara_grade
        ini = melhor_ini % n
        cobre_meia_noite = False
        for k in range(melhor_len):
            if (ini + k) % n == 0:
                cobre_meia_noite = True
                break
        if cobre_meia_noite:
            return imagem_desdobrada, mascara_grade
        offset = n // 2
        desdobrada = np.roll(imagem_desdobrada, -int(offset), axis=1)
        mask2 = (
            np.roll(mascara_grade, -int(offset), axis=1)
            if mascara_grade is not None
            else None
        )
        return desdobrada, mask2

    def nitidez_laplaciana(self, imagem_cinza: NDArray[np.uint8]) -> float:
        """Variância do Laplaciano — fotos borradas têm valor baixo."""
        return float(cv2.Laplacian(imagem_cinza, cv2.CV_64F).var())

    def avaliar_qualidade(
        self,
        curva: list[PontoVelocidade],
        distancia_odometro_km: float | None,
        alinhamento_gota: bool,
        nitidez: float,
        tem_grade: bool,
    ) -> tuple[float, str]:
        """Nota 0–100 e um aviso em português para o operador."""
        pontos = [p["velocidade_kmh"] for p in curva]
        n = max(len(pontos), 1)
        frac_traco = sum(1 for v in pontos if v >= 0.5) / n
        nota = 0.0
        avisos: list[str] = []

        if tem_grade:
            nota += 22.0
        else:
            avisos.append("Grade impressa fraca — centro pode oscilar.")

        if alinhamento_gota:
            nota += 18.0
        else:
            nota += 8.0
            avisos.append("Furo em gota pouco visível — horário 00:00 pode deslocar.")

        if distancia_odometro_km is not None and distancia_odometro_km > 0:
            nota += 25.0
        else:
            avisos.append("Odômetro gráfico não lido — distância indisponível.")

        if frac_traco >= 0.12:
            nota += 20.0
        elif frac_traco >= 0.04:
            nota += 10.0
        else:
            avisos.append("Pouco traço de agulha — foto escura ou disco parado.")

        if nitidez >= NITIDEZ_MINIMA:
            nota += 15.0
        else:
            nota += 5.0
            avisos.append("Foto pouco nítida. Aproxime e evite tremer.")

        nota = float(max(0.0, min(100.0, round(nota, 1))))
        aviso = " ".join(avisos)
        return nota, aviso

    def garantir_pasta_temp(self) -> Path:
        PASTA_TEMP.mkdir(parents=True, exist_ok=True)
        return PASTA_TEMP

    def salvar_imagem_desdobrada(
        self,
        imagem_desdobrada: NDArray[np.uint8],
        nome_base: str | None = None,
    ) -> Path:
        if imagem_desdobrada.size == 0:
            raise ErroProcessamentoDisco("Imagem desdobrada vazia; nada a salvar.")

        pasta = self.garantir_pasta_temp()
        carimbo = datetime.now().strftime("%Y%m%d_%H%M%S")
        prefixo = nome_base or "disco_desdobrado"
        prefixo_limpo = "".join(
            c if c.isalnum() or c in ("-", "_") else "_" for c in prefixo
        )
        caminho = pasta / f"{prefixo_limpo}_{carimbo}.png"

        ok = cv2.imwrite(str(caminho), imagem_desdobrada)
        if not ok:
            raise ErroProcessamentoDisco(f"Falha ao salvar imagem em: {caminho}")

        return caminho

    @staticmethod
    def _minutos_para_hora(minutos_totais: int) -> str:
        minutos_norm = minutos_totais % MINUTOS_NO_DIA
        horas = minutos_norm // 60
        minutos = minutos_norm % 60
        return f"{horas:02d}:{minutos:02d}"

    def _preparar_imagem_para_traco(
        self,
        imagem_desdobrada: NDArray[np.uint8],
        mascara_grade: NDArray[np.uint8] | None = None,
    ) -> NDArray[np.uint8]:
        # 0) Pinta a grade verde de branco — só a cera/grafite da agulha resta.
        trabalho = imagem_desdobrada.copy()
        if mascara_grade is not None and mascara_grade.shape == trabalho.shape:
            trabalho[mascara_grade > 0] = 255

        # 1) CLAHE + black-hat: realça riscos escuros finos da agulha de cera.
        equalizada = self._equalizar_iluminacao(trabalho)
        nucleo_hat = cv2.getStructuringElement(cv2.MORPH_RECT, (11, 3))
        realce = cv2.morphologyEx(equalizada, cv2.MORPH_BLACKHAT, nucleo_hat)
        combinada = cv2.addWeighted(equalizada, 0.75, realce, 2.5, 0)
        suavizada = cv2.GaussianBlur(combinada, (5, 5), 0)

        # 2) Binarização Otsu: tinta escura (agulha) vs fundo do papel.
        _, mascara_tinta = cv2.threshold(
            suavizada,
            0,
            255,
            cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU,
        )
        _, mascara_hat = cv2.threshold(
            realce,
            0,
            255,
            cv2.THRESH_BINARY + cv2.THRESH_OTSU,
        )
        # Otsu no papel comprimido (WhatsApp) marca textura como tinta (~70%)
        # e o passo seguinte apaga o dia inteiro. O black-hat fica na agulha.
        if float((mascara_tinta > 0).mean()) > 0.40:
            mascara_tinta = mascara_hat

        # 3) Subtrai o gabarito verde impresso — números/grade não viram “pico”.
        #    Dilatação ampla: a grade ondulada (foto inclinada) deixa resíduo que
        #    o rastreador confunde com a agulha e trava em ~96 km/h planos.
        if mascara_grade is not None and mascara_grade.shape == mascara_tinta.shape:
            nucleo_grade = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
            grade_dilatada = cv2.dilate(mascara_grade, nucleo_grade, iterations=2)
            mascara_tinta[grade_dilatada > 0] = 0

        # 3b) Círculos concêntricos da escala viram linhas horizontais contínuas
        #     no polar: não são a agulha (que é uma curva localizada).
        mascara_tinta = self._remover_linhas_de_escala(mascara_tinta)

        # 4) CLOSE une pedaços da agulha; OPEN apaga respingos.
        nucleo_close = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        mascara_limpa = cv2.morphologyEx(
            mascara_tinta, cv2.MORPH_CLOSE, nucleo_close, iterations=1,
        )
        nucleo_open = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        mascara_limpa = cv2.morphologyEx(
            mascara_limpa, cv2.MORPH_OPEN, nucleo_open, iterations=1,
        )

        # 5) Componentes curtos no eixo do tempo = dígitos/sujeira, não a agulha.
        mascara_limpa = self._filtrar_componentes_curtos(mascara_limpa)

        preparada = imagem_desdobrada.copy()
        preparada[mascara_limpa == 0] = 255
        return preparada

    def _filtrar_componentes_curtos(
        self,
        mascara: NDArray[np.uint8],
    ) -> NDArray[np.uint8]:
        """Remove blobs isolados (números da escala, pontinhos) sem continuidade temporal."""
        n, rotulos, stats, _ = cv2.connectedComponentsWithStats(mascara, connectivity=8)
        if n <= 1:
            return mascara
        filtrada = np.zeros_like(mascara)
        for i in range(1, n):
            largura = int(stats[i, cv2.CC_STAT_WIDTH])
            area = int(stats[i, cv2.CC_STAT_AREA])
            if largura >= LARGURA_MINIMA_TRACO_PX and area >= LARGURA_MINIMA_TRACO_PX:
                filtrada[rotulos == i] = 255
        return filtrada

    def _remover_linhas_de_escala(
        self,
        mascara: NDArray[np.uint8],
    ) -> NDArray[np.uint8]:
        """Apaga linhas que atravessam quase o dia inteiro (gabarito, não agulha)."""
        if mascara.size == 0:
            return mascara
        largura = mascara.shape[1]
        if largura < 8:
            return mascara
        limiar = 0.32 * 255.0
        media_linha = mascara.mean(axis=1)
        limpa = mascara.copy()
        limpa[media_linha >= limiar, :] = 0
        return limpa

    def _coluna_tem_traco_valido(
        self,
        coluna: NDArray[np.uint8],
        y_candidato: int,
    ) -> bool:
        if coluna.size == 0:
            return False

        y = max(0, min(int(y_candidato), int(coluna.shape[0]) - 1))
        intensidade_min = int(coluna[y])
        mediana = float(np.median(coluna))
        contraste = mediana - float(intensidade_min)

        if contraste < float(CONTRASTE_MINIMO_TRACO):
            return False

        limiar_local = int(max(0, mediana - CONTRASTE_MINIMO_TRACO * 0.65))
        y0 = max(0, y - 4)
        y1 = min(int(coluna.shape[0]), y + 5)
        vizinhanca = coluna[y0:y1]
        pixels_escuros = int(np.count_nonzero(vizinhanca <= limiar_local))
        return pixels_escuros >= PIXEIS_ESCUROS_MINIMOS

    def _aplicar_media_movel(
        self,
        velocidades: list[float],
        janela: int = 5,
    ) -> list[float]:
        if janela < 1:
            raise ValueError("A janela da média móvel deve ser >= 1.")
        if not velocidades:
            return []
        if janela == 1 or len(velocidades) < janela:
            return [float(v) for v in velocidades]

        arr = np.asarray(velocidades, dtype=np.float64)
        kernel = np.ones(janela, dtype=np.float64) / float(janela)
        suavizada = np.convolve(arr, kernel, mode="same")
        return [float(v) for v in suavizada]

    def _aplicar_mediana_movel(
        self,
        velocidades: list[float],
        janela: int = 5,
    ) -> list[float]:
        """Remove picos isolados (números da escala) melhor que a média."""
        if janela < 1 or not velocidades:
            return [float(v) for v in velocidades]
        if janela == 1 or len(velocidades) < janela:
            return [float(v) for v in velocidades]
        arr = np.asarray(velocidades, dtype=np.float64)
        pad = janela // 2
        padded = np.pad(arr, (pad, pad), mode="edge")
        return [
            float(np.median(padded[i:i + janela]))
            for i in range(len(arr))
        ]

    def _suprimir_borda_externa(
        self,
        imagem: NDArray[np.uint8],
    ) -> NDArray[np.uint8]:
        """Pinta de claro a faixa do raio externo (fundo/mesa após o unwrap)."""
        altura = int(imagem.shape[0])
        corte = max(2, int(round(altura * MARGEM_Y_BORDA_EXTERNA)))
        saida = imagem.copy()
        saida[:corte, :] = 255
        return saida

    def _branquear_extremos_de_mesa(
        self,
        imagem_desdobrada: NDArray[np.uint8],
    ) -> NDArray[np.uint8]:
        """
        Colunas cuja faixa externa é muito mais escura que o papel: residual da
        mesa após o unwrap. Branqueia o topo (alta velocidade) nessas colunas.
        """
        altura, largura = imagem_desdobrada.shape[:2]
        if altura < 16 or largura < 16:
            return imagem_desdobrada
        faixa = max(4, int(altura * 0.14))
        topo = imagem_desdobrada[:faixa, :].astype(np.float64)
        media = topo.mean(axis=0)
        limiar = float(np.median(media)) * 0.62
        escuras = media < limiar
        if not np.any(escuras):
            return imagem_desdobrada
        saida = imagem_desdobrada.copy()
        saida[:faixa, escuras] = 255
        return saida

    def _branquear_costura_polar(
        self,
        imagem_desdobrada: NDArray[np.uint8],
    ) -> NDArray[np.uint8]:
        """
        Ponta esquerda/direita do unwrap (= 00:00/24:00): borda do papel e
        manuscritos do miolo vazam na costura polar e viram 114 km/h à 00:02.
        """
        altura, largura = imagem_desdobrada.shape[:2]
        if largura < 48:
            return imagem_desdobrada
        minutos = max(6, int(round(largura * (MINUTOS_COSTURA_POLAR / float(MINUTOS_NO_DIA)))))
        minutos = min(minutos, largura // 8)
        saida = imagem_desdobrada.copy()
        saida[:, :minutos] = 255
        saida[:, -minutos:] = 255
        return saida

    def _filtrar_saltos_irrealistas(
        self,
        velocidades: list[float],
        max_subida_kmh: float = SALTO_MAXIMO_KMH_POR_MINUTO,
        max_descida_kmh: float = 25.0,
    ) -> list[float]:
        """
        Δv/Δt da agulha mecânica. Sobe no máximo ~12 km/h por minuto;
        um salto rumo a 125 km/h é borda preta, não o veículo.
        """
        if not velocidades:
            return []
        out = [float(v) for v in velocidades]
        teto_falso = float(self.velocidade_maxima_kmh) * 0.88
        for i in range(1, len(out)):
            dv = out[i] - out[i - 1]
            if dv > max_subida_kmh:
                if out[i] >= teto_falso:
                    out[i] = out[i - 1]
                else:
                    out[i] = out[i - 1] + max_subida_kmh
            elif dv < -max_descida_kmh:
                out[i] = out[i - 1] - max_descida_kmh
        return out

    def extrair_curva_velocidade(
        self,
        imagem_desdobrada: NDArray[np.uint8],
        janela_media_movel: int = 5,
        mascara_grade: NDArray[np.uint8] | None = None,
    ) -> list[PontoVelocidade]:
        if imagem_desdobrada is None or imagem_desdobrada.ndim != 2:
            raise ImagemInvalidaError("A imagem desdobrada deve estar em escala de cinza.")

        altura, largura = imagem_desdobrada.shape
        if altura < 2 or largura < 1:
            raise ImagemInvalidaError("Dimensões insuficientes para extrair a curva.")

        try:
            preparada = self._preparar_imagem_para_traco(imagem_desdobrada, mascara_grade)
            preparada = self._branquear_extremos_de_mesa(preparada)
            preparada = self._suprimir_borda_externa(preparada)
        except Exception as erro:
            raise ErroProcessamentoDisco("Falha no pré-processamento da curva.") from erro

        denominador_x = max(largura - 1, 1)
        denominador_y = max(altura - 1, 1)
        salto_max_px = max(
            2.0,
            (SALTO_MAXIMO_KMH_POR_MINUTO / float(self.velocidade_maxima_kmh)) * denominador_y,
        )

        y_anterior: int | None = None
        velocidades_brutas: list[float] = []
        horas: list[str] = []

        for x in range(largura):
            minutos = int(round((x / denominador_x) * (MINUTOS_NO_DIA - 1)))
            horas.append(self._minutos_para_hora(minutos))

            coluna = preparada[:, x]
            y = self._rastrear_agulha_na_coluna(coluna, y_anterior, salto_max_px)
            if y is None:
                velocidades_brutas.append(0.0)
                continue

            y_anterior = y
            fracao_altura = 1.0 - (float(y) / denominador_y)
            velocidade = fracao_altura * float(self.velocidade_maxima_kmh)
            velocidades_brutas.append(
                float(max(0.0, min(velocidade, float(self.velocidade_maxima_kmh))))
            )

        velocidades_suaves = self._aplicar_mediana_movel(
            velocidades_brutas,
            janela=5,
        )
        velocidades_suaves = self._aplicar_media_movel(
            velocidades_suaves,
            janela=max(1, int(janela_media_movel)),
        )

        for i in range(1, len(velocidades_suaves) - 1):
            if velocidades_suaves[i] > 8.0 and velocidades_suaves[i - 1] < 1.0 and velocidades_suaves[i + 1] < 1.0:
                velocidades_suaves[i] = 0.0

        velocidades_suaves = self._filtrar_saltos_irrealistas(velocidades_suaves)

        n = min(len(horas), len(velocidades_suaves))
        curva: list[PontoVelocidade] = []
        for i in range(n):
            velocidade = velocidades_suaves[i]
            velocidade_final = 0.0 if velocidade < 0.5 else round(float(velocidade), 1)
            curva.append(
                {
                    "hora": horas[i],
                    "velocidade_kmh": float(max(0.0, min(velocidade_final, float(self.velocidade_maxima_kmh)))),
                }
            )

        if not curva:
            raise ErroProcessamentoDisco("Não foi possível extrair pontos de velocidade.")

        return curva

    def _rastrear_agulha_na_coluna(
        self,
        coluna: NDArray[np.uint8],
        y_anterior: int | None,
        salto_max_px: float,
    ) -> int | None:
        """
        Y da agulha com continuidade + centróide subpixel dos pixels escuros.
        """
        if coluna.size == 0:
            return None

        altura = int(coluna.shape[0])
        y_corte = max(1, int(round(altura * MARGEM_Y_BORDA_EXTERNA)))
        if y_anterior is None:
            # Não começa no 45% inferior: a agulha real fica na coroa externa (topo).
            y_inicio = max(y_corte, int(altura * 0.12))
            trecho = coluna[y_inicio:]
            y = int(np.argmin(trecho)) + y_inicio
            if not self._coluna_tem_traco_valido(coluna, y):
                y = int(np.argmin(coluna[y_inicio:])) + y_inicio
                if not self._coluna_tem_traco_valido(coluna, y):
                    return None
            if y < y_corte:
                return None
            return int(round(self._centroide_escuro(coluna, y, 6.0)))

        y0 = max(y_corte, int(round(y_anterior - salto_max_px)))
        y1 = min(altura, int(round(y_anterior + salto_max_px)) + 1)
        janela = coluna[y0:y1]
        if janela.size == 0:
            return None

        y_local = int(np.argmin(janela)) + y0
        if y_local < y_corte:
            return None
        if not self._coluna_tem_traco_valido(coluna, y_local):
            return None
        return int(round(self._centroide_escuro(coluna, y_local, salto_max_px)))

    def _centroide_escuro(
        self,
        coluna: NDArray[np.uint8],
        y_ref: int,
        raio: float,
    ) -> float:
        """Centróide ponderado (pixels escuros) numa janela em torno de y_ref."""
        altura = int(coluna.shape[0])
        y0 = max(0, int(round(y_ref - raio)))
        y1 = min(altura, int(round(y_ref + raio)) + 1)
        trecho = coluna[y0:y1].astype(np.float64)
        if trecho.size == 0:
            return float(y_ref)
        pesos = np.maximum(0.0, float(np.median(coluna)) - trecho)
        soma = float(pesos.sum())
        if soma < 1.0:
            return float(y_ref)
        ys = np.arange(y0, y1, dtype=np.float64)
        return float(np.sum(ys * pesos) / soma)

    def processar(self, dados_imagem: bytes) -> ResultadoProcessamento:
        # 1) Decodifica a imagem colorida (precisamos da cor para a máscara verde)
        imagem_bgr = self._decodificar_bgr(dados_imagem)
        imagem_cinza = cv2.cvtColor(imagem_bgr, cv2.COLOR_BGR2GRAY)
        nitidez = self.nitidez_laplaciana(imagem_cinza)

        # 2) Máscara da grade impressa (subtração de grid no unwrap)
        mascara_verde = self._mascara_verde(imagem_bgr)

        # 4) Elipse → quadro 2000×2000 com centro em (1000, 1000); polar só depois
        circulo = self._circulo_do_papel(imagem_cinza, imagem_bgr) or self.detectar_centro(
            imagem_bgr, imagem_cinza, mascara_verde,
        )
        imagem_bgr, circulo, homografia = self.corrigir_perspectiva(
            imagem_bgr, circulo, mascara_verde,
        )
        if homografia is None:
            imagem_cinza = cv2.cvtColor(imagem_bgr, cv2.COLOR_BGR2GRAY)
            circulo = self._circulo_do_papel(imagem_cinza, imagem_bgr) or self.detectar_centro(
                imagem_bgr, imagem_cinza, mascara_verde,
            )
            imagem_bgr, circulo = self._enquadrar_disco(imagem_bgr, circulo)

        # Centro das circunferências verdes — usa (x0,y0) refinado no quadro fixo
        circulo = self._refinar_centro_por_grade_verde(imagem_bgr, circulo)
        ja_no_quadro = (
            imagem_bgr.shape[0] == LADO_QUADRO_PX
            and imagem_bgr.shape[1] == LADO_QUADRO_PX
        )
        meio = LADO_QUADRO_PX // 2
        if ja_no_quadro:
            # Foto real: mantém (x0,y0) refinado; desvio pequeno → centro do quadro
            if abs(circulo.centro_x - meio) <= 24 and abs(circulo.centro_y - meio) <= 24:
                circulo = CirculoDetectado(
                    centro_x=meio,
                    centro_y=meio,
                    raio=circulo.raio,
                )
        elif abs(circulo.centro_x - meio) > 8 or abs(circulo.centro_y - meio) > 8:
            imagem_bgr, circulo = self._enquadrar_disco(imagem_bgr, circulo)
        mascara_verde = self._mascara_somente_verde(imagem_bgr)

        imagem_eq = self._equalizar_iluminacao(cv2.cvtColor(imagem_bgr, cv2.COLOR_BGR2GRAY))

        imagem_proc = imagem_eq
        raio_papel = float(circulo.raio)
        preenchimento = 255
        imagem_proc = self._mascarar_fundo_fora_do_papel(
            imagem_proc, circulo, raio_papel, preenchimento=preenchimento,
        )
        imagem_bgr = self._mascarar_fundo_fora_do_papel(
            imagem_bgr, circulo, raio_papel, preenchimento=255,
        )
        if mascara_verde is not None:
            mascara_verde = self._mascarar_fundo_fora_do_papel(
                mascara_verde, circulo, raio_papel, preenchimento=0,
            )

        # 6) X=0 = 00:00 (madrugada parada 16h–05h; não o topo da foto)
        angulo_zero_detectado, alinhamento_gota = self._angulo_zero_temporal(
            imagem_proc, circulo, raio_papel, imagem_bgr=imagem_bgr,
        )
        angulo_zero = 0.0
        if angulo_zero_detectado is not None:
            angulo_zero = float(angulo_zero_detectado)
            imagem_proc = self._rotacionar_em_torno(
                imagem_proc, circulo, angulo_zero, borda=preenchimento,
            )
            imagem_bgr = self._rotacionar_em_torno(
                imagem_bgr, circulo, angulo_zero, borda=(255, 255, 255),
            )
            if mascara_verde is not None:
                mascara_verde = self._rotacionar_em_torno(
                    mascara_verde, circulo, angulo_zero, borda=0,
                )
            imagem_proc = self._mascarar_fundo_fora_do_papel(
                imagem_proc, circulo, raio_papel, preenchimento=preenchimento,
            )
            imagem_bgr = self._mascarar_fundo_fora_do_papel(
                imagem_bgr, circulo, raio_papel, preenchimento=255,
            )
            if mascara_verde is not None:
                mascara_verde = self._mascarar_fundo_fora_do_papel(
                    mascara_verde, circulo, raio_papel, preenchimento=0,
                )

        # 7) Anel de velocidade na coroa 0.70–0.92 R + HSV da grade no linear
        r_min, r_max = self._calcular_raios_anel_velocidade(
            imagem_proc, circulo, mascara_verde, raio_papel=raio_papel,
        )
        r_max = min(r_max, raio_papel * FRACAO_RMAX_VS_PAPEL)
        bgr_linear = self._desdobrar_anel(imagem_bgr, circulo, r_min, r_max)
        imagem_desdobrada, mascara_grade_desdobrada = self._separar_grade_hsv_linear(
            bgr_linear,
        )

        imagem_desdobrada, mascara_grade_desdobrada = self._alinhar_marcas_hora(
            imagem_proc,
            circulo,
            imagem_desdobrada,
            mascara_grade_desdobrada,
            raio_papel=raio_papel,
        )
        imagem_desdobrada, mascara_grade_desdobrada = self._alinhar_fase_por_parada(
            imagem_desdobrada, mascara_grade_desdobrada,
        )
        imagem_desdobrada, mascara_grade_desdobrada = self._endireitar_grade_no_linear(
            imagem_desdobrada, mascara_grade_desdobrada,
        )
        imagem_desdobrada = self._branquear_extremos_de_mesa(imagem_desdobrada)
        imagem_desdobrada = self._branquear_costura_polar(imagem_desdobrada)

        # 8) Odômetro no anel interno (grade inclinada inflava os km)
        raio_disco = raio_papel * FRACAO_MASCARA_PAPEL
        distancia_odo, ciclos_odo = self._estimar_distancia_odometro(
            imagem_proc, circulo, raio_disco, r_min, imagem_bgr=imagem_bgr,
        )

        altura, largura = imagem_desdobrada.shape[:2]
        return ResultadoProcessamento(
            imagem_cinza=imagem_proc,
            circulo=circulo,
            imagem_desdobrada=imagem_desdobrada,
            largura_px=int(largura),
            altura_px=int(altura),
            mascara_grade_desdobrada=mascara_grade_desdobrada,
            distancia_odometro_km=distancia_odo,
            ciclos_odometro=ciclos_odo,
            angulo_zero_graus=angulo_zero,
            nitidez=nitidez,
            alinhamento_gota=alinhamento_gota,
        )