import {
  Component,
  ElementRef,
  OnDestroy,
  afterRenderEffect,
  input,
  viewChild,
} from '@angular/core';
import {
  CategoryScale,
  Chart,
  Filler,
  LineController,
  LineElement,
  LinearScale,
  PointElement,
  Tooltip,
} from 'chart.js';

import { PontoCurva } from '../core/modelos';

Chart.register(LineController, LineElement, PointElement, LinearScale, CategoryScale, Filler, Tooltip);

@Component({
  selector: 'app-grafico-velocidade',
  template: `<div class="chart-wrap"><canvas #canvas aria-label="Gráfico de velocidade ao longo do dia"></canvas></div>`,
  styles: `.chart-wrap { position: relative; height: 300px; }`,
})
export class GraficoVelocidade implements OnDestroy {
  readonly curva = input.required<PontoCurva[]>();
  readonly limite = input(80);

  private readonly canvas = viewChild.required<ElementRef<HTMLCanvasElement>>('canvas');
  private grafico: Chart | null = null;

  constructor() {
    afterRenderEffect(() => this.desenhar(this.curva(), this.limite()));
  }

  ngOnDestroy(): void {
    this.grafico?.destroy();
  }

  private desenhar(curva: PontoCurva[], limite: number): void {
    this.grafico?.destroy();
    this.grafico = new Chart(this.canvas().nativeElement, {
      type: 'line',
      data: {
        labels: curva.map((p) => p.hora),
        datasets: [
          {
            label: 'Velocidade (km/h)',
            data: curva.map((p) => p.velocidade_kmh),
            borderColor: '#3b82f6',
            backgroundColor: (ctx) => {
              const g = ctx.chart.ctx.createLinearGradient(0, 0, 0, 300);
              g.addColorStop(0, 'rgba(59,130,246,0.30)');
              g.addColorStop(1, 'rgba(124,58,237,0.03)');
              return g;
            },
            borderWidth: 2,
            pointRadius: 0,
            pointHoverRadius: 4,
            fill: true,
            tension: 0.18,
          },
          {
            label: `Limite (${limite} km/h)`,
            data: curva.map(() => limite),
            borderColor: 'rgba(239,68,68,0.6)',
            borderDash: [6, 4],
            borderWidth: 1,
            pointRadius: 0,
            fill: false,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: 'index', intersect: false },
        plugins: {
          tooltip: {
            backgroundColor: 'rgba(7,17,43,0.92)',
            borderColor: 'rgba(59,130,246,0.35)',
            borderWidth: 1,
            titleColor: '#94a3b8',
            bodyColor: '#e2e8f0',
            filter: (item) => item.datasetIndex === 0,
            callbacks: { label: (ctx) => `${ctx.parsed.y} km/h` },
          },
        },
        scales: {
          x: {
            title: { display: true, text: 'Hora do dia', color: '#64748b' },
            ticks: { maxTicksLimit: 13, autoSkip: true, color: '#64748b' },
            grid: { color: 'rgba(59,130,246,0.08)' },
          },
          y: {
            title: { display: true, text: 'km/h', color: '#64748b' },
            min: 0,
            suggestedMax: 125,
            ticks: { color: '#64748b' },
            grid: { color: 'rgba(59,130,246,0.08)' },
          },
        },
      },
    });
  }
}
