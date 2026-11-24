import { ChangeDetectionStrategy, Component, ViewEncapsulation } from '@angular/core';
import { Toast } from 'primeng/toast';

@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  // El toast se monta en `body`: sus clases deben vivir sin encapsulación.
  encapsulation: ViewEncapsulation.None,
  imports: [Toast],
  selector: 'app-ui-toast',
  styleUrl: './ui-toast.css',
  templateUrl: './ui-toast.html',
})
export class UiToast {}
