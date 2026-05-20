from typing import List, Optional
from uuid import UUID
from datetime import datetime, timezone
from sqlmodel import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from pos_core.customers.models import Customer
from pos_core.customers.schemas import CustomerCreate, CustomerUpdate
from pos_core.crypto import CryptoService

class CustomerService:
    @staticmethod
    async def create(db: AsyncSession, customer_in: CustomerCreate) -> Customer:
        data = customer_in.model_dump(exclude={"name", "phone", "email", "password", "telegram_id"})
        
        # Generar loyalty_code si no viene
        if not data.get("loyalty_code"):
            from uuid import uuid4
            data["loyalty_code"] = uuid4().hex[:8].upper()
        
        # PII Encryption
        data["encrypted_name"] = CryptoService.encrypt_data(customer_in.name)
        data["encrypted_email"] = CryptoService.encrypt_data(customer_in.email) if customer_in.email else None
        data["encrypted_phone"] = CryptoService.encrypt_data(customer_in.phone) if customer_in.phone else None
        data["encrypted_telegram_id"] = CryptoService.encrypt_data(customer_in.telegram_id) if customer_in.telegram_id else None
        
        # Hashes for exact search
        data["phone_hash"] = CryptoService.hash_data(customer_in.phone) if customer_in.phone else None
        
        # Password
        if customer_in.password:
            data["hashed_password"] = CryptoService.hash_password(customer_in.password)

        customer = Customer(**data)
        db.add(customer)
        await db.commit()
        await db.refresh(customer)
        return customer

    @staticmethod
    async def get_by_id(db: AsyncSession, customer_id: UUID) -> Optional[Customer]:
        return await db.get(Customer, customer_id)

    @staticmethod
    async def get_by_phone(db: AsyncSession, phone: str) -> Optional[Customer]:
        phone_hash = CryptoService.hash_data(phone)
        statement = select(Customer).where(Customer.phone_hash == phone_hash)
        result = await db.execute(statement)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_username(db: AsyncSession, username: str) -> Optional[Customer]:
        statement = select(Customer).where(Customer.username == username)
        result = await db.execute(statement)
        return result.scalar_one_or_none()

    @staticmethod
    async def search(db: AsyncSession, query: str, limit: int = 10) -> List[Customer]:
        # Nota: Ya no podemos hacer ILIKE en nombre o email cifrados.
        # Búsqueda determinista o parcial por username, hash de teléfono, nfc_tag_id o loyalty_code
        phone_hash = CryptoService.hash_data(query)
        
        # Búsqueda parcial (insensible a mayúsculas/minúsculas)
        like_query = f"%{query}%"
        
        statement = (
            select(Customer)
            .where(
                or_(
                    Customer.username.ilike(like_query),
                    Customer.phone_hash == phone_hash,
                    Customer.nfc_tag_id.ilike(like_query),
                    Customer.loyalty_code.ilike(like_query)
                )
            )
            .limit(limit)
        )
        result = await db.execute(statement)
        return result.scalars().all()

    @staticmethod
    async def update(db: AsyncSession, customer: Customer, customer_in: CustomerUpdate) -> Customer:
        update_data = customer_in.model_dump(exclude_unset=True)
        
        # Handle special fields
        if "name" in update_data:
            customer.encrypted_name = CryptoService.encrypt_data(update_data.pop("name"))
        if "email" in update_data:
            val = update_data.pop("email")
            customer.encrypted_email = CryptoService.encrypt_data(val) if val else None
        if "phone" in update_data:
            val = update_data.pop("phone")
            customer.encrypted_phone = CryptoService.encrypt_data(val) if val else None
            customer.phone_hash = CryptoService.hash_data(val) if val else None
        if "telegram_id" in update_data:
            val = update_data.pop("telegram_id")
            customer.encrypted_telegram_id = CryptoService.encrypt_data(val) if val else None
        if "password" in update_data:
            customer.hashed_password = CryptoService.hash_password(update_data.pop("password"))
        
        for key, value in update_data.items():
            setattr(customer, key, value)
        
        # Al actualizar localmente, marcamos como no sincronizado para que el Bridge lo detecte
        customer.is_synced = False
        
        db.add(customer)
        await db.commit()
        await db.refresh(customer)
        return customer

    @staticmethod
    async def list_all(db: AsyncSession, limit: int = 50) -> List[Customer]:
        statement = select(Customer).order_by(Customer.username).limit(limit)
        result = await db.execute(statement)
        return result.scalars().all()

    @staticmethod
    async def update_last_visit(db: AsyncSession, customer_id: UUID):
        customer = await db.get(Customer, customer_id)
        if customer:
            customer.last_visit_at = datetime.utcnow()
            db.add(customer)
            await db.commit()

    @staticmethod
    async def add_points(db: AsyncSession, customer_id: UUID, points: int) -> Optional[Customer]:
        customer = await db.get(Customer, customer_id)
        if customer:
            customer.points += points
            customer.is_synced = False
            db.add(customer)
            await db.commit()
            await db.refresh(customer)
        return customer

    @staticmethod
    async def delete(db: AsyncSession, customer_id: UUID) -> bool:
        customer = await db.get(Customer, customer_id)
        if not customer:
            return False

        # Evitar importaciones circulares importando localmente
        from sqlalchemy import update
        from pos_core.sales.models import Order
        from pos_core.tables.models import Reservation

        # Desvincular órdenes de venta
        await db.execute(
            update(Order)
            .where(Order.customer_id == customer_id)
            .values(customer_id=None)
        )

        # Desvincular reservaciones
        await db.execute(
            update(Reservation)
            .where(Reservation.customer_id == customer_id)
            .values(customer_id=None)
        )

        # Eliminar físicamente al cliente
        await db.delete(customer)
        await db.commit()
        return True

