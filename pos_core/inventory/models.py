from typing import Optional, List, TYPE_CHECKING
from enum import Enum
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship

if TYPE_CHECKING:
    # Para tipado, aunque intentamos no depender fuertemente
    pass

class IngredientBase(SQLModel):
    name: str = Field(index=True, unique=True)
    measure_type: str = Field(default="unit", description="Tipo de medida: weight, volume, unit")
    unit: str = Field(description="Unidad base de almacenamiento (g, ml, pz)")
    current_stock: float = Field(default=0.0)
    minimum_stock: float = Field(default=0.0)
    
    # Información Nutricional
    protein_per_unit: float = Field(default=0.0, description="Proteína por unidad de medida")
    calories_per_unit: float = Field(default=0.0, description="Calorías por unidad de medida")
    carbs_per_unit: float = Field(default=0.0, description="Carbohidratos por unidad de medida")
    fats_per_unit: float = Field(default=0.0, description="Grasas por unidad de medida")

class Ingredient(IngredientBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # No back_populates a Catalog para evitar acoplamiento. 
    # El Catálogo conoce al Inventario, pero no al revés.
    batches: List["IngredientBatch"] = Relationship(back_populates="ingredient")

class IngredientCreate(IngredientBase):
    pass

class IngredientUpdate(SQLModel):
    name: Optional[str] = None
    measure_type: Optional[str] = None
    unit: Optional[str] = None
    current_stock: Optional[float] = None
    minimum_stock: Optional[float] = None
    protein_per_unit: Optional[float] = None
    calories_per_unit: Optional[float] = None
    carbs_per_unit: Optional[float] = None
    fats_per_unit: Optional[float] = None

# --- Registro de Merma / Ajustes de Inventario ---

class AdjustmentReason(str, Enum):
    # Salidas (Decremento)
    WASTE = "WASTE"
    EXPIRED = "EXPIRED"
    ERROR = "ERROR"
    THEFT = "THEFT"
    PERSONAL_CONSUMPTION = "PERSONAL_CONSUMPTION"
    
    # Entradas (Incremento)
    PURCHASE = "PURCHASE"
    RESTOCK = "RESTOCK"
    
    # Ajustes (Seteo Directo / Corrección)
    PHYSICAL_COUNT = "PHYSICAL_COUNT"
    CORRECTION = "CORRECTION"

class InventoryAdjustmentBase(SQLModel):
    ingredient_id: int = Field(foreign_key="ingredient.id")
    quantity: float = Field(description="Cantidad descontada (en unidad base)")
    reason: AdjustmentReason = Field(default=AdjustmentReason.WASTE)
    note: Optional[str] = None
    actor_uuid: Optional[str] = None
    actor_name: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    expiration_date: Optional[datetime] = None # Para entradas que generan lotes

class InventoryAdjustment(InventoryAdjustmentBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    ingredient: "Ingredient" = Relationship()

class InventoryAdjustmentCreate(SQLModel):
    ingredient_id: int
    quantity: float
    reason: AdjustmentReason
    note: Optional[str] = None
    expiration_date: Optional[datetime] = None

class IngredientBatch(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    ingredient_id: int = Field(foreign_key="ingredient.id")
    original_quantity: float = Field(description="Cantidad inicial del lote")
    current_quantity: float = Field(description="Cantidad restante")
    expiration_date: Optional[datetime] = None
    arrival_date: datetime = Field(default_factory=datetime.utcnow)
    
    ingredient: "Ingredient" = Relationship(back_populates="batches")

class IngredientBatchRead(SQLModel):
    id: int
    current_quantity: float
    expiration_date: Optional[datetime]
    arrival_date: datetime

class IngredientRead(IngredientBase):
    id: int
    batches: List[IngredientBatchRead] = []

IngredientRead.model_rebuild()
