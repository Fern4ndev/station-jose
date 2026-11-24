import { ChangeDetectionStrategy, Component, input } from '@angular/core';

export type UiIconName =
  | 'dashboard'
  | 'orders'
  | 'vouchers'
  | 'attendances'
  | 'reports'
  | 'users'
  | 'search'
  | 'bell'
  | 'user'
  | 'menu'
  | 'close'
  | 'arrow-right'
  | 'plus'
  | 'check'
  | 'download'
  | 'eye'
  | 'edit'
  | 'trash'
  | 'refresh'
  | 'logout';

@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  selector: 'app-ui-icon',
  templateUrl: './ui-icon.html',
})
export class UiIcon {
  readonly name = input.required<UiIconName>();
  readonly size = input(16);
  readonly strokeWidth = input(1.6);
}
