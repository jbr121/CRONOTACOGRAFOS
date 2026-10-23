"""
Análise de viagem e detecção de infrações a partir da curva de velocidade.

Fase de Tratamento de Ruído / Infrações (PGI):
- Excesso de velocidade acima do limite configurável
- Paradas prolongadas (velocidade zero por mais de 10 minutos)
- Distância pela pista do odômetro (zigue-zague), não pela integração da curva
"""

from __future__ import annotations

from typing import Final, Literal, TypedDict


MINUTOS_PARADA_PROLONGADA: Final[int] = 10
LIMITE_VELOCIDADE_PADRAO_KMH: Final[float] = 80.0
TOLERANCIA_PARADO_KMH: Final[float] = 0.5
# Picos de 1 minuto (sujeira) não viram infração
MINUTOS_MINIMOS_EXCESSO: Final[int] = 2


class PontoCurva(TypedDict):
    """Formato esperado de cada ponto da curva de velocidade."""

    hora: str
    velocidade_kmh: float


class InfracaoExcesso(TypedDict):
    """Evento contínuo de velocidade acima do limite."""

    tipo: Literal["excesso_velocidade"]
    hora_inicio: str
    hora_fim: str
    velocidade_maxima_kmh: float
    duracao_minutos: int


class InfracaoParada(TypedDict):
    """Período de velocidade zero (ou quase) por tempo prolongado."""

    tipo: Literal["parada_prolongada"]
    hora_inicio: str
    hora_fim: str
    duracao_minutos: int


Infracao = InfracaoExcesso | InfracaoParada


class ResumoViagem(TypedDict):
    """Indicadores agregados da jornada lida no disco."""

    distancia_estimada_km: float
    velocidade_maxima_kmh: float
    velocidade_media_kmh: float
    limite_velocidade_kmh: float
    origem_distancia: str
    total_pontos: int
    total_infracoes: int
    total_excessos: int
    total_paradas_prolongadas: int
    minutos_em_movimento: int
    minutos_excesso: int


class ResultadoAnalise(TypedDict):
    """Saída completa do AnalisadorDisco."""

    resumo: ResumoViagem
    infracoes: list[Infracao]


class AnalisadorDisco:
    """
    Interpreta a curva tempo × velocidade e gera alertas/infrações.

    Premissa da Fase 1: cada ponto da curva representa ~1 minuto
    (desdobramento com 1440 colunas ≈ 24 h × 60 min).
    """

    def __init__(
        self,
        minutos_parada_prolongada: int = MINUTOS_PARADA_PROLONGADA,
        tolerancia_parado_kmh: float = TOLERANCIA_PARADO_KMH,
        minutos_minimos_excesso: int = MINUTOS_MINIMOS_EXCESSO,
    ) -> None:
        if minutos_parada_prolongada <= 0:
            raise ValueError("minutos_parada_prolongada deve ser positivo.")
        if tolerancia_parado_kmh < 0:
            raise ValueError("tolerancia_parado_kmh não pode ser negativa.")
        if minutos_minimos_excesso < 1:
            raise ValueError("minutos_minimos_excesso deve ser >= 1.")

        self.minutos_parada_prolongada = minutos_parada_prolongada
        self.tolerancia_parado_kmh = tolerancia_parado_kmh
        self.minutos_minimos_excesso = minutos_minimos_excesso

    def analisar_infracoes(
        self,
        curva_velocidade: list[dict[str, object]] | list[PontoCurva],
        limite_velocidade: float = LIMITE_VELOCIDADE_PADRAO_KMH,
        distancia_km: float | None = None,
    ) -> ResultadoAnalise:
        """
        Analisa a curva tratada e devolve resumo + lista de infrações.

        Parâmetros:
        - curva_velocidade: lista no formato [{"hora": "00:00", "velocidade_kmh": 0.0}, ...]
        - limite_velocidade: limiar em km/h para marcar excesso (padrão 80.0)
        - distancia_km: se informada (pista do odômetro), substitui a integração
          da curva de velocidade — que infla km quando há picos de ruído.
        """
        if limite_velocidade <= 0:
            raise ValueError("limite_velocidade deve ser positivo.")

        pontos = self._normalizar_curva(curva_velocidade)
        if not pontos:
            return {
                "resumo": {
                    "distancia_estimada_km": 0.0,
                    "velocidade_maxima_kmh": 0.0,
                    "velocidade_media_kmh": 0.0,
                    "limite_velocidade_kmh": float(limite_velocidade),
                    "origem_distancia": "indisponivel",
                    "total_pontos": 0,
                    "total_infracoes": 0,
                    "total_excessos": 0,
                    "total_paradas_prolongadas": 0,
                    "minutos_em_movimento": 0,
                    "minutos_excesso": 0,
                },
                "infracoes": [],
            }

        excessos = self._detectar_excessos(pontos, limite_velocidade)
        paradas = self._detectar_paradas_prolongadas(pontos)
        infracoes: list[Infracao] = [*excessos, *paradas]

        if distancia_km is not None and distancia_km >= 0:
            distancia = float(distancia_km)
            origem_distancia = "odometro"
        else:
            # Último recurso: não usa a curva ruidosa como fonte primária
            distancia = 0.0
            origem_distancia = "indisponivel"

        velocidades = [p["velocidade_kmh"] for p in pontos]
        velocidade_maxima = max(velocidades)
        em_movimento = [v for v in velocidades if v > self.tolerancia_parado_kmh]
        velocidade_media = (
            sum(em_movimento) / len(em_movimento) if em_movimento else 0.0
        )
        minutos_excesso = sum(int(e["duracao_minutos"]) for e in excessos)

        resumo: ResumoViagem = {
            "distancia_estimada_km": round(distancia, 2),
            "velocidade_maxima_kmh": round(velocidade_maxima, 1),
            "velocidade_media_kmh": round(velocidade_media, 1),
            "limite_velocidade_kmh": float(limite_velocidade),
            "origem_distancia": origem_distancia,
            "total_pontos": len(pontos),
            "total_infracoes": len(infracoes),
            "total_excessos": len(excessos),
            "total_paradas_prolongadas": len(paradas),
            "minutos_em_movimento": len(em_movimento),
            "minutos_excesso": minutos_excesso,
        }

        return {"resumo": resumo, "infracoes": infracoes}

    def _normalizar_curva(
        self,
        curva_velocidade: list[dict[str, object]] | list[PontoCurva],
    ) -> list[PontoCurva]:
        """Valida e tipa os pontos recebidos da extração de imagem."""
        pontos: list[PontoCurva] = []
        for item in curva_velocidade:
            hora = item.get("hora")
            velocidade = item.get("velocidade_kmh")
            if not isinstance(hora, str):
                raise TypeError("Cada ponto deve conter 'hora' (str).")
            if not isinstance(velocidade, (int, float)):
                raise TypeError("Cada ponto deve conter 'velocidade_kmh' (número).")
            pontos.append(
                {
                    "hora": hora,
                    "velocidade_kmh": float(velocidade),
                }
            )
        return pontos

    def _esta_parado(self, velocidade_kmh: float) -> bool:
        """Considera parado velocidades nulas ou residualmente baixas após suavização."""
        return velocidade_kmh <= self.tolerancia_parado_kmh

    def _detectar_excessos(
        self,
        pontos: list[PontoCurva],
        limite_velocidade: float,
    ) -> list[InfracaoExcesso]:
        """Agrupa segmentos consecutivos com velocidade acima do limite."""
        infracoes: list[InfracaoExcesso] = []
        inicio: int | None = None
        maxima = 0.0

        def fechar(fim_exclusivo: int) -> None:
            nonlocal inicio, maxima
            if inicio is None:
                return
            duracao = fim_exclusivo - inicio
            if duracao < self.minutos_minimos_excesso:
                inicio = None
                maxima = 0.0
                return
            infracoes.append(
                {
                    "tipo": "excesso_velocidade",
                    "hora_inicio": pontos[inicio]["hora"],
                    "hora_fim": pontos[fim_exclusivo - 1]["hora"],
                    "velocidade_maxima_kmh": round(maxima, 1),
                    "duracao_minutos": fim_exclusivo - inicio,
                }
            )
            inicio = None
            maxima = 0.0

        for indice, ponto in enumerate(pontos):
            velocidade = ponto["velocidade_kmh"]
            if velocidade > limite_velocidade:
                if inicio is None:
                    inicio = indice
                    maxima = velocidade
                else:
                    maxima = max(maxima, velocidade)
            else:
                fechar(indice)

        fechar(len(pontos))
        return infracoes

    def _detectar_paradas_prolongadas(
        self,
        pontos: list[PontoCurva],
    ) -> list[InfracaoParada]:
        """
        Identifica blocos consecutivos parados por mais de N minutos.

        Cada ponto ≈ 1 minuto → duração = quantidade de pontos no bloco.
        """
        infracoes: list[InfracaoParada] = []
        inicio: int | None = None

        def fechar(fim_exclusivo: int) -> None:
            nonlocal inicio
            if inicio is None:
                return
            duracao = fim_exclusivo - inicio
            if duracao <= self.minutos_parada_prolongada:
                inicio = None
                return
            # Ignora pátio no começo/fim do disco (caminhão já parado)
            if inicio == 0 or fim_exclusivo >= len(pontos):
                inicio = None
                return
            infracoes.append(
                {
                    "tipo": "parada_prolongada",
                    "hora_inicio": pontos[inicio]["hora"],
                    "hora_fim": pontos[fim_exclusivo - 1]["hora"],
                    "duracao_minutos": duracao,
                }
            )
            inicio = None

        for indice, ponto in enumerate(pontos):
            if self._esta_parado(ponto["velocidade_kmh"]):
                if inicio is None:
                    inicio = indice
            else:
                fechar(indice)

        fechar(len(pontos))
        return infracoes

    def _calcular_distancia_km(self, pontos: list[PontoCurva]) -> float:
        """
        Integração velocidade × tempo (NÃO usada como km oficial).

        Mantida só como referência interna. O laudo usa a pista do odômetro.
        """
        dt_horas = 1.0 / 60.0
        return float(sum(p["velocidade_kmh"] * dt_horas for p in pontos))
