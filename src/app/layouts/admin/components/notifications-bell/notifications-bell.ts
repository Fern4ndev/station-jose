import { ChangeDetectionStrategy, Component, computed, inject } from '@angular/core';
import { RouterLink } from '@angular/router';
import { AuthStore } from '../../../../core/services/auth/auth';

@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink],
  selector: 'app-notifications-bell',
  templateUrl: './notifications-bell.html',
})
export class NotificationsBell {
  private readonly auth = inject(AuthStore);
  protected readonly canReview = computed(() => this.auth.hasPermission('attendances.verify'));
}
