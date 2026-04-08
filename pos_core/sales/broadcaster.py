"""
Broadcaster de eventos para comunicación en tiempo real.

Implementa un patrón pub/sub simple usando asyncio.Condition.
Cuando cualquier endpoint de escritura (crear orden, cambiar estado, etc.)
llama a `notify()`, todos los listeners SSE activos reciben la notificación
y emiten los datos actualizados al cliente.
"""
import asyncio


class OrderBroadcaster:
    """
    Broadcaster centralizado para notificar cambios en órdenes.
    Se instancia una sola vez en el lifespan de la app (singleton).
    """

    def __init__(self) -> None:
        self._condition = asyncio.Condition()

    async def notify(self) -> None:
        """Notifica a todos los listeners activos de que hay un cambio."""
        async with self._condition:
            self._condition.notify_all()

    async def wait_for_update(self) -> None:
        """Bloquea hasta que se llame a notify(). Usar dentro de un SSE generator."""
        async with self._condition:
            await self._condition.wait()


# Instancia global — se importa desde router.py y service.py
broadcaster = OrderBroadcaster()
