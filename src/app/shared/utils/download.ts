/**
 * Descarga un `Blob` (PDF/Excel/CSV de FastAPI) sin dejar object URLs vivos.
 * Crea un ancla temporal, dispara la descarga y revoca la URL en el siguiente
 * ciclo para que el navegador alcance a iniciarla.
 */
export function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  link.rel = 'noopener';
  link.style.display = 'none';

  document.body.appendChild(link);
  link.click();
  link.remove();

  setTimeout(() => URL.revokeObjectURL(url), 0);
}
