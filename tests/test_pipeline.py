"""Smoke do pipeline de imagem com disco sintético (grade + odômetro + agulha)."""

from __future__ import annotations

import unittest

import cv2
import numpy as np

from core.analisador import AnalisadorDisco
from core.processador_imagem import LeitorDisco


def _desenhar_conteudo_disco(img: np.ndarray, cx: int, cy: int, raio: int, linha_24h: bool) -> None:
    verde = (60, 150, 60)
    for r in range(int(0.70 * raio), int(0.96 * raio), 12):
        cv2.circle(img, (cx, cy), r, verde, 2)

    if linha_24h:
        x1 = int(cx + 0.20 * raio)
        x2 = int(cx + 0.97 * raio)
        cv2.line(img, (x1, cy), (x2, cy), (30, 80, 30), 3)
        for hora in range(24):
            ang = hora / 24.0 * 2 * np.pi
            r0 = 0.93 * raio
            r1 = 0.98 * raio
            p0 = (int(cx + r0 * np.cos(ang)), int(cy + r0 * np.sin(ang)))
            p1 = (int(cx + r1 * np.cos(ang)), int(cy + r1 * np.sin(ang)))
            cv2.line(img, p0, p1, (40, 110, 40), 2)

    n = 29
    r_odo = 0.42 * raio
    amp = 0.05 * raio
    pts = []
    for i in range(720):
        a = i / 720 * 2 * np.pi
        r = r_odo + np.sin(a * n) * amp
        pts.append((int(cx + r * np.cos(a)), int(cy + r * np.sin(a))))
    cv2.polylines(img, [np.array(pts)], False, (25, 25, 25), 2)

    r_vel = 0.70 * raio + (50 / 125) * 0.20 * raio
    for i in range(8 * 30, 18 * 30):
        a = (i / (24 * 30)) * 2 * np.pi
        cv2.circle(
            img,
            (int(cx + r_vel * np.cos(a)), int(cy + r_vel * np.sin(a))),
            2,
            (20, 20, 20),
            -1,
        )

    cv2.circle(img, (cx, cy), 28, (15, 15, 15), -1)
    cv2.fillConvexPoly(
        img,
        np.array([[cx - 52, cy], [cx - 18, cy - 14], [cx - 18, cy + 14]]),
        (15, 15, 15),
    )


def _disco_sintetico(fundo_preto: bool = False, linha_24h: bool = True) -> bytes:
    h = w = 900
    cx = cy = 450
    raio = 360
    if fundo_preto:
        img = np.full((h, w, 3), 18, np.uint8)
        cv2.circle(img, (cx, cy), raio + 4, (245, 245, 245), -1)
    else:
        img = np.full((h, w, 3), 245, np.uint8)
    _desenhar_conteudo_disco(img, cx, cy, raio, linha_24h)
    ok, buf = cv2.imencode(".png", img)
    if not ok:
        raise RuntimeError("Falha ao gerar PNG sintético.")
    return buf.tobytes()


def _disco_sobre_mousepad_azul_claro() -> bytes:
    """Pad azul-claro (V alto) como a foto real do laudo 18 — não só pad escuro."""
    h, w = 1024, 576
    img = np.full((h, w, 3), (170, 95, 35), np.uint8)
    cv2.circle(img, (280, 420), 390, (210, 150, 55), 18)
    cv2.circle(img, (400, 700), 280, (190, 120, 40), 14)
    cv2.line(img, (0, 200), (w, 500), (200, 140, 50), 10)
    cv2.line(img, (40, 0), (200, h), (160, 80, 30), 8)
    cx, cy, raio = 270, 550, 265
    cv2.circle(img, (cx, cy), raio + 4, (245, 245, 245), -1)
    _desenhar_conteudo_disco(img, cx, cy, raio, linha_24h=True)
    ok, buf = cv2.imencode(".png", img)
    if not ok:
        raise RuntimeError("Falha ao gerar PNG com mousepad claro.")
    return buf.tobytes()


def _disco_sobre_mousepad() -> bytes:
    """Disco deslocado sobre fundo RGB geométrico (caso do laudo 18)."""
    h, w = 1400, 1600
    img = np.full((h, w, 3), 22, np.uint8)
    for i in range(-h, w, 36):
        cv2.line(img, (i, 0), (i + 420, h), (0, 90, 210), 4)
        cv2.line(img, (0, i), (w, i + 90), (40, 190, 40), 3)
    for y in range(0, h, 80):
        cv2.rectangle(img, (40, y), (w - 40, y + 18), (18, 18, 28), -1)
    cx, cy, raio = 520, 780, 340
    cv2.circle(img, (cx, cy), raio + 4, (245, 245, 245), -1)
    _desenhar_conteudo_disco(img, cx, cy, raio, linha_24h=True)
    ok, buf = cv2.imencode(".png", img)
    if not ok:
        raise RuntimeError("Falha ao gerar PNG com mousepad.")
    return buf.tobytes()


class TestPipelineSintetico(unittest.TestCase):
    def test_velocidade_e_odometro_plausiveis(self) -> None:
        leitor = LeitorDisco()
        resultado = leitor.processar(_disco_sintetico())
        curva = leitor.extrair_curva_velocidade(
            resultado.imagem_desdobrada,
            mascara_grade=resultado.mascara_grade_desdobrada,
        )
        analise = AnalisadorDisco().analisar_infracoes(
            curva,
            distancia_km=resultado.distancia_odometro_km,
        )
        resumo = analise["resumo"]
        self.assertLess(resumo["velocidade_maxima_kmh"], 100.0)
        self.assertGreater(resumo["velocidade_maxima_kmh"], 30.0)
        self.assertEqual(resumo["origem_distancia"], "odometro")
        self.assertGreaterEqual(resumo["distancia_estimada_km"], 200.0)
        self.assertLessEqual(resumo["distancia_estimada_km"], 400.0)
        confianca, _aviso = leitor.avaliar_qualidade(
            curva,
            resultado.distancia_odometro_km,
            resultado.alinhamento_gota,
            resultado.nitidez,
            tem_grade=True,
        )
        self.assertGreaterEqual(confianca, 70.0)

    def test_fundo_preto_nao_vira_125_kmh(self) -> None:
        leitor = LeitorDisco()
        resultado = leitor.processar(_disco_sintetico(fundo_preto=True))
        curva = leitor.extrair_curva_velocidade(
            resultado.imagem_desdobrada,
            mascara_grade=resultado.mascara_grade_desdobrada,
        )
        vmax = max(p["velocidade_kmh"] for p in curva)
        self.assertLess(vmax, 100.0, f"borda preta lida como agulha: vmax={vmax}")

    def test_elipse_com_mesa_preta_nao_gera_125(self) -> None:
        png = _disco_sintetico(fundo_preto=True)
        buf = np.frombuffer(png, dtype=np.uint8)
        img = cv2.imdecode(buf, cv2.IMREAD_COLOR)
        assert img is not None
        h, w = img.shape[:2]
        src = np.float32([[0, 0], [w - 1, 0], [w - 1, h - 1], [0, h - 1]])
        dst = np.float32(
            [[w * 0.08, h * 0.12], [w * 0.92, 0], [w * 0.95, h * 0.88], [0, h * 0.95]]
        )
        H = cv2.getPerspectiveTransform(src, dst)
        inclinada = cv2.warpPerspective(
            img, H, (w, h), borderMode=cv2.BORDER_CONSTANT, borderValue=(18, 18, 18),
        )
        ok, out = cv2.imencode(".png", inclinada)
        self.assertTrue(ok)
        leitor = LeitorDisco()
        resultado = leitor.processar(out.tobytes())
        curva = leitor.extrair_curva_velocidade(
            resultado.imagem_desdobrada,
            mascara_grade=resultado.mascara_grade_desdobrada,
        )
        vmax = max(p["velocidade_kmh"] for p in curva)
        self.assertLess(vmax, 110.0, f"elipse/mesa lida como agulha: vmax={vmax}")

    def test_mousepad_nao_desloca_o_polar(self) -> None:
        leitor = LeitorDisco()
        resultado = leitor.processar(_disco_sobre_mousepad())
        self.assertGreater(
            float(resultado.imagem_desdobrada.mean()),
            120.0,
            "unwrap escuro demais: polar provavelmente pegou o mousepad",
        )
        curva = leitor.extrair_curva_velocidade(
            resultado.imagem_desdobrada,
            mascara_grade=resultado.mascara_grade_desdobrada,
        )
        vmax = max(p["velocidade_kmh"] for p in curva)
        self.assertGreater(vmax, 30.0, f"pista de velocidade fora do ROI: vmax={vmax}")
        self.assertLess(vmax, 100.0)
        self.assertGreaterEqual(resultado.distancia_odometro_km or 0.0, 200.0)
        self.assertLessEqual(resultado.distancia_odometro_km or 0.0, 400.0)

    def test_mousepad_azul_claro_nao_desloca_o_polar(self) -> None:
        leitor = LeitorDisco()
        resultado = leitor.processar(_disco_sobre_mousepad_azul_claro())
        curva = leitor.extrair_curva_velocidade(
            resultado.imagem_desdobrada,
            mascara_grade=resultado.mascara_grade_desdobrada,
        )
        vmax = max(p["velocidade_kmh"] for p in curva)
        self.assertGreater(vmax, 30.0, f"pista fora do ROI: vmax={vmax}")
        self.assertLess(vmax, 110.0, f"borda do pad lida como agulha: vmax={vmax}")
        self.assertGreaterEqual(resultado.distancia_odometro_km or 0.0, 200.0)
        self.assertLessEqual(resultado.distancia_odometro_km or 0.0, 400.0)

    def test_grade_verde_fica_horizontal_no_unwrap(self) -> None:
        leitor = LeitorDisco()
        resultado = leitor.processar(_disco_sintetico())
        mascara = resultado.mascara_grade_desdobrada
        self.assertIsNotNone(mascara)
        assert mascara is not None
        ondulacao = leitor._score_ondulacao_grade(mascara)
        self.assertLess(ondulacao, 12.0, f"grade ondulada no polar: std={ondulacao:.2f}")

    def test_madrugada_parada_e_x0_meia_noite(self) -> None:
        leitor = LeitorDisco()
        resultado = leitor.processar(_disco_sintetico())
        curva = leitor.extrair_curva_velocidade(
            resultado.imagem_desdobrada,
            mascara_grade=resultado.mascara_grade_desdobrada,
        )
        por_hora = {p["hora"]: p["velocidade_kmh"] for p in curva}

        def media(h0: str, h1: str) -> float:
            vals = [
                p["velocidade_kmh"]
                for p in curva
                if h0 <= p["hora"] < h1
            ]
            return float(sum(vals) / max(len(vals), 1))

        self.assertLess(media("00:00", "05:00"), 15.0)
        self.assertGreater(media("10:00", "16:00"), 25.0)
        self.assertLess(por_hora.get("00:00", 99.0), 15.0)

    def test_salto_irrealista_para_125_e_descartado(self) -> None:
        leitor = LeitorDisco()
        filtrado = leitor._filtrar_saltos_irrealistas(
            [0.0, 0.0, 121.9, 121.9, 111.7, 40.0],
        )
        self.assertLess(filtrado[2], 20.0)
        self.assertLess(max(filtrado), 90.0)


if __name__ == "__main__":
    unittest.main()
