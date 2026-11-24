import {
  CUSTOM_ELEMENTS_SCHEMA,
  ChangeDetectionStrategy,
  Component,
  input,
  output,
} from '@angular/core';
import { USER_ROLES } from '../../users-data';
import 'iconify-icon';

@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  schemas: [CUSTOM_ELEMENTS_SCHEMA],
  selector: 'app-users-toolbar',
  templateUrl: './users-toolbar.html',
})
export class UsersToolbar {
  readonly total = input.required<number>();
  readonly query = input.required<string>();

  readonly queryChange = output<string>();

  protected readonly roleCount = USER_ROLES.length;

  protected onQuery(event: Event): void {
    this.queryChange.emit((event.target as HTMLInputElement).value);
  }
}
