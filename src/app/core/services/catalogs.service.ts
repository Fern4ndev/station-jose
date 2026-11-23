import { Injectable, signal } from '@angular/core';
import { finalize, tap, type Observable } from 'rxjs';
import { BaseApi } from '../api/api-url';
import { API_ENDPOINTS } from '../api/endpoints';
import type { BranchResponse, FuelTypeResponse } from '../models/catalog.model';

/** Catálogos: sedes y tipos de combustible, cacheados como signals. */
@Injectable({ providedIn: 'root' })
export class CatalogsService extends BaseApi {
  private readonly loadingState = signal(false);
  private readonly branchesState = signal<readonly BranchResponse[]>([]);
  private readonly fuelTypesState = signal<readonly FuelTypeResponse[]>([]);

  readonly loading = this.loadingState.asReadonly();
  readonly branches = this.branchesState.asReadonly();
  readonly fuelTypes = this.fuelTypesState.asReadonly();

  loadBranches(): Observable<readonly BranchResponse[]> {
    this.loadingState.set(true);
    return this.get<readonly BranchResponse[]>(API_ENDPOINTS.branches).pipe(
      tap((branches) => this.branchesState.set(branches)),
      finalize(() => this.loadingState.set(false)),
    );
  }

  loadFuelTypes(): Observable<readonly FuelTypeResponse[]> {
    this.loadingState.set(true);
    return this.get<readonly FuelTypeResponse[]>(API_ENDPOINTS.fuelTypes).pipe(
      tap((fuelTypes) => this.fuelTypesState.set(fuelTypes)),
      finalize(() => this.loadingState.set(false)),
    );
  }
}
