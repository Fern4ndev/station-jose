import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { FormBuilder, Validators } from '@angular/forms';
import { EmptyState } from '../../../shared/components/empty-state/empty-state';
import { PageHeader } from '../../../shared/components/page-header/page-header';
import { SectionPanel } from '../../../shared/components/section-panel/section-panel';
import { VerificationForm } from '../verification-form/verification-form';

@Component({ changeDetection: ChangeDetectionStrategy.OnPush, imports: [EmptyState, PageHeader, SectionPanel, VerificationForm], selector: 'app-verification-detail-page', templateUrl: './verification-detail-page.html' })
export class VerificationDetailPage {
  private readonly fb = inject(FormBuilder).nonNullable;
  protected readonly attendanceId = inject(ActivatedRoute).snapshot.paramMap.get('attendanceId') ?? '';
  protected readonly form = this.fb.group({
    decision: ['VERIFIED' as 'VERIFIED' | 'OBSERVED', Validators.required],
    observation: [''],
  });
}
