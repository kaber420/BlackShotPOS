import asyncio
from sqlmodel import select
from pos_core.database import async_session_maker
from pos_core.inventory.models import Product, RecipeItem, Ingredient, ModifierGroup, Modifier, ProductVariant, Measure

async def diagnose():
    async with async_session_maker() as session:
        print("--- Diagnostic: Products and Recipes ---")
        
        # Get all products
        stmt = select(Product)
        products = (await session.execute(stmt)).scalars().all()
        
        for p in products:
            print(f"\nProduct: {p.name} (ID: {p.id})")
            
            # Base Recipe
            stmt = select(RecipeItem).where(RecipeItem.product_id == p.id)
            items = (await session.execute(stmt)).scalars().all()
            for ri in items:
                ing_name = "None"
                if ri.ingredient_id:
                    ing = await session.get(Ingredient, ri.ingredient_id)
                    ing_name = ing.name if ing else "Unknown"
                
                grp_name = "None"
                if ri.modifier_group_id:
                    grp = await session.get(ModifierGroup, ri.modifier_group_id)
                    grp_name = grp.name if grp else "Unknown"
                
                print(f"  - RecipeItem: Ing={ing_name} (ID:{ri.ingredient_id}), Group={grp_name} (ID:{ri.modifier_group_id}), Qty={ri.quantity}")

        print("\n--- Diagnostic: Modifiers ---")
        stmt = select(Modifier)
        modifiers = (await session.execute(stmt)).scalars().all()
        for m in modifiers:
            ing_name = "None"
            if m.ingredient_id:
                ing = await session.get(Ingredient, m.ingredient_id)
                ing_name = ing.name if ing else "Unknown"
            print(f"  - Modifier: {m.name} (ID: {m.id}), Ingredient: {ing_name} (ID: {m.ingredient_id}), GroupID: {m.modifier_group_id}")

if __name__ == "__main__":
    asyncio.run(diagnose())
