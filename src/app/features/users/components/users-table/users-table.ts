import { ChangeDetectionStrategy, Component, computed, input, linkedSignal, output, signal } from '@angular/core';
import { TablePagination } from '../../../../shared/components/table-pagination/table-pagination';
import { UiStatusBadge } from '../../../../shared/components/ui-status-badge/ui-status-badge';
import { userInitials, type DemoUserRow } from '../../users-data';

@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [TablePagination, UiStatusBadge],
  selector: 'app-users-table',
  templateUrl: './users-table.html',
})
export class UsersTable {
  readonly rows = input.required<readonly DemoUserRow[]>();
  protected readonly first = linkedSignal({ source: this.rows, computation: () => 0 });
  protected readonly pageSize = signal(10);
  protected readonly pageRows = computed(() => this.rows().slice(this.first(), this.first() + this.pageSize()));

  protected onPage(event: { first?: number; rows?: number }): void {
    this.first.set(event.first ?? 0);
    this.pageSize.set(event.rows ?? 10);
  }

  readonly toggle = output<DemoUserRow>();

  protected initials = userInitials;
}
