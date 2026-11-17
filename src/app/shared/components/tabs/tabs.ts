import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';
import { TabsModule } from 'primeng/tabs';

export interface UiTabItem {
  readonly label: string;
  readonly value: string;
  readonly disabled?: boolean;
}

@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [TabsModule],
  selector: 'app-tabs',
  templateUrl: './tabs.html',
})
export class UiTabs {
  readonly items = input.required<readonly UiTabItem[]>();
  readonly value = input.required<string | number>();
  readonly valueChange = output<string | number | undefined>();
}
