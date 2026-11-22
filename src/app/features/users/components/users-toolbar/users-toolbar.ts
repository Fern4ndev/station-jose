import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';
import { USER_ROLES } from '../../users-data';

@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
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
