import { ChangeDetectionStrategy, Component, input } from '@angular/core';
import { AvatarModule } from 'primeng/avatar';

@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [AvatarModule],
  selector: 'app-avatar',
  templateUrl: './avatar.html',
})
export class ProfileAvatar {
  readonly label = input('');
  readonly image = input<string | undefined>();
  readonly size = input<'normal' | 'large' | 'xlarge'>('normal');
  readonly shape = input<'circle' | 'square'>('circle');
  readonly ariaLabel = input('Perfil de usuario');
}
