import { ChangeDetectionStrategy, Component, input, output, signal } from '@angular/core';
import { UiIcon } from '../../../../shared/components/ui-icon/ui-icon';
import { NotificationsBell } from '../notifications-bell/notifications-bell';

@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [NotificationsBell, UiIcon],
  selector: 'app-admin-header',
  templateUrl: './admin-header.html',
})
export class AdminHeader {
  readonly pageLabel = input.required<string>();
  readonly menuOpen = input(false);
  readonly menuToggle = output<void>();

  protected readonly searchTerm = signal('');

  protected onSearch(event: Event): void {
    this.searchTerm.set((event.target as HTMLInputElement).value);
  }
}
