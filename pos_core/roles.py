from typing import Dict, Set

class PosRole:
    ADMIN   = "admin"
    MANAGER = "manager"
    CASHIER = "cashier"
    KITCHEN = "kitchen"
    WAITER  = "waiter"

class Permission:
    TAKE_ORDERS          = "can_take_orders"
    SEND_TO_KITCHEN      = "can_send_to_kitchen"
    CHARGE               = "can_charge"
    MANAGE_KITCHEN_STATUS = "can_manage_kitchen_status"
    VIEW_ORDERS          = "can_view_orders"
    MANAGE_TABLES        = "can_manage_tables"
    VIEW_KITCHEN         = "can_view_kitchen"
    MANAGE_MENU          = "can_manage_menu"
    MANAGE_INVENTORY     = "can_manage_inventory"
    MANAGE_USERS         = "can_manage_users"
    MANAGE_SHIFTS        = "can_manage_shifts"
    VIEW_REPORTS         = "can_view_reports"
    MANAGE_SETTINGS       = "can_manage_settings"

_ALL_PERMISSIONS = [v for k, v in vars(Permission).items() if not k.startswith("_") and isinstance(v, str)]

ROLE_PRESETS: Dict[str, Dict[str, bool]] = {
    PosRole.ADMIN: {p: True for p in _ALL_PERMISSIONS},
    PosRole.MANAGER: {
        Permission.TAKE_ORDERS: True,
        Permission.SEND_TO_KITCHEN: True,
        Permission.CHARGE: True,
        Permission.MANAGE_KITCHEN_STATUS: True,
        Permission.VIEW_ORDERS: True,
        Permission.MANAGE_TABLES: True,
        Permission.VIEW_KITCHEN: True,
        Permission.MANAGE_MENU: True,
        Permission.MANAGE_INVENTORY: True,
        Permission.MANAGE_USERS: False,
        Permission.MANAGE_SHIFTS: True,
        Permission.VIEW_REPORTS: True,
        Permission.MANAGE_SETTINGS: True,
    },
    PosRole.CASHIER: {
        Permission.TAKE_ORDERS: True,
        Permission.SEND_TO_KITCHEN: True,
        Permission.CHARGE: True,
        Permission.MANAGE_KITCHEN_STATUS: True,
        Permission.VIEW_ORDERS: True,
        Permission.MANAGE_TABLES: True,
        Permission.VIEW_KITCHEN: True,
        Permission.MANAGE_MENU: False,
        Permission.MANAGE_INVENTORY: False,
        Permission.MANAGE_USERS: False,
        Permission.MANAGE_SHIFTS: True,
        Permission.VIEW_REPORTS: True,
    },
    PosRole.KITCHEN: {
        Permission.TAKE_ORDERS: False,
        Permission.SEND_TO_KITCHEN: False,
        Permission.CHARGE: False,
        Permission.MANAGE_KITCHEN_STATUS: True,
        Permission.VIEW_ORDERS: True,
        Permission.MANAGE_TABLES: False,
        Permission.VIEW_KITCHEN: True,
        Permission.MANAGE_MENU: False,
        Permission.MANAGE_INVENTORY: False,
        Permission.MANAGE_USERS: False,
        Permission.MANAGE_SHIFTS: False,
        Permission.VIEW_REPORTS: False,
    },
    PosRole.WAITER: {
        Permission.TAKE_ORDERS: True,
        Permission.SEND_TO_KITCHEN: True,
        Permission.CHARGE: False,
        Permission.MANAGE_KITCHEN_STATUS: False,
        Permission.VIEW_ORDERS: True,
        Permission.MANAGE_TABLES: True,
        Permission.VIEW_KITCHEN: False,
        Permission.MANAGE_MENU: False,
        Permission.MANAGE_INVENTORY: False,
        Permission.MANAGE_USERS: False,
        Permission.MANAGE_SHIFTS: False,
        Permission.VIEW_REPORTS: False,
    },
}

# 'operator' es el rol legacy por defecto de omni_auth — se mapea a admin
ROLE_PRESETS["operator"] = ROLE_PRESETS[PosRole.ADMIN].copy()

def resolve_permissions(role: str, metadata_permissions: dict) -> Dict[str, bool]:
    """
    Combina el preset del rol con los overrides individuales del usuario.
    Si el rol es desconocido, otorga todos los permisos (fail-open)
    para evitar que usuarios legítimos queden bloqueados.
    """
    base = ROLE_PRESETS.get(role, ROLE_PRESETS[PosRole.ADMIN]).copy()
    base.update(metadata_permissions)
    return base
