import { Component, effect, inject, input, signal } from '@angular/core';
import { RouterLink } from '@angular/router';

import { Alerta } from '../compartilhado/alerta';
import { ResultadoLeitura } from '../compartilhado/resultado-leitura';
import { ApiService, mensagemDeErro } from '../core/api.service';
import { LeituraExibida } from '../core/modelos';

@Component({
  selector: 'app-detalhe-viagem',
  imports: [Alerta, ResultadoLeitura, RouterLink],
  template: `
    <a routerLink="/historico" class="link-voltar">← Voltar ao histórico</a>
    @if (erro()) {
      <app-alerta tipo="erro">{{ erro() }}</app-alerta>
    } @else if (leitura(); as l) {
      <app-resultado-leitura [leitura]="l" />
    } @else {
      <p class="vazio"><span class="spinner"></span> Carregando viagem…</p>
    }
  `,
})
export class DetalheViagem {
  private readonly api = inject(ApiService);

  /** Vem da rota viagens/:id (withComponentInputBinding). */
  readonly id = input.required<string>();

  protected readonly leitura = signal<LeituraExibida | null>(null);
  protected readonly erro = signal<string | null>(null);

  constructor() {
    effect(() => this.carregar(Number(this.id())));
  }

  private carregar(id: number): void {
    this.leitura.set(null);
    this.erro.set(null);
    this.api.detalharViagem(id).subscribe({
      next: (d) =>
        this.leitura.set({
          viagemId: d.id,
          placa: d.placa_veiculo,
          dataProcessamento: d.data_processamento,
          resumo: d.resumo_viagem,
          infracoes: d.infracoes ?? [],
          avisos: [],
        }),
      error: (e) => this.erro.set(mensagemDeErro(e, `Viagem ${id} não encontrada.`)),
    });
  }
}
