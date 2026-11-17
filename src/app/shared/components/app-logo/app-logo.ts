import { ChangeDetectionStrategy, Component, input } from '@angular/core';

@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  selector: 'app-logo',
  templateUrl: './app-logo.html',
})
export class AppLogo {
  readonly label = input('San José');
  readonly compact = input(false);
}
