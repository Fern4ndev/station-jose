export interface BranchSummary {
  readonly id: string;
  readonly code: string;
  readonly name: string;
}

export interface BranchResponse extends BranchSummary {
  readonly is_active: boolean;
}

export interface FuelTypeResponse {
  readonly id: string;
  readonly code: string;
  readonly name: string;
  readonly is_active: boolean;
}

export interface HealthResponse {
  readonly status: string;
  readonly database?: string;
}
