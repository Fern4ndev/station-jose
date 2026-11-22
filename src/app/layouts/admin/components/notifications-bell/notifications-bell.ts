import { ChangeDetectionStrategy, Component } from '@angular/core';
import { UiIcon } from '../../../../shared/components/ui-icon/ui-icon';

@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [UiIcon],
  selector: 'app-notifications-bell',
  templateUrl: './notifications-bell.html',
})
export class NotificationsBell {}
