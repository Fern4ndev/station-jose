import { ChangeDetectionStrategy, Component } from '@angular/core';
import { ReportPage } from '../report-page/report-page';

@Component({ changeDetection: ChangeDetectionStrategy.OnPush, imports: [ReportPage], selector: 'app-report-purchase-orders-page', templateUrl: './report-purchase-orders-page.html' })
export class ReportPurchaseOrdersPage {}
