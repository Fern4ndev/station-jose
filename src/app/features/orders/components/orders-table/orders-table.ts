import { ChangeDetectionStrategy, Component, computed, input, linkedSignal, output, signal } from '@angular/core';
import { TablePagination } from '../../../../shared/components/table-pagination/table-pagination';
import { UiIcon } from '../../../../shared/components/ui-icon/ui-icon';
import { UiStatusBadge } from '../../../../shared/components/ui-status-badge/ui-status-badge';
import { formatGallons, orderBalance, orderPercent, type DemoOrder } from '../../orders-data';

@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [TablePagination, UiIcon, UiStatusBadge],
  selector: 'app-orders-table',
  templateUrl: './orders-table.html',
})
export class OrdersTable {
  readonly rows = input.required<readonly DemoOrder[]>();
  readonly countLabel = input<string | null>(null);
  readonly canManage = input(false);
  readonly lockedOrderIds = input<readonly string[]>([]);
  protected readonly first = linkedSignal({ source: this.rows, computation: () => 0 });
  protected readonly pageSize = signal(10);
  /** El servidor entrega lo más reciente primero; la tabla se lista en forma ascendente. */
  protected readonly orderedRows = computed(() => [...this.rows()].reverse());
  protected readonly pageRows = computed(() =>
    this.orderedRows().slice(this.first(), this.first() + this.pageSize()),
  );

  /** Correlativo ascendente, estable entre páginas. */
  protected rowNumber(index: number): number {
    return this.first() + index + 1;
  }

  protected onPage(event: { first?: number; rows?: number }): void {
    this.first.set(event.first ?? 0);
    this.pageSize.set(event.rows ?? 10);
  }

  readonly view = output<DemoOrder>();
  readonly edit = output<DemoOrder>();
  readonly remove = output<DemoOrder>();

  protected balance(order: DemoOrder): string {
    return `${formatGallons(orderBalance(order))} gal`;
  }

  protected percent(order: DemoOrder): string {
    return `${orderPercent(order)}% del total`;
  }

  protected total(order: DemoOrder): string {
    return `${formatGallons(order.total)} gal`;
  }

  protected hasBalance(order: DemoOrder): boolean {
    return orderBalance(order) > 0;
  }
}
