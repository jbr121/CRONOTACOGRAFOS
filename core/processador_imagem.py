"""
Processador de imagem para discos de cronotacógrafo analógico (VDO 125 km/h).

Leitor v2 — calibrado com fotos reais de celular (ver experimentos/leitura_v2).
Fluxo principal:
1. Decodificar a imagem colorida (BGR)
2. Localizar a borda do disco (papel branco) e ajustar uma elipse a ela
3. Achar o centro real (projetado) do disco: o ponto que deixa os anéis
   impressos mais nítidos após a retificação
4. Retificar a perspectiva com uma homografia (elipse → círculo)
5. Desdobrar o disco (polar → cartesiano) com 1 linha por minuto
6. Orientar pelo arco verde grosso impresso na borda (12h → 24h)
7. Extrair a curva de velocidade só nos minutos em que a barra de
   atividade indica movimento, ignorando a impressão fixa do disco

Layout do disco (fração do raio externo), medido nas amostras:
- 0,96       borda com a escala de horas
- 0,63–0,96  velocidade (anéis de 20 km/h em 0,683 / 0,738 / ... / 0,960)
- ~0,51      barra de atividade (escura = em movimento)
- 0,35–0,46  zigue-zague de distância (cada traço completo = 5 km)
- < 0,33     área central manuscrita
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Final, TypedDict

import cv2
import numpy as np
from numpy.typing import NDArray


# Constantes do domínio do cronotacógrafo (disco analógico diário)
HORAS_NO_DIA: Final[int] = 24
MINUTOS_NO_DIA: Final[int] = HORAS_NO_DIA * 60
VELOCIDADE_MAXIMA_KMH: Final[int] = 125

# Raio (px) do disco retificado; o desdobramento tem 1 linha por minuto
RAIO_RETIFICADO_PX: Final[int] = 600
# Raio menor usado na busca do centro (mais rápido, mesma precisão relativa)
RAIO_BUSCA_CENTRO_PX: Final[int] = 600

# Escala de velocidade (VDO 125 km/h): raio de 0 km/h e de 120 km/h
FRACAO_RAIO_0_KMH: Final[float] = 0.628
FRACAO_RAIO_120_KMH: Final[float] = 0.960
KMH_POR_FRACAO_RAIO: Final[float] = 120.0 / (FRACAO_RAIO_120_KMH - FRACAO_RAIO_0_KMH)

# Faixas lidas (fração do raio)
FAIXA_TRACO_VELOCIDADE: Final[tuple[float, float]] = (0.640, 0.955)
FAIXA_ATIVIDADE: Final[tuple[float, float]] = (0.485, 0.530)
FAIXA_ARCO_VERDE: Final[tuple[float, float]] = (0.945, 0.980)
# Recorte salvo como imagem de debug: da barra de atividade até a borda
FAIXA_IMAGEM_DEBUG: Final[tuple[float, float]] = (0.46, 1.0)

# Limiares do traço (diferença para o fundo local, canal V do HSV)
CONTRASTE_TINTA_VELOCIDADE: Final[float] = 30.0
CONTRASTE_TINTA_ATIVIDADE: Final[float] = 25.0
# Fração mínima da faixa de atividade escura para considerar "em movimento"
FRACAO_ATIVIDADE_MOVIMENTO: Final[float] = 0.15
# Buracos menores que isto na barra de atividade são preenchidos (minutos)
LACUNA_MAXIMA_ATIVIDADE_MIN: Final[int] = 4
# Raio considerado "impressão fixa" se estiver escuro em > 8% dos minutos parados
FRACAO_IMPRESSO_FIXO: Final[float] = 0.08

# Faixa HSV do verde impresso do disco
VERDE_HSV_BAIXO: Final[tuple[int, int, int]] = (30, 60, 20)
VERDE_HSV_ALTO: Final[tuple[int, int, int]] = (90, 255, 255)

# Anéis tracejados de 20/40/60/80/100 km/h (fração do raio) usados para validar
# a retificação e autocalibrar a escala radial (variação real medida: ±3%)
ANEIS_ESCALA_VELOCIDADE: Final[tuple[float, ...]] = (0.683, 0.738, 0.793, 0.848, 0.905)
ESCALA_RADIAL_MIN_MAX: Final[tuple[float, float]] = (0.97, 1.03)
# Nota dos anéis (resposta nos raios esperados / mediana da faixa):
# abaixo do mínimo a foto é recusada; abaixo do "confiável" gera aviso
NOTA_ANEIS_MINIMA: Final[float] = 1.4
NOTA_ANEIS_CONFIAVEL: Final[float] = 2.0
# Pixels verdes por linha (média na metade 12h–24h) abaixo disto = orientação incerta
VERDE_MINIMO_ARCO: Final[float] = 0.8

# Pasta de debug na raiz do projeto
RAIZ_PROJETO: Final[Path] = Path(__file__).resolve().parent.parent
PASTA_TEMP: Final[Path] = RAIZ_PROJETO / "temp"

Elipse = tuple[tuple[float, float], tuple[float, float], float]


class PontoVelocidade(TypedDict):
    """Um ponto da curva: hora do dia + velocidade estimada."""
    hora: str
    velocidade_kmh: float


@dataclass(frozen=True, slots=True)
class CirculoDetectado:
    """Centro real do disco (coordenadas da foto) e raio médio da borda."""
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
    # Disco desdobrado inteiro (BGR), linha 0 = 00:00, coluna = raio em px
    polar_orientado: NDArray[np.uint8]
    # Fator que corrige os raios padrão para este disco/foto (autocalibração)
    escala_radial: float = 1.0
    # Nota de alinhamento dos anéis impressos (>= 2 é leitura confiável)
    nota_aneis: float = 0.0
    avisos: list[str] = field(default_factory=list)


class ErroProcessamentoDisco(Exception):
    """Erro de domínio genérico no processamento do disco."""


class ImagemInvalidaError(ErroProcessamentoDisco):
    """Imagem ausente, corrompida ou em formato não suportado."""


class FuroNaoEncontradoError(ErroProcessamentoDisco):
    """Não foi possível localizar o disco / seu centro na foto."""


def _canal_brancura(imagem_bgr: NDArray[np.uint8]) -> NDArray[np.uint8]:
    """Papel branco = brilho alto e saturação baixa; fundo colorido/escuro some."""
    hsv = cv2.cvtColor(imagem_bgr, cv2.COLOR_BGR2HSV)
    s = hsv[..., 1].astype(np.int16)
    v = hsv[..., 2].astype(np.int16)
    return np.clip(v - s, 0, 255).astype(np.uint8)


def _mascara_verde(imagem_bgr: NDArray[np.uint8]) -> NDArray[np.bool_]:
    hsv = cv2.cvtColor(imagem_bgr, cv2.COLOR_BGR2HSV)
    return cv2.inRange(hsv, np.array(VERDE_HSV_BAIXO), np.array(VERDE_HSV_ALTO)) > 0


def _pontos_elipse(elipse: Elipse, n: int = 360) -> NDArray[np.float64]:
    (ex, ey), (eixo_a, eixo_b), angulo = elipse
    t = np.linspace(0, 2 * np.pi, n, endpoint=False)
    a = np.deg2rad(angulo)
    x = eixo_a / 2 * np.cos(t)
    y = eixo_b / 2 * np.sin(t)
    return np.stack([ex + x * np.cos(a) - y * np.sin(a), ey + x * np.sin(a) + y * np.cos(a)], 1)


def _conica(elipse: Elipse) -> NDArray[np.float64]:
    """Matriz 3x3 da cônica (x^T C x = 0) que representa a elipse."""
    p = _pontos_elipse(elipse, 60)
    x, y = p[:, 0], p[:, 1]
    d = np.stack([x * x, x * y, y * y, x, y, np.ones_like(x)], 1)
    a, b, c, dd, e, f = np.linalg.svd(d)[2][-1]
    return np.array([[a, b / 2, dd / 2], [b / 2, c, e / 2], [dd / 2, e / 2, f]])


def _desdobrar_polar(imagem: NDArray[np.uint8], raio: int, linhas: int) -> NDArray[np.uint8]:
    """Linhas = ângulo (sentido horário na foto), colunas = raio de 0 a `raio`."""
    return cv2.warpPolar(
        imagem, (raio, linhas), (raio, raio), raio,
        cv2.WARP_POLAR_LINEAR + cv2.INTER_LINEAR,
    )


class LeitorDisco:
    """
    Transforma a foto de um disco de cronotacógrafo em uma curva
    tempo × velocidade (1 ponto por minuto, 00:00 a 23:59).
    """

    def __init__(
        self,
        raio_retificado: int = RAIO_RETIFICADO_PX,
        velocidade_maxima_kmh: int = VELOCIDADE_MAXIMA_KMH,
    ) -> None:
        if raio_retificado < 100:
            raise ValueError("O raio retificado deve ser de pelo menos 100 px.")
        if velocidade_maxima_kmh <= 0:
            raise ValueError("A velocidade máxima deve ser positiva.")

        self.raio_retificado = raio_retificado
        self.velocidade_maxima_kmh = velocidade_maxima_kmh

    # ------------------------------------------------------------------ entrada

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

        if imagem_bgr.size == 0 or min(imagem_bgr.shape[:2]) < 200:
            raise ImagemInvalidaError(
                "A imagem é muito pequena. Envie a foto com pelo menos 200 px no menor lado."
            )

        return imagem_bgr

    # --------------------------------------------------------- borda do disco

    def _candidatos_hough(self, canal: NDArray[np.uint8]) -> list[tuple[float, float, float]]:
        altura, largura = canal.shape
        escala = 480.0 / max(altura, largura)
        pequena = cv2.resize(canal, None, fx=escala, fy=escala, interpolation=cv2.INTER_AREA)
        pequena = cv2.GaussianBlur(pequena, (5, 5), 1.5)
        menor = min(pequena.shape)
        circulos = cv2.HoughCircles(
            pequena, cv2.HOUGH_GRADIENT, dp=1.5, minDist=max(4, menor // 20),
            param1=80, param2=30, minRadius=int(menor * 0.25), maxRadius=int(menor * 0.75),
        )
        if circulos is None:
            return []
        return [(x / escala, y / escala, r / escala) for x, y, r in circulos[0][:10]]

    def _candidatos_contorno(self, canal: NDArray[np.uint8]) -> list[tuple[float, float, float]]:
        """Arcos longos de borda viram elipses candidatas (cobre falhas do Hough)."""
        menor = min(canal.shape)
        borda = cv2.Canny(cv2.GaussianBlur(canal, (5, 5), 0), 30, 90)
        borda = cv2.dilate(borda, np.ones((3, 3), np.uint8))
        contornos, _ = cv2.findContours(borda, cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)
        candidatos: list[tuple[float, float, float]] = []
        for contorno in sorted(contornos, key=len, reverse=True)[:25]:
            if len(contorno) < 150:
                break
            (ex, ey), (eixo_a, eixo_b), _ = cv2.fitEllipse(contorno)
            raio = (eixo_a + eixo_b) / 4
            if menor * 0.25 <= raio <= menor * 0.75 and min(eixo_a, eixo_b) / max(eixo_a, eixo_b) > 0.6:
                candidatos.append((ex, ey, raio))
        return candidatos

    def _refinar_elipse(
        self,
        canal: NDArray[np.uint8],
        x: float,
        y: float,
        raio: float,
        n: int = 360,
    ) -> tuple[Elipse, float] | None:
        """
        Busca radial da borda: em cada ângulo, maior queda de brilho perto de `raio`.
        Devolve a elipse ajustada e a fração de ângulos que confirmaram a borda.
        """
        suave = cv2.GaussianBlur(canal, (5, 5), 0).astype(np.float32)
        altura, largura = suave.shape
        pontos = []
        raios = np.arange(raio * 0.8, raio * 1.2, 1.0)
        for t in np.linspace(0, 2 * np.pi, n, endpoint=False):
            xs = x + raios * np.cos(t)
            ys = y + raios * np.sin(t)
            ok = (xs >= 1) & (xs < largura - 1) & (ys >= 1) & (ys < altura - 1)
            if ok.sum() < 10:
                continue
            perfil = cv2.remap(
                suave,
                xs[ok].astype(np.float32).reshape(1, -1),
                ys[ok].astype(np.float32).reshape(1, -1),
                cv2.INTER_LINEAR,
            )[0]
            queda = perfil[:-4] - perfil[4:]
            i = int(np.argmax(queda))
            if queda[i] < 12:
                continue
            r = raios[ok][i + 2]
            pontos.append((x + r * np.cos(t), y + r * np.sin(t)))

        if len(pontos) < 60:
            return None

        pts = np.array(pontos, np.float32)
        # Descarta pontos longe da elipse (sombras, objetos encostados no disco)
        for _ in range(3):
            (ex, ey), (eixo_a, eixo_b), ang = cv2.fitEllipse(pts)
            c, s = np.cos(np.deg2rad(ang)), np.sin(np.deg2rad(ang))
            dx, dy = pts[:, 0] - ex, pts[:, 1] - ey
            u = (dx * c + dy * s) / (eixo_a / 2)
            v = (-dx * s + dy * c) / (eixo_b / 2)
            residuo = np.abs(np.sqrt(u * u + v * v) - 1)
            if (residuo < 0.02).sum() > 40:
                pts = pts[residuo < 0.02]
        return cv2.fitEllipse(pts), len(pts) / n

    @staticmethod
    def _contraste_borda(canal: NDArray[np.uint8], elipse: Elipse) -> float:
        """Brilho logo dentro da elipse menos brilho logo fora."""
        (ex, ey), (eixo_a, eixo_b), ang = elipse
        if min(eixo_a, eixo_b) / max(eixo_a, eixo_b) < 0.6:
            return -1.0
        dentro = np.zeros(canal.shape, np.uint8)
        fora = np.zeros(canal.shape, np.uint8)
        cv2.ellipse(dentro, ((ex, ey), (eixo_a * 0.97, eixo_b * 0.97), ang), 255, -1)
        cv2.ellipse(dentro, ((ex, ey), (eixo_a * 0.80, eixo_b * 0.80), ang), 0, -1)
        cv2.ellipse(fora, ((ex, ey), (eixo_a * 1.15, eixo_b * 1.15), ang), 255, -1)
        cv2.ellipse(fora, ((ex, ey), (eixo_a * 1.03, eixo_b * 1.03), ang), 0, -1)
        if cv2.countNonZero(fora) < 100:
            return -1.0
        return float(cv2.mean(canal, dentro)[0] - cv2.mean(canal, fora)[0])

    def detectar_borda_disco(self, imagem_bgr: NDArray[np.uint8]) -> Elipse:
        """
        Elipse da borda do disco na foto.

        Gera candidatos (Hough + contornos) nos canais de brancura e de cinza,
        refina cada um pela borda real e escolhe o de maior
        contraste dentro/fora × suporte de borda².
        """
        brancura = _canal_brancura(imagem_bgr)
        cinza = cv2.cvtColor(imagem_bgr, cv2.COLOR_BGR2GRAY)
        candidatos = (
            self._candidatos_hough(brancura) + self._candidatos_hough(cinza)
            + self._candidatos_contorno(brancura) + self._candidatos_contorno(cinza)
        )

        melhor: Elipse | None = None
        melhor_pontuacao = 0.0
        for x, y, raio in candidatos:
            for base in (brancura, cinza):
                refinado = self._refinar_elipse(base, x, y, raio)
                if refinado is None:
                    continue
                elipse, suporte = refinado
                contraste = max(
                    self._contraste_borda(brancura, elipse),
                    self._contraste_borda(cinza, elipse),
                    0.0,
                )
                pontuacao = contraste * suporte ** 2
                if pontuacao > melhor_pontuacao:
                    melhor, melhor_pontuacao = elipse, pontuacao

        if melhor is None:
            raise FuroNaoEncontradoError(
                "Não foi possível localizar o disco na foto. Fotografe o disco inteiro, "
                "de cima, sobre um fundo escuro e sem reflexos."
            )
        return melhor

    # ------------------------------------------------ perspectiva e centro real

    def _homografia(self, elipse: Elipse, centro: tuple[float, float], raio: int) -> NDArray[np.float64]:
        """
        Homografia que leva a elipse da borda a um círculo de raio `raio`
        centrado em (raio, raio), com `centro` (ponto da foto) indo para o meio.

        A reta polar do centro em relação à cônica da borda é a imagem da
        reta no infinito; mandá-la de volta ao infinito remove a perspectiva,
        e um afim final transforma a elipse restante em círculo.
        """
        l = _conica(elipse) @ np.array([centro[0], centro[1], 1.0])
        h_afim = np.array([[1, 0, 0], [0, 1, 0], [l[0] / l[2], l[1] / l[2], 1]])

        pts = cv2.perspectiveTransform(_pontos_elipse(elipse).reshape(-1, 1, 2), h_afim).reshape(-1, 2)
        (_, _), (eixo_a, eixo_b), ang = cv2.fitEllipse(pts.astype(np.float32))
        t = np.deg2rad(ang)
        rot = np.array([[np.cos(t), -np.sin(t)], [np.sin(t), np.cos(t)]])
        m2 = rot @ np.diag([2 * raio / eixo_a, 2 * raio / eixo_b]) @ rot.T

        centro_h = cv2.perspectiveTransform(
            np.array([[[centro[0], centro[1]]]], np.float64), h_afim
        )[0, 0]
        afim = np.eye(3)
        afim[:2, :2] = m2
        afim[:2, 2] = np.array([raio, raio]) - m2 @ centro_h
        return afim @ h_afim

    def _nitidez_aneis(
        self,
        cinza: NDArray[np.uint8],
        elipse: Elipse,
        centro: tuple[float, float],
    ) -> float:
        """Anéis impressos concêntricos ⇒ perfil radial médio com vales nítidos."""
        raio = RAIO_BUSCA_CENTRO_PX
        h = self._homografia(elipse, centro, raio)
        retificada = cv2.warpPerspective(cinza, h, (2 * raio, 2 * raio), flags=cv2.INTER_LINEAR, borderValue=255)
        polar = _desdobrar_polar(retificada, raio, 360).astype(np.float32)
        perfil = np.median(polar[:, int(0.55 * raio):int(0.97 * raio)], axis=0)
        return float(np.abs(np.diff(perfil)).sum()) * (RAIO_RETIFICADO_PX / raio)

    def encontrar_centro_real(
        self,
        cinza: NDArray[np.uint8],
        elipse: Elipse,
    ) -> tuple[tuple[float, float], float]:
        """
        Centro projetado do disco na foto.

        Em foto inclinada o centro da elipse da borda NÃO é o centro do disco;
        busca local (compass search) pelo ponto que maximiza a nitidez dos anéis.
        """
        (ex, ey), (eixo_a, eixo_b), _ = elipse
        cx, cy = ex, ey
        melhor = self._nitidez_aneis(cinza, elipse, (cx, cy))
        passo = (eixo_a + eixo_b) / 4 * 0.08
        direcoes = ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, -1), (1, -1), (-1, 1))
        while passo > 0.5:
            proximo = None
            for dx, dy in direcoes:
                ponto = (cx + dx * passo, cy + dy * passo)
                nitidez = self._nitidez_aneis(cinza, elipse, ponto)
                if nitidez > melhor:
                    melhor, proximo = nitidez, ponto
            if proximo is None:
                passo /= 2
            else:
                cx, cy = proximo
        return (cx, cy), melhor

    # ------------------------------------------------------------- orientação

    def orientar(self, polar: NDArray[np.uint8]) -> tuple[int, float]:
        """
        Linha polar correspondente a 00:00.

        O disco tem um arco verde grosso na borda indo das 12h às 24h; a janela
        de 12 h com mais verde começa às 12h e termina à meia-noite.
        Devolve (linha da meia-noite, pixels verdes por linha na metade do arco).
        """
        r = self.raio_retificado
        faixa = polar[:, int(FAIXA_ARCO_VERDE[0] * r):int(FAIXA_ARCO_VERDE[1] * r)]
        verde = _mascara_verde(faixa).sum(1).astype(np.float64)
        verde = np.clip(verde - np.median(verde), 0, None)  # tira a linha fina que dá a volta toda
        meio = MINUTOS_NO_DIA // 2
        soma = np.convolve(np.r_[verde, verde], np.ones(meio), "valid")[:MINUTOS_NO_DIA]
        inicio_arco = int(np.argmax(soma))
        return (inicio_arco + meio) % MINUTOS_NO_DIA, float(soma[inicio_arco] / meio)

    def calibrar_escala(self, polar: NDArray[np.uint8]) -> tuple[float, float]:
        """
        Ajusta a escala radial pelos anéis tracejados de velocidade.

        Devolve (escala, nota). Nota = resposta média de escuridão nos raios
        esperados dos anéis / mediana da faixa; ~1 significa que os anéis não
        estão onde deveriam (disco mal detectado ou foto muito distorcida).
        """
        r = self.raio_retificado
        cinza = cv2.cvtColor(polar, cv2.COLOR_BGR2GRAY).astype(np.float32)
        perfil = np.clip(cv2.GaussianBlur(cinza, (0, 0), 8) - cinza, 0, None).mean(0)
        base = max(float(np.median(perfil[int(0.55 * r):int(0.99 * r)])), 1e-6)
        aneis = np.array(ANEIS_ESCALA_VELOCIDADE)

        melhor_resposta, melhor_escala = -1.0, 1.0
        for escala in np.arange(ESCALA_RADIAL_MIN_MAX[0], ESCALA_RADIAL_MIN_MAX[1] + 1e-9, 0.0025):
            raios = np.round(aneis * escala * r).astype(int)
            resposta = float(np.mean([perfil[x - 2:x + 3].max() for x in raios]))
            if resposta > melhor_resposta:
                melhor_resposta, melhor_escala = resposta, float(escala)
        return melhor_escala, melhor_resposta / base

    # --------------------------------------------------------------- pipeline

    def processar(self, dados_imagem: bytes) -> ResultadoProcessamento:
        imagem_bgr = self._decodificar_bgr(dados_imagem)
        cinza = cv2.cvtColor(imagem_bgr, cv2.COLOR_BGR2GRAY)
        avisos: list[str] = []

        # 1) Borda do disco (elipse na foto)
        elipse = self.detectar_borda_disco(imagem_bgr)

        # 2) Centro real + homografia (corrige a perspectiva da foto)
        centro, _ = self.encontrar_centro_real(cinza, elipse)
        r = self.raio_retificado
        h = self._homografia(elipse, centro, r)
        retificada = cv2.warpPerspective(imagem_bgr, h, (2 * r, 2 * r), flags=cv2.INTER_CUBIC, borderValue=(0, 0, 0))

        # 3) Desdobramento com 1 linha por minuto, orientado para 00:00 na linha 0
        polar = _desdobrar_polar(retificada, r, MINUTOS_NO_DIA)

        # 4) Validação + autocalibração pelos anéis de velocidade impressos
        escala, nota = self.calibrar_escala(polar)
        if nota < NOTA_ANEIS_MINIMA:
            raise FuroNaoEncontradoError(
                "O disco não foi reconhecido com segurança: a escala de velocidade "
                "impressa não ficou alinhada. Fotografe de cima, com o disco inteiro "
                "sobre um fundo escuro (não use mesa branca ou madeira clara) e sem reflexos."
            )
        if nota < NOTA_ANEIS_CONFIAVEL:
            avisos.append(
                "Leitura com baixa confiança: a escala impressa ficou pouco nítida. "
                "Confira a imagem desdobrada; se os anéis estiverem ondulados, tire outra foto."
            )

        meia_noite, verde_arco = self.orientar(polar)
        if verde_arco < VERDE_MINIMO_ARCO:
            avisos.append(
                "Orientação do disco incerta: o arco verde 12h–24h da borda não ficou "
                "nítido. Os horários podem estar deslocados."
            )
        polar = np.roll(polar, -meia_noite, axis=0)

        # 5) Imagem de debug: x = minuto do dia, y = raio (borda no topo)
        c0, c1 = int(FAIXA_IMAGEM_DEBUG[0] * r), int(FAIXA_IMAGEM_DEBUG[1] * r)
        desdobrada = cv2.rotate(polar[:, c0:c1], cv2.ROTATE_90_COUNTERCLOCKWISE)

        altura, largura = desdobrada.shape[:2]
        (_, _), (eixo_a, eixo_b), _ = elipse
        return ResultadoProcessamento(
            imagem_cinza=cv2.cvtColor(retificada, cv2.COLOR_BGR2GRAY),
            circulo=CirculoDetectado(
                centro_x=int(round(centro[0])),
                centro_y=int(round(centro[1])),
                raio=int(round((eixo_a + eixo_b) / 4)),
            ),
            imagem_desdobrada=desdobrada,
            largura_px=int(largura),
            altura_px=int(altura),
            polar_orientado=polar,
            escala_radial=round(escala, 4),
            nota_aneis=round(nota, 2),
            avisos=avisos,
        )

    # ---------------------------------------------------------- curva de sinal

    @staticmethod
    def _minutos_para_hora(minutos_totais: int) -> str:
        minutos_norm = minutos_totais % MINUTOS_NO_DIA
        return f"{minutos_norm // 60:02d}:{minutos_norm % 60:02d}"

    @staticmethod
    def _fechar_lacunas(em_movimento: NDArray[np.bool_], lacuna_max: int) -> NDArray[np.bool_]:
        """Preenche buracos curtos na barra de atividade (falhas de tinta/reflexo)."""
        resultado = em_movimento.copy()
        indices = np.nonzero(em_movimento)[0]
        for a, b in zip(indices[:-1], indices[1:]):
            if 1 < b - a <= lacuna_max:
                resultado[a:b] = True
        return resultado

    def detectar_movimento(
        self,
        polar_orientado: NDArray[np.uint8],
        escala_radial: float = 1.0,
    ) -> NDArray[np.bool_]:
        """Minutos em que a barra de atividade (~0,51 R) está marcada."""
        r = self.raio_retificado
        v = cv2.cvtColor(polar_orientado, cv2.COLOR_BGR2HSV)[..., 2].astype(np.float32)
        escuridao = cv2.GaussianBlur(v, (0, 0), 12) - v
        a0, a1 = int(FAIXA_ATIVIDADE[0] * escala_radial * r), int(FAIXA_ATIVIDADE[1] * escala_radial * r)
        marcado = (escuridao[:, a0:a1] > CONTRASTE_TINTA_ATIVIDADE).mean(1) > FRACAO_ATIVIDADE_MOVIMENTO
        return self._fechar_lacunas(marcado, LACUNA_MAXIMA_ATIVIDADE_MIN)

    def extrair_curva_velocidade(
        self,
        resultado: ResultadoProcessamento,
        janela_media_movel: int = 3,
    ) -> list[PontoVelocidade]:
        """
        Curva de 1440 pontos (1 por minuto). Velocidade = mediana radial do traço
        do estilete, lida só nos minutos com movimento; minutos parados = 0.
        """
        polar = resultado.polar_orientado
        r = self.raio_retificado
        if polar is None or polar.ndim != 3 or polar.shape[0] != MINUTOS_NO_DIA:
            raise ImagemInvalidaError("Disco desdobrado inválido para extrair a curva.")

        k = resultado.escala_radial
        em_movimento = self.detectar_movimento(polar, k)

        hsv = cv2.cvtColor(polar, cv2.COLOR_BGR2HSV)
        v = hsv[..., 2].astype(np.float32)
        escuridao = cv2.GaussianBlur(v, (0, 0), 12) - v
        a0, a1 = int(FAIXA_TRACO_VELOCIDADE[0] * k * r), int(min(FAIXA_TRACO_VELOCIDADE[1] * k, 0.99) * r)
        tinta = escuridao[:, a0:a1] > CONTRASTE_TINTA_VELOCIDADE
        tinta &= ~_mascara_verde(polar[:, a0:a1])

        # Raios com impressão fixa (linhas tracejadas, números): escuros mesmo parado
        if (~em_movimento).sum() > 60:
            impresso = tinta[~em_movimento].mean(0) > FRACAO_IMPRESSO_FIXO
            tinta[:, impresso] = False

        velocidades = np.zeros(MINUTOS_NO_DIA, dtype=np.float64)
        for minuto in np.nonzero(em_movimento)[0]:
            idx = np.nonzero(tinta[minuto])[0]
            if idx.size >= 3:
                fracao = (np.median(idx) + a0) / (r * k)
                velocidades[minuto] = (fracao - FRACAO_RAIO_0_KMH) * KMH_POR_FRACAO_RAIO

        if janela_media_movel > 1:
            suave = np.convolve(velocidades, np.ones(janela_media_movel) / janela_media_movel, "same")
            velocidades = np.where(em_movimento, suave, 0.0)

        velocidades = np.clip(velocidades, 0.0, float(self.velocidade_maxima_kmh))
        return [
            {
                "hora": self._minutos_para_hora(minuto),
                "velocidade_kmh": 0.0 if vel < 0.5 else round(float(vel), 1),
            }
            for minuto, vel in enumerate(velocidades)
        ]

    # -------------------------------------------------------------------- debug

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
