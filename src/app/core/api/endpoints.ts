/** Rutas exactas del `openapi.json` (prefijo `/api/v1` viene de `environment.apiUrl`). */
export const API_ENDPOINTS = {
  health: {
    live: '/health/live',
    ready: '/health/ready',
  },
  auth: {
    login: '/auth/login',
    logout: '/auth/logout',
    me: '/auth/me',
  },
  users: {
    base: '/users',
    byId: (userId: string) => `/users/${encodeURIComponent(userId)}`,
    role: (userId: string) => `/users/${encodeURIComponent(userId)}/role`,
    status: (userId: string) => `/users/${encodeURIComponent(userId)}/status`,
  },
  branches: '/branches',
  fuelTypes: '/fuel-types',
  purchaseOrders: {
    base: '/purchase-orders',
    byId: (orderId: string) => `/purchase-orders/${encodeURIComponent(orderId)}`,
    attendances: (orderId: string) =>
      `/purchase-orders/${encodeURIComponent(orderId)}/attendances`,
  },
  vouchers: {
    base: '/vouchers',
    attended: '/vouchers/attended',
    byId: (voucherId: string) => `/vouchers/${encodeURIComponent(voucherId)}`,
    descriptiveData: (voucherId: string) =>
      `/vouchers/${encodeURIComponent(voucherId)}/descriptive-data`,
    attendances: (voucherId: string) =>
      `/vouchers/${encodeURIComponent(voucherId)}/attendances`,
  },
  reports: {
    dashboard: '/reports/dashboard',
    purchaseOrders: '/reports/purchase-orders',
    purchaseOrdersExport: '/reports/purchase-orders/export',
    attendances: '/reports/attendances',
    attendancesExport: '/reports/attendances/export',
  },
  ocr: {
    purchaseOrderPreviews: '/ocr/purchase-order-previews',
  },
} as const;

/** Cabecera requerida por los dos endpoints de atenciones. */
export const IDEMPOTENCY_HEADER = 'Idempotency-Key';
