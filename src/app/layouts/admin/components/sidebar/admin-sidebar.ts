import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';
import { UiIcon } from '../../../../shared/components/ui-icon/ui-icon';
import type { NavChild, NavGroup } from '../../../../core/constants/nav';
import type { AdminUser } from '../../admin-ui-state';

@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [UiIcon],
  selector: 'app-admin-sidebar',
  styleUrl: './admin-sidebar.css',
  templateUrl: './admin-sidebar.html',
})
export class AdminSidebar {
  readonly groups = input.required<readonly NavGroup[]>();
  readonly active = input.required<string>();
  readonly user = input.required<AdminUser>();
  readonly branch = input.required<string>();
  readonly branches = input.required<readonly string[]>();
  readonly branchLocked = input(false);
  readonly mobileOpen = input(false);

  readonly pageChange = output<NavChild>();
  readonly branchChange = output<string>();

  protected onNavigate(page: NavChild): void {
    this.pageChange.emit(page);
  }

  protected onBranchChange(event: Event): void {
    this.branchChange.emit((event.target as HTMLSelectElement).value);
  }
}
