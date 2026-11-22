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
  readonly email: string;
  readonly dni: string;
  readonly role: UserRole;
  readonly branch: string;
  readonly active: boolean;
}

export interface UserDraft {
  readonly name: string;
  readonly email: string;
  readonly dni: string;
  readonly role: UserRoleValue;
  readonly branch: string;
}

/** Opciones del formulario en el orden del mockup. */
export const USER_ROLES = (['OFFICE', 'ATTENDANT', 'ADMIN'] as const).map((value) => ({
  value,
  label: ROLE_DETAILS[value].label,
}));

/** Filas del panel "Roles del sistema", con el Administrador primero. */
export const ROLE_SUMMARY = (['ADMIN', 'OFFICE', 'ATTENDANT'] as const).map(
  (value) => ROLE_DETAILS[value],
);

export const DEMO_USERS: readonly DemoUserRow[] = [
  {
    id: 'u1',
    name: 'Carlos Mendoza',
    email: 'carlos.mendoza@estacion.test',
    dni: '45812036',
    role: 'Administrador',
    branch: '—',
    active: true,
  },
  {
    id: 'u2',
    name: 'María Paredes',
    email: 'maria.paredes@estacion.test',
    dni: '42761590',
    role: 'Oficina',
    branch: 'Ambas sedes',
    active: true,
  },
  {
    id: 'u3',
    name: 'Ana Salazar',
    email: 'ana.salazar@estacion.test',
    dni: '41620875',
    role: 'Oficina',
    branch: 'Ambas sedes',
    active: true,
  },
  {
    id: 'u4',
    name: 'Luis Cárdenas',
    email: 'luis.cardenas@estacion.test',
    dni: '43892014',
    role: 'Grifero',
    branch: 'San José',
    active: true,
  },
  {
    id: 'u5',
    name: 'Rosa Méndez',
    email: 'rosa.mendez@estacion.test',
    dni: '46200851',
    role: 'Grifero',
    branch: 'Santa Marta',
    active: true,
  },
  {
    id: 'u6',
    name: 'Jorge Silva',
    email: 'jorge.silva@estacion.test',
    dni: '42917360',
    role: 'Grifero',
    branch: 'Santa Marta',
    active: false,
  },
];

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

/** La oficina administra ambas sedes; el administrador no queda atado a una. */
export const userBranch = (role: UserRoleValue, branch: string): string => {
  if (role === 'ATTENDANT') {
    return branch;
  }
  return role === 'OFFICE' ? 'Ambas sedes' : '—';
};

export function createUser(draft: UserDraft): DemoUserRow {
  return {
    id: `u-${draft.email.toLowerCase()}`,
    name: draft.name.trim(),
    email: draft.email.trim(),
    dni: draft.dni.trim(),
    role: ROLE_DETAILS[draft.role].label,
    branch: userBranch(draft.role, draft.branch),
    active: true,
  };
}
