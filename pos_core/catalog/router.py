from fastapi import APIRouter, Depends, HTTPException, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
import os
import uuid
import shutil
from typing import List, Optional

from pos_core.database import get_session
from .models import (
    Category, CategoryCreate, CategoryUpdate, CategoryRead, 
    Product, ProductCreate, ProductUpdate, ProductRead, 
    RecipeItem, RecipeItemCreate, 
    ModifierGroup, ModifierGroupCreate, ModifierGroupUpdate, ModifierGroupRead, 
    Modifier, ModifierCreate, ModifierUpdate, ModifierRead, 
    POSPreset, POSPresetCreate, 
    Measure, MeasureCreate, MeasureRead, 
    ProductVariant, ProductVariantCreate, ProductVariantUpdate, ProductVariantRead,
    Tax, TaxCreate, TaxUpdate, TaxRead
)
from pos_core.inventory.models import Ingredient
from pos_core.inventory import unit_converter
from .services import (
    category_service, product_service, modifier_service, recipe_service
)
from pos_core.auth.dependencies import require_role

router = APIRouter()

# --- Endpoints de Categorías ---

@router.get("/categories", response_model=List[CategoryRead])
async def list_categories(db: AsyncSession = Depends(get_session)):
    """Listado de todas las categorías de productos."""
    return await category_service.get_categories(db)

@router.post("/categories", response_model=Category, dependencies=[Depends(require_role("admin"))])
async def create_category(category: CategoryCreate, db: AsyncSession = Depends(get_session)):
    """Crea una nueva categoría."""
    return await category_service.create_category(db, category)

@router.put("/categories/{category_id}", response_model=Category, dependencies=[Depends(require_role("admin"))])
async def update_category(category_id: int, category: CategoryUpdate, db: AsyncSession = Depends(get_session)):
    """Actualiza una categoría existente."""
    updated_category = await category_service.update_category(db, category_id, category)
    if not updated_category:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")
    return updated_category

@router.delete("/categories/{category_id}", dependencies=[Depends(require_role("admin"))])
async def delete_category(category_id: int, db: AsyncSession = Depends(get_session)):
    """Elimina una categoría."""
    success = await category_service.delete_category(db, category_id)
    if not success:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")
    return {"detail": "Categoría eliminada"}

# --- Endpoints de Productos ---

@router.get("/products", response_model=List[ProductRead])
async def list_products(
    category_id: Optional[int] = None, 
    include_inactive: bool = False, 
    search: Optional[str] = None,
    offset: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_session)
):
    """Listado de productos con soporte para paginación y búsqueda."""
    return await product_service.get_products(
        db, 
        category_id=category_id, 
        include_inactive=include_inactive, 
        search=search, 
        offset=offset, 
        limit=limit
    )

@router.post("/products", response_model=ProductRead, dependencies=[Depends(require_role("admin"))])
async def create_product(product: ProductCreate, db: AsyncSession = Depends(get_session)):
    """Registra un nuevo producto en el catálogo."""
    return await product_service.create_product(db, product)

@router.put("/products/{product_id}", response_model=ProductRead, dependencies=[Depends(require_role("admin"))])
async def update_product(product_id: int, product: ProductUpdate, db: AsyncSession = Depends(get_session)):
    """Actualiza un producto existente."""
    updated_product = await product_service.update_product(db, product_id, product)
    if not updated_product:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return updated_product

@router.delete("/products/{product_id}", dependencies=[Depends(require_role("admin"))])
async def delete_product(product_id: int, db: AsyncSession = Depends(get_session)):
    """Desactiva un producto."""
    success = await product_service.delete_product(db, product_id)
    if not success:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return {"detail": "Producto desactivado"}

# --- Endpoints de Recetas ---

@router.post("/products/{product_id}/ingredients", response_model=RecipeItem, dependencies=[Depends(require_role("admin"))])
async def add_ingredient_to_recipe(
    product_id: int, 
    ingredient_id: int, 
    quantity: float, 
    input_quantity: Optional[float] = None,
    input_unit: Optional[str] = None,
    db: AsyncSession = Depends(get_session)
):
    recipe_item = RecipeItem(
        product_id=product_id, 
        ingredient_id=ingredient_id, 
        quantity=quantity,
        input_quantity=input_quantity,
        input_unit=input_unit
    )
    return await recipe_service.add_ingredient_to_product(db, recipe_item)


@router.get("/products/{product_id}/recipe", response_model=List[RecipeItem])
async def get_recipe(product_id: int, db: AsyncSession = Depends(get_session)):
    return await recipe_service.get_product_recipe(db, product_id)

@router.post("/products/{product_id}/child-products", response_model=RecipeItem, dependencies=[Depends(require_role("admin"))])
async def add_child_product_to_recipe(
    product_id: int, 
    child_product_id: int, 
    quantity: float = 1.0, 
    child_variant_id: Optional[int] = None,
    db: AsyncSession = Depends(get_session)
):
    recipe_item = RecipeItem(
        product_id=product_id, 
        child_product_id=child_product_id, 
        child_variant_id=child_variant_id,
        quantity=quantity
    )
    return await recipe_service.add_ingredient_to_product(db, recipe_item)

@router.post("/variants/{variant_id}/ingredients", response_model=RecipeItem, dependencies=[Depends(require_role("admin"))])
async def add_ingredient_to_variant(
    variant_id: int, 
    ingredient_id: int, 
    quantity: float, 
    input_quantity: Optional[float] = None,
    input_unit: Optional[str] = None,
    db: AsyncSession = Depends(get_session)
):
    recipe_item = RecipeItem(
        variant_id=variant_id, 
        ingredient_id=ingredient_id, 
        quantity=quantity,
        input_quantity=input_quantity,
        input_unit=input_unit
    )
    return await recipe_service.add_ingredient_to_product(db, recipe_item)

@router.post("/variants/{variant_id}/modifier-groups", response_model=RecipeItem, dependencies=[Depends(require_role("admin"))])
async def add_group_to_variant(
    variant_id: int, 
    modifier_group_id: int, 
    quantity: float, 
    input_quantity: Optional[float] = None,
    input_unit: Optional[str] = None,
    db: AsyncSession = Depends(get_session)
):
    recipe_item = RecipeItem(
        variant_id=variant_id, 
        modifier_group_id=modifier_group_id, 
        quantity=quantity,
        input_quantity=input_quantity or quantity,
        input_unit=input_unit or ""
    )
    return await recipe_service.add_ingredient_to_product(db, recipe_item)

@router.get("/variants/{variant_id}/recipe", response_model=List[RecipeItem])
async def get_variant_recipe(variant_id: int, db: AsyncSession = Depends(get_session)):
    return await recipe_service.get_variant_recipe(db, variant_id)

# --- Endpoints de Modificadores y Presets ---

@router.get("/modifier-groups", response_model=List[ModifierGroupRead])
async def list_modifier_groups(db: AsyncSession = Depends(get_session)):
    return await modifier_service.get_modifier_groups(db)

@router.post("/modifier-groups", response_model=ModifierGroupRead, dependencies=[Depends(require_role("admin"))])
async def create_modifier_group(group: ModifierGroupCreate, db: AsyncSession = Depends(get_session)):
    return await modifier_service.create_modifier_group(db, group)

@router.put("/modifier-groups/{group_id}", response_model=ModifierGroupRead, dependencies=[Depends(require_role("admin"))])
async def update_modifier_group(group_id: int, group: ModifierGroupUpdate, db: AsyncSession = Depends(get_session)):
    updated_group = await modifier_service.update_modifier_group(db, group_id, group)
    if not updated_group:
        raise HTTPException(status_code=404, detail="Grupo no encontrado")
    return updated_group

@router.delete("/modifier-groups/{group_id}", dependencies=[Depends(require_role("admin"))])
async def delete_modifier_group(group_id: int, db: AsyncSession = Depends(get_session)):
    success = await modifier_service.delete_modifier_group(db, group_id)
    if not success:
        raise HTTPException(status_code=404, detail="Grupo no encontrado")
    return {"detail": "Grupo eliminado"}

@router.post("/modifiers", response_model=ModifierRead, dependencies=[Depends(require_role("admin"))])
async def create_modifier(modifier: ModifierCreate, db: AsyncSession = Depends(get_session)):
    return await modifier_service.create_modifier(db, modifier)

@router.put("/modifiers/{modifier_id}", response_model=ModifierRead, dependencies=[Depends(require_role("admin"))])
async def update_modifier(modifier_id: int, modifier: ModifierUpdate, db: AsyncSession = Depends(get_session)):
    updated_modifier = await modifier_service.update_modifier(db, modifier_id, modifier)
    if not updated_modifier:
        raise HTTPException(status_code=404, detail="Modificador no encontrado")
    return updated_modifier

@router.delete("/modifiers/{modifier_id}", dependencies=[Depends(require_role("admin"))])
async def delete_modifier(modifier_id: int, db: AsyncSession = Depends(get_session)):
    success = await modifier_service.delete_modifier(db, modifier_id)
    if not success:
        raise HTTPException(status_code=404, detail="Modificador no encontrado")
    return {"detail": "Modificador eliminado"}

@router.post("/modifiers/{modifier_id}/measures/{measure_id}/quantity", dependencies=[Depends(require_role("admin"))])
async def update_modifier_measure_quantity(modifier_id: int, measure_id: int, quantity: float, db: AsyncSession = Depends(get_session)):
    return await modifier_service.update_modifier_quantity(db, modifier_id, measure_id, quantity)

@router.post("/products/{product_id}/modifier-groups/{group_id}", dependencies=[Depends(require_role("admin"))])
async def link_group_to_product(product_id: int, group_id: int, db: AsyncSession = Depends(get_session)):
    return await modifier_service.link_modifier_group_to_product(db, product_id, group_id)

@router.get("/products/{product_id}/presets", response_model=List[POSPreset])
async def get_presets(product_id: int, db: AsyncSession = Depends(get_session)):
    return await product_service.get_product_presets(db, product_id)

@router.post("/products/{product_id}/presets", response_model=POSPreset)
async def create_preset(product_id: int, name: str, modifier_ids: List[int], db: AsyncSession = Depends(get_session)):
    import json
    preset = POSPreset(product_id=product_id, name=name, modifier_ids_json=json.dumps(modifier_ids))
    return await product_service.create_preset(db, preset)

# --- Endpoints de Medidas (Sizes) ---

@router.get("/measures", response_model=List[Measure])
async def list_measures(db: AsyncSession = Depends(get_session)):
    return await product_service.get_measures(db)

@router.post("/measures", response_model=Measure, dependencies=[Depends(require_role("admin"))])
async def create_measure(measure: MeasureCreate, db: AsyncSession = Depends(get_session)):
    return await product_service.create_measure(db, measure)

# --- Endpoints de Impuestos (Taxes) ---

@router.get("/taxes", response_model=List[TaxRead])
async def list_taxes(db: AsyncSession = Depends(get_session)):
    """Listado de impuestos disponibles en el catálogo."""
    return await product_service.get_taxes(db)

@router.post("/taxes", response_model=TaxRead, dependencies=[Depends(require_role("admin"))])
async def create_tax(tax: TaxCreate, db: AsyncSession = Depends(get_session)):
    return await product_service.create_tax(db, tax)

@router.put("/taxes/{tax_id}", response_model=TaxRead, dependencies=[Depends(require_role("admin"))])
async def update_tax(tax_id: int, tax: TaxUpdate, db: AsyncSession = Depends(get_session)):
    updated_tax = await product_service.update_tax(db, tax_id, tax)
    if not updated_tax:
        raise HTTPException(status_code=404, detail="Impuesto no encontrado")
    return updated_tax

@router.delete("/taxes/{tax_id}", dependencies=[Depends(require_role("admin"))])
async def delete_tax(tax_id: int, db: AsyncSession = Depends(get_session)):
    success = await product_service.delete_tax(db, tax_id)
    if not success:
        raise HTTPException(status_code=404, detail="Impuesto no encontrado")
    return {"detail": "Impuesto eliminado"}


# --- Endpoints de Variantes de Producto ---

@router.get("/products/{product_id}/variants", response_model=List[ProductVariantRead])
async def list_variants(product_id: int, db: AsyncSession = Depends(get_session)):
    return await product_service.get_variants_by_product(db, product_id)

@router.post("/products/{product_id}/variants", response_model=ProductVariantRead, dependencies=[Depends(require_role("admin"))])
async def create_variant(product_id: int, variant: ProductVariantCreate, db: AsyncSession = Depends(get_session)):
    variant.product_id = product_id
    return await product_service.create_variant(db, variant)

@router.put("/variants/{variant_id}", response_model=ProductVariantRead, dependencies=[Depends(require_role("admin"))])
async def update_variant(variant_id: int, variant: ProductVariantUpdate, db: AsyncSession = Depends(get_session)):
    updated_variant = await product_service.update_variant(db, variant_id, variant)
    if not updated_variant:
        raise HTTPException(status_code=404, detail="Variante no encontrada")
    return updated_variant

@router.delete("/variants/{variant_id}", dependencies=[Depends(require_role("admin"))])
async def delete_variant(variant_id: int, db: AsyncSession = Depends(get_session)):
    success = await product_service.delete_variant(db, variant_id)
    if not success:
        raise HTTPException(status_code=404, detail="Variante no encontrada")
    return {"detail": "Variante eliminada"}

@router.delete("/variants/{variant_id}/recipe", dependencies=[Depends(require_role("admin"))])
async def clear_variant_recipe(variant_id: int, db: AsyncSession = Depends(get_session)):
    await product_service.clear_variant_recipe(db, variant_id)
    return {"detail": "Receta eliminada"}
