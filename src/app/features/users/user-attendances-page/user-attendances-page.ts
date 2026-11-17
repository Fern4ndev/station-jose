import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { RecordListPage } from '../../../shared/components/record-list-page/record-list-page';

@Component({ changeDetection: ChangeDetectionStrategy.OnPush, imports: [RecordListPage], selector: 'app-user-attendances-page', templateUrl: './user-attendances-page.html' })
export class UserAttendancesPage {
  protected readonly userId = inject(ActivatedRoute).snapshot.paramMap.get('userId') ?? '';
  protected readonly columns = ['Vale', 'Orden', 'Fecha y hora', 'Sede', 'Combustible', 'Galones'];
}
