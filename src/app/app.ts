import { ChangeDetectionStrategy, Component } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { ConfirmDialog } from 'primeng/confirmdialog';
import { UiTheme } from './shared/components/ui-theme/ui-theme';
import { UiToast } from './shared/components/ui-toast/ui-toast';

@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [ConfirmDialog, RouterOutlet, UiTheme, UiToast],
  selector: 'app-root',
  styleUrl: './app.css',
  templateUrl: './app.html',
})
export class App {
}
