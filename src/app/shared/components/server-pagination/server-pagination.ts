import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';

@Component({ changeDetection: ChangeDetectionStrategy.OnPush, selector: 'app-server-pagination', templateUrl: './server-pagination.html' })
export class ServerPagination {
  readonly page = input.required<number>();
  readonly pages = input.required<number>();
  readonly pageChange = output<number>();

  protected previous(): void { if (this.page() > 1) this.pageChange.emit(this.page() - 1); }
  protected next(): void { if (this.page() < this.pages()) this.pageChange.emit(this.page() + 1); }
}
