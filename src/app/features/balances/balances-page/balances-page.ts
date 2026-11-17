import { ChangeDetectionStrategy, Component } from '@angular/core';
import { EmptyState } from '../../../shared/components/empty-state/empty-state';
import { PageHeader } from '../../../shared/components/page-header/page-header';
import { SectionPanel } from '../../../shared/components/section-panel/section-panel';
import { BalanceLookup } from '../balance-lookup/balance-lookup';

@Component({ changeDetection: ChangeDetectionStrategy.OnPush, imports: [BalanceLookup, EmptyState, PageHeader, SectionPanel], selector: 'app-balances-page', templateUrl: './balances-page.html' })
export class BalancesPage {}
