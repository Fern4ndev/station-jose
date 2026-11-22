import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';
import { UiIcon } from '../../../../shared/components/ui-icon/ui-icon';
import type { AdminNavItem, AdminUser, PageId } from '../../admin-nav';

@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [UiIcon],
  selector: 'app-admin-sidebar',
  styleUrl: './admin-sidebar.css',
  templateUrl: './admin-sidebar.html',
})
export class AdminSidebar {
  readonly items = input.required<readonly AdminNavItem[]>();
  readonly active = input.required<PageId>();
  readonly user = input.required<AdminUser>();
  readonly branch = input.required<string>();
  readonly branches = input.required<readonly string[]>();
  readonly branchLocked = input(false);
  readonly mobileOpen = input(false);

  readonly pageChange = output<PageId>();
  readonly branchChange = output<string>();

  protected onNavigate(page: PageId): void {
    this.pageChange.emit(page);
  }

  protected onBranchChange(event: Event): void {
    this.branchChange.emit((event.target as HTMLSelectElement).value);
  }
}
