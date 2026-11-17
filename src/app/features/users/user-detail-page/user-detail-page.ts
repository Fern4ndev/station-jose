import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { PageHeader } from '../../../shared/components/page-header/page-header';
import { SectionPanel } from '../../../shared/components/section-panel/section-panel';
import { EmptyState } from '../../../shared/components/empty-state/empty-state';

@Component({ changeDetection: ChangeDetectionStrategy.OnPush, imports: [EmptyState, PageHeader, SectionPanel], selector: 'app-user-detail-page', templateUrl: './user-detail-page.html' })
export class UserDetailPage {
  private readonly route = inject(ActivatedRoute);
  protected readonly userId = this.route.snapshot.paramMap.get('userId') ?? '';
}
