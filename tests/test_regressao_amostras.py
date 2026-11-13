"""
Regressão do leitor com fotos reais de discos (pasta amostras/, fora do git).

Rode na raiz do projeto:  python -m unittest tests.test_regressao_amostras -v
Sem a pasta amostras/ os testes são pulados.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from core.processador_imagem import ErroProcessamentoDisco, LeitorDisco

RAIZ = Path(__file__).resolve().parent.parent
PASTA_AMOSTRAS = RAIZ / "amostras"
GABARITO = json.loads((Path(__file__).parent / "gabarito_amostras.json").read_text(encoding="utf-8"))


@unittest.skipUnless(PASTA_AMOSTRAS.is_dir(), "pasta amostras/ ausente (fotos reais ficam fora do git)")
class RegressaoAmostrasTest(unittest.TestCase):
    leitor: LeitorDisco

    @classmethod
    def setUpClass(cls) -> None:
        cls.leitor = LeitorDisco()

    def _dados(self, nome: str) -> bytes:
        return (PASTA_AMOSTRAS / f"{nome}.jpg").read_bytes()

    def test_fotos_ruins_sao_recusadas(self) -> None:
        for nome in GABARITO["recusadas"]:
            with self.subTest(foto=nome), self.assertRaises(ErroProcessamentoDisco):
                self.leitor.processar(self._dados(nome))

    def test_distancia_pelo_zigue_zague_bate_com_o_odometro(self) -> None:
        esperado = GABARITO["disco_a_km"]
        tolerancia = GABARITO["tolerancia_distancia"]
        for nome in GABARITO["zigue_zague_legivel"]:
            with self.subTest(foto=nome):
                distancia = self.leitor.medir_distancia_zigue_zague(self.leitor.processar(self._dados(nome)))
                self.assertIsNotNone(distancia.km, "zigue-zague deveria ser legível")
                erro = abs(distancia.km - esperado) / esperado
                self.assertLess(erro, tolerancia, f"{distancia.km} km, esperado ~{esperado} km")

    def test_zigue_zague_ilegivel_nao_inventa_distancia(self) -> None:
        for nome in GABARITO["zigue_zague_ilegivel"]:
            with self.subTest(foto=nome):
                distancia = self.leitor.medir_distancia_zigue_zague(self.leitor.processar(self._dados(nome)))
                self.assertIsNone(distancia.km)


if __name__ == "__main__":
    unittest.main()
