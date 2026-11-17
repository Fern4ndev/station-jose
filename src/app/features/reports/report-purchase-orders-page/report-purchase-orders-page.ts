import { ChangeDetectionStrategy, Component, signal } from '@angular/core';
import { DataTable } from '../../../shared/components/data-table/data-table';
import { PageHeader } from '../../../shared/components/page-header/page-header';
import { ReportFilterBar, ReportFilterValue } from '../../../shared/components/report-filter-bar/report-filter-bar';
import { SectionPanel } from '../../../shared/components/section-panel/section-panel';
import { ReportExportActions } from '../../../shared/components/report-export-actions/report-export-actions';

@Component({ changeDetection: ChangeDetectionStrategy.OnPush, imports: [DataTable, PageHeader, ReportExportActions, ReportFilterBar, SectionPanel], selector: 'app-report-purchase-orders-page', templateUrl: './report-purchase-orders-page.html' })
export class ReportPurchaseOrdersPage {
  protected readonly filters = signal<ReportFilterValue>({ from: '', to: '', status: '', userId: '' });
  protected readonly columns = ['Orden', 'Entidad', 'Sede', 'Fecha', 'Combustible', 'Autorizado', 'Despachado', 'Saldo'];
}
