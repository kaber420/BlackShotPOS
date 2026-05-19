import asyncio
import os
import sys
from uuid import uuid4
from datetime import datetime

# Añadir el directorio raíz al path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from pos_core.database import async_session_maker, init_db
from pos_core.sales.services.order_lifecycle_service import create_order, get_order_with_relations, recalculate_order_totals
from pos_core.sales.services.order_item_service import add_item_to_order
from pos_core.sales.payment_service import add_payment
from pos_core.sales.services import order_action_service
from pos_core.sales.models import OrderType, PaymentMethod, OrderStatus, OrderFinancialStatus, Order, Payment, OrderItem
from pos_core.catalog.models import Category, Product, RecipeItem, Measure, ProductVariant
from pos_core.inventory.models import Ingredient
from pos_core.accounting.models import CashMovementType, CashRegister, Shift, CashMovement, CashMovementCategory
from pos_core.accounting import service as accounting_service
from pos_core.auth.models import User
from sqlmodel import select, delete

async def test_financials_enhanced():
    print("--- INICIANDO PRUEBAS DE ARQUITECTURA FINANCIERA ENHANCED ---")
    await init_db()

    async with async_session_maker() as session:
        # 1. Limpieza de tablas para tener entorno determinista
        await session.execute(delete(CashMovement))
        await session.execute(delete(Payment))
        await session.execute(delete(OrderItem))
        await session.execute(delete(Order))
        await session.execute(delete(RecipeItem))
        await session.execute(delete(ProductVariant))
        await session.execute(delete(Product))
        await session.execute(delete(Category))
        await session.execute(delete(Ingredient))
        await session.execute(delete(Shift))
        await session.execute(delete(User))
        await session.commit()

        # 2. Configurar Caja y Turno
        register = CashRegister(name="Caja Principal")
        session.add(register)
        await session.commit()
        await session.refresh(register)

        user = User(
            id=uuid4(),
            email="manager@blackshot.app",
            username="manager_test",
            hashed_password="xxx",
            is_active=True
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        shift = await accounting_service.open_shift(
            session,
            initial_cash=1000.0,
            register_id=register.id,
            user_id=user.id
        )
        print(f"Turno abierto con $1000. ID: {shift.id}")

        # 3. Configurar Insumos, Productos y Recetas
        # Ingrediente con costo unitario de 0.05
        ingrediente = Ingredient(
            name="Café Mezcla Especial",
            measure_type="weight",
            unit="g",
            current_stock=1000.0,
            minimum_stock=100.0,
            cost_per_unit=0.05
        )
        session.add(ingrediente)
        await session.commit()
        await session.refresh(ingrediente)

        category = Category(name="Bebidas Calientes")
        session.add(category)
        await session.commit()
        await session.refresh(category)

        product = Product(name="Americano Especial", price=50.0, category_id=category.id)
        session.add(product)
        await session.commit()
        await session.refresh(product)

        measure = Measure(name="Mediano", value=12.0, unit="oz")
        session.add(measure)
        await session.commit()
        await session.refresh(measure)

        variant = ProductVariant(product_id=product.id, measure_id=measure.id, price=50.0)
        session.add(variant)
        await session.commit()
        await session.refresh(variant)

        recipe = RecipeItem(
            variant_id=variant.id,
            ingredient_id=ingrediente.id,
            quantity=20.0,
            input_quantity=20.0,
            input_unit="g"
        )
        session.add(recipe)
        await session.commit()

        # 4. Asegurar existencia de las categorías requeridas de Caja Chica
        cat_courtesy = (await session.execute(
            select(CashMovementCategory).where(CashMovementCategory.name == "Gastos por Cortesías / Mermas")
        )).scalar_one_or_none()
        if not cat_courtesy:
            cat_courtesy = CashMovementCategory(
                name="Gastos por Cortesías / Mermas",
                type=CashMovementType.EXPENSE,
                description="Costo de insumos para cortesías"
            )
            session.add(cat_courtesy)

        cat_refund = (await session.execute(
            select(CashMovementCategory).where(CashMovementCategory.name == "Varios / Emergencias")
        )).scalar_one_or_none()
        if not cat_refund:
            cat_refund = CashMovementCategory(
                name="Varios / Emergencias",
                type=CashMovementType.EXPENSE,
                description="Gastos varios y emergencias"
            )
            session.add(cat_refund)
        await session.commit()
        await session.refresh(cat_courtesy)
        await session.refresh(cat_refund)

        # =====================================================================
        # TEST ESCENARIO A: FLUJO DE PAGOS Y REEMBOLSO
        # =====================================================================
        print("\n--- Ejecutando Escenario A: Pago Parcial, Pago Completo y Reembolso ---")
        order_a = await create_order(session, OrderType.DINE_IN, waiter_name="Test Waiter")
        # Añadir item
        await add_item_to_order(session, order_a.id, product.id, quantity=1, product_variant_id=variant.id)
        
        # Verificar estado inicial de pago
        order_a = await get_order_with_relations(session, order_a.id)
        assert order_a.financial_status == OrderFinancialStatus.UNPAID
        assert order_a.total_amount == 50.0
        assert order_a.balance_due == 50.0
        print(f"Orden A creada. Total: {order_a.total_amount}. Estado financiero: {order_a.financial_status}")

        # Registrar pago parcial de $20.0
        await add_payment(session, order_a.id, PaymentMethod.CASH, amount=20.0)
        order_a = await get_order_with_relations(session, order_a.id)
        assert order_a.financial_status == OrderFinancialStatus.PARTIALLY_PAID
        assert order_a.balance_due == 30.0
        print(f"Pago parcial agregado. Saldo pendiente: {order_a.balance_due}. Estado financiero: {order_a.financial_status}")

        # Registrar pago final de $30.0
        await add_payment(session, order_a.id, PaymentMethod.CARD, amount=30.0)
        order_a = await get_order_with_relations(session, order_a.id)
        assert order_a.financial_status == OrderFinancialStatus.PAID
        assert order_a.balance_due == 0.0
        print(f"Pago final agregado. Saldo pendiente: {order_a.balance_due}. Estado financiero: {order_a.financial_status}")

        # Ejecutar reembolso
        print("Ejecutando reembolso autorizado por manager...")
        await order_action_service.refund_order(
            session,
            order_a.id,
            reason="Cliente insatisfecho",
            manager_uuid=str(user.id),
            manager_name=user.username
        )
        
        # Recargar y validar estado REFUNDED
        order_a = await get_order_with_relations(session, order_a.id)
        assert order_a.financial_status == OrderFinancialStatus.REFUNDED
        print(f"Orden A reembolsada exitosamente. Estado financiero: {order_a.financial_status}")

        # Verificar movimiento de caja generado por el reembolso (debe ser de tipo EXPENSE por el monto cobrado)
        refund_movements = (await session.execute(
            select(CashMovement).where(CashMovement.reason.like("%Reembolso de Orden%"))
        )).scalars().all()
        assert len(refund_movements) == 1
        assert refund_movements[0].amount == 50.0  # El reembolso total es por los $50 cobrados
        assert refund_movements[0].type == CashMovementType.EXPENSE
        print(f"Movimiento de caja por reembolso verificado. Tipo: {refund_movements[0].type}, Monto: {refund_movements[0].amount}")

        # =====================================================================
        # TEST ESCENARIO B: FLUJO DE CORTESÍA DE LA CASA
        # =====================================================================
        print("\n--- Ejecutando Escenario B: Cortesía de la Casa y Descarga de Costos ---")
        order_b = await create_order(session, OrderType.DINE_IN, waiter_name="Test Waiter")
        await add_item_to_order(session, order_b.id, product.id, quantity=1, product_variant_id=variant.id)
        
        # Verificar stock inicial
        await session.refresh(ingrediente)
        stock_inicial = ingrediente.current_stock
        print(f"Stock inicial de ingrediente: {stock_inicial} g")

        # Aplicar Cortesía
        print("Aplicando cortesía autorizada por manager...")
        await order_action_service.mark_order_as_courtesy(
            session,
            order_b.id,
            reason="Atención por demora",
            manager_uuid=str(user.id),
            manager_name=user.username
        )

        # Recargar y validar estado COMPLIMENTARY y totales en cero
        order_b = await get_order_with_relations(session, order_b.id)
        assert order_b.financial_status == OrderFinancialStatus.COMPLIMENTARY
        assert order_b.total_amount == 0.0
        assert order_b.balance_due == 0.0
        print(f"Orden B marcada como cortesía. Total: {order_b.total_amount}. Estado financiero: {order_b.financial_status}")

        # Verificar descarga de stock de insumo (20 gramos requeridos)
        await session.refresh(ingrediente)
        assert ingrediente.current_stock == stock_inicial - 20.0
        print(f"Stock de ingrediente descargado exitosamente. Nuevo stock: {ingrediente.current_stock} g (esperado: {stock_inicial - 20.0})")

        # Verificar movimiento de caja de cortesía generado (Costo: 20g * 0.05 = 1.0)
        courtesy_movements = (await session.execute(
            select(CashMovement).where(CashMovement.category_id == cat_courtesy.id)
        )).scalars().all()
        assert len(courtesy_movements) == 1
        assert courtesy_movements[0].amount == 1.0
        assert courtesy_movements[0].type == CashMovementType.EXPENSE
        print(f"Movimiento de costo de cortesía verificado. Categoría: {cat_courtesy.name}, Monto (Costo de Insumos): {courtesy_movements[0].amount}")

        # =====================================================================
        # TEST ESCENARIO C: CÓMPUTO DE CORTE DE CAJA (SHIFTS EN CAJA CHICA)
        # =====================================================================
        print("\n--- Ejecutando Escenario C: Verificación de Corte de Caja / Totales del Turno ---")
        
        # Totales del turno:
        # Inicial: $1000
        # Ventas en Efectivo: $20.0 (del pago parcial de la Orden A)
        # Ventas en Tarjeta: $30.0 (del pago final de la Orden A)
        # Egresos ordinarios por reembolso de Orden A: $50.0 (afecta expected_cash ya que salió efectivo)
        # Egresos por cortesía de la Orden B: $1.0 (NO DEBE afectar expected_cash de la caja física)
        # expected_cash = 1000 (inicial) + 20 (ventas efectivo) - 50 (egreso ordinario por reembolso) = 970.0
        
        totals = await accounting_service.get_shift_report(session, shift.id)
        print(f"Reporte de caja obtenido: {totals}")
        
        # Validar caja física esperada
        assert totals["shift"]["expected_cash"] == 970.0
        # Validar cortesías acumuladas en la sección de ventas
        assert totals["sales"]["courtesies_total"] == 1.0
        print(f"Validación exitosa del Corte de Caja:")
        print(f"  - Efectivo esperado en caja física: {totals['shift']['expected_cash']} (esperado: 970.0)")
        print(f"  - Total acumulado de cortesías (informativo): {totals['sales']['courtesies_total']} (esperado: 1.0)")

    print("\n✨ TODAS LAS PRUEBAS DE ARQUITECTURA FINANCIERA PASARON CON 100% DE ÉXITO ✨\n")

if __name__ == "__main__":
    asyncio.run(test_financials_enhanced())
