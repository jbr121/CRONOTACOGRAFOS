import { Injectable, signal } from '@angular/core';

import { LeituraExibida, ResultadoUpload } from './modelos';

/** Guarda o último upload para ele continuar visível ao trocar de tela. */
@Injectable({ providedIn: 'root' })
export class LeituraAtualService {
  readonly leitura = signal<LeituraExibida | null>(null);

  definirDoUpload(r: ResultadoUpload): void {
    this.leitura.set({
      viagemId: r.viagem_id,
      placa: r.placa_veiculo,
      resumo: r.resumo_viagem,
      infracoes: r.infracoes ?? [],
      curva: r.curva_velocidade ?? [],
      imagemUrl: r.imagem_desdobrada?.url ? `${r.imagem_desdobrada.url}?t=${Date.now()}` : undefined,
      centro: r.furo_central,
      avisos: r.avisos ?? [],
      qualidade: r.qualidade_leitura,
    });
  }

  limpar(): void {
    this.leitura.set(null);
  }
}
