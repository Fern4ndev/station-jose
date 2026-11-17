import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';
import { DataTable } from '../data-table/data-table';
import { PageHeader } from '../page-header/page-header';
import { SearchField } from '../search-field/search-field';
import { SectionPanel } from '../section-panel/section-panel';

@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [DataTable, PageHeader, SearchField, SectionPanel],
  selector: 'app-record-list-page',
  templateUrl: './record-list-page.html',
})
export class RecordListPage {
  readonly title = input.required<string>();
  readonly description = input.required<string>();
  readonly columns = input.required<readonly string[]>();
  readonly listDescription = input.required<string>();
  readonly searchLabel = input('');
  readonly emptyDescription = input.required<string>();
  readonly queryChange = output<string>();
}
