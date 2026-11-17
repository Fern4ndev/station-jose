import { ChangeDetectionStrategy, Component } from '@angular/core';
import { RouterLink } from '@angular/router';
import { PageHeader } from '../../../shared/components/page-header/page-header';
import { SectionPanel } from '../../../shared/components/section-panel/section-panel';

@Component({ changeDetection: ChangeDetectionStrategy.OnPush, imports: [PageHeader, RouterLink, SectionPanel], selector: 'app-reports-page', templateUrl: './reports-page.html' })
export class ReportsPage {}
