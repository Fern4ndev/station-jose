import { ChangeDetectionStrategy, Component } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { ConfirmDialog } from 'primeng/confirmdialog';
import { UiToast } from './shared/components/ui-toast/ui-toast';

@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [ConfirmDialog, RouterOutlet, UiToast],
  selector: 'app-root',
  templateUrl: './app.html',
})
export class App {
}
