import { ChangeDetectionStrategy, Component, computed, input, model, output, signal } from '@angular/core';

/**
 * Zona *drag & drop* del mockup (comprobantes OCR, importaciones). Valida
 * extensión y tamaño antes de emitir el archivo y muestra su vista previa.
 */
@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  selector: 'app-file-drop',
  templateUrl: './file-drop.html',
})
export class FileDrop {
  readonly accept = input<readonly string[]>(['.pdf', 'application/pdf']);
  readonly maxSizeMb = input(5);
  readonly label = input('Arrastra el archivo o selecciónalo desde tu equipo');
  readonly hint = input('');
  readonly file = model<File | null>(null);

  /** Mensaje legible cuando el archivo no cumple las reglas. */
  readonly rejected = output<string>();

  protected readonly dragging = signal(false);
  protected readonly error = signal('');

  protected readonly acceptAttr = computed(() => this.accept().join(','));
  protected readonly fileSize = computed(() => {
    const file = this.file();
    return file ? this.formatSize(file.size) : '';
  });

  protected onDragOver(event: DragEvent): void {
    event.preventDefault();
    this.dragging.set(true);
  }

  protected onDragLeave(): void {
    this.dragging.set(false);
  }

  protected onDrop(event: DragEvent): void {
    event.preventDefault();
    this.dragging.set(false);
    this.select(event.dataTransfer?.files?.[0] ?? null);
  }

  protected onPick(event: Event): void {
    const input = event.target as HTMLInputElement;
    this.select(input.files?.[0] ?? null);
    input.value = '';
  }

  protected clear(): void {
    this.file.set(null);
    this.error.set('');
  }

  private select(candidate: File | null): void {
    if (!candidate) {
      return;
    }
    const problem = this.validate(candidate);
    if (problem) {
      this.file.set(null);
      this.error.set(problem);
      this.rejected.emit(problem);
      return;
    }
    this.error.set('');
    this.file.set(candidate);
  }

  private validate(candidate: File): string | null {
    const name = candidate.name.toLowerCase();
    const type = candidate.type.toLowerCase();
    const allowed = this.accept().map((rule) => rule.trim().toLowerCase()).filter(Boolean);

    const matches = allowed.some((rule) =>
      rule.startsWith('.')
        ? name.endsWith(rule)
        : rule.endsWith('/*')
          ? type.startsWith(rule.slice(0, -1))
          : type === rule,
    );
    if (!matches) {
      return `Formato no permitido. Usa: ${this.accept().join(', ')}.`;
    }

    if (candidate.size > this.maxSizeMb() * 1024 * 1024) {
      return `El archivo supera el máximo de ${this.maxSizeMb()} MB.`;
    }

    return null;
  }

  private formatSize(bytes: number): string {
    const mb = bytes / (1024 * 1024);
    return mb >= 1 ? `${mb.toFixed(1)} MB` : `${Math.max(1, Math.round(bytes / 1024))} KB`;
  }
}
