import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';

export type ReportFileFormat = 'pdf' | 'xlsx';

@Component({ changeDetection: ChangeDetectionStrategy.OnPush, selector: 'app-report-export-actions', templateUrl: './report-export-actions.html' })
export class ReportExportActions {
  readonly disabled = input(false);
  readonly exporting = input(false);
  readonly export = output<ReportFileFormat>();
}
