import { ChangeDetectionStrategy, Component, ViewEncapsulation } from '@angular/core';

/**
 * Declara los tokens visuales del mockup (tinta, menta, combustible y lienzo)
 * una sola vez, sin tocar `styles.css`. Se monta en el shell de la aplicación.
 */
@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  encapsulation: ViewEncapsulation.None,
  selector: 'app-ui-theme',
  styleUrl: './ui-theme.css',
  template: '',
})
export class UiTheme {}
