import { ChangeDetectionStrategy, Component } from '@angular/core';
import { Toast } from 'primeng/toast';

@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [Toast],
  selector: 'app-ui-toast',
  templateUrl: './ui-toast.html',
})
export class UiToast {}
