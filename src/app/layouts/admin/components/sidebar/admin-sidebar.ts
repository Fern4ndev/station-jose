import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';
import { UiIcon } from '../../../../shared/components/ui-icon/ui-icon';
import { ROLE_OPTIONS, type AdminNavItem, type DemoRole, type DemoUser, type PageId } from '../../admin-nav';

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
  readonly user = input.required<DemoUser>();
  readonly role = input.required<DemoRole>();
  readonly branch = input.required<string>();
  readonly mobileOpen = input(false);

  readonly pageChange = output<PageId>();
  readonly roleChange = output<DemoRole>();
  readonly branchChange = output<string>();

  protected readonly roleOptions = ROLE_OPTIONS;

  protected onNavigate(page: PageId): void {
    this.pageChange.emit(page);
  }

  protected onRoleChange(event: Event): void {
    const value = (event.target as HTMLSelectElement).value as DemoRole;
    this.roleChange.emit(value);
  }

  protected onBranchChange(event: Event): void {
    this.branchChange.emit((event.target as HTMLSelectElement).value);
  }
}
