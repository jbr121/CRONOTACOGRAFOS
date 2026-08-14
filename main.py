"""
API FastAPI — Leitor de Discos de Cronotacógrafo Analógico.

Serve a SPA, processa discos, persiste leituras e expõe o histórico de viagens.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, File, Form, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, selectinload

from core.analisador import AnalisadorDisco
from core.database import Infracao, LeituraViagem, criar_tabelas, get_db
from core.gerador_pdf import GeradorLaudoPDF
from core.processador_imagem import (
    ErroProcessamentoDisco,
    FuroNaoEncontradoError,
    ImagemInvalidaError,
    LeitorDisco,
)

RAIZ_PROJETO = Path(__file__).resolve().parent
PASTA_TEMP = RAIZ_PROJETO / "temp"
PASTA_STATIC = RAIZ_PROJETO / "static"
ARQUIVO_INDEX = PASTA_STATIC / "index.html"

PASTA_TEMP.mkdir(parents=True, exist_ok=True)
PASTA_STATIC.mkdir(parents=True, exist_ok=True)

app = FastAPI(
    title="Leitor de Discos de Cronotacógrafo",
    description=(
        "Protótipo (PGI): análise de discos, histórico, laudos PDF e "
        "tratamento robusto de falhas (Sprint 5)."
    ),
    version="0.8.0",
)

# Garante o schema do banco ao subir a API
criar_tabelas()

leitor = LeitorDisco()
analisador = AnalisadorDisco()
gerador_pdf = GeradorLaudoPDF(limite_velocidade_kmh=80.0)

AMOSTRAS_CURVA_JSON: int = 10
LIMITE_VELOCIDADE_PADRAO_KMH: float = 80.0

# Mapa em memória: viagem_id → caminho da imagem desdobrada (válido na sessão da API)
IMAGENS_DEBUG_POR_VIAGEM: dict[int, str] = {}


def _json_erro(status_code: int, mensagem: str, codigo: str) -> JSONResponse:
    """Resposta de erro padronizada em português para a SPA."""
    return JSONResponse(
        status_code=status_code,
        content={
            "sucesso": False,
            "erro": codigo,
            "detail": mensagem,
            "mensagem": mensagem,
        },
    )


@app.exception_handler(ImagemInvalidaError)
async def tratar_imagem_invalida(
    _request: Request,
    exc: ImagemInvalidaError,
) -> JSONResponse:
    """HTTP 400 — arquivo de imagem inválido ou inadequado."""
    return _json_erro(status.HTTP_400_BAD_REQUEST, str(exc), "imagem_invalida")


@app.exception_handler(FuroNaoEncontradoError)
async def tratar_furo_nao_encontrado(
    _request: Request,
    exc: FuroNaoEncontradoError,
) -> JSONResponse:
    """HTTP 422 — centro do disco não detectado."""
    return _json_erro(
        status.HTTP_422_UNPROCESSABLE_ENTITY,
        str(exc),
        "furo_nao_encontrado",
    )


@app.exception_handler(ErroProcessamentoDisco)
async def tratar_erro_processamento(
    _request: Request,
    exc: ErroProcessamentoDisco,
) -> JSONResponse:
    """HTTP 422 — demais falhas do pipeline OpenCV."""
    return _json_erro(
        status.HTTP_422_UNPROCESSABLE_ENTITY,
        str(exc),
        "erro_processamento",
    )


@app.exception_handler(SQLAlchemyError)
async def tratar_erro_banco(
    _request: Request,
    exc: SQLAlchemyError,
) -> JSONResponse:
    """HTTP 422 — falha de persistência/consulta no SQLite."""
    return _json_erro(
        status.HTTP_422_UNPROCESSABLE_ENTITY,
        "Falha ao acessar o banco de dados. Tente novamente. "
        f"Detalhe técnico: {exc.__class__.__name__}",
        "erro_banco",
    )


@app.exception_handler(Exception)
async def tratar_erro_generico(
    _request: Request,
    exc: Exception,
) -> JSONResponse:
    """HTTP 500 — rede de segurança; preserva HTTPException."""
    if isinstance(exc, HTTPException):
        detail = exc.detail
        mensagem = detail if isinstance(detail, str) else str(detail)
        return _json_erro(int(exc.status_code), mensagem, "http_error")

    return _json_erro(
        status.HTTP_500_INTERNAL_SERVER_ERROR,
        f"Erro interno inesperado: {exc}",
        "erro_interno",
    )


@app.get("/")
async def raiz() -> FileResponse:
    """Entrega a interface visual (SPA) do protótipo."""
    if not ARQUIVO_INDEX.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Arquivo static/index.html não encontrado.",
        )
    return FileResponse(ARQUIVO_INDEX, media_type="text/html")


@app.get("/api/health")
async def health() -> dict[str, str]:
    """Health check da API."""
    return {
        "projeto": "Leitor de Discos de Cronotacógrafo",
        "fase": "Sprint 5 - Robustez e apresentação",
        "status": "ok",
    }


@app.get("/api/v1/viagens")
async def listar_viagens(
    placa: str | None = Query(default=None, description="Filtro opcional por placa"),
    db: Session = Depends(get_db),
) -> JSONResponse:
    """
    Lista viagens persistidas, da mais recente para a mais antiga.

    Query opcional:
    - placa: filtra por coincidência parcial (case-insensitive)
    """
    try:
        # Subconsulta: total de infrações por viagem
        contagem_infracoes = (
            select(
                Infracao.viagem_id.label("viagem_id"),
                func.count(Infracao.id).label("total_infracoes"),
            )
            .group_by(Infracao.viagem_id)
            .subquery()
        )

        consulta = (
            select(
                LeituraViagem.id,
                LeituraViagem.placa_veiculo,
                LeituraViagem.data_processamento,
                LeituraViagem.distancia_total_km,
                LeituraViagem.velocidade_maxima,
                func.coalesce(contagem_infracoes.c.total_infracoes, 0).label(
                    "total_infracoes"
                ),
            )
            .outerjoin(
                contagem_infracoes,
                LeituraViagem.id == contagem_infracoes.c.viagem_id,
            )
            .order_by(LeituraViagem.data_processamento.desc())
        )

        if placa and placa.strip():
            termo = f"%{placa.strip().upper()}%"
            consulta = consulta.where(LeituraViagem.placa_veiculo.like(termo))

        linhas = db.execute(consulta).all()
    except Exception as erro:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Falha ao consultar o histórico: {erro}",
        ) from erro

    viagens: list[dict[str, Any]] = []
    for linha in linhas:
        data = linha.data_processamento
        viagens.append(
            {
                "id": int(linha.id),
                "placa_veiculo": str(linha.placa_veiculo),
                "data_processamento": data.isoformat(sep=" ", timespec="seconds")
                if isinstance(data, datetime)
                else str(data),
                "distancia_total_km": float(linha.distancia_total_km),
                "velocidade_maxima": float(linha.velocidade_maxima),
                "total_infracoes": int(linha.total_infracoes),
            }
        )

    return JSONResponse(
        content={"total": len(viagens), "viagens": viagens},
        status_code=status.HTTP_200_OK,
    )


@app.get("/api/v1/viagens/{viagem_id}")
async def detalhar_viagem(
    viagem_id: int,
    db: Session = Depends(get_db),
) -> JSONResponse:
    """
    Retorna o resumo de uma viagem e a lista detalhada de infrações.

    Responde HTTP 404 se o ID não existir.
    """
    try:
        viagem = db.execute(
            select(LeituraViagem)
            .options(selectinload(LeituraViagem.infracoes))
            .where(LeituraViagem.id == viagem_id)
        ).scalar_one_or_none()
    except Exception as erro:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Falha ao buscar a viagem: {erro}",
        ) from erro

    if viagem is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Viagem {viagem_id} não encontrada.",
        )

    infracoes_json: list[dict[str, Any]] = []
    for item in viagem.infracoes:
        infracoes_json.append(
            {
                "id": int(item.id),
                "tipo_infracao": str(item.tipo_infracao),
                # Alias compatível com o renderer da SPA (upload recente)
                "tipo": str(item.tipo_infracao),
                "hora_inicio": str(item.hora_inicio),
                "hora_fim": str(item.hora_fim),
                "velocidade_registrada": (
                    float(item.velocidade_registrada)
                    if item.velocidade_registrada is not None
                    else None
                ),
                "velocidade_maxima_kmh": (
                    float(item.velocidade_registrada)
                    if item.velocidade_registrada is not None
                    else 0.0
                ),
            }
        )

    data = viagem.data_processamento
    payload: dict[str, Any] = {
        "id": int(viagem.id),
        "placa_veiculo": str(viagem.placa_veiculo),
        "data_processamento": data.isoformat(sep=" ", timespec="seconds")
        if isinstance(data, datetime)
        else str(data),
        "distancia_total_km": float(viagem.distancia_total_km),
        "velocidade_maxima": float(viagem.velocidade_maxima),
        "total_infracoes": len(infracoes_json),
        "resumo_viagem": {
            "distancia_estimada_km": float(viagem.distancia_total_km),
            "velocidade_maxima_kmh": float(viagem.velocidade_maxima),
            # Média não é persistida no banco; a SPA exibe "—" quando ausente
            "velocidade_media_kmh": None,
            "limite_velocidade_kmh": LIMITE_VELOCIDADE_PADRAO_KMH,
            "total_infracoes": len(infracoes_json),
        },
        "infracoes": infracoes_json,
    }

    return JSONResponse(content=payload, status_code=status.HTTP_200_OK)


@app.get("/api/v1/viagens/{viagem_id}/pdf")
async def gerar_laudo_pdf(
    viagem_id: int,
    db: Session = Depends(get_db),
) -> Response:
    """
    Gera e devolve o laudo PDF de auditoria da viagem informada.

    Content-Disposition: inline — o navegador pode abrir em nova aba.
    """
    try:
        viagem = db.execute(
            select(LeituraViagem)
            .options(selectinload(LeituraViagem.infracoes))
            .where(LeituraViagem.id == viagem_id)
        ).scalar_one_or_none()
    except Exception as erro:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Falha ao buscar a viagem para o laudo: {erro}",
        ) from erro

    if viagem is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Viagem {viagem_id} não encontrada.",
        )

    caminho_imagem = IMAGENS_DEBUG_POR_VIAGEM.get(viagem_id)
    # Se o mapa em memória não tiver a imagem (API reiniciada), tenta o PNG mais recente em temp/
    if not caminho_imagem or not Path(caminho_imagem).is_file():
        candidatos = sorted(
            PASTA_TEMP.glob("*.png"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        caminho_imagem = str(candidatos[0]) if candidatos else None

    try:
        pdf_bytes = gerador_pdf.gerar_pdf_viagem(
            viagem=viagem,
            infracoes=list(viagem.infracoes),
            caminho_imagem_desdobrada=caminho_imagem,
        )
    except Exception as erro:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Falha ao gerar o PDF: {erro}",
        ) from erro

    placa_arquivo = "".join(
        c if c.isalnum() or c in ("-", "_") else "_" for c in viagem.placa_veiculo
    )
    nome_arquivo = f"laudo_{placa_arquivo}_{viagem.id}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="{nome_arquivo}"',
        },
    )


@app.post("/upload-disco/")
async def upload_disco(
    arquivo: UploadFile = File(...),
    placa_veiculo: str = Form(...),
    db: Session = Depends(get_db),
) -> JSONResponse:
    """
    Recebe imagem + placa, processa o disco, salva a viagem/infrações no SQLite
    e devolve o JSON completo para a SPA.
    """
    placa = placa_veiculo.strip().upper()
    if not placa:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Informe a placa do veículo.",
        )

    content_type = (arquivo.content_type or "").lower()
    if not content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Envie um arquivo de imagem (PNG, JPEG, etc.).",
        )

    dados = await arquivo.read()
    if not dados:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="O arquivo enviado está vazio.",
        )

    try:
        resultado = leitor.processar(dados)

        nome_origem = Path(arquivo.filename or "disco").stem
        caminho_salvo = leitor.salvar_imagem_desdobrada(
            resultado.imagem_desdobrada,
            nome_base=nome_origem,
        )

        curva_tratada = leitor.extrair_curva_velocidade(resultado.imagem_desdobrada)
        analise = analisador.analisar_infracoes(
            curva_tratada,
            limite_velocidade=LIMITE_VELOCIDADE_PADRAO_KMH,
        )
    except ErroProcessamentoDisco:
        # Deixa o exception handler global formatar 400/422 em português
        raise

    resumo = analise["resumo"]
    infracoes_detectadas = analise["infracoes"]

    # --- Persistência: viagem + infrações ---
    try:
        viagem = LeituraViagem(
            placa_veiculo=placa,
            data_processamento=datetime.now(),
            distancia_total_km=float(resumo["distancia_estimada_km"]),
            velocidade_maxima=float(resumo["velocidade_maxima_kmh"]),
        )
        db.add(viagem)
        db.flush()  # obtém viagem.id antes do commit

        for item in infracoes_detectadas:
            tipo = str(item["tipo"])
            if tipo == "excesso_velocidade":
                velocidade = float(item.get("velocidade_maxima_kmh", 0.0))  # type: ignore[arg-type]
            else:
                velocidade = 0.0

            db.add(
                Infracao(
                    viagem_id=viagem.id,
                    tipo_infracao=tipo,
                    hora_inicio=str(item["hora_inicio"]),
                    hora_fim=str(item["hora_fim"]),
                    velocidade_registrada=velocidade,
                )
            )

        db.commit()
        db.refresh(viagem)
        viagem_id = viagem.id
        # Associa a imagem de debug à viagem (para o laudo PDF nesta sessão)
        IMAGENS_DEBUG_POR_VIAGEM[viagem_id] = str(caminho_salvo)
    except SQLAlchemyError:
        db.rollback()
        raise
    except Exception as erro:  # noqa: BLE001
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Falha ao gravar no banco de dados: {erro}",
        ) from erro

    url_imagem = f"/temp/{caminho_salvo.name}"

    payload: dict[str, Any] = {
        "sucesso": True,
        "mensagem": "Disco processado, analisado e salvo com sucesso.",
        "arquivo": arquivo.filename,
        "placa_veiculo": placa,
        "viagem_id": viagem_id,
        "furo_central": {
            "x": resultado.circulo.centro_x,
            "y": resultado.circulo.centro_y,
            "raio": resultado.circulo.raio,
        },
        "imagem_desdobrada": {
            "caminho_local": str(caminho_salvo),
            "url": url_imagem,
            "largura_px": resultado.largura_px,
            "altura_px": resultado.altura_px,
            "eixo_x": "24 horas",
            "eixo_y": "velocidade 0 a 120 km/h",
        },
        "resumo_viagem": resumo,
        "infracoes": infracoes_detectadas,
        "curva_velocidade": curva_tratada,
        "curva_velocidade_amostra": curva_tratada[:AMOSTRAS_CURVA_JSON],
        "curva_velocidade_total_pontos": len(curva_tratada),
    }

    return JSONResponse(content=payload, status_code=status.HTTP_200_OK)


app.mount("/temp", StaticFiles(directory=str(PASTA_TEMP)), name="temp")
app.mount("/static", StaticFiles(directory=str(PASTA_STATIC)), name="static")


if __name__ == "__main__":
    import os

    import uvicorn

    # Porta 8081 por padrão para conviver com outro software na 8080.
    # Para mudar: set PORT=8090  (PowerShell: $env:PORT=8090)
    porta = int(os.getenv("PORT", "8081"))

    # reload=False no Windows evita processo "zumbi" com a página carregando eternamente
    uvicorn.run("main:app", host="127.0.0.1", port=porta, reload=False)
