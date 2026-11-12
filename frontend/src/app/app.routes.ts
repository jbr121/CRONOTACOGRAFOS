import { Routes } from '@angular/router';

import { DetalheViagem } from './paginas/detalhe-viagem';
import { Escanear } from './paginas/escanear';
import { Historico } from './paginas/historico';

export const routes: Routes = [
  { path: '', component: Escanear, title: 'Novo escaneamento — CronotaScan' },
  { path: 'historico', component: Historico, title: 'Histórico — CronotaScan' },
  { path: 'viagens/:id', component: DetalheViagem, title: 'Detalhe da viagem — CronotaScan' },
  { path: '**', redirectTo: '' },
];
