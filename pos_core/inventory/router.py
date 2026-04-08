from fastapi import APIRouter, Depends, HTTPException, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
import os
import uuid
import shutil
from pos_core.database import get_session
from .models import (
    Category, CategoryCreate, CategoryUpdate, CategoryRead, 
    Product, ProductCreate, ProductUpdate, ProductRead, 
    Ingredient, IngredientCreate, IngredientUpdate, IngredientRead, 
    RecipeItem, RecipeItemCreate, 
    ModifierGroup, ModifierGroupCreate, ModifierGroupUpdate, ModifierGroupRead, 
    Modifier, ModifierCreate, ModifierUpdate, ModifierRead, 
    POSPreset, POSPresetCreate, 
    Measure, MeasureCreate, MeasureRead, 
    ProductVariant, ProductVariantCreate, ProductVariantUpdate, ProductVariantRead
)
from . import service
from omni_auth.security import verify_omni_token, require_role
from typing import List, Optional

router = APIRouter()

# --- Endpoints de Gestión de Archivos ---

@router.post("/upload", dependencies=[Depends(require_role("admin"))])
async def upload_image(file: UploadFile = File(...)):
    """Sube una imagen al servidor y retorna su URL relativa."""
    # Validar extensión
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in [".jpg", ".jpeg", ".png", ".webp", ".gif"]:
        raise HTTPException(status_code=400, detail="Formato de imagen no permitido")
    
    # Generar nombre único
    filename = f"{uuid.uuid4()}{ext}"
    file_path = os.path.join("data/img", filename)
    
    # Guardar archivo
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    return {"url": f"/uploads/{filename}", "filename": filename}

@router.delete("/upload/{filename}", dependencies=[Depends(require_role("admin"))])
async def delete_image(filename: str):
    """Elimina un archivo del servidor."""
    file_path = os.path.join("data/img", filename)
    if os.path.exists(file_path):
        os.remove(file_path)
        return {"detail": "Archivo eliminado"}
    raise HTTPException(status_code=404, detail="Archivo no encontrado")

@router.get("/categories", response_model=List[CategoryRead])
async def list_categories(db: AsyncSession = Depends(get_session)):
    """Listado de todas las categorías de productos."""
    return await service.get_categories(db)

@router.post("/categories", response_model=Category, dependencies=[Depends(require_role("admin"))])
async def create_category(category: CategoryCreate, db: AsyncSession = Depends(get_session)):
    """Crea una nueva categoría (ejemplo: Bebidas, Postres). Requiere rol: admin."""
    return await service.create_category(db, category)

@router.put("/categories/{category_id}", response_model=Category, dependencies=[Depends(require_role("admin"))])
async def update_category(category_id: int, category: CategoryUpdate, db: AsyncSession = Depends(get_session)):
    """Actualiza una categoría existente. Requiere rol: admin."""
    updated_category = await service.update_category(db, category_id, category)
    if not updated_category:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")
    return updated_category

@router.delete("/categories/{category_id}", dependencies=[Depends(require_role("admin"))])
async def delete_category(category_id: int, db: AsyncSession = Depends(get_session)):
    """Elimina una categoría. Requiere rol: admin."""
    success = await service.delete_category(db, category_id)
    if not success:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")
    return {"detail": "Categoría eliminada"}

@router.get("/products", response_model=List[ProductRead])
async def list_products(category_id: Optional[int] = None, include_inactive: bool = False, db: AsyncSession = Depends(get_session)):
    """Listado de productos, filtrable por categoría."""
    return await service.get_products(db, category_id, include_inactive)

@router.post("/products", response_model=ProductRead, dependencies=[Depends(require_role("admin"))])
async def create_product(product: ProductCreate, db: AsyncSession = Depends(get_session)):
    """Registra un nuevo producto en el catálogo. Requiere rol: admin."""
    return await service.create_product(db, product)

@router.put("/products/{product_id}", response_model=ProductRead, dependencies=[Depends(require_role("admin"))])
async def update_product(product_id: int, product: ProductUpdate, db: AsyncSession = Depends(get_session)):
    """Actualiza un producto existente. Requiere rol: admin."""
    updated_product = await service.update_product(db, product_id, product)
    if not updated_product:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return updated_product

@router.delete("/products/{product_id}", dependencies=[Depends(require_role("admin"))])
async def delete_product(product_id: int, db: AsyncSession = Depends(get_session)):
    """Desactiva un producto. Requiere rol: admin."""
    success = await service.delete_product(db, product_id)
    if not success:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return {"detail": "Producto desactivado"}

# --- Endpoints de Ingredientes ---

@router.get("/ingredients", response_model=List[Ingredient])
async def list_ingredients(db: AsyncSession = Depends(get_session)):
    """Listado de materia prima en el almacén."""
    return await service.get_ingredients(db)

@router.post("/ingredients", response_model=Ingredient, dependencies=[Depends(require_role("admin"))])
async def create_ingredient(ingredient: IngredientCreate, db: AsyncSession = Depends(get_session)):
    """Añade un nuevo ingrediente al almacén."""
    return await service.create_ingredient(db, ingredient)

@router.put("/ingredients/{ingredient_id}", response_model=Ingredient, dependencies=[Depends(require_role("admin"))])
async def update_ingredient(ingredient_id: int, ingredient: IngredientUpdate, db: AsyncSession = Depends(get_session)):
    """Actualiza un ingrediente existente. Requiere rol: admin."""
    updated_ingredient = await service.update_ingredient(db, ingredient_id, ingredient)
    if not updated_ingredient:
        raise HTTPException(status_code=404, detail="Ingrediente no encontrado")
    return updated_ingredient

@router.delete("/ingredients/{ingredient_id}", dependencies=[Depends(require_role("admin"))])
async def delete_ingredient(ingredient_id: int, db: AsyncSession = Depends(get_session)):
    """Elimina un ingrediente. Requiere rol: admin."""
    success = await service.delete_ingredient(db, ingredient_id)
    if not success:
        raise HTTPException(status_code=404, detail="Ingrediente no encontrado")
    return {"detail": "Ingrediente eliminado"}

# --- Endpoints de Recetas ---

@router.post("/products/{product_id}/ingredients", response_model=RecipeItem, dependencies=[Depends(require_role("admin"))])
async def add_ingredient_to_recipe(product_id: int, ingredient_id: int, quantity: float, db: AsyncSession = Depends(get_session)):
    """Define cuánto de un ingrediente usa un producto específico."""
    recipe_item = RecipeItem(product_id=product_id, ingredient_id=ingredient_id, quantity=quantity)
    return await service.add_ingredient_to_product(db, recipe_item)

@router.get("/products/{product_id}/recipe", response_model=List[RecipeItem])
async def get_recipe(product_id: int, db: AsyncSession = Depends(get_session)):
    """Consulta los ingredientes que componen un plato."""
    return await service.get_product_recipe(db, product_id)

@router.post("/variants/{variant_id}/ingredients", response_model=RecipeItem, dependencies=[Depends(require_role("admin"))])
async def add_ingredient_to_variant(variant_id: int, ingredient_id: int, quantity: float, db: AsyncSession = Depends(get_session)):
    """Define cuánto de un ingrediente usa una variante específica."""
    recipe_item = RecipeItem(variant_id=variant_id, ingredient_id=ingredient_id, quantity=quantity)
    return await service.add_ingredient_to_product(db, recipe_item)

@router.post("/variants/{variant_id}/modifier-groups", response_model=RecipeItem, dependencies=[Depends(require_role("admin"))])
async def add_group_to_variant(variant_id: int, modifier_group_id: int, quantity: float, db: AsyncSession = Depends(get_session)):
    """Define cuánto de un grupo usa una variante específica (ej. 250ml de Leches)."""
    recipe_item = RecipeItem(variant_id=variant_id, modifier_group_id=modifier_group_id, quantity=quantity)
    return await service.add_ingredient_to_product(db, recipe_item)

@router.get("/variants/{variant_id}/recipe", response_model=List[RecipeItem])
async def get_variant_recipe(variant_id: int, db: AsyncSession = Depends(get_session)):
    """Consulta la receta de una variante específica."""
    return await service.get_variant_recipe(db, variant_id)

# --- Endpoints de Modificadores y Presets ---

@router.get("/modifier-groups", response_model=List[ModifierGroupRead])
async def list_modifier_groups(db: AsyncSession = Depends(get_session)):
    """Listado de todos los grupos de modificadores."""
    return await service.get_modifier_groups(db)

@router.post("/modifier-groups", response_model=ModifierGroupRead, dependencies=[Depends(require_role("admin"))])
async def create_modifier_group(group: ModifierGroupCreate, db: AsyncSession = Depends(get_session)):
    """Crea un grupo de modificadores (ej: 'Tipo de Leche')."""
    return await service.create_modifier_group(db, group)

@router.put("/modifier-groups/{group_id}", response_model=ModifierGroupRead, dependencies=[Depends(require_role("admin"))])
async def update_modifier_group(group_id: int, group: ModifierGroupUpdate, db: AsyncSession = Depends(get_session)):
    """Actualiza un grupo de modificadores."""
    updated_group = await service.update_modifier_group(db, group_id, group)
    if not updated_group:
        raise HTTPException(status_code=404, detail="Grupo de modificadores no encontrado")
    return updated_group

@router.delete("/modifier-groups/{group_id}", dependencies=[Depends(require_role("admin"))])
async def delete_modifier_group(group_id: int, db: AsyncSession = Depends(get_session)):
    """Elimina un grupo de modificadores."""
    success = await service.delete_modifier_group(db, group_id)
    if not success:
        raise HTTPException(status_code=404, detail="Grupo de modificadores no encontrado")
    return {"detail": "Grupo de modificadores eliminado"}

@router.post("/modifiers", response_model=ModifierRead, dependencies=[Depends(require_role("admin"))])
async def create_modifier(modifier: ModifierCreate, db: AsyncSession = Depends(get_session)):
    """Crea una opción de modificador (ej: 'Soya 100ml')."""
    return await service.create_modifier(db, modifier)

@router.put("/modifiers/{modifier_id}", response_model=ModifierRead, dependencies=[Depends(require_role("admin"))])
async def update_modifier(modifier_id: int, modifier: ModifierUpdate, db: AsyncSession = Depends(get_session)):
    """Actualiza una opción de modificador."""
    updated_modifier = await service.update_modifier(db, modifier_id, modifier)
    if not updated_modifier:
        raise HTTPException(status_code=404, detail="Modificador no encontrado")
    return updated_modifier

@router.delete("/modifiers/{modifier_id}", dependencies=[Depends(require_role("admin"))])
async def delete_modifier(modifier_id: int, db: AsyncSession = Depends(get_session)):
    """Elimina una opción de modificador."""
    success = await service.delete_modifier(db, modifier_id)
    if not success:
        raise HTTPException(status_code=404, detail="Modificador no encontrado")
    return {"detail": "Modificador eliminado"}

@router.post("/modifiers/{modifier_id}/measures/{measure_id}/quantity", dependencies=[Depends(require_role("admin"))])
async def update_modifier_measure_quantity(modifier_id: int, measure_id: int, quantity: float, db: AsyncSession = Depends(get_session)):
    """Configura la cantidad de descuento de un modificador para una medida específica."""
    return await service.update_modifier_quantity(db, modifier_id, measure_id, quantity)

@router.post("/products/{product_id}/modifier-groups/{group_id}", dependencies=[Depends(require_role("admin"))])
async def link_group_to_product(product_id: int, group_id: int, db: AsyncSession = Depends(get_session)):
    """Vincula un grupo de modificadores a un producto."""
    return await service.link_modifier_group_to_product(db, product_id, group_id)

@router.get("/products/{product_id}/presets", response_model=List[POSPreset])
async def get_presets(product_id: int, db: AsyncSession = Depends(get_session)):
    """Obtiene los presets guardados para un producto."""
    return await service.get_product_presets(db, product_id)

@router.post("/products/{product_id}/presets", response_model=POSPreset)
async def create_preset(product_id: int, name: str, modifier_ids: List[int], db: AsyncSession = Depends(get_session)):
    """Guarda una combinación de modificadores como preset."""
    import json
    preset = POSPreset(product_id=product_id, name=name, modifier_ids_json=json.dumps(modifier_ids))
    return await service.create_preset(db, preset)

# --- Endpoints de Medidas (Sizes) ---

@router.get("/measures", response_model=List[Measure])
async def list_measures(db: AsyncSession = Depends(get_session)):
    """Listado de todas las medidas configuradas (Chico, Grande, etc)."""
    return await service.get_measures(db)

@router.post("/measures", response_model=Measure, dependencies=[Depends(require_role("admin"))])
async def create_measure(measure: MeasureCreate, db: AsyncSession = Depends(get_session)):
    """Crea una nueva medida base. Requiere rol: admin."""
    return await service.create_measure(db, measure)

# --- Endpoints de Variantes de Producto ---

@router.get("/products/{product_id}/variants", response_model=List[ProductVariantRead])
async def list_variants(product_id: int, db: AsyncSession = Depends(get_session)):
    """Obtiene todas las variantes (tallas) de un producto."""
    return await service.get_variants_by_product(db, product_id)

@router.post("/products/{product_id}/variants", response_model=ProductVariantRead, dependencies=[Depends(require_role("admin"))])
async def create_variant(product_id: int, variant: ProductVariantCreate, db: AsyncSession = Depends(get_session)):
    """Crea una variante (asigna talla y precio) a un producto. Requiere rol: admin."""
    variant.product_id = product_id
    return await service.create_variant(db, variant)

@router.put("/variants/{variant_id}", response_model=ProductVariantRead, dependencies=[Depends(require_role("admin"))])
async def update_variant(variant_id: int, variant: ProductVariantUpdate, db: AsyncSession = Depends(get_session)):
    """Actualiza una variante existente. Requiere rol: admin."""
    updated_variant = await service.update_variant(db, variant_id, variant)
    if not updated_variant:
        raise HTTPException(status_code=404, detail="Variante no encontrada")
    return updated_variant

@router.delete("/variants/{variant_id}", dependencies=[Depends(require_role("admin"))])
async def delete_variant(variant_id: int, db: AsyncSession = Depends(get_session)):
    """Elimina una variante de producto. Requiere rol: admin."""
    success = await service.delete_variant(db, variant_id)
    if not success:
        raise HTTPException(status_code=404, detail="Variante no encontrada")
    return {"detail": "Variante eliminada"}

@router.delete("/variants/{variant_id}/recipe", dependencies=[Depends(require_role("admin"))])
async def clear_variant_recipe(variant_id: int, db: AsyncSession = Depends(get_session)):
    """Limpia todos los ingredientes/grupos de la receta de una variante. Requiere rol: admin."""
    await service.clear_variant_recipe(db, variant_id)
    return {"detail": "Receta de variante eliminada"}
