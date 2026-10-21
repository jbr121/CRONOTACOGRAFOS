"""Discos sintéticos com gabarito, no layout VDO lido pelo LeitorDisco."""

from __future__ import annotations

import cv2
import numpy as np

from core.processador_imagem import (
    ANEIS_ESCALA_VELOCIDADE,
    FRACAO_RAIO_0_KMH,
    KMH_POR_FRACAO_RAIO,
    MINUTOS_NO_DIA,
)


def velocidade_para_fracao(velocidade_kmh: float | np.ndarray) -> float | np.ndarray:
    return FRACAO_RAIO_0_KMH + np.asarray(velocidade_kmh, dtype=np.float64) / KMH_POR_FRACAO_RAIO


def renderizar_disco(
    velocidades: np.ndarray,
    *,
    raio: int = 430,
    tamanho: int = 1040,
    escala_y: float = 1.0,
    angulo_graus: float = 0.0,
    deslocamento: tuple[int, int] = (0, 0),
) -> np.ndarray:
    """
    Foto sintética de um disco diário.

    O traço e a barra de atividade seguem o mesmo ângulo que o warpPolar usa
    depois da orientação pelo arco verde 12h–24h.
    """
    if velocidades.shape != (MINUTOS_NO_DIA,):
        raise ValueError("A curva sintética precisa ter um valor por minuto.")

    lado = raio * 2
    disco = np.full((lado, lado, 3), (16, 18, 22), dtype=np.uint8)
    cv2.circle(disco, (raio, raio), raio - 2, (244, 244, 242), thickness=-1)

    for fracao in ANEIS_ESCALA_VELOCIDADE:
        cv2.circle(
            disco,
            (raio, raio),
            int(round(fracao * raio)),
            (70, 70, 70),
            thickness=1,
            lineType=cv2.LINE_AA,
        )

    yy, xx = np.indices(disco.shape[:2])
    dx = xx - raio
    dy = yy - raio
    distancia = np.sqrt(dx * dx + dy * dy)
    angulo = np.arctan2(dy, dx) % (2 * np.pi)
    minuto = np.rint(angulo / (2 * np.pi) * MINUTOS_NO_DIA - MINUTOS_NO_DIA / 2).astype(np.int32)
    minuto %= MINUTOS_NO_DIA

    arco_verde = (angulo < np.pi) & (distancia > 0.948 * raio) & (distancia < 0.978 * raio)
    disco[arco_verde] = (40, 170, 45)

    em_movimento = velocidades > 1.0
    atividade = (
        em_movimento[minuto]
        & (distancia > 0.495 * raio)
        & (distancia < 0.518 * raio)
    )
    disco[atividade] = (25, 25, 25)

    fracao_traco = velocidade_para_fracao(velocidades)
    raio_traco = fracao_traco[minuto] * raio
    traco = em_movimento[minuto] & (np.abs(distancia - raio_traco) <= 2.2) & (distancia < raio - 4)
    disco[traco] = (12, 12, 12)

    canvas = np.full((tamanho, tamanho, 3), (16, 18, 22), dtype=np.uint8)
    centro = (tamanho // 2 + deslocamento[0], tamanho // 2 + deslocamento[1])
    matriz = cv2.getRotationMatrix2D((raio, raio), angulo_graus, 1.0)
    matriz[0, 2] += centro[0] - raio
    matriz[1, 2] += centro[1] - raio
    if escala_y != 1.0:
        ajuste = np.array([[1.0, 0.0, 0.0], [0.0, escala_y, centro[1] * (1.0 - escala_y)]], dtype=np.float32)
        matriz = ajuste @ np.vstack([matriz, [0.0, 0.0, 1.0]])
    return cv2.warpAffine(
        disco,
        matriz,
        (tamanho, tamanho),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=(16, 18, 22),
    )


def curva_constante(inicio_minuto: int, fim_minuto: int, velocidade_kmh: float) -> np.ndarray:
    curva = np.zeros(MINUTOS_NO_DIA, dtype=np.float64)
    curva[inicio_minuto:fim_minuto] = velocidade_kmh
    return curva


def curva_rampa(inicio_minuto: int, fim_minuto: int, velocidade_inicial: float, velocidade_final: float) -> np.ndarray:
    curva = np.zeros(MINUTOS_NO_DIA, dtype=np.float64)
    curva[inicio_minuto:fim_minuto] = np.linspace(
        velocidade_inicial,
        velocidade_final,
        fim_minuto - inicio_minuto,
        endpoint=False,
    )
    return curva
