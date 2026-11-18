import { ChangeDetectionStrategy, Component, inject, output } from '@angular/core';
import { ActivatedRoute, NavigationEnd, Router } from '@angular/router';
import { filter, map, startWith } from 'rxjs';
import { toSignal } from '@angular/core/rxjs-interop';
import { NotificationsBell } from '../notifications-bell/notifications-bell';

@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [NotificationsBell],
  selector: 'app-header',
  styleUrl: './header.css',
  templateUrl: './header.html',
})
export class Header {
  private readonly router = inject(Router);
  private readonly activatedRoute = inject(ActivatedRoute);

  readonly menuClick = output<void>();

  protected readonly pageTitle = toSignal(
    this.router.events.pipe(
      filter((event): event is NavigationEnd => event instanceof NavigationEnd),
      startWith(null),
      map(() => {
        let route = this.activatedRoute.firstChild;
        while (route?.firstChild) route = route.firstChild;
        return String(route?.snapshot.data['title'] ?? 'Panel principal');
      }),
    ),
    { initialValue: 'Panel principal' },
  );
}
