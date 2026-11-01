"""Envío de correo saliente con `aiosmtplib` (RF-AUT-05, decisión P-08).

Si no hay cuenta de correo configurada, el enlace de recuperación solo se
imprime en la consola del backend: el resto del flujo (token de un solo
uso, vencimiento, restablecimiento) es idéntico.
"""

import logging
from email.message import EmailMessage

import aiosmtplib

from app.config import obtener_settings

logger = logging.getLogger("app.correo")

ASUNTO_RECUPERACION = "San José — restablecer contraseña"


async def enviar_enlace_recuperacion(destinatario: str, enlace: str) -> None:
    """Envía por SMTP o imprime el enlace en consola; nunca lanza hacia arriba."""
    ajustes = obtener_settings()
    if ajustes.smtp_host:
        mensaje = EmailMessage()
        mensaje["From"] = ajustes.smtp_from or ajustes.smtp_user
        mensaje["To"] = destinatario
        mensaje["Subject"] = ASUNTO_RECUPERACION
        mensaje.set_content(
            "Se solicitó restablecer tu contraseña del sistema de vales de la "
            "estación de servicio San José.\n\n"
            "Abre este enlace: el token es de un solo uso y vence en el tiempo "
            "definido por el sistema.\n\n"
            f"{enlace}\n\nSi no fuiste tú, desestima este mensaje."
        )
        try:
            await aiosmtplib.send(
                mensaje,
                hostname=ajustes.smtp_host,
                port=ajustes.smtp_port,
                username=ajustes.smtp_user or None,
                password=ajustes.smtp_password or None,
                start_tls=True,
            )
        except Exception:
            # No exponer el fallo ni el link ni el destinatario en el error 500;
            # en producción SMTP debe funcionar, aquí solo registramos.
            logger.exception("No se pudo enviar el correo de recuperación.")
            _imprimir(destinatario, enlace)
        return
    _imprimir(destinatario, enlace)


def _imprimir(destinatario: str, enlace: str) -> None:
    print(f"[recuperación] destinatario={destinatario} enlace={enlace}", flush=True)
