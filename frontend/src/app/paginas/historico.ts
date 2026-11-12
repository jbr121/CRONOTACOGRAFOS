import { DecimalPipe } from '@angular/common';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';

import { Alerta } from '../compartilhado/alerta';
import { ApiService, mensagemDeErro } from '../core/api.service';
import {
  classeVelocidade,
  formatarDataHora,
  normalizarPlaca,
  severidadeInfracoes,
} from '../core/formatos';
import { ViagemResumo } from '../core/modelos';

@Component({
  selector: 'app-historico',
  imports: [DecimalPipe, RouterLink, Alerta],
  templateUrl: './historico.html',
})
export class Historico implements OnInit {
  private readonly api = inject(ApiService);

  protected readonly viagens = signal<ViagemResumo[]>([]);
  protected readonly filtro = signal('');
  protected readonly carregando = signal(true);
  protected readonly erro = signal<string | null>(null);

  protected readonly linhas = computed(() =>
    this.viagens().map((v) => ({
      ...v,
      data: formatarDataHora(v.data_processamento),
      severidade: severidadeInfracoes(Number(v.total_infracoes)),
      classeVel: classeVelocidade(Number(v.velocidade_maxima)),
    })),
  );

  ngOnInit(): void {
    this.carregar();
  }

  protected aoDigitarFiltro(evento: Event): void {
    const campo = evento.target as HTMLInputElement;
    campo.value = normalizarPlaca(campo.value);
    this.filtro.set(campo.value);
  }

  protected filtrar(): void {
    this.carregar();
  }

  protected limparFiltro(): void {
    this.filtro.set('');
    this.carregar();
  }

  protected abrirPdf(id: number): void {
    window.open(this.api.urlLaudoPdf(id), '_blank');
  }

  private carregar(): void {
    this.carregando.set(true);
    this.erro.set(null);
    this.api.listarViagens(this.filtro()).subscribe({
      next: (lista) => {
        this.viagens.set(lista);
        this.carregando.set(false);
      },
      error: (e) => {
        this.erro.set(mensagemDeErro(e, 'Falha ao carregar o histórico.'));
        this.carregando.set(false);
      },
    });
  }
}
