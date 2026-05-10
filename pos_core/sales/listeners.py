import logging
from pos_core.events.bus import on_event
from pos_core.database import async_session_maker
from .models import OrderStatus
from .repository import item_repo, order_repo

logger = logging.getLogger(__name__)

# Ventas no escucha a Cocina por diseño EDA.
# El dominio de Ventas solo emite eventos comerciales.
# Los estados PREPARING/READY son internos de Cocina.
