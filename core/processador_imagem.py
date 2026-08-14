"""
Processador de imagem para discos de cronotacógrafo analógico.

Fase 1 (PGI): protótipo focado em escaneamentos limpos.
Fluxo principal:
1. Decodificar a imagem colorida (BGR)
2. Detectar o centro pela grade verde impressa (fallback: furo físico/Hough)
3. Desdobrar o disco circular em uma imagem retangular (polar → cartesiana)
4. Salvar a imagem desdobrada em temp/ (debug)
5. Extrair a curva de velocidade com tratamento de ruído (grade/sujeira)
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Final, TypedDict

import cv2
import numpy as np
from numpy.typing import NDArray


# Constantes do domínio do cronotacógrafo (disco analógico padrão)
HORAS_NO_DIA: Final[int] = 24
MINUTOS_NO_DIA: Final[int] = HORAS_NO_DIA * 60
VELOCIDADE_MAXIMA_KMH: Final[int] = 120

# Resolução padrão do desdobramento
LARGURA_PADRAO_PX: Final[int] = 1440  # 24 h * 60 min → 1 px ≈ 1 minuto
ALTURA_PADRAO_PX: Final[int] = 480    # faixa de velocidade 0–120 km/h

# CORREÇÃO CRÍTICA DOS RAIOS (Kienzle):
# - 0.52 elimina o miolo escrito (data, nome, odômetro e furo pera)
# - 0.82 limita o topo do gráfico antes das atividades de trabalho
FRACAO_RAIO_MIN_VELOCIDADE: Final[float] = 0.52
FRACAO_RAIO_MAX_VELOCIDADE: Final[float] = 0.82

# Critérios para aceitar um traço de estilete na coluna
CONTRASTE_MINIMO_TRACO: Final[int] = 28
PIXEIS_ESCUROS_MINIMOS: Final[int] = 4

# Faixa HSV do verde impresso do disco (grade/escala de velocidade).
# H no OpenCV vai de 0 a 179; o verde do papel varia entre esverdeado e oliva.
VERDE_HSV_BAIXO: Final[tuple[int, int, int]] = (30, 20, 20)
VERDE_HSV_ALTO: Final[tuple[int, int, int]] = (95, 255, 255)
# Fração mínima de pixels verdes para considerar a grade detectável
FRACAO_MINIMA_VERDE: Final[float] = 0.004

# CLAHE (equalização adaptativa) — normaliza sombras e reflexos do papel brilhante
CLAHE_CLIP_LIMIT: Final[float] = 2.0
CLAHE_TILE_GRID: Final[tuple[int, int]] = (8, 8)

# Correção de perspectiva: só corrige se a elipse detectada estiver dentro
# desta faixa de razão entre eixos (evita "corrigir" fits ruins/absurdos)
RAZAO_ELIPSE_MINIMA: Final[float] = 1.08
RAZAO_ELIPSE_MAXIMA: Final[float] = 1.80

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
    ) -> None:
        if largura_desdobramento <= 0 or altura_desdobramento <= 0:
            raise ValueError("As dimensões do desdobramento devem ser positivas.")
        if velocidade_maxima_kmh <= 0:
            raise ValueError("A velocidade máxima deve ser positiva.")
        if not (0.0 < fracao_raio_min < fracao_raio_max <= 1.0):
            raise ValueError("As frações de raio devem obedecer: 0 < min < max <= 1.")

        self.largura_desdobramento = largura_desdobramento
        self.altura_desdobramento = altura_desdobramento
        self.velocidade_maxima_kmh = velocidade_maxima_kmh
        self.fracao_raio_min = fracao_raio_min
        self.fracao_raio_max = fracao_raio_max

    def _decodificar_bgr(self, dados_imagem: bytes) -> NDArray[np.uint8]:
        """Decodifica os bytes recebidos em uma imagem colorida (BGR) validada."""
        if not dados_imagem:
            raise ImagemInvalidaError("Arquivo de imagem vazio. Selecione um PNG ou JPG válido.")

        try:
            buffer = np.frombuffer(dados_imagem, dtype=np.uint8)
            imagem_bgr = cv2.imdecode(buffer, cv2.IMREAD_COLOR)
        except Exception as erro:
            raise ImagemInvalidaError("Falha ao ler o arquivo de imagem.") from erro

        if imagem_bgr is None:
            raise ImagemInvalidaError("Não foi possível decodificar a imagem.")

        if imagem_bgr.size == 0 or min(imagem_bgr.shape[:2]) < 50:
            raise ImagemInvalidaError("A imagem é muito pequena ou inválida.")

        return imagem_bgr

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
        """
        Isola a tinta verde impressa (grade/escala) no espaço HSV.

        HSV separa cor (matiz) de brilho, então a máscara verde sobrevive a
        variações de iluminação melhor do que limiares em RGB/cinza.
        """
        if imagem_bgr is None or imagem_bgr.ndim != 3:
            return None

        hsv = cv2.cvtColor(imagem_bgr, cv2.COLOR_BGR2HSV)
        baixo = np.array(VERDE_HSV_BAIXO, dtype=np.uint8)
        alto = np.array(VERDE_HSV_ALTO, dtype=np.uint8)
        mascara = cv2.inRange(hsv, baixo, alto)

        # Abertura remove respingos; fechamento reconecta as finas linhas da grade
        nucleo = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        mascara = cv2.morphologyEx(mascara, cv2.MORPH_OPEN, nucleo, iterations=1)
        mascara = cv2.morphologyEx(mascara, cv2.MORPH_CLOSE, nucleo, iterations=1)
        return mascara

    def detectar_centro(
        self,
        imagem_bgr: NDArray[np.uint8],
        imagem_cinza: NDArray[np.uint8],
        mascara_verde: NDArray[np.uint8] | None = None,
    ) -> CirculoDetectado:
        """
        Determina o centro/raio de referência do disco.

        Estratégia principal (mais precisa para o warpPolar):
        - Isola a cor verde da grade impressa e usa o centroide dela como centro
          absoluto, e o anel externo verde como raio de referência.
        Fallback:
        - Se a grade verde não for detectável, cai para HoughCircles + centroide
          do furo físico.
        """
        centro_verde = self.encontrar_centro_pela_grade_verde(
            imagem_bgr,
            mascara_verde,
        )
        if centro_verde is not None:
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

    def corrigir_perspectiva(
        self,
        imagem_cinza: NDArray[np.uint8],
        circulo: CirculoDetectado,
        mascara_verde: NDArray[np.uint8] | None,
    ) -> tuple[NDArray[np.uint8], CirculoDetectado]:
        """
        Corrige a distorção de perspectiva (elipse → círculo).

        Motivo: se a foto foi tirada em ângulo, o disco circular aparece como
        elipse. Ao desdobrar (warpPolar) uma elipse, um mesmo raio real cai em
        posições diferentes conforme o ângulo, deslocando a curva de velocidade
        (daí a divergência de km entre fotos). Ajustamos uma elipse à grade verde
        e aplicamos um warpAffine anisotrópico que estica o eixo menor até igualar
        o maior, devolvendo um círculo perfeito antes do desdobramento.

        Se não houver elipse confiável, retorna a imagem e o círculo inalterados.
        """
        if mascara_verde is None:
            return imagem_cinza, circulo

        contornos, _ = cv2.findContours(
            mascara_verde,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE,
        )
        contornos = [c for c in contornos if len(c) >= 5]
        if not contornos:
            return imagem_cinza, circulo

        maior = max(contornos, key=cv2.contourArea)
        (ex, ey), (eixo1, eixo2), angulo = cv2.fitEllipse(maior)

        semi1 = float(eixo1) / 2.0
        semi2 = float(eixo2) / 2.0
        if semi1 <= 1.0 or semi2 <= 1.0:
            return imagem_cinza, circulo

        razao = max(semi1, semi2) / min(semi1, semi2)
        # Fora da faixa: ou é praticamente círculo (não precisa), ou fit ruim
        if razao < RAZAO_ELIPSE_MINIMA or razao > RAZAO_ELIPSE_MAXIMA:
            return imagem_cinza, circulo

        # Monta a transformação afim que circulariza a elipse em torno do centro.
        # Direções dos eixos da elipse: u (ângulo) e v (ângulo + 90°).
        theta = np.deg2rad(float(angulo))
        rot = np.array(
            [[np.cos(theta), -np.sin(theta)],
             [np.sin(theta), np.cos(theta)]],
            dtype=np.float64,
        )
        raio_alvo = max(semi1, semi2)
        escala = np.diag([raio_alvo / semi1, raio_alvo / semi2])
        matriz_2x2 = rot @ escala @ rot.T

        centro = np.array([float(ex), float(ey)], dtype=np.float64)
        deslocamento = centro - matriz_2x2 @ centro
        matriz_afim = np.hstack([matriz_2x2, deslocamento.reshape(2, 1)]).astype(np.float32)

        altura, largura = imagem_cinza.shape[:2]
        corrigida = cv2.warpAffine(
            imagem_cinza,
            matriz_afim,
            (largura, altura),
            flags=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=255,
        )

        novo_circulo = CirculoDetectado(
            centro_x=int(round(float(ex))),
            centro_y=int(round(float(ey))),
            raio=int(round(float(raio_alvo))),
        )
        return corrigida, novo_circulo

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

    def _calcular_raios_anel_velocidade(
        self,
        imagem_cinza: NDArray[np.uint8],
        circulo: CirculoDetectado,
    ) -> tuple[float, float]:
        altura, largura = imagem_cinza.shape
        distancias_borda = (
            circulo.centro_x,
            circulo.centro_y,
            largura - circulo.centro_x - 1,
            altura - circulo.centro_y - 1,
        )
        raio_borda = float(max(1, min(distancias_borda)))

        # Prefere o raio da grade verde impressa (referência absoluta da escala);
        # limita à borda da imagem para não amostrar pixels fora (região preta).
        raio_disco = float(circulo.raio) if circulo.raio > 0 else raio_borda
        raio_disco = min(raio_disco, raio_borda)

        min_radius = raio_disco * self.fracao_raio_min
        max_radius = raio_disco * self.fracao_raio_max

        if max_radius - min_radius < 8.0:
            min_radius = raio_disco * 0.45
            max_radius = raio_disco * 0.85

        min_radius = max(1.0, min_radius)
        max_radius = max(min_radius + 1.0, max_radius)
        return float(min_radius), float(max_radius)

    def desdobrar_disco(
        self,
        imagem_cinza: NDArray[np.uint8],
        circulo: CirculoDetectado,
    ) -> NDArray[np.uint8]:
        centro = (float(circulo.centro_x), float(circulo.centro_y))
        min_radius, max_radius = self._calcular_raios_anel_velocidade(
            imagem_cinza,
            circulo,
        )

        polar = cv2.warpPolar(
            src=imagem_cinza,
            dsize=(self.altura_desdobramento, self.largura_desdobramento),
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
            (self.altura_desdobramento, self.largura_desdobramento),
            interpolation=cv2.INTER_LINEAR,
        )

        retangular = cv2.rotate(polar_anel, cv2.ROTATE_90_COUNTERCLOCKWISE)
        retangular = cv2.flip(retangular, 0)

        return retangular

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
    ) -> NDArray[np.uint8]:
        # 1) CLAHE novamente no recorte: reforça o traço em regiões que ainda
        #    ficaram sob sombra/reflexo após o desdobramento.
        equalizada = self._equalizar_iluminacao(imagem_desdobrada)
        suavizada = cv2.GaussianBlur(equalizada, (9, 9), 0)

        # 2) Binarização Otsu: separa tinta (traço/grade) do fundo do papel.
        _, mascara_tinta = cv2.threshold(
            suavizada,
            0,
            255,
            cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU,
        )

        # 3) MORPH_CLOSE: une pedaços do traço que ficaram partidos (falhas de
        #    tinta ou brilho), deixando a linha do estilete contínua.
        nucleo_close = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        mascara_limpa = cv2.morphologyEx(
            mascara_tinta,
            cv2.MORPH_CLOSE,
            nucleo_close,
            iterations=1,
        )

        # 4) MORPH_OPEN: apaga respingos/ruídos pequenos gerados por sombras e
        #    sujeira, sem engordar o traço principal.
        nucleo_open = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        mascara_limpa = cv2.morphologyEx(
            mascara_limpa,
            cv2.MORPH_OPEN,
            nucleo_open,
            iterations=1,
        )

        preparada = imagem_desdobrada.copy()
        preparada[mascara_limpa == 0] = 255
        return preparada

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

    def extrair_curva_velocidade(
        self,
        imagem_desdobrada: NDArray[np.uint8],
        janela_media_movel: int = 5,
    ) -> list[PontoVelocidade]:
        if imagem_desdobrada is None or imagem_desdobrada.ndim != 2:
            raise ImagemInvalidaError("A imagem desdobrada deve estar em escala de cinza.")

        altura, largura = imagem_desdobrada.shape
        if altura < 2 or largura < 1:
            raise ImagemInvalidaError("Dimensões insuficientes para extrair a curva.")

        try:
            preparada = self._preparar_imagem_para_traco(imagem_desdobrada)
        except Exception as erro:
            raise ErroProcessamentoDisco("Falha no pré-processamento da curva.") from erro

        indices_y = np.argmin(preparada, axis=0).astype(np.int32)
        intensidades_min = preparada.min(axis=0)

        denominador_x = max(largura - 1, 1)
        denominador_y = max(altura - 1, 1)
        velocidades_brutas: list[float] = []
        horas: list[str] = []

        for x in range(largura):
            minutos = int(round((x / denominador_x) * (MINUTOS_NO_DIA - 1)))
            horas.append(self._minutos_para_hora(minutos))

            try:
                y = int(indices_y[x])
                intensidade = int(intensidades_min[x])
            except IndexError:
                velocidades_brutas.append(0.0)
                continue

            y = max(0, min(y, altura - 1))

            if intensidade >= 250:
                velocidades_brutas.append(0.0)
                continue

            coluna = preparada[:, x]
            if not self._coluna_tem_traco_valido(coluna, y):
                velocidades_brutas.append(0.0)
                continue

            fracao_altura = 1.0 - (y / denominador_y)
            velocidade = fracao_altura * float(self.velocidade_maxima_kmh)
            velocidades_brutas.append(float(max(0.0, min(velocidade, float(self.velocidade_maxima_kmh)))))

        velocidades_suaves = self._aplicar_media_movel(
            velocidades_brutas,
            janela=max(1, int(janela_media_movel)),
        )

        for i in range(1, len(velocidades_suaves) - 1):
            if velocidades_suaves[i] > 8.0 and velocidades_suaves[i - 1] < 1.0 and velocidades_suaves[i + 1] < 1.0:
                velocidades_suaves[i] = 0.0

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

    def processar(self, dados_imagem: bytes) -> ResultadoProcessamento:
        # 1) Decodifica a imagem colorida (precisamos da cor para a máscara verde)
        imagem_bgr = self._decodificar_bgr(dados_imagem)
        imagem_cinza = cv2.cvtColor(imagem_bgr, cv2.COLOR_BGR2GRAY)

        # 2) CLAHE: normaliza iluminação/sombras/reflexos antes de tudo
        imagem_eq = self._equalizar_iluminacao(imagem_cinza)

        # 3) Máscara verde da grade impressa (reutilizada por centro e perspectiva)
        mascara_verde = self._mascara_verde(imagem_bgr)

        # 4) Centro/raio via grade verde (fallback: HoughCircles no cinza equalizado)
        circulo = self.detectar_centro(imagem_bgr, imagem_eq, mascara_verde)

        # 5) Correção de perspectiva (elipse → círculo) antes do desdobramento
        imagem_proc, circulo = self.corrigir_perspectiva(
            imagem_eq,
            circulo,
            mascara_verde,
        )

        # 6) Desdobramento polar → cartesiano do anel de velocidade
        imagem_desdobrada = self.desdobrar_disco(imagem_proc, circulo)

        altura, largura = imagem_desdobrada.shape[:2]
        return ResultadoProcessamento(
            imagem_cinza=imagem_proc,
            circulo=circulo,
            imagem_desdobrada=imagem_desdobrada,
            largura_px=int(largura),
            altura_px=int(altura),
        )