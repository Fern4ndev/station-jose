import { ChangeDetectionStrategy, Component, input } from '@angular/core';

@Component({
  selector: 'app-scan-loader',
  imports: [],
  templateUrl: './scan-loader.html',
  styleUrl: './scan-loader.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ScanLoader {
  readonly label = input('Analizando documento…');
}
