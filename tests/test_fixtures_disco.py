from __future__ import annotations

import json
import unittest
from pathlib import Path

from core.analisador import AnalisadorDisco
from core.processador_imagem import LeitorDisco


PASTA_FIXTURES = Path(__file__).resolve().parent / "fixtures"
TOLERANCIA_DISTANCIA = 0.08
TOLERANCIA_VELOCIDADE_KMH = 5.0


class LeituraFixturesDiscoTest(unittest.TestCase):
    def test_fotos_batem_distancia_e_velocidade_maxima(self) -> None:
        gabarito = json.loads((PASTA_FIXTURES / "gabarito.json").read_text(encoding="utf-8"))
        leitor = LeitorDisco()
        analisador = AnalisadorDisco()

        for nome, esperado in gabarito.items():
            with self.subTest(disco=nome):
                dados = (PASTA_FIXTURES / f"{nome}.png").read_bytes()
                resultado = leitor.processar(dados)
                curva = leitor.extrair_curva_velocidade(resultado)
                resumo = analisador.analisar_infracoes(curva)["resumo"]

                self.assertFalse(resultado.avisos)
                erro_distancia = abs(resumo["distancia_estimada_km"] - esperado["distancia_km"])
                self.assertLess(erro_distancia / esperado["distancia_km"], TOLERANCIA_DISTANCIA)
                self.assertLess(
                    abs(resumo["velocidade_maxima_kmh"] - esperado["velocidade_maxima_kmh"]),
                    TOLERANCIA_VELOCIDADE_KMH,
                )


if __name__ == "__main__":
    unittest.main()
