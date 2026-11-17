import { ChangeDetectionStrategy, Component, input } from '@angular/core';

@Component({ changeDetection: ChangeDetectionStrategy.OnPush, selector: 'app-branch-label', templateUrl: './branch-label.html' })
export class BranchLabel {
  readonly name = input.required<string>();
}
