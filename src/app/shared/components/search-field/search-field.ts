import { ChangeDetectionStrategy, Component, DestroyRef, inject, output } from '@angular/core';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { debounceTime, distinctUntilChanged } from 'rxjs';

@Component({ changeDetection: ChangeDetectionStrategy.OnPush, imports: [ReactiveFormsModule], selector: 'app-search-field', templateUrl: './search-field.html' })
export class SearchField {
  private readonly destroyRef = inject(DestroyRef);
  readonly queryChange = output<string>();
  protected readonly query = new FormControl('', { nonNullable: true });
  protected readonly id = `search-${crypto.randomUUID()}`;

  constructor() {
    this.query.valueChanges.pipe(debounceTime(300), distinctUntilChanged(), takeUntilDestroyed(this.destroyRef))
      .subscribe((query) => this.queryChange.emit(query.trim()));
  }
}
