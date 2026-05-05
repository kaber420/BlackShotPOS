import os
import importlib
import logging
import pkgutil

logger = logging.getLogger(__name__)

def discover_event_providers():
    """
    Escanea automáticamente el paquete 'pos_core' buscando módulos llamados 'providers'
    e impórtalos para activar los decoradores de registro de eventos.
    """
    print("\n📡 [Discovery] Buscando proveedores de eventos...")
    
    import pos_core
    # La ruta base es la carpeta que CONTIENE pos_core, o la ruta de pos_core mismo.
    # Vamos a usar la ruta del paquete pos_core.
    pkg_path = os.path.dirname(pos_core.__file__)
    
    # Escaneamos los subcarpetas de pos_core
    for loader, module_name, is_pkg in pkgutil.walk_packages([pkg_path], prefix="pos_core."):
        if module_name.endswith(".providers"):
            try:
                print(f"🔍 [Discovery] Cargando: {module_name}")
                importlib.import_module(module_name)
            except Exception as e:
                print(f"❌ [Discovery] Error en {module_name}: {e}")

    print("✅ [Discovery] Finalizado.\n")
