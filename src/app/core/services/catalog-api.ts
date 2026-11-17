import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { API_BASE_URL } from '../api/api-url';

export interface CatalogItem {
  readonly id: string;
  readonly code: string;
  readonly name: string;
  readonly is_active: boolean;
}

@Injectable({ providedIn: 'root' })
export class CatalogApi {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = inject(API_BASE_URL);
  branches(): Observable<CatalogItem[]> { return this.http.get<CatalogItem[]>(`${this.baseUrl}/branches`); }
  fuelTypes(): Observable<CatalogItem[]> { return this.http.get<CatalogItem[]>(`${this.baseUrl}/fuel-types`); }
}
