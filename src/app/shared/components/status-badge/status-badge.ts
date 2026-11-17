import { ChangeDetectionStrategy, Component, computed, input } from '@angular/core';

const STATUS_LABELS: Readonly<Record<string, string>> = {
  ACTIVE: 'Activo', INACTIVE: 'Deshabilitado', PENDING: 'Pendiente', VERIFIED: 'Verificado',
  OBSERVED: 'Observado', COMPLETED: 'Completado', PARTIALLY_ATTENDED: 'Parcial',
  BLOCKED_BY_ORDER_BALANCE: 'Bloqueado por saldo de orden', PARTIALLY_BLOCKED: 'Parcialmente bloqueado',
};

@Component({ changeDetection: ChangeDetectionStrategy.OnPush, selector: 'app-status-badge', templateUrl: './status-badge.html' })
export class StatusBadge {
  readonly status = input.required<string>();
  protected readonly label = computed(() => STATUS_LABELS[this.status()] ?? this.status().replaceAll('_', ' ').toLowerCase());
  protected readonly tone = computed(() => {
    const status = this.status();
    if (['VERIFIED', 'ACTIVE', 'COMPLETED'].includes(status)) return 'bg-emerald-50 text-emerald-800';
    if (['OBSERVED', 'INACTIVE', 'BLOCKED_BY_ORDER_BALANCE'].includes(status)) return 'bg-amber-50 text-amber-800';
    return 'bg-slate-100 text-slate-700';
  });
}
