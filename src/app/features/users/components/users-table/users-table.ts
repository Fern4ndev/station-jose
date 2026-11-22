import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';
import { UiStatusBadge } from '../../../../shared/components/ui-status-badge/ui-status-badge';
import { userInitials, type DemoUserRow } from '../../users-data';

@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [UiStatusBadge],
  selector: 'app-users-table',
  styleUrl: './users-table.css',
  templateUrl: './users-table.html',
})
export class UsersTable {
  readonly rows = input.required<readonly DemoUserRow[]>();

  readonly toggle = output<DemoUserRow>();

  protected initials = userInitials;
}
