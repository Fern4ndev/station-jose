import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { PageHeader } from '../page-header/page-header';
import { DataTable } from '../data-table/data-table';
import { SectionPanel } from '../section-panel/section-panel';

@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [DataTable, PageHeader, SectionPanel],
  selector: 'app-feature-placeholder',
  styleUrl: './feature-placeholder.css',
  templateUrl: './feature-placeholder.html',
})
export class FeaturePlaceholder {
  private readonly route = inject(ActivatedRoute);

  protected readonly title = String(this.route.snapshot.data['title'] ?? 'Módulo');
  protected readonly description = String(
    this.route.snapshot.data['description'] ?? 'Esta pantalla estará disponible en una próxima fase.',
  );
  protected readonly columns: readonly string[] = Array.isArray(this.route.snapshot.data['columns'])
    ? (this.route.snapshot.data['columns'] as readonly string[])
    : [];
  protected readonly listDescription = String(
    this.route.snapshot.data['listDescription'] ?? 'Consulta los registros disponibles para tu perfil.',
  );
}
