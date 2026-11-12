/** Contratos da API FastAPI do CronotaScan (main.py). */

export interface PontoCurva {
  hora: string;
  velocidade_kmh: number;
}

export interface ResumoViagem {
  distancia_estimada_km: number;
  velocidade_maxima_kmh: number;
  velocidade_media_kmh: number | null;
  limite_velocidade_kmh: number;
  total_infracoes: number;
  total_excessos?: number;
  total_paradas_prolongadas?: number;
}

export interface Infracao {
  tipo?: string;
  tipo_infracao?: string;
  hora_inicio: string;
  hora_fim: string;
  velocidade_maxima_kmh?: number;
  velocidade_registrada?: number | null;
  duracao_minutos?: number;
}

export interface QualidadeLeitura {
  nota_aneis: number;
  escala_radial?: number;
}

/** Resposta de POST /upload-disco/ */
export interface ResultadoUpload {
  sucesso: boolean;
  mensagem: string;
  arquivo: string;
  placa_veiculo: string;
  viagem_id: number;
  furo_central: { x: number; y: number; raio: number };
  imagem_desdobrada: { url: string; largura_px: number; altura_px: number };
  avisos?: string[];
  qualidade_leitura?: QualidadeLeitura;
  resumo_viagem: ResumoViagem;
  infracoes: Infracao[];
  curva_velocidade: PontoCurva[];
}

/** Linha de GET /api/v1/viagens */
export interface ViagemResumo {
  id: number;
  placa_veiculo: string;
  data_processamento: string;
  distancia_total_km: number;
  velocidade_maxima: number;
  total_infracoes: number;
}

/** Resposta de GET /api/v1/viagens/{id} */
export interface ViagemDetalhe extends ViagemResumo {
  resumo_viagem: ResumoViagem;
  infracoes: Infracao[];
  imagem_desdobrada: { url: string } | null;
  avisos: string[];
  qualidade_leitura: { nota_aneis: number } | null;
}

/** Formato comum que a tela de resultado sabe exibir (upload recente ou histórico). */
export interface LeituraExibida {
  viagemId: number;
  placa: string;
  dataProcessamento?: string;
  resumo: ResumoViagem;
  infracoes: Infracao[];
  curva?: PontoCurva[];
  imagemUrl?: string;
  centro?: { x: number; y: number; raio: number };
  avisos: string[];
  qualidade?: QualidadeLeitura;
}
