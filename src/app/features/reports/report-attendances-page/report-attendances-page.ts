import { ChangeDetectionStrategy, Component } from '@angular/core';
import { ReportPage } from '../report-page/report-page';

@Component({ changeDetection: ChangeDetectionStrategy.OnPush, imports: [ReportPage], selector: 'app-report-attendances-page', templateUrl: './report-attendances-page.html' })
export class ReportAttendancesPage {}
