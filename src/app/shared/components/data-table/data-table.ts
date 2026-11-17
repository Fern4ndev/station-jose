import { ChangeDetectionStrategy, Component, input } from '@angular/core';
import { EmptyState } from '../empty-state/empty-state';

@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [EmptyState],
  selector: 'app-data-table',
  styleUrl: './data-table.css',
  templateUrl: './data-table.html',
})
export class DataTable {
  readonly columns = input.required<readonly string[]>();
  readonly emptyTitle = input('Sin registros para mostrar');
  readonly emptyDescription = input('La integración de datos de esta pantalla está pendiente; todavía no hay registros reales para consultar.');
}
