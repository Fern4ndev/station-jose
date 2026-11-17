import { ChangeDetectionStrategy, Component } from '@angular/core';
import { RouterLink } from '@angular/router';
import { RecordListPage } from '../../../shared/components/record-list-page/record-list-page';

@Component({ changeDetection: ChangeDetectionStrategy.OnPush, imports: [RecordListPage, RouterLink], selector: 'app-users-page', templateUrl: './users-page.html' })
export class UsersPage {
  protected readonly columns = ['Usuario', 'DNI', 'Correo', 'Rol', 'Sede', 'Estado'];
}
