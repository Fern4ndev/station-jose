import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';
import { FileUploadModule } from 'primeng/fileupload';

@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [FileUploadModule],
  selector: 'app-file-drop',
  templateUrl: './file-drop.html',
})
export class FileDrop {
  readonly accept = input('.pdf');
  readonly multiple = input(false);
  readonly chooseLabel = input('Seleccionar archivo');
  readonly selected = output<readonly File[]>();

  onSelect(event: { readonly files: File[] }): void {
    this.selected.emit(event.files);
  }
}
