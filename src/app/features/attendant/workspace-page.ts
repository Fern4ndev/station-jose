import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { EmptyState } from '../../shared/components/empty-state/empty-state';
import { PageHeader } from '../../shared/components/page-header/page-header';
import { SectionPanel } from '../../shared/components/section-panel/section-panel';

@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [EmptyState, PageHeader, SectionPanel],
  selector: 'app-attendant-workspace-page',
  styleUrl: './workspace-page.css',
  templateUrl: './workspace-page.html',
})
export class WorkspacePage {
  private readonly route = inject(ActivatedRoute);
  protected readonly title = String(this.route.snapshot.data['title'] ?? 'Espacio de atención');
  protected readonly description = String(this.route.snapshot.data['description'] ?? 'Consulta órdenes y registra atenciones.');
}
