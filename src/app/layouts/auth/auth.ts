import { ChangeDetectionStrategy, Component } from '@angular/core';
import { AuthBrandPanel } from './auth-brand-panel/auth-brand-panel';

@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [AuthBrandPanel],
  selector: 'app-auth-layout',
  styleUrl: './auth.css',
  templateUrl: './auth.html',
})
export class AuthLayout {}
