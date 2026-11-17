import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { EmptyState } from '../../../shared/components/empty-state/empty-state';
import { PageHeader } from '../../../shared/components/page-header/page-header';
import { SectionPanel } from '../../../shared/components/section-panel/section-panel';

@Component({ changeDetection: ChangeDetectionStrategy.OnPush, imports: [EmptyState, PageHeader, SectionPanel], selector: 'app-attendance-detail-page', templateUrl: './attendance-detail-page.html' })
export class AttendanceDetailPage {
  protected readonly attendanceId = inject(ActivatedRoute).snapshot.paramMap.get('attendanceId') ?? '';
}
