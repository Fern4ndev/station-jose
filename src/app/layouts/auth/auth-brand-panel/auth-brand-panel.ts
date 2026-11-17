import { ChangeDetectionStrategy, Component } from '@angular/core';

@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  selector: 'app-auth-brand-panel',
  templateUrl: './auth-brand-panel.html',
})
export class AuthBrandPanel { }
