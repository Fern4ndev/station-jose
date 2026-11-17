import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { ActivatedRoute } from '@angular/router';

@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  selector: 'app-feature-placeholder',
  templateUrl: './feature-placeholder.html',
})
export class FeaturePlaceholder {
  private readonly route = inject(ActivatedRoute);

  protected readonly title = String(this.route.snapshot.data['title'] ?? 'Módulo');
  protected readonly description = String(
    this.route.snapshot.data['description'] ?? 'Esta pantalla estará disponible en una próxima fase.',
  );
}
