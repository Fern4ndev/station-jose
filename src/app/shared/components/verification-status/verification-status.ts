import { ChangeDetectionStrategy, Component, input } from '@angular/core';
import { StatusBadge } from '../status-badge/status-badge';

@Component({ changeDetection: ChangeDetectionStrategy.OnPush, imports: [StatusBadge], selector: 'app-verification-status', templateUrl: './verification-status.html' })
export class VerificationStatus {
  readonly status = input.required<string>();
}
