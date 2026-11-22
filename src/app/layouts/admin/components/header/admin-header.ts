import {
  ChangeDetectionStrategy,
  Component,
  HostListener,
  computed,
  inject,
  input,
  output,
  signal,
} from '@angular/core';
import { ROLE_LABELS } from '../../../../core/constants/system.constants';
import { AuthService } from '../../../../core/services/auth.service';
import { UiIcon } from '../../../../shared/components/ui-icon/ui-icon';
import { NotificationsBell } from '../notifications-bell/notifications-bell';

@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [NotificationsBell, UiIcon],
  selector: 'app-admin-header',
  templateUrl: './admin-header.html',
})
export class AdminHeader {
  private readonly auth = inject(AuthService);

  readonly pageLabel = input.required<string>();
  readonly menuOpen = input(false);
  readonly menuToggle = output<void>();

  protected readonly searchTerm = signal('');
  protected readonly profileOpen = signal(false);

  protected readonly fullName = this.auth.fullName;
  protected readonly initials = this.auth.initials;
  protected readonly email = computed(() => this.auth.user()?.email ?? '');
  protected readonly roleLabel = computed(() => {
    const role = this.auth.role();
    if (!role) {
      return 'Sesión sin rol';
    }
    const branch = this.auth.user()?.branch?.name;
    return branch ? `${ROLE_LABELS[role]} · ${branch}` : ROLE_LABELS[role];
  });

  protected onSearch(event: Event): void {
    this.searchTerm.set((event.target as HTMLInputElement).value);
  }

  protected toggleProfile(): void {
    this.profileOpen.update((open) => !open);
  }

  protected logout(): void {
    this.profileOpen.set(false);
    this.auth.logout();
  }

  @HostListener('document:keydown.escape')
  protected onEscape(): void {
    this.profileOpen.set(false);
  }
}
