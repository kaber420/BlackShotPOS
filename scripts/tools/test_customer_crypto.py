import sys
import os
import asyncio
from uuid import uuid4

# Añadir ruta al path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from sqlmodel import SQLModel, create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from pos_core.customers.models import Customer
from pos_core.customers.schemas import CustomerCreate, CustomerUpdate
from pos_core.customers.service import CustomerService
from pos_core.crypto import CryptoService

DATABASE_URL = "sqlite+aiosqlite:///:memory:"

engine = create_async_engine(DATABASE_URL, echo=False)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

async def main():
    await init_db()
    
    async with async_session() as session:
        print("--- Testing CryptoService ---")
        original_text = "secret_data_123"
        encrypted = CryptoService.encrypt_data(original_text)
        decrypted = CryptoService.decrypt_data(encrypted)
        
        print(f"Original: {original_text}")
        print(f"Encrypted: {encrypted}")
        print(f"Decrypted: {decrypted}")
        assert original_text == decrypted
        print("CryptoService: OK\n")
        
        print("--- Testing CustomerService Create ---")
        customer_in = CustomerCreate(
            name="John Doe",
            email="john@example.com",
            phone="1234567890",
            username="johndoe",
            password="supersecretpassword",
            telegram_id="tg123"
        )
        customer = await CustomerService.create(session, customer_in)
        
        print(f"Customer ID: {customer.id}")
        print(f"Encrypted Name DB: {customer.encrypted_name}")
        print(f"Encrypted Email DB: {customer.encrypted_email}")
        print(f"Decrypted Name Prop: {customer.name}")
        assert customer.name == "John Doe"
        print("Customer Create: OK\n")
        
        print("--- Testing CustomerService Get By Phone ---")
        fetched = await CustomerService.get_by_phone(session, "1234567890")
        assert fetched is not None
        assert fetched.name == "John Doe"
        print("Customer Get By Phone: OK\n")
        
        print("--- Testing CustomerService Search (by hash/exact & partial) ---")
        searched = await CustomerService.search(session, "1234567890")
        assert len(searched) == 1
        assert searched[0].name == "John Doe"
        
        searched_by_user = await CustomerService.search(session, "johndoe")
        assert len(searched_by_user) == 1
        
        # Test similar/prefix searches
        searched_by_prefix = await CustomerService.search(session, "john")
        assert len(searched_by_prefix) == 1
        assert searched_by_prefix[0].username == "johndoe"

        # Test case-insensitivity
        searched_by_case = await CustomerService.search(session, "JOHN")
        assert len(searched_by_case) == 1
        
        print("Customer Search: OK\n")
        
        print("--- Testing Customer Update ---")
        update_in = CustomerUpdate(name="Jane Doe", phone="0987654321")
        updated = await CustomerService.update(session, customer, update_in)
        
        assert updated.name == "Jane Doe"
        assert updated.phone == "0987654321"
        # We need to test the fields since update() overwrites the passed instance in this flow
        # In the real flow we'd re-fetch to be safe
        
        # Verify old phone search fails
        not_found = await CustomerService.get_by_phone(session, "1234567890")
        assert not_found is None
        
        # Verify new phone search succeeds
        found = await CustomerService.get_by_phone(session, "0987654321")
        assert found is not None
        assert found.name == "Jane Doe"
        print("Customer Update: OK\n")
        
        print("All tests passed successfully!")

if __name__ == "__main__":
    asyncio.run(main())
