import { ChangeDetectionStrategy, Component, OnInit, inject } from '@angular/core';
import { Router } from '@angular/router';
import { homePathForPermissions } from '../../core/models/auth.models';
import { AuthStore } from '../../core/services/auth/auth';

@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  selector: 'app-home-redirect',
  template: '<p class="text-sm text-slate-600" role="status">Abriendo tu espacio de trabajo…</p>',
})
export class AppHomeRedirect implements OnInit {
  private readonly authStore = inject(AuthStore);
  private readonly router = inject(Router);

  ngOnInit(): void {
    const user = this.authStore.user();
    if (user) {
      void this.router.navigateByUrl(homePathForPermissions(this.authStore.permissions()), { replaceUrl: true });
    }
  }
}
