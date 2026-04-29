import jwt
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, List
import httpx
from sqlmodel import Session, select
from sqlalchemy.orm import selectinload
from models import Branch, User, Region, GlobalProduct, GlobalCategory, GlobalMenu, engine

class CentralConnectionManager:
    """
    Manager de Conexiones para el Panel Central.
    Maneja el registro de sucursales, llaves privadas y la generación
    de tokens Bridge para enviar comandos, con persistencia en DB.
    """
    
    def get_branch(self, branch_id: str) -> Optional[Branch]:
        with Session(engine) as session:
            return session.get(Branch, branch_id)

    def list_branches(self, region_id: Optional[int] = None) -> List[Branch]:
        with Session(engine) as session:
            statement = select(Branch).options(
                selectinload(Branch.region),
                selectinload(Branch.manager)
            )
            if region_id:
                statement = statement.where(Branch.region_id == region_id)
            return session.exec(statement).all()

    def list_regions(self) -> List[Region]:
        with Session(engine) as session:
            statement = select(Region).options(
                selectinload(Region.branches),
                selectinload(Region.managers)
            )
            return session.exec(statement).all()

    def list_global_products(self) -> List[GlobalProduct]:
        with Session(engine) as session:
            statement = select(GlobalProduct).options(
                selectinload(GlobalProduct.category),
                selectinload(GlobalProduct.menus)
            )
            return session.exec(statement).all()

    def list_users(self) -> List[User]:
        with Session(engine) as session:
            statement = select(User).options(
                selectinload(User.regions),
                selectinload(User.managed_branches)
            )
            return session.exec(statement).all()

    def list_categories(self) -> List[GlobalCategory]:
        with Session(engine) as session:
            return session.exec(select(GlobalCategory)).all()

    def generate_bridge_token(self, branch: Branch, expiration_minutes: int = 5) -> str:
        """
        Genera un JWT firmado con la llave privada para una sucursal específica.
        """
        payload = {
            "iss": "blackshot-central",
            "sub": branch.id,
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc) + timedelta(minutes=expiration_minutes),
            "user": {
                "id": "uuid-central-admin",
                "email": "central@blackshot.app",
                "role": "admin",
                "is_bridge": True
            }
        }
        
        token = jwt.encode(payload, branch.private_key, algorithm="RS256")
        return token
        
    async def fetch_branch_data(self, branch_id: str, endpoint: str) -> dict:
        """
        Consulta datos de una sucursal usando el Bridge Auth.
        """
        branch = self.get_branch(branch_id)
        if not branch:
            raise ValueError("Sucursal no encontrada")
            
        token = self.generate_bridge_token(branch)
        url = f"{branch.base_url.rstrip('/')}{endpoint}"
        
        headers = {
            "X-Blackshot-Bridge-Auth": token,
            "Accept": "application/json"
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, headers=headers, timeout=5.0)
                response.raise_for_status()
                return response.json()
            except Exception as e:
                return {"error": str(e), "status": "offline"}

manager = CentralConnectionManager()
