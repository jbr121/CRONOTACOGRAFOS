/** Placa antiga (ABC-1234 / ABC1234) ou Mercosul (ABC1D23). */
export const REGEX_PLACA = /^[A-Z]{3}-?\d[A-Z0-9]\d{2}$/;

export function normalizarPlaca(valor: string): string {
  return valor.toUpperCase().replace(/[^A-Z0-9-]/g, '');
}

/** "2026-08-13 09:40:37" → { dia: "13/08/26", hora: "09:40" } */
export function formatarDataHora(texto: string): { dia: string; hora: string } {
  const [data = '', hora = ''] = (texto ?? '').split(' ');
  const [ano, mes, dia] = data.split('-');
  return {
    dia: ano && mes && dia ? `${dia}/${mes}/${ano.slice(2)}` : data,
    hora: hora.slice(0, 5),
  };
}

export type Severidade = 'ok' | 'baixo' | 'medio' | 'alto';

export function severidadeInfracoes(total: number): Severidade {
  if (total === 0) return 'ok';
  if (total <= 5) return 'baixo';
  if (total <= 15) return 'medio';
  return 'alto';
}

export function classeVelocidade(kmh: number): string {
  if (kmh <= 80) return 'vel-ok';
  if (kmh <= 100) return 'vel-warn';
  return 'vel-danger';
}
