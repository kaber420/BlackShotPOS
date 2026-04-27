from typing import List, Optional
from uuid import UUID
from datetime import datetime, timezone
from sqlmodel import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from pos_core.customers.models import Customer
from pos_core.customers.schemas import CustomerCreate, CustomerUpdate

class CustomerService:
    @staticmethod
    async def create(db: AsyncSession, customer_in: CustomerCreate) -> Customer:
        customer = Customer.model_validate(customer_in)
        db.add(customer)
        await db.commit()
        await db.refresh(customer)
        return customer

    @staticmethod
    async def get_by_id(db: AsyncSession, customer_id: UUID) -> Optional[Customer]:
        return await db.get(Customer, customer_id)

    @staticmethod
    async def get_by_phone(db: AsyncSession, phone: str) -> Optional[Customer]:
        statement = select(Customer).where(Customer.phone == phone)
        result = await db.execute(statement)
        return result.scalar_one_or_none()

    @staticmethod
    async def search(db: AsyncSession, query: str, limit: int = 10) -> List[Customer]:
        statement = (
            select(Customer)
            .where(
                or_(
                    Customer.name.ilike(f"%{query}%"),
                    Customer.phone.contains(query),
                    Customer.email.ilike(f"%{query}%")
                )
            )
            .limit(limit)
        )
        result = await db.execute(statement)
        return result.scalars().all()

    @staticmethod
    async def update(db: AsyncSession, customer: Customer, customer_in: CustomerUpdate) -> Customer:
        update_data = customer_in.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(customer, key, value)
        
        # Al actualizar localmente, marcamos como no sincronizado para que el Bridge lo detecte
        customer.is_synced = False
        
        db.add(customer)
        await db.commit()
        await db.refresh(customer)
        return customer

    @staticmethod
    async def update_last_visit(db: AsyncSession, customer_id: UUID):
        customer = await db.get(Customer, customer_id)
        if customer:
            customer.last_visit_at = datetime.now(timezone.utc)
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
