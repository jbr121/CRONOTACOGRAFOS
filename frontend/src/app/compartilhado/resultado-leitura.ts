import { DecimalPipe } from '@angular/common';
import { Component, computed, inject, input } from '@angular/core';

import { ApiService } from '../core/api.service';
import { Infracao, LeituraExibida } from '../core/modelos';
import { Alerta } from './alerta';
import { GraficoVelocidade } from './grafico-velocidade';

interface LinhaInfracao {
  excesso: boolean;
  inicio: string;
  fim: string;
  detalhe: string;
}

/** Painel completo de uma leitura: métricas, qualidade, gráfico, imagem e infrações. */
@Component({
  selector: 'app-resultado-leitura',
  imports: [DecimalPipe, Alerta, GraficoVelocidade],
  templateUrl: './resultado-leitura.html',
})
export class ResultadoLeitura {
  private readonly api = inject(ApiService);

  readonly leitura = input.required<LeituraExibida>();

  protected readonly qualidade = computed(() => {
    const nota = this.leitura().qualidade?.nota_aneis;
    if (nota == null) return null;
    return nota >= 2
      ? { classe: 'qualidade-boa', rotulo: 'Leitura confiável', nota }
      : { classe: 'qualidade-baixa', rotulo: 'Baixa confiança', nota };
  });

  protected readonly linhas = computed<LinhaInfracao[]>(() =>
    this.leitura().infracoes.map((i) => this.paraLinha(i)),
  );

  protected readonly totalExcessos = computed(() => this.linhas().filter((l) => l.excesso).length);
  protected readonly totalParadas = computed(() => this.linhas().filter((l) => !l.excesso).length);

  protected abrirPdf(): void {
    window.open(this.api.urlLaudoPdf(this.leitura().viagemId), '_blank');
  }

  private paraLinha(item: Infracao): LinhaInfracao {
    const excesso = (item.tipo ?? item.tipo_infracao) === 'excesso_velocidade';
    const vel = (item.velocidade_maxima_kmh ?? item.velocidade_registrada ?? 0).toLocaleString('pt-BR', {
      maximumFractionDigits: 1,
    });
    const dur = item.duracao_minutos;
    const detalhe = excesso
      ? dur != null ? `Máx. ${vel} km/h · ${dur} min` : `Máx. ${vel} km/h`
      : dur != null ? `Parado por ${dur} min` : 'Parada prolongada';
    return { excesso, inicio: item.hora_inicio, fim: item.hora_fim, detalhe };
  }
}
