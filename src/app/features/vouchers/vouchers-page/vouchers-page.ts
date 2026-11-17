import { ChangeDetectionStrategy, Component } from '@angular/core';
import { RecordListPage } from '../../../shared/components/record-list-page/record-list-page';

@Component({ changeDetection: ChangeDetectionStrategy.OnPush, imports: [RecordListPage], selector: 'app-vouchers-page', templateUrl: './vouchers-page.html' })
export class VouchersPage {
  protected readonly columns = ['N.º de vale', 'Orden / emisor', 'Combustible', 'Autorizado', 'Atendido', 'Saldo del vale', 'Verificación'];
}
