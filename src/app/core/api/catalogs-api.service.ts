import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import type { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { API_ENDPOINTS } from '../constants/api.constants';
import type { BranchResponse, FuelTypeResponse } from '../models/catalog.model';

@Injectable({ providedIn: 'root' })
export class CatalogsApiService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = environment.apiUrl;

  branches(): Observable<readonly BranchResponse[]> {
    return this.http.get<readonly BranchResponse[]>(`${this.baseUrl}${API_ENDPOINTS.branches}`);
  }

  fuelTypes(): Observable<readonly FuelTypeResponse[]> {
    return this.http.get<readonly FuelTypeResponse[]>(`${this.baseUrl}${API_ENDPOINTS.fuelTypes}`);
  }
}
