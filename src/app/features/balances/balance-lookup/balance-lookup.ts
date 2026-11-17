import { ChangeDetectionStrategy, Component, output } from '@angular/core';
import { SearchField } from '../../../shared/components/search-field/search-field';

@Component({ changeDetection: ChangeDetectionStrategy.OnPush, imports: [SearchField], selector: 'app-balance-lookup', templateUrl: './balance-lookup.html' })
export class BalanceLookup {
  readonly queryChange = output<string>();
}
