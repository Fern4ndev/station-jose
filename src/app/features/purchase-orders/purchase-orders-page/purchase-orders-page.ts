import { ChangeDetectionStrategy, Component } from '@angular/core';
import { RouterLink } from '@angular/router';
import { RecordListPage } from '../../../shared/components/record-list-page/record-list-page';

@Component({ changeDetection: ChangeDetectionStrategy.OnPush, imports: [RecordListPage, RouterLink], selector: 'app-purchase-orders-page', templateUrl: './purchase-orders-page.html' })
export class PurchaseOrdersPage {
  protected readonly columns = ['Orden / entidad', 'Sede', 'Fecha', 'Combustible', 'Autorizado', 'Despachado', 'Disponible', 'Estado'];
}
