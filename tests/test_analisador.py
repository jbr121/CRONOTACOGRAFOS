"""Testes das regras de infração (excesso, parada, média em movimento)."""

from __future__ import annotations

import unittest

from core.analisador import AnalisadorDisco


def _curva(*velocidades: float) -> list[dict[str, object]]:
    pontos: list[dict[str, object]] = []
    for i, vel in enumerate(velocidades):
        h, m = divmod(i, 60)
        pontos.append({"hora": f"{h:02d}:{m:02d}", "velocidade_kmh": vel})
    return pontos


class TestAnalisadorDisco(unittest.TestCase):
    def setUp(self) -> None:
        self.analisador = AnalisadorDisco()

    def test_pico_de_1_minuto_nao_e_excesso(self) -> None:
        curva = _curva(40.0, 90.0, 40.0)
        resultado = self.analisador.analisar_infracoes(curva, limite_velocidade=80.0)
        self.assertEqual(resultado["resumo"]["total_excessos"], 0)

    def test_dois_minutos_consecutivos_sao_excesso(self) -> None:
        curva = _curva(40.0, 90.0, 91.0, 40.0)
        resultado = self.analisador.analisar_infracoes(curva, limite_velocidade=80.0)
        self.assertEqual(resultado["resumo"]["total_excessos"], 1)
        self.assertEqual(resultado["resumo"]["minutos_excesso"], 2)

    def test_patio_no_inicio_e_fim_nao_conta_parada(self) -> None:
        # 12 min parado no começo, 5 min andando, 12 min parado no fim
        velocidades = [0.0] * 12 + [50.0] * 5 + [0.0] * 12
        resultado = self.analisador.analisar_infracoes(_curva(*velocidades))
        self.assertEqual(resultado["resumo"]["total_paradas_prolongadas"], 0)

    def test_parada_no_meio_da_jornada_conta(self) -> None:
        velocidades = [50.0] * 5 + [0.0] * 12 + [50.0] * 5
        resultado = self.analisador.analisar_infracoes(_curva(*velocidades))
        self.assertEqual(resultado["resumo"]["total_paradas_prolongadas"], 1)

    def test_media_so_em_movimento(self) -> None:
        curva = _curva(0.0, 0.0, 80.0, 100.0)
        resultado = self.analisador.analisar_infracoes(curva)
        self.assertAlmostEqual(resultado["resumo"]["velocidade_media_kmh"], 90.0, places=1)

    def test_distancia_do_odometro_tem_prioridade(self) -> None:
        curva = _curva(80.0, 80.0)
        resultado = self.analisador.analisar_infracoes(curva, distancia_km=123.0)
        self.assertEqual(resultado["resumo"]["origem_distancia"], "odometro")
        self.assertEqual(resultado["resumo"]["distancia_estimada_km"], 123.0)


if __name__ == "__main__":
    unittest.main()
