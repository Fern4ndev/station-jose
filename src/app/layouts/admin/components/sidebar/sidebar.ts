import {
  ChangeDetectionStrategy,
  Component,
  ElementRef,
  HostListener,
  computed,
  inject,
  input,
  output,
  signal,
} from '@angular/core';
import { RouterLink, RouterLinkActive } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { SelectModule } from 'primeng/select';
import { navForRole, type NavChild, type NavEntry, type NavGroup } from '../../../../core/constants/nav';
import { AuthService } from '../../../../core/services/auth/auth';
import { UiIcon } from '../../../../shared/components/ui-icon/ui-icon';
import { AdminUiState } from '../../admin-ui-state';

@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink, RouterLinkActive, UiIcon, FormsModule, SelectModule],
  selector: 'app-sidebar',
  templateUrl: './sidebar.html',
})
export class Sidebar {
  private readonly auth = inject(AuthService);
  private readonly element = inject(ElementRef<HTMLElement>);
  private readonly state = inject(AdminUiState);

  readonly collapsed = input(false);
  readonly mobileOpen = input(false);

  readonly close = output<void>();
  readonly collapseToggle = output<void>();

  /** Menú del rol vigente: `role` sale del usuario que cargó `AuthService`. */
  protected readonly entries = computed<readonly NavEntry[]>(() =>
    navForRole(this.auth.currentUser()?.role ?? undefined),
  );
  protected readonly groups = computed(() =>
    this.entries().filter((entry): entry is NavGroup => this.isGroup(entry)),
  );
  protected readonly links = computed(() =>
    this.entries().filter((entry): entry is NavChild => !this.isGroup(entry)),
  );

  protected readonly user = this.state.user;
  protected readonly branch = this.state.branch;
  protected readonly branches = this.state.branches;
  protected readonly branchOptions = computed(() => this.branches().map((item) => ({ value: item, label: item })));
  protected readonly branchLocked = this.state.branchLocked;

  protected readonly profileOpen = signal(false);

  protected readonly isGroup = (entry: NavEntry): entry is NavGroup => 'children' in entry;

  protected onBranchChange(value: string): void {
    this.state.setBranch(value);
  }

  protected logout(): void {
    this.profileOpen.set(false);
    this.auth.logout();
  }

  @HostListener('document:click', ['$event'])
  protected onDocumentClick(event: MouseEvent): void {
    if (!this.element.nativeElement.contains(event.target as Node)) this.profileOpen.set(false);
  }

  @HostListener('document:keydown.escape')
  protected onEscape(): void {
    this.profileOpen.set(false);
  }
}
