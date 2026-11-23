import type { UserRole } from './auth.model';
import type { BranchSummary } from './catalog.model';
import type { PaginatedResponse } from './pagination.model';

export interface UserResponse {
  readonly id: string;
  readonly first_name: string;
  readonly last_name: string;
  readonly dni: string;
  readonly email: string;
  readonly role: UserRole;
  readonly branch: BranchSummary | null;
  readonly is_active: boolean;
}

export interface UserCreate {
  readonly first_name: string;
  readonly last_name: string;
  readonly dni: string;
  readonly email: string;
  readonly password: string;
  readonly role: UserRole;
  readonly branch_id?: string | null;
}

export interface UserUpdate {
  readonly first_name?: string | null;
  readonly last_name?: string | null;
}

export interface UserRoleUpdate {
  readonly role: UserRole;
  readonly branch_id?: string | null;
}

export interface UserStatusUpdate {
  readonly is_active: boolean;
}

export type UserListResponse = PaginatedResponse<UserResponse>;

export type UserListQuery = {
  readonly page?: number;
  readonly page_size?: number;
};
