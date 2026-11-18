export type UserRole = 'ADMIN' | 'OFFICE' | 'ATTENDANT';

export interface BranchSummaryDto {
  readonly id: string;
  readonly code: string;
  readonly name: string;
}

export interface AuthenticatedUserDto {
  readonly id: string;
  readonly first_name: string;
  readonly last_name: string;
  readonly dni: string;
  readonly email: string;
  readonly role: UserRole;
  readonly branch: BranchSummaryDto | null;
  readonly is_active: boolean;
}

export interface LoginRequest {
  readonly email: string;
  readonly password: string;
}

export interface LoginResponseDto {
  readonly access_token: string;
  readonly token_type: 'bearer';
  readonly expires_in: number;
  readonly user: AuthenticatedUserDto;
  readonly permissions: readonly string[];
}

export interface CurrentUserResponseDto extends AuthenticatedUserDto {
  readonly permissions: readonly string[];
}

export interface BranchSummary {
  readonly id: string;
  readonly code: string;
  readonly name: string;
}

export interface AuthenticatedUser {
  readonly id: string;
  readonly firstName: string;
  readonly lastName: string;
  readonly dni: string;
  readonly email: string;
  readonly role: UserRole;
  readonly branch: BranchSummary | null;
  readonly isActive: boolean;
}

export interface CurrentUser extends AuthenticatedUser {
  readonly permissions: readonly string[];
}

export interface LoginResult {
  readonly accessToken: string;
  readonly expiresIn: number;
  readonly user: AuthenticatedUser;
  readonly permissions: readonly string[];
}

export interface AuthSession {
  readonly accessToken: string;
  readonly expiresAt: number;
  readonly user: AuthenticatedUser;
  readonly permissions: readonly string[];
}

export function mapAuthenticatedUser(dto: AuthenticatedUserDto): AuthenticatedUser {
  return {
    id: dto.id,
    firstName: dto.first_name,
    lastName: dto.last_name,
    dni: dto.dni,
    email: dto.email,
    role: dto.role,
    branch: dto.branch,
    isActive: dto.is_active,
  };
}

export function mapLoginResponse(dto: LoginResponseDto): LoginResult {
  return {
    accessToken: dto.access_token,
    expiresIn: dto.expires_in,
    user: mapAuthenticatedUser(dto.user),
    permissions: dto.permissions,
  };
}

export function mapCurrentUserResponse(dto: CurrentUserResponseDto): CurrentUser {
  return {
    ...mapAuthenticatedUser(dto),
    permissions: dto.permissions,
  };
}

export const ROLE_LABELS: Readonly<Record<UserRole, string>> = {
  ADMIN: 'Administrador',
  OFFICE: 'Oficina',
  ATTENDANT: 'Grifero',
};

export function homePathForRole(role: UserRole): string {
  return role === 'ATTENDANT' ? '/attendant/workspace' : '/dashboard';
}

export function homePathForPermissions(permissions: readonly string[]): string {
  if (permissions.includes('reports.read')) return '/dashboard';
  if (permissions.includes('attendances.create')) return '/attendant/workspace';
  return '/access-denied';
}

export function safeReturnUrl(value: string | null): string | null {
  if (!value || !value.startsWith('/') || value.startsWith('//') || /[\\\u0000-\u001f]/.test(value)) return null;
  if (/^\/auth(?:[/?#]|$)/.test(value)) return null;
  return value;
}
