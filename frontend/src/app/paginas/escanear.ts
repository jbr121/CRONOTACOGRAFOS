import { HttpEventType } from '@angular/common/http';
import { Component, OnDestroy, computed, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';

import { Alerta } from '../compartilhado/alerta';
import { ResultadoLeitura } from '../compartilhado/resultado-leitura';
import { ApiService, mensagemDeErro } from '../core/api.service';
import { REGEX_PLACA, normalizarPlaca } from '../core/formatos';
import { LeituraAtualService } from '../core/leitura-atual.service';

const TAMANHO_MAXIMO_MB = 20;

type Etapa = 'pronto' | 'enviando' | 'processando';

@Component({
  selector: 'app-escanear',
  imports: [Alerta, ResultadoLeitura, RouterLink],
  templateUrl: './escanear.html',
})
export class Escanear implements OnDestroy {
  private readonly api = inject(ApiService);
  protected readonly atual = inject(LeituraAtualService);

  protected readonly placa = signal('');
  protected readonly placaTocada = signal(false);
  protected readonly arquivo = signal<File | null>(null);
  protected readonly previa = signal<string | null>(null);
  protected readonly arrastando = signal(false);
  protected readonly etapa = signal<Etapa>('pronto');
  protected readonly progresso = signal(0);
  protected readonly erro = signal<string | null>(null);
  protected readonly dicasAbertas = signal(true);

  protected readonly placaValida = computed(() => REGEX_PLACA.test(this.placa()));
  protected readonly ocupado = computed(() => this.etapa() !== 'pronto');
  protected readonly podeEnviar = computed(
    () => this.placaValida() && !!this.arquivo() && !this.ocupado(),
  );

  ngOnDestroy(): void {
    this.liberarPrevia();
  }

  protected aoDigitarPlaca(evento: Event): void {
    const campo = evento.target as HTMLInputElement;
    const valor = normalizarPlaca(campo.value);
    campo.value = valor;
    this.placa.set(valor);
  }

  protected aoEscolherArquivo(evento: Event): void {
    const campo = evento.target as HTMLInputElement;
    this.definirArquivo(campo.files?.[0] ?? null);
    campo.value = '';
  }

  protected aoArrastar(evento: DragEvent, dentro: boolean): void {
    evento.preventDefault();
    this.arrastando.set(dentro);
  }

  protected aoSoltar(evento: DragEvent): void {
    evento.preventDefault();
    this.arrastando.set(false);
    this.definirArquivo(evento.dataTransfer?.files?.[0] ?? null);
  }

  protected removerArquivo(): void {
    this.definirArquivo(null);
  }

  protected tamanhoLegivel(bytes: number): string {
    return bytes > 1024 * 1024 ? `${(bytes / 1024 / 1024).toFixed(1)} MB` : `${Math.round(bytes / 1024)} KB`;
  }

  protected novoEscaneamento(): void {
    this.atual.limpar();
    this.definirArquivo(null);
    this.placa.set('');
    this.placaTocada.set(false);
    this.erro.set(null);
  }

  protected enviar(): void {
    this.placaTocada.set(true);
    const arquivo = this.arquivo();
    if (!this.placaValida()) {
      this.erro.set('Informe uma placa válida: ABC-1234 (antiga) ou ABC1D23 (Mercosul).');
      return;
    }
    if (!arquivo) {
      this.erro.set('Selecione a foto do disco.');
      return;
    }

    this.erro.set(null);
    this.progresso.set(0);
    this.etapa.set('enviando');

    this.api.enviarDisco(this.placa(), arquivo).subscribe({
      next: (evento) => {
        if (evento.type === HttpEventType.UploadProgress) {
          const total = evento.total ?? arquivo.size;
          this.progresso.set(Math.round((100 * evento.loaded) / total));
          if (evento.loaded >= total) this.etapa.set('processando');
        } else if (evento.type === HttpEventType.Response && evento.body) {
          this.atual.definirDoUpload(evento.body);
          this.definirArquivo(null);
          this.etapa.set('pronto');
        }
      },
      error: (e) => {
        this.erro.set(mensagemDeErro(e, 'Falha ao processar o disco.'));
        this.etapa.set('pronto');
      },
    });
  }

  private definirArquivo(arquivo: File | null): void {
    this.erro.set(null);
    if (arquivo && !arquivo.type.startsWith('image/')) {
      this.erro.set('O arquivo precisa ser uma imagem (JPG ou PNG).');
      return;
    }
    if (arquivo && arquivo.size > TAMANHO_MAXIMO_MB * 1024 * 1024) {
      this.erro.set(`A imagem passa de ${TAMANHO_MAXIMO_MB} MB. Envie uma foto menor.`);
      return;
    }
    this.liberarPrevia();
    this.arquivo.set(arquivo);
    this.previa.set(arquivo ? URL.createObjectURL(arquivo) : null);
  }

  private liberarPrevia(): void {
    const url = this.previa();
    if (url) URL.revokeObjectURL(url);
  }
}
