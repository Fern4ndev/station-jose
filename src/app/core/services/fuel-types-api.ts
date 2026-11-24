import { Injectable } from '@angular/core';
import type { Observable } from 'rxjs';
import { API_ENDPOINTS, BaseApi } from '../api/api-url';
import type {
  FuelTypeCreate,
  FuelTypeListQuery,
  FuelTypeManageOut,
  FuelTypeOut,
  FuelTypeStatusUpdate,
  FuelTypeUpdate,
} from '../models/fuel-type';

/** Catálogo de combustibles: listado administrativo y mutaciones. */
@Injectable({ providedIn: 'root' })
export class FuelTypesApi extends BaseApi {
  list(query: FuelTypeListQuery = {}): Observable<readonly FuelTypeManageOut[]> {
    return this.get<readonly FuelTypeManageOut[]>(API_ENDPOINTS.fuelTypes.manage, query);
  }

  create(payload: FuelTypeCreate): Observable<FuelTypeOut> {
    return this.post<FuelTypeOut>(API_ENDPOINTS.fuelTypes.base, payload);
  }

  update(fuelTypeId: string, payload: FuelTypeUpdate): Observable<FuelTypeOut> {
    return this.patch<FuelTypeOut>(API_ENDPOINTS.fuelTypes.byId(fuelTypeId), payload);
  }

  setStatus(
    fuelTypeId: string,
    payload: FuelTypeStatusUpdate,
  ): Observable<FuelTypeOut> {
    return this.patch<FuelTypeOut>(
      API_ENDPOINTS.fuelTypes.status(fuelTypeId),
      payload,
    );
  }
}
