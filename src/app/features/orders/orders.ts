import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { MessageService } from 'primeng/api';
import { AdminUiState } from '../../layouts/admin/admin-ui-state';
import { UiConfirmDialog } from '../../shared/components/ui-confirm-dialog/ui-confirm-dialog';
import { UiIcon } from '../../shared/components/ui-icon/ui-icon';
import { UiPageHeading } from '../../shared/components/ui-page-heading/ui-page-heading';
import { UiPanel } from '../../shared/components/ui-panel/ui-panel';
import { UiToast } from '../../shared/components/ui-toast/ui-toast';
import { DEMO_VOUCHERS } from '../vouchers/vouchers-data';
import { OrderDetailDialog } from './components/order-detail-dialog/order-detail-dialog';
import { OrderFormDialog } from './components/order-form-dialog/order-form-dialog';
import { OrdersTable } from './components/orders-table/orders-table';
import { OrdersToolbar } from './components/orders-toolbar/orders-toolbar';
import {
  DEMO_ORDERS,
  filterOrders,
  type DemoOrder,
  type OrderDraft,
  type OrderFilter,
} from './orders-data';

@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    OrderDetailDialog,
    OrderFormDialog,
    OrdersTable,
    OrdersToolbar,
    UiConfirmDialog,
    UiIcon,
    UiPageHeading,
    UiPanel,
    UiToast,
  ],
  selector: 'app-orders',
  templateUrl: './orders.html',
})
export class Orders {
  private readonly state = inject(AdminUiState);
  private readonly messages = inject(MessageService);

  protected readonly orders = signal<readonly DemoOrder[]>([...DEMO_ORDERS]);
  protected readonly filter = signal<OrderFilter>('Todas');
  protected readonly query = signal('');

  protected readonly formOpen = signal(false);
  protected readonly editing = signal<DemoOrder | null>(null);
  protected readonly detailOpen = signal(false);
  protected readonly selected = signal<DemoOrder | null>(null);
  protected readonly deleteOpen = signal(false);

  protected readonly canManage = computed(() => this.state.role() !== 'ATTENDANT');
  protected readonly rows = computed(() =>
    filterOrders(this.orders(), this.filter(), this.query(), this.state.branch()),
  );
  protected readonly countText = computed(() => {
    const total = this.rows().length;
    return `${total} ${total === 1 ? 'orden encontrada' : 'órdenes encontradas'}`;
  });
  protected readonly lockedIds = computed(() => DEMO_VOUCHERS.map((voucher) => voucher.orderId));
  protected readonly takenIds = computed(() => this.orders().map((order) => order.id));

  protected openNew(): void {
    this.editing.set(null);
    this.formOpen.set(true);
  }

  protected openEdit(order: DemoOrder): void {
    this.editing.set(order);
    this.formOpen.set(true);
  }

  protected openDetail(order: DemoOrder): void {
    this.selected.set(order);
    this.detailOpen.set(true);
  }

  protected askDelete(order: DemoOrder): void {
    if (this.lockedIds().includes(order.id)) {
      this.messages.add({
        severity: 'warn',
        summary: 'No se puede eliminar una orden que ya tiene vales asociados.',
        life: 2800,
      });
      return;
    }
    this.selected.set(order);
    this.deleteOpen.set(true);
  }

  protected confirmDelete(): void {
    const order = this.selected();
    if (!order) {
      return;
    }
    this.orders.update((orders) => orders.filter((item) => item.id !== order.id));
    this.deleteOpen.set(false);
    this.messages.add({ severity: 'success', summary: 'Orden eliminada.', life: 2800 });
  }

  protected save(draft: OrderDraft): void {
    const existing = this.editing();
    if (existing) {
      this.orders.update((orders) =>
        orders.map((order) =>
          order.id === existing.id
            ? { ...order, entity: draft.entity, branch: draft.branch, fuel: draft.fuel, total: draft.total }
            : order,
        ),
      );
      this.messages.add({ severity: 'success', summary: 'Cambios guardados en la orden.', life: 2800 });
    } else {
      this.orders.update((orders) => [{ ...draft, used: 0 }, ...orders]);
      this.messages.add({ severity: 'success', summary: 'Orden guardada.', life: 2800 });
    }
    this.editing.set(null);
  }

  protected loadMore(): void {
    this.messages.add({
      severity: 'info',
      summary: 'Se muestran todas las órdenes de demostración.',
      life: 2800,
    });
  }
}
