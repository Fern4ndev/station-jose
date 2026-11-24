import {
  CUSTOM_ELEMENTS_SCHEMA,
  ChangeDetectionStrategy,
  Component,
  input,
  output,
  signal,
} from '@angular/core';
import { UiIcon } from '../../../../shared/components/ui-icon/ui-icon';
import { NotificationsBell } from '../notifications-bell/notifications-bell';
import 'iconify-icon';

@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [NotificationsBell, UiIcon],
  schemas: [CUSTOM_ELEMENTS_SCHEMA],
  selector: 'app-header',
  templateUrl: './header.html',
})
export class Header {
  readonly pageLabel = input.required<string>();
  readonly mobileOpen = input(false);
  readonly menuToggle = output<void>();

  protected readonly searchTerm = signal('');

  protected onSearch(event: Event): void {
    this.searchTerm.set((event.target as HTMLInputElement).value);
  }

}
