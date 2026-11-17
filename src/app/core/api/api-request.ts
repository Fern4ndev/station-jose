export function isApiRequest(url: string, baseUrl: string): boolean {
  try {
    const base = new URL(baseUrl, document.baseURI);
    const target = new URL(url, document.baseURI);
    const path = base.pathname.replace(/\/+$/, '');
    return target.origin === base.origin && (target.pathname === path || target.pathname.startsWith(`${path}/`));
  } catch {
    return false;
  }
}
