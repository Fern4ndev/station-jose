import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { EmptyState } from '../../../shared/components/empty-state/empty-state';
import { PageHeader } from '../../../shared/components/page-header/page-header';
import { SectionPanel } from '../../../shared/components/section-panel/section-panel';

@Component({ changeDetection: ChangeDetectionStrategy.OnPush, imports: [EmptyState, PageHeader, RouterLink, SectionPanel], selector: 'app-purchase-order-detail-page', templateUrl: './purchase-order-detail-page.html' })
export class PurchaseOrderDetailPage {
  protected readonly orderId = inject(ActivatedRoute).snapshot.paramMap.get('orderId') ?? '';
}
