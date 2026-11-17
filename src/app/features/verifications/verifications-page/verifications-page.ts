import { ChangeDetectionStrategy, Component } from '@angular/core';
import { RecordListPage } from '../../../shared/components/record-list-page/record-list-page';

@Component({ changeDetection: ChangeDetectionStrategy.OnPush, imports: [RecordListPage], selector: 'app-verifications-page', templateUrl: './verifications-page.html' })
export class VerificationsPage {
  protected readonly columns = ['Vale / orden', 'Combustible', 'Galones', 'Fecha y hora', 'Usuario', 'Sede', 'Estado'];
}
