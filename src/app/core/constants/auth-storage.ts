// Reserved storage keys. The current session is kept in memory; the backend
// does not expose refresh tokens. Do not treat these keys as an active session.
export const ACCESS_TOKEN_KEY = 'sanjose_token';
export const REFRESH_TOKEN_KEY = 'sanjose_refresh_token';
export const ACCESS_TOKEN_EXPIRES_AT_KEY = 'sanjose_token_expires_at';
export const REFRESH_TOKEN_EXPIRES_AT_KEY = 'sanjose_refresh_expires_at';
export const SESSION_KEY = 'sanjose_session';
