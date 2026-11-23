import { Injectable } from '@angular/core';
import type { Observable } from 'rxjs';
import { API_ENDPOINTS, BaseApi } from '../api/api-url';
import type { BranchResponse, FuelTypeResponse } from '../models/catalog';

/** Catálogos de solo lectura: sedes y tipos de combustible. */
@Injectable({ providedIn: 'root' })
export class CatalogApi extends BaseApi {
  branches(): Observable<readonly BranchResponse[]> {
    return this.get<readonly BranchResponse[]>(API_ENDPOINTS.branches);
  }

  fuelTypes(): Observable<readonly FuelTypeResponse[]> {
    return this.get<readonly FuelTypeResponse[]>(API_ENDPOINTS.fuelTypes);
  }
}
