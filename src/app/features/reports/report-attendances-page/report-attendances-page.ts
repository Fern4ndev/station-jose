import { ChangeDetectionStrategy, Component, signal } from '@angular/core';
import { DataTable } from '../../../shared/components/data-table/data-table';
import { PageHeader } from '../../../shared/components/page-header/page-header';
import { ReportFilterBar, ReportFilterValue } from '../../../shared/components/report-filter-bar/report-filter-bar';
import { SectionPanel } from '../../../shared/components/section-panel/section-panel';
import { ReportExportActions } from '../../../shared/components/report-export-actions/report-export-actions';

@Component({ changeDetection: ChangeDetectionStrategy.OnPush, imports: [DataTable, PageHeader, ReportExportActions, ReportFilterBar, SectionPanel], selector: 'app-report-attendances-page', templateUrl: './report-attendances-page.html' })
export class ReportAttendancesPage {
  protected readonly filters = signal<ReportFilterValue>({ from: '', to: '', status: '', userId: '' });
  protected readonly columns = ['Vale', 'Orden', 'Fecha y hora', 'Grifero', 'Sede', 'Combustible', 'Galones', 'Verificación'];
}
