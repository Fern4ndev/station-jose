import { ChangeDetectionStrategy, Component, output } from '@angular/core';
import { SearchField } from '../../../shared/components/search-field/search-field';

@Component({ changeDetection: ChangeDetectionStrategy.OnPush, imports: [SearchField], selector: 'app-voucher-search', templateUrl: './voucher-search.html' })
export class VoucherSearch {
  readonly voucherQuery = output<string>();
}
