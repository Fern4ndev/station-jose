export type UserRoleValue = 'OFFICE' | 'ATTENDANT' | 'ADMIN';

/** Única definición de los roles: de aquí salen el formulario y el panel de roles. */
const ROLE_DETAILS = {
  OFFICE: { label: 'Oficina', detail: 'Órdenes, consulta de vales, saldos y reportes' },
  ATTENDANT: { label: 'Grifero', detail: 'Consulta y registro de sus atenciones' },
  ADMIN: { label: 'Administrador', detail: 'Acceso a todos los módulos' },
} as const satisfies Record<UserRoleValue, { label: string; detail: string }>;

export type UserRole = (typeof ROLE_DETAILS)[UserRoleValue]['label'];

export interface DemoUserRow {
  readonly id: string;
  readonly name: string;
  readonly firstName: string;
  readonly lastName: string;
  readonly email: string;
  readonly dni: string;
  readonly role: UserRole;
  readonly branch: string;
  readonly branchId?: string;
  readonly active: boolean;
  readonly roleValue?: UserRoleValue;
}

export interface UserDraft {
  readonly firstName: string;
  readonly lastName: string;
  readonly email: string;
  readonly dni: string;
  readonly role: UserRoleValue;
  readonly branch: string;
  readonly password: string;
}

/** Opciones del formulario en el orden del mockup. */
export const USER_ROLES = (['OFFICE', 'ATTENDANT'] as const).map((value) => ({
  value,
  label: ROLE_DETAILS[value].label,
}));

/** Filas del panel "Roles del sistema", con el Administrador primero. */
export const ROLE_SUMMARY = (['ADMIN', 'OFFICE', 'ATTENDANT'] as const).map(
  (value) => ROLE_DETAILS[value],
);


export const userInitials = (name: string): string =>
  name
    .split(' ')
    .filter(Boolean)
    .slice(0, 2)
    .map((word) => word[0])
    .join('')
    .toUpperCase();

export const filterUsers = (
  users: readonly DemoUserRow[],
  query: string,
): readonly DemoUserRow[] => {
  const term = query.trim().toLowerCase();
  return users.filter((user) => `${user.name} ${user.email} ${user.dni}`.toLowerCase().includes(term));
};

