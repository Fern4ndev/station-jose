import { ChangeDetectionStrategy, Component, HostListener, computed, signal } from '@angular/core';
import { UiIcon } from '../../../../shared/components/ui-icon/ui-icon';

/**
 * Sin endpoint de notificaciones en `openapi.json`: la campana conserva el
 * elemento del mockup y muestra un estado vacío, sin llamadas de red.
 */
@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [UiIcon],
  selector: 'app-notifications-bell',
  templateUrl: './notifications-bell.html',
})
export class NotificationsBell {
  protected readonly open = signal(false);
  protected readonly notifications = signal<readonly string[]>([]);
  protected readonly loading = signal(false);
  protected readonly unreadCount = computed(() => this.notifications().length);

  protected toggle(): void {
    this.open.update((open) => !open);
  }

  @HostListener('document:keydown.escape')
  protected onEscape(): void {
    this.open.set(false);
  }
}
