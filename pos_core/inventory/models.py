from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship

class CategoryBase(SQLModel):
    name: str = Field(index=True, unique=True)
    description: Optional[str] = None
    is_modifier_category: bool = Field(default=False)

class Category(CategoryBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Relación uno-a-muchos con productos
    products: List["Product"] = Relationship(back_populates="category")

class CategoryCreate(CategoryBase):
    pass

class CategoryUpdate(SQLModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_modifier_category: Optional[bool] = None

class IngredientBase(SQLModel):
    name: str = Field(index=True, unique=True)
    measure_type: str = Field(default="unit", description="Tipo de medida: weight, volume, unit")
    unit: str = Field(description="Unidad base de almacenamiento (g, ml, pz)")
    current_stock: float = Field(default=0.0)
    minimum_stock: float = Field(default=0.0)
    
    # Información Nutricional (opcional, para lugar 'fit')
    protein_per_unit: float = Field(default=0.0, description="Proteína por unidad de medida")
    calories_per_unit: float = Field(default=0.0, description="Calorías por unidad de medida")
    carbs_per_unit: float = Field(default=0.0, description="Carbohidratos por unidad de medida")
    fats_per_unit: float = Field(default=0.0, description="Grasas por unidad de medida")

class Ingredient(IngredientBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Un ingrediente puede estar en muchas recetas o modificadores
    recipe_items: List["RecipeItem"] = Relationship(back_populates="ingredient")
    modifiers: List["Modifier"] = Relationship(back_populates="ingredient")

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

class MeasureBase(SQLModel):
    name: str = Field(index=True)
    value: float = Field(description="Valor numérico de la medida")
    unit: str = Field(description="Unidad (oz, ml, g, pz, etc.)")

class Measure(MeasureBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    variants: List["ProductVariant"] = Relationship(back_populates="measure")

class MeasureCreate(MeasureBase):
    pass

class MeasureUpdate(SQLModel):
    name: Optional[str] = None
    value: Optional[float] = None
    unit: Optional[str] = None

class ProductVariantBase(SQLModel):
    product_id: int = Field(foreign_key="product.id")
    measure_id: int = Field(foreign_key="measure.id")
    price: float = Field(description="Precio fijo para esta variante")
    
    # Estimaciones nutricionales manuales por variante
    protein: float = Field(default=0.0)
    calories: float = Field(default=0.0)
    carbs: float = Field(default=0.0)
    fats: float = Field(default=0.0)
    image_url: Optional[str] = None

class ProductVariant(ProductVariantBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    
    product: "Product" = Relationship(back_populates="variants")
    measure: Measure = Relationship(back_populates="variants")
    recipe_items: List["RecipeItem"] = Relationship(back_populates="variant")

class ProductVariantCreate(ProductVariantBase):
    product_id: Optional[int] = None # Permitir que el router lo asigne

class ProductVariantUpdate(SQLModel):
    product_id: Optional[int] = None
    measure_id: Optional[int] = None
    price: Optional[float] = None
    protein: Optional[float] = None
    calories: Optional[float] = None
    carbs: Optional[float] = None
    fats: Optional[float] = None
    image_url: Optional[str] = None

class RecipeItemBase(SQLModel):
    product_id: Optional[int] = Field(default=None, foreign_key="product.id", nullable=True)
    variant_id: Optional[int] = Field(default=None, foreign_key="productvariant.id", nullable=True)
    ingredient_id: Optional[int] = Field(default=None, foreign_key="ingredient.id", nullable=True)
    modifier_group_id: Optional[int] = Field(default=None, foreign_key="modifiergroup.id", ondelete="CASCADE", nullable=True)
    quantity: float = Field(default=0.0, description="Cantidad en la unidad base del ingrediente (g, ml, pz)")
    input_quantity: float = Field(default=0.0, description="Cantidad original ingresada por el chef")
    input_unit: str = Field(default="", description="Unidad original ingresada por el chef (ej: L, oz, kg)")

class RecipeItem(RecipeItemBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    
    product: Optional["Product"] = Relationship(back_populates="recipe_items")
    variant: Optional["ProductVariant"] = Relationship(back_populates="recipe_items")
    ingredient: Optional["Ingredient"] = Relationship(back_populates="recipe_items")
    modifier_group: Optional["ModifierGroup"] = Relationship()

class RecipeItemCreate(RecipeItemBase):
    pass

class RecipeItemUpdate(SQLModel):
    product_id: Optional[int] = None
    variant_id: Optional[int] = None
    ingredient_id: Optional[int] = None
    modifier_group_id: Optional[int] = None
    quantity: Optional[float] = None
    input_quantity: Optional[float] = None
    input_unit: Optional[str] = None

class ProductModifierLink(SQLModel, table=True):
    """Vínculo entre productos y grupos de modificadores (Categorías de opciones)."""
    product_id: int = Field(foreign_key="product.id", primary_key=True, ondelete="CASCADE")
    modifier_group_id: int = Field(foreign_key="modifiergroup.id", primary_key=True, ondelete="CASCADE")

class ModifierGroupBase(SQLModel):
    name: str = Field(index=True)
    description: Optional[str] = None
    min_selection: int = Field(default=0)
    max_selection: int = Field(default=1)
    is_required: bool = Field(default=False)

class ModifierGroup(ModifierGroupBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    
    modifiers: List["Modifier"] = Relationship(back_populates="group", sa_relationship_kwargs={"cascade": "all, delete-orphan"})
    products: List["Product"] = Relationship(back_populates="modifier_groups", link_model=ProductModifierLink)

class ModifierGroupCreate(ModifierGroupBase):
    pass

class ModifierGroupUpdate(SQLModel):
    name: Optional[str] = None
    description: Optional[str] = None
    min_selection: Optional[int] = None
    max_selection: Optional[int] = None
    is_required: Optional[bool] = None

class ModifierBase(SQLModel):
    name: str = Field(index=True)
    extra_price: float = Field(default=0.0)
    modifier_group_id: int = Field(foreign_key="modifiergroup.id", ondelete="CASCADE")
    ingredient_id: Optional[int] = Field(default=None, foreign_key="ingredient.id")
    quantity: float = Field(default=0.0, description="Cantidad base a descontar en unidad base")
    input_quantity: float = Field(default=0.0, description="Cantidad original ingresada")
    input_unit: str = Field(default="", description="Unidad original ingresada")

class Modifier(ModifierBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    
    group: ModifierGroup = Relationship(back_populates="modifiers")
    ingredient: Optional[Ingredient] = Relationship(back_populates="modifiers")
    quantities: List["ModifierQuantity"] = Relationship(back_populates="modifier", sa_relationship_kwargs={"cascade": "all, delete-orphan"})

class ModifierCreate(ModifierBase):
    pass

class ModifierUpdate(SQLModel):
    name: Optional[str] = None
    extra_price: Optional[float] = None
    modifier_group_id: Optional[int] = None
    ingredient_id: Optional[int] = None
    quantity: Optional[float] = None
    input_quantity: Optional[float] = None
    input_unit: Optional[str] = None

class ModifierQuantityBase(SQLModel):
    modifier_id: int = Field(foreign_key="modifier.id", primary_key=True, ondelete="CASCADE")
    measure_id: int = Field(foreign_key="measure.id", primary_key=True, ondelete="CASCADE")
    quantity: float

class ModifierQuantity(ModifierQuantityBase, table=True):
    modifier: "Modifier" = Relationship(back_populates="quantities")
    measure: Measure = Relationship()

class ModifierQuantityUpdate(SQLModel):
    quantity: Optional[float] = None

class ProductBase(SQLModel):
    name: str = Field(index=True)
    description: Optional[str] = None
    recipe_markdown: Optional[str] = Field(
        default=None,
        description="Instrucciones de preparación en formato Markdown. Solo visible en cocina."
    )
    price: float
    image_url: Optional[str] = None
    stock: Optional[int] = 0
    is_active: bool = Field(default=True)
    category_id: Optional[int] = Field(default=None, foreign_key="category.id")
    protein: float = Field(default=0.0)
    calories: float = Field(default=0.0)
    carbs: float = Field(default=0.0)
    fats: float = Field(default=0.0)

class Product(ProductBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    
    category: Optional[Category] = Relationship(back_populates="products")
    recipe_items: List[RecipeItem] = Relationship(back_populates="product")
    variants: List[ProductVariant] = Relationship(back_populates="product", sa_relationship_kwargs={"lazy": "selectin"})
    modifier_groups: List[ModifierGroup] = Relationship(back_populates="products", link_model=ProductModifierLink, sa_relationship_kwargs={"lazy": "selectin"})

class ProductCreate(ProductBase):
    pass

class ProductUpdate(SQLModel):
    name: Optional[str] = None
    description: Optional[str] = None
    recipe_markdown: Optional[str] = None
    price: Optional[float] = None
    image_url: Optional[str] = None
    stock: Optional[int] = None
    is_active: Optional[bool] = None
    category_id: Optional[int] = None
    protein: Optional[float] = None
    calories: Optional[float] = None
    carbs: Optional[float] = None
    fats: Optional[float] = None
    modifier_groups: Optional[List[dict]] = None # To handle incoming modifier groups IDs/Dicts gracefully

class POSPresetBase(SQLModel):
    product_id: int = Field(foreign_key="product.id")
    name: str = Field(description="Nombre corto del preset (ej: 'Mediano Coco')")
    modifier_ids_json: str = Field(description="JSON array de IDs de modificadores seleccionados")

class POSPreset(POSPresetBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

class POSPresetCreate(POSPresetBase):
    pass
# --- Modelos de Lectura (Read) para respuestas API con relaciones ---

class IngredientRead(IngredientBase):
    id: int

class MeasureRead(MeasureBase):
    id: int

class ModifierRead(ModifierBase):
    id: int
    ingredient: Optional[IngredientRead] = None

class ModifierGroupRead(ModifierGroupBase):
    id: int
    modifiers: List[ModifierRead] = []

class ProductVariantRead(ProductVariantBase):
    id: int
    measure: MeasureRead

class ProductRead(ProductBase):
    id: int
    category: Optional[CategoryBase] = None
    variants: List[ProductVariantRead] = []
    modifier_groups: List[ModifierGroupRead] = []
    recipe_markdown: Optional[str] = None

class CategoryRead(CategoryBase):
    id: int
    products: List[ProductRead] = []

# Resolver referencias circulares si las hay
ProductRead.model_rebuild()
ModifierGroupRead.model_rebuild()
CategoryRead.model_rebuild()
