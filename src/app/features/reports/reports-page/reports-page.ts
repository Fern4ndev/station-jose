import { ChangeDetectionStrategy, Component } from '@angular/core';
import { PageHeader } from '../../../shared/components/page-header/page-header';
import { DashboardShortcut } from '../../dashboard/dashboard-shortcut/dashboard-shortcut';

@Component({ changeDetection: ChangeDetectionStrategy.OnPush, imports: [DashboardShortcut, PageHeader], selector: 'app-reports-page', templateUrl: './reports-page.html' })
export class ReportsPage {}
