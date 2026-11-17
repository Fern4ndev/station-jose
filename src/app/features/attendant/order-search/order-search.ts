import { ChangeDetectionStrategy, Component, output } from '@angular/core';
import { SearchField } from '../../../shared/components/search-field/search-field';

@Component({ changeDetection: ChangeDetectionStrategy.OnPush, imports: [SearchField], selector: 'app-order-search', templateUrl: './order-search.html' })
export class OrderSearch {
  readonly orderQuery = output<string>();
}
