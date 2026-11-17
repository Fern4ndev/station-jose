import { ChangeDetectionStrategy, Component, computed, input } from '@angular/core';

@Component({ changeDetection: ChangeDetectionStrategy.OnPush, selector: 'app-loading-skeleton', templateUrl: './loading-skeleton.html' })
export class LoadingSkeleton {
  readonly rows = input(4);
  protected readonly placeholders = computed(() => Array.from({ length: this.rows() }, (_, index) => index));
}
