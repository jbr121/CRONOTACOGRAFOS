import { Component, input } from '@angular/core';

export type TipoAlerta = 'erro' | 'aviso' | 'sucesso' | 'info';

const ICONES: Record<TipoAlerta, string> = {
  erro: '✕',
  aviso: '⚠',
  sucesso: '✓',
  info: 'i',
};

/** Caixa de mensagem: erro (vermelho), aviso (amarelo), sucesso (verde), info (azul). */
@Component({
  selector: 'app-alerta',
  template: `
    <div class="alerta" [class]="'alerta alerta-' + tipo()" [attr.role]="tipo() === 'erro' ? 'alert' : 'status'">
      <span class="alerta-icone" aria-hidden="true">{{ icone() }}</span>
      <div class="alerta-corpo">
        @if (titulo()) {
          <strong>{{ titulo() }}</strong>
        }
        <ng-content />
      </div>
    </div>
  `,
})
export class Alerta {
  readonly tipo = input<TipoAlerta>('info');
  readonly titulo = input<string>('');

  protected icone(): string {
    return ICONES[this.tipo()];
  }
}
