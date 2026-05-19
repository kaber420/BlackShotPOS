import asyncio
import os
import sys
from uuid import uuid4
from fastapi.exceptions import HTTPException

# Añadir la raíz del proyecto al path para importaciones
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy.ext.asyncio import AsyncSession
from pos_core.database import async_session_maker
from pos_core.accounting.models import CashMovementType, CashRegister, Shift, CashMovement, ShiftStatus
from pos_core.accounting import service as accounting_service
from pos_core.auth.models import User
from pos_core.sales.models import Order, Payment, PaymentMethod, OrderType, OrderItem
from pos_core.catalog.models import Category, Product, RecipeItem, Measure, ProductVariant
from pos_core.inventory.models import Ingredient
from pos_core.tables.models import Table
from pos_core.settings.models import BusinessSettings
from pos_core.iot.models import IoTDevice
from pos_core.customers.models import Customer
from bs_sync.models import SyncEvent
from pos_core.kitchen.models import ProductionArea
from sqlmodel import select

async def test_accounting_robustness():
    async with async_session_maker() as session:
        print("\n🧪 Iniciando Pruebas de Robustez de Contabilidad...")

        # 1. Asegurar base de datos limpia de turnos
        from sqlalchemy import delete
        await session.execute(delete(CashMovement))
        await session.execute(delete(Payment))
        await session.execute(delete(OrderItem))
        await session.execute(delete(Order))
        await session.execute(delete(Shift))
        await session.commit()

        # 2. Asegurar Caja y Usuario de prueba
        reg_stmt = select(CashRegister).where(CashRegister.name == "Caja Robustez")
        register = (await session.execute(reg_stmt)).scalar_one_or_none()
        if not register:
            register = await accounting_service.create_cash_register(session, "Caja Robustez")
            print(f"✅ Caja creada ID: {register.id}")

        user_stmt = select(User).limit(1)
        user = (await session.execute(user_stmt)).scalar_one_or_none()
        if not user:
            user = User(
                id=uuid4(),
                email="robustness@blackshot.app",
                username="robust_cashier",
                hashed_password="xxx",
                is_active=True
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            print(f"✅ Usuario de prueba creado ID: {user.id}")

        # 3. Validar: No se puede abrir un turno con saldo inicial negativo
        print("🛡️ Probando validación de monto inicial negativo al abrir turno...")
        try:
            await accounting_service.open_shift(
                session,
                initial_cash=-100.0,
                register_id=register.id,
                user_id=user.id
            )
            assert False, "Se debió lanzar un HTTPException al abrir turno con monto negativo."
        except HTTPException as e:
            assert e.status_code == 422
            assert "Initial cash cannot be negative" in e.detail
            print("✅ Validación exitosa: Denegada la apertura con inicial negativo.")

        # 4. Abrir un turno válido de $1000
        shift = await accounting_service.open_shift(
            session,
            initial_cash=1000.0,
            register_id=register.id,
            user_id=user.id
        )
        print(f"✅ Turno abierto exitosamente con $1000. ID: {shift.id}")

        # 5. Validar: No se puede registrar un movimiento con monto negativo o cero
        print("🛡️ Probando validación de monto de movimiento negativo o cero...")
        
        # Obtener una categoría de movimiento (Ingresos / Corrección)
        from pos_core.accounting.models import CashMovementCategory
        cat_stmt = select(CashMovementCategory).limit(1)
        m_cat = (await session.execute(cat_stmt)).scalar_one_or_none()
        if not m_cat:
            m_cat = CashMovementCategory(name="Corrección", type=CashMovementType.INCOME, description="Ajuste")
            session.add(m_cat)
            await session.flush()

        try:
            await accounting_service.add_cash_movement(
                session,
                shift_id=shift.id,
                type=m_cat.type,
                category_id=m_cat.id,
                amount=-50.0,
                reason="Intento negativo",
                user_id=user.id
            )
            assert False, "Se debió lanzar un HTTPException al crear movimiento negativo."
        except HTTPException as e:
            assert e.status_code == 422
            assert "Amount must be greater than zero" in e.detail
            print("✅ Validación exitosa: Denegado movimiento negativo.")

        try:
            await accounting_service.add_cash_movement(
                session,
                shift_id=shift.id,
                type=m_cat.type,
                category_id=m_cat.id,
                amount=0.0,
                reason="Intento cero",
                user_id=user.id
            )
            assert False, "Se debió lanzar un HTTPException al crear movimiento con monto cero."
        except HTTPException as e:
            assert e.status_code == 422
            assert "Amount must be greater than zero" in e.detail
            print("✅ Validación exitosa: Denegado movimiento de monto cero.")

        # 6. Registrar un egreso legítimo de $200 (eg. compra de insumos)
        insumos_stmt = select(CashMovementCategory).where(CashMovementCategory.name == "Insumos")
        insumos_cat = (await session.execute(insumos_stmt)).scalar_one_or_none()
        if not insumos_cat:
            insumos_cat = CashMovementCategory(name="Insumos", type=CashMovementType.EXPENSE, description="Gastos de insumos")
            session.add(insumos_cat)
            await session.flush()

        movement = await accounting_service.add_cash_movement(
            session,
            shift_id=shift.id,
            type=CashMovementType.EXPENSE,
            category_id=insumos_cat.id,
            amount=200.0,
            reason="Compra de Café Extra",
            user_id=user.id
        )
        print(f"✅ Movimiento registrado: Egreso de $200. ID: {movement.id}")

        # 7. Verificar cálculo de balance esperado antes del cierre
        # Inicial $1000 - Egreso $200 = $800
        totals = await accounting_service.get_shift_report(session, shift.id)
        print(f"DEBUG TOTALS: {totals}")
        assert totals["shift"]["expected_cash"] == 800.0
        assert totals["shift"]["expected_card"] == 0.0
        assert totals["shift"]["expected_transfer"] == 0.0
        print("✅ Totales calculados en tiempo real correctos: Esperado $800 en efectivo.")

        # 8. Cerrar turno con $810 en efectivo (diferencia de +$10)
        closed_shift = await accounting_service.close_shift(
            session,
            shift_id=shift.id,
            actual_cash=810.0,
            actual_card=0.0,
            actual_transfer=0.0,
            notes="Diferencia de +10 sobrante de caja"
        )
        
        # 9. Validaciones finales del turno cerrado
        assert closed_shift.status == ShiftStatus.CLOSED
        assert closed_shift.expected_cash == 800.0
        assert closed_shift.actual_cash == 810.0
        assert closed_shift.difference_cash == 10.0
        assert closed_shift.end_time is not None
        
        # Validar que end_time sea naive UTC (sin zona horaria en el objeto guardado en DB)
        assert closed_shift.end_time.tzinfo is None
        print("✅ Validación exitosa: El turno se cerró correctamente y end_time es un datetime UTC naive.")

        print("\n✨ ¡TODAS LAS PRUEBAS DE ROBUSTEZ PASARON PERFECTAMENTE! ✨\n")

if __name__ == "__main__":
    asyncio.run(test_accounting_robustness())
