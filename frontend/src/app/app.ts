import { Component } from '@angular/core';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';

@Component({
  selector: 'app-root',
  imports: [RouterOutlet, RouterLink, RouterLinkActive],
  template: `
    <div class="app-shell">
      <header class="gp-header">
        <a routerLink="/" class="gp-logo-wrap" aria-label="CronotaScan — início">
          <img src="/static/img/logo-galaxypro.png" alt="Galaxy Pro" />
          <div>
            <div class="gp-brand-title">Galaxy Pro</div>
            <div class="gp-app-name">CronotaScan</div>
            <div class="gp-tagline">Leitor de discos <span>analógicos</span></div>
          </div>
        </a>
        <nav class="gp-nav" aria-label="Navegação principal">
          <a routerLink="/" routerLinkActive="ativo" [routerLinkActiveOptions]="{ exact: true }">📥 Novo escaneamento</a>
          <a routerLink="/historico" routerLinkActive="ativo">🗂 Histórico</a>
        </nav>
      </header>

      <main>
        <router-outlet />
      </main>

      <footer class="gp-footer">
        <img src="/static/img/logo-galaxypro.png" alt="" />
        Galaxy Pro — Tecnologia • Desenvolvimento • Inovação
      </footer>
    </div>
  `,
})
export class App {}
