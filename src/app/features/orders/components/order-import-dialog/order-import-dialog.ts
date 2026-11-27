import { ChangeDetectionStrategy, Component, DestroyRef, effect, inject, model, output, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { finalize, type Subscription } from 'rxjs';
import { OcrApi, type PurchaseOrderOcrPreview } from '../../../../core/services/ocr-api';
import { ScanLoader } from '../../../../shared/components/scan-loader/scan-loader';
import { UiDialog } from '../../../../shared/components/ui-dialog/ui-dialog';
import { extractApiError } from '../../../../shared/utils/api-error';

/** Selección y lectura del PDF, antes de revisar la orden. */
@Component({
  selector: 'app-order-import-dialog',
  imports: [UiDialog, ScanLoader],
  templateUrl: './order-import-dialog.html',
  styleUrl: './order-import-dialog.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class OrderImportDialog {
  private readonly ocr = inject(OcrApi);
  private readonly destroyRef = inject(DestroyRef);
  private request: Subscription | null = null;

  readonly visible = model(false);
  readonly imported = output<PurchaseOrderOcrPreview>();
  protected readonly file = signal<File | null>(null);
  protected readonly loading = signal(false);
  protected readonly dragging = signal(false);
  protected readonly error = signal('');

  constructor() {
    effect(() => {
      if (!this.visible()) {
        this.request?.unsubscribe();
        return;
      }
      this.file.set(null);
      this.error.set('');
      this.dragging.set(false);
    });
  }

  protected onFile(event: Event): void {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    input.value = '';
    if (file) this.selectFile(file);
  }

  protected onDragOver(event: DragEvent): void {
    event.preventDefault();
    if (!this.loading()) this.dragging.set(true);
  }

  protected onDrop(event: DragEvent): void {
    event.preventDefault();
    this.dragging.set(false);
    const file = event.dataTransfer?.files[0];
    if (file && !this.loading()) this.selectFile(file);
  }

  private selectFile(file: File): void {
    this.error.set('');
    this.file.set(null);
    if (file.type !== 'application/pdf' && !file.name.toLowerCase().endsWith('.pdf')) {
      this.error.set('Selecciona un archivo PDF.');
    } else if (file.size > 10 * 1024 * 1024) {
      this.error.set('El PDF debe pesar hasta 10 MB.');
    } else if (file.size === 0) {
      this.error.set('El archivo está vacío. Selecciona otro PDF.');
    } else {
      this.file.set(file);
    }
  }

  protected process(): void {
    const file = this.file();
    if (!file || this.loading() || !this.visible()) return;
    this.error.set('');
    this.loading.set(true);
    let received = false;
    this.request = this.ocr.analyze(file).pipe(
      takeUntilDestroyed(this.destroyRef),
      finalize(() => this.loading.set(false)),
    ).subscribe({
      next: (preview) => {
        received = true;
        this.visible.set(false);
        this.imported.emit(preview);
      },
      error: (error: unknown) => this.error.set(extractApiError(error, 'No se pudo leer el PDF. Inténtalo de nuevo.')),
      complete: () => {
        if (!received) this.error.set('No se recibieron datos. Inténtalo de nuevo.');
      },
    });
  }

  protected cancel(): void {
    this.request?.unsubscribe();
    this.visible.set(false);
  }
}
