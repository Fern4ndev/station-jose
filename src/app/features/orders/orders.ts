import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { MessageService } from 'primeng/api';
import { firstValueFrom } from 'rxjs';
import type { BranchResponse, FuelTypeResponse } from '../../core/models/catalog';
import { CatalogApi } from '../../core/services/catalog-api';
import { PurchaseOrdersApi } from '../../core/services/purchase-orders-api';
import { VouchersApi } from '../../core/services/vouchers-api';
import { AdminUiState } from '../../layouts/admin/admin-ui-state';
import { UiConfirmDialog } from '../../shared/components/ui-confirm-dialog/ui-confirm-dialog';
import { UiIcon } from '../../shared/components/ui-icon/ui-icon';
import { UiPageHeading } from '../../shared/components/ui-page-heading/ui-page-heading';
import { UiPanel } from '../../shared/components/ui-panel/ui-panel';
import { TableRefresh } from '../../shared/components/table-refresh/table-refresh';
import { extractApiError } from '../../shared/utils/api-error';
import { OrderDetailDialog } from './components/order-detail-dialog/order-detail-dialog';
import { OrderFormDialog } from './components/order-form-dialog/order-form-dialog';
import { OrdersTable } from './components/orders-table/orders-table';
import { OrdersToolbar } from './components/orders-toolbar/orders-toolbar';
import { filterOrders, toOrderRows, type DemoOrder, type OrderDraft, type OrderFilter } from './orders-data';

@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [OrderDetailDialog, OrderFormDialog, OrdersTable, OrdersToolbar, TableRefresh, UiConfirmDialog, UiIcon, UiPageHeading, UiPanel],
  selector: 'app-orders',
  templateUrl: './orders.html',
})
export class Orders {
  private readonly state = inject(AdminUiState);
  private readonly messages = inject(MessageService);
  private readonly api = inject(PurchaseOrdersApi);
  private readonly vouchersApi = inject(VouchersApi);
  private readonly catalog = inject(CatalogApi);

  protected readonly orders = signal<readonly DemoOrder[]>([]);
  protected readonly branches = signal<readonly BranchResponse[]>([]);
  protected readonly fuels = signal<readonly FuelTypeResponse[]>([]);
  protected readonly lockedIds = signal<readonly string[]>([]);
  protected readonly filter = signal<OrderFilter>('Todas');
  protected readonly query = signal('');
  protected readonly formOpen = signal(false);
  protected readonly editing = signal<DemoOrder | null>(null);
  protected readonly detailOpen = signal(false);
  protected readonly selected = signal<DemoOrder | null>(null);
  protected readonly deleteOpen = signal(false);
  protected readonly saving = signal(false);
  protected readonly refreshing = signal(false);

  protected readonly canManage = computed(() => this.state.role() !== 'ATTENDANT');
  protected readonly rows = computed(() => filterOrders(this.orders(), this.filter(), this.query(), this.state.role() === 'ATTENDANT' ? 'Todas las sedes' : this.state.branch()));
  protected readonly countText = computed(() => `${new Set(this.rows().map((order) => order.apiId)).size} órdenes encontradas`);
  protected readonly takenIds = computed(() => this.orders().map((order) => order.id));

  constructor() {
    void this.load();
    this.catalog.branches().subscribe({ next: (items) => this.branches.set(items), error: (error: unknown) => this.showError(error) });
    if (this.canManage()) {
      this.catalog.fuelTypes().subscribe({ next: (items) => this.fuels.set(items), error: (error: unknown) => this.showError(error) });
    }
  }

  private async load(): Promise<void> {
    this.refreshing.set(true);
    try {
      const orders: DemoOrder[] = [];
      for (let page = 1; ; page += 1) {
        const response = await firstValueFrom(this.api.list({ page, page_size: 100 }));
        orders.push(...response.items.flatMap(toOrderRows));
        if (page >= response.pagination.pages) break;
      }
      this.orders.set(orders);
      if (this.canManage()) {
        const locked: string[] = [];
        for (let page = 1; ; page += 1) {
          const response = await firstValueFrom(this.vouchersApi.list({ page, page_size: 100 }));
          locked.push(...response.items.map((voucher) => voucher.purchase_order_id));
          if (page >= response.pagination.pages) break;
        }
        this.lockedIds.set(orders.filter((order) => locked.includes(order.apiId ?? '')).map((order) => order.id));
      }
    } catch (error) {
      this.showError(error);
    } finally {
      this.refreshing.set(false);
    }
  }

  private showError(error: unknown): void {
    this.messages.add({ severity: 'error', summary: extractApiError(error), life: 4000 });
  }

  protected openNew(): void { this.editing.set(null); this.formOpen.set(true); }
  protected openEdit(order: DemoOrder): void { this.editing.set(order); this.formOpen.set(true); }
  protected openDetail(order: DemoOrder): void { this.selected.set(order); this.detailOpen.set(true); }

  protected askDelete(order: DemoOrder): void {
    if (this.lockedIds().includes(order.id)) return;
    this.selected.set(order);
    this.deleteOpen.set(true);
  }

  protected confirmDelete(): void {
    const order = this.selected();
    if (!order?.apiId) return;
    this.api.remove(order.apiId).subscribe({
      next: () => { this.deleteOpen.set(false); void this.load(); this.messages.add({ severity: 'success', summary: 'Orden eliminada.', life: 2800 }); },
      error: (error: unknown) => this.showError(error),
    });
  }

  protected save(draft: OrderDraft): void {
    if (this.saving()) return;
    this.saving.set(true);
    const existing = this.editing();
    const request = existing?.apiId
      ? this.api.update(existing.apiId, draft.payload)
      : this.api.create(draft.payload);
    request.subscribe({
      next: () => { this.saving.set(false); this.formOpen.set(false); this.editing.set(null); void this.load(); this.messages.add({ severity: 'success', summary: 'Orden guardada.', life: 2800 }); },
      error: (error: unknown) => { this.saving.set(false); this.showError(error); },
    });
  }

  protected loadMore(): void { void this.load(); }
}
