import { ChangeDetectionStrategy, Component, DestroyRef, inject, input, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule } from '@angular/forms';
import { Subject, catchError, finalize, map, of, switchMap } from 'rxjs';
import { AuthStore } from '../../../core/services/auth/auth';
import { CatalogApi, CatalogItem } from '../../../core/services/catalog-api';
import { DataTable } from '../../../shared/components/data-table/data-table';
import { PageHeader } from '../../../shared/components/page-header/page-header';
import { ReportExportActions, ReportFileFormat } from '../../../shared/components/report-export-actions/report-export-actions';
import { SectionPanel } from '../../../shared/components/section-panel/section-panel';
import { ReportApi, ReportKind, ReportQuery } from '../report-api';

@Component({ changeDetection: ChangeDetectionStrategy.OnPush, imports: [DataTable, PageHeader, ReactiveFormsModule, ReportExportActions, SectionPanel], selector: 'app-report-page', templateUrl: './report-page.html' })
export class ReportPage {
  readonly kind = input.required<ReportKind>();
  readonly title = input.required<string>();
  readonly description = input.required<string>();
  private readonly api = inject(ReportApi);
  private readonly catalog = inject(CatalogApi);
  private readonly destroyRef = inject(DestroyRef);
  private readonly fb = inject(FormBuilder).nonNullable;
  private readonly requests = new Subject<ReportQuery>();
  protected readonly auth = inject(AuthStore);
  protected readonly filters = this.fb.group({ dateFrom: '', dateTo: '', branchId: '' });
  protected readonly branches = signal<CatalogItem[]>([]);
  protected readonly catalogError = signal(false);
  protected readonly state = signal<'loading' | 'error' | 'empty' | 'success'>('empty');
  protected readonly rows = signal<readonly Readonly<Record<string, string | number | null>>[]>([]);
  protected readonly applied = signal<ReportQuery | null>(null);
  protected readonly error = signal('');
  protected readonly exporting = signal(false);
  protected readonly columns = signal<readonly string[]>([]);

  constructor() {
    this.loadBranches();
    this.requests.pipe(switchMap((query) => {
      this.state.set('loading');
      return this.api.get(this.kind(), query).pipe(map((response) => ({ response, query })), catchError(() => of({ response: null, query })));
    }), takeUntilDestroyed(this.destroyRef)).subscribe(({ response, query }) => {
      if (!response) { this.state.set('error'); return; }
      const mapping = this.kind() === 'purchase-orders'
        ? { Orden: 'order_number', Entidad: 'institution_name', Sede: 'branch_name', Fecha: 'issue_date', Combustible: 'fuel_type_name', Autorizado: 'authorized_gallons', Atendido: 'attended_gallons', Disponible: 'available_gallons' }
        : { Vale: 'voucher_number', Orden: 'order_number', Fecha: 'attended_at', Grifero: 'performer_name', Sede: 'branch_name', Combustible: 'fuel_type_name', Galones: 'attended_gallons' };
      const entries = Object.entries(mapping);
      this.columns.set(entries.map(([label]) => label));
      this.rows.set(response.items.map((item) => Object.fromEntries(entries.map(([label, key]) => [label, item[key] ?? null]))));
      this.applied.set(query);
      this.state.set(response.items.length ? 'success' : 'empty');
    });
  }
  protected loadBranches(): void {
    this.catalogError.set(false);
    this.catalog.branches().pipe(takeUntilDestroyed(this.destroyRef)).subscribe({ next: (items) => this.branches.set(items.filter((item) => item.is_active)), error: () => this.catalogError.set(true) });
  }
  protected consult(): void {
    const query = this.filters.getRawValue();
    if (query.dateFrom && query.dateTo && query.dateFrom > query.dateTo) { this.error.set('La fecha inicial no puede ser posterior a la final.'); return; }
    this.error.set(''); this.requests.next(query);
  }
  protected download(format: ReportFileFormat): void {
    const query = this.applied();
    if (!query || this.exporting() || !this.auth.hasPermission('reports.export')) return;
    this.error.set(''); this.exporting.set(true);
    this.api.export(this.kind(), query, format).pipe(takeUntilDestroyed(this.destroyRef), finalize(() => this.exporting.set(false))).subscribe({
      next: (blob) => {
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url; link.download = `reporte-${this.kind()}.${format}`; link.click();
        setTimeout(() => URL.revokeObjectURL(url), 0);
      },
      error: () => this.error.set('No se pudo exportar el reporte. Inténtalo nuevamente.'),
    });
  }
}
