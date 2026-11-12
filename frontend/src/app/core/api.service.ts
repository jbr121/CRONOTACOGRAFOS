import { HttpClient, HttpErrorResponse, HttpEvent, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, map } from 'rxjs';

import { ResultadoUpload, ViagemDetalhe, ViagemResumo } from './modelos';

@Injectable({ providedIn: 'root' })
export class ApiService {
  private readonly http = inject(HttpClient);

  listarViagens(placa?: string): Observable<ViagemResumo[]> {
    let params = new HttpParams();
    if (placa?.trim()) params = params.set('placa', placa.trim().toUpperCase());
    return this.http
      .get<{ total: number; viagens: ViagemResumo[] }>('/api/v1/viagens', { params })
      .pipe(map((r) => r.viagens ?? []));
  }

  detalharViagem(id: number): Observable<ViagemDetalhe> {
    return this.http.get<ViagemDetalhe>(`/api/v1/viagens/${id}`);
  }

  /** Envia o disco com eventos de progresso (upload) para a barra da tela. */
  enviarDisco(placa: string, arquivo: File): Observable<HttpEvent<ResultadoUpload>> {
    const dados = new FormData();
    dados.append('arquivo', arquivo);
    dados.append('placa_veiculo', placa);
    return this.http.post<ResultadoUpload>('/upload-disco/', dados, {
      reportProgress: true,
      observe: 'events',
    });
  }

  urlLaudoPdf(id: number): string {
    return `/api/v1/viagens/${id}/pdf`;
  }
}

/** Extrai a mensagem em português que o backend devolve em `mensagem`/`detail`. */
export function mensagemDeErro(erro: unknown, padrao: string): string {
  if (erro instanceof HttpErrorResponse) {
    if (erro.status === 0) return 'Não foi possível falar com o servidor. Ele está rodando?';
    const corpo = erro.error;
    if (corpo && typeof corpo === 'object') {
      if (typeof corpo.mensagem === 'string' && corpo.mensagem) return corpo.mensagem;
      if (typeof corpo.detail === 'string' && corpo.detail) return corpo.detail;
      if (Array.isArray(corpo.detail)) {
        return corpo.detail.map((i: { msg?: string }) => i.msg ?? JSON.stringify(i)).join(' ');
      }
    }
  }
  return padrao;
}
