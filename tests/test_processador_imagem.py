from __future__ import annotations

import unittest

import numpy as np

from core.processador_imagem import (
    FRACAO_RAIO_0_KMH,
    KMH_POR_FRACAO_RAIO,
    MINUTOS_NO_DIA,
    RAIO_RETIFICADO_PX,
    ResultadoProcessamento,
    CirculoDetectado,
    LeitorDisco,
)


def _raio_para_velocidade(velocidade_kmh: float) -> int:
    fracao = FRACAO_RAIO_0_KMH + velocidade_kmh / KMH_POR_FRACAO_RAIO
    return int(round(fracao * RAIO_RETIFICADO_PX))


class ExtracaoCurvaVelocidadeTest(unittest.TestCase):
    def _resultado_sintetico(self, velocidades: np.ndarray) -> ResultadoProcessamento:
        polar = np.full(
            (MINUTOS_NO_DIA, RAIO_RETIFICADO_PX, 3),
            255,
            dtype=np.uint8,
        )

        # Anéis impressos escuros e recorrentes; o extrator deve removê-los.
        for velocidade_anel in (20.0, 40.0, 60.0, 80.0, 100.0):
            raio = _raio_para_velocidade(velocidade_anel)
            polar[:, raio - 1:raio + 2] = 45

        for minuto, velocidade in enumerate(velocidades):
            raio = _raio_para_velocidade(float(velocidade))
            polar[minuto, raio - 2:raio + 3] = 0

        return ResultadoProcessamento(
            imagem_cinza=np.zeros((10, 10), dtype=np.uint8),
            circulo=CirculoDetectado(centro_x=0, centro_y=0, raio=RAIO_RETIFICADO_PX),
            imagem_desdobrada=np.zeros((10, 10, 3), dtype=np.uint8),
            largura_px=10,
            altura_px=10,
            polar_orientado=polar,
            escala_radial=1.0,
            nota_aneis=3.0,
            avisos=[],
        )

    def test_rastreia_curva_sem_barra_de_atividade(self) -> None:
        velocidades_esperadas = np.linspace(25.0, 85.0, MINUTOS_NO_DIA)
        leitor = LeitorDisco()

        curva = leitor.extrair_curva_velocidade(
            self._resultado_sintetico(velocidades_esperadas),
            janela_media_movel=1,
        )

        lidas = np.array([ponto["velocidade_kmh"] for ponto in curva], dtype=np.float64)
        self.assertEqual(len(lidas), MINUTOS_NO_DIA)
        self.assertGreater(np.count_nonzero(lidas), MINUTOS_NO_DIA * 0.95)
        self.assertLess(float(np.mean(np.abs(lidas - velocidades_esperadas))), 3.0)

    def test_interpola_lacunas_curtas_do_traco(self) -> None:
        velocidades_esperadas = np.full(MINUTOS_NO_DIA, 70.0, dtype=np.float64)
        resultado = self._resultado_sintetico(velocidades_esperadas)
        resultado.polar_orientado[300:305, :] = 255

        curva = LeitorDisco().extrair_curva_velocidade(resultado, janela_media_movel=1)
        lidas = np.array([ponto["velocidade_kmh"] for ponto in curva], dtype=np.float64)

        self.assertTrue(np.all(lidas[300:305] > 60.0))
        self.assertLess(float(np.max(np.abs(lidas[295:310] - 70.0))), 6.0)


if __name__ == "__main__":
    unittest.main()
