import { ChangeDetectionStrategy, Component } from '@angular/core';
import { RecordListPage } from '../../../shared/components/record-list-page/record-list-page';

@Component({ changeDetection: ChangeDetectionStrategy.OnPush, imports: [RecordListPage], selector: 'app-attendances-page', templateUrl: './attendances-page.html' })
export class AttendancesPage {
  protected readonly columns = ['Vale / orden', 'Grifero', 'Sede', 'Fecha y hora', 'Combustible', 'Galones', 'Verificación'];
}
