import { ChangeDetectionStrategy, Component, input, output, signal } from '@angular/core';

@Component({ changeDetection: ChangeDetectionStrategy.OnPush, selector: 'app-pdf-upload', templateUrl: './pdf-upload.html' })
export class PdfUpload {
  readonly disabled = input(false);
  readonly fileSelected = output<File>();
  readonly fileCleared = output<void>();
  protected readonly filename = signal('');

  protected selectFile(event: Event): void {
    const input = event.target;
    if (!(input instanceof HTMLInputElement)) return;
    const file = input.files?.item(0);
    if (!file) return;
    this.filename.set(file.name);
    this.fileSelected.emit(file);
  }

  protected clearFile(): void {
    this.filename.set('');
    this.fileCleared.emit();
  }
}
