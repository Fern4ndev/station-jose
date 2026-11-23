import { Injectable } from '@angular/core';
import type { Observable } from 'rxjs';
import { API_ENDPOINTS, BaseApi } from '../api/api-url';

/* Contratos exclusivos de este router. */

export interface LiveResponse {
  readonly status: string;
}

export interface ReadyResponse {
  readonly status: string;
  readonly database: string;
}

/** Sondas de salud del backend. */
@Injectable({ providedIn: 'root' })
export class HealthApi extends BaseApi {
  live(): Observable<LiveResponse> {
    return this.get<LiveResponse>(API_ENDPOINTS.health.live);
  }

  ready(): Observable<ReadyResponse> {
    return this.get<ReadyResponse>(API_ENDPOINTS.health.ready);
  }
}
