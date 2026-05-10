import os
import importlib
import logging
import sys

logger = logging.getLogger(__name__)

def discover_event_providers():
    """
    Escanea automáticamente el paquete 'pos_core' buscando módulos llamados 'providers'.
    """
    _discover_modules_by_suffix(".providers", "proveedores de eventos")

def discover_event_listeners():
    """
    Escanea automáticamente el paquete 'pos_core' buscando módulos llamados 'listeners'.
    """
    _discover_modules_by_suffix(".listeners", "suscriptores de eventos internos")

def _discover_modules_by_suffix(suffix: str, label: str):
    """
    Lógica genérica para encontrar e importar módulos con un sufijo específico.
    """
    import pos_core
    pkg_path = os.path.dirname(pos_core.__file__)
    
    print(f"\n📡 [Discovery] Buscando {label}...")
    
    count = 0
    # Recorremos manualmente los directorios para mayor fiabilidad
    for root, dirs, files in os.walk(pkg_path):
        for file in files:
            if file.endswith(".py") and file.replace(".py", "").endswith(suffix.split(".")[-1]):
                # Construir el nombre del módulo
                rel_path = os.path.relpath(os.path.join(root, file), os.path.dirname(pkg_path))
                module_name = rel_path.replace(os.path.sep, ".").replace(".py", "")
                
                # Filtrar para asegurar que coincida con el sufijo completo (ej: .listeners)
                if module_name.endswith(suffix):
                    try:
                        print(f"🔍 [Discovery] Cargando: {module_name}")
                        importlib.import_module(module_name)
                        count += 1
                    except Exception as e:
                        print(f"❌ [Discovery] Error crítico en {module_name}: {e}")
                        logger.error(f"Error cargando módulo {module_name}: {e}", exc_info=True)

    print(f"✅ [Discovery] {label} finalizado. ({count} módulos cargados)\n")
