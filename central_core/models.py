import uuid
from datetime import datetime
from typing import Optional, List
from sqlmodel import SQLModel, Field, create_engine, Session, select, Relationship
from sqlalchemy import JSON

# --- Regional and User Management ---

class UserRegionLink(SQLModel, table=True):
    user_id: int = Field(foreign_key="user.id", primary_key=True)
    region_id: int = Field(foreign_key="region.id", primary_key=True)

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True)
    full_name: str
    hashed_password: str
    role: str = Field(default="branch_manager") # superadmin, regional_manager, branch_manager
    is_active: bool = Field(default=True)

    # Relaciones
    regions: List["Region"] = Relationship(back_populates="managers", link_model=UserRegionLink)
    managed_branches: List["Branch"] = Relationship(back_populates="manager")

class Region(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    description: Optional[str] = None

    # Relaciones
    branches: List["Branch"] = Relationship(back_populates="region")
    managers: List[User] = Relationship(back_populates="regions", link_model=UserRegionLink)

class Branch(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    name: str
    base_url: str
    private_key: str
    public_key: str
    is_active: bool = Field(default=True)
    last_ping: Optional[str] = None
    
    # Relación con Región
    region_id: Optional[int] = Field(default=None, foreign_key="region.id")
    region: Optional[Region] = Relationship(back_populates="branches")
    
    # Relación con Manager (fijo en sucursal)
    manager_id: Optional[int] = Field(default=None, foreign_key="user.id")
    manager: Optional[User] = Relationship(back_populates="managed_branches")

# --- Global Product Catalog ---

class GlobalCategory(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    description: Optional[str] = None
    
    products: List["GlobalProduct"] = Relationship(back_populates="category")

class GlobalMenuProductLink(SQLModel, table=True):
    menu_id: int = Field(foreign_key="globalmenu.id", primary_key=True)
    product_id: int = Field(foreign_key="globalproduct.id", primary_key=True)

class GlobalProduct(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    description: Optional[str] = None
    price_suggested: float = 0.0
    
    # Receta e Información Nutrimental
    recipe_markdown: Optional[str] = Field(default=None, description="Instrucciones de preparación")
    calories: float = Field(default=0.0)
    protein: float = Field(default=0.0)
    carbs: float = Field(default=0.0)
    fats: float = Field(default=0.0)
    
    category_id: Optional[int] = Field(default=None, foreign_key="globalcategory.id")
    category: Optional[GlobalCategory] = Relationship(back_populates="products")
    
    menus: List["GlobalMenu"] = Relationship(back_populates="products", link_model=GlobalMenuProductLink)

class GlobalMenu(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    description: Optional[str] = None
    
    products: List[GlobalProduct] = Relationship(back_populates="menus", link_model=GlobalMenuProductLink)

# --- Sales (Synced from Branches) ---

class GlobalSale(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    branch_id: str = Field(foreign_key="branch.id")
    branch_name: str
    amount: float
    items_count: int
    created_at: str # ISO format

    # Relación con los items vendidos
    items: List["GlobalSaleItem"] = Relationship(back_populates="sale")

class GlobalSaleItem(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    sale_id: int = Field(foreign_key="globalsale.id")
    product_name: str
    quantity: int
    unit_price: float

    # Relación inversa
    sale: GlobalSale = Relationship(back_populates="items")

# --- Global Customers ---

class GlobalCustomer(SQLModel, table=True):
    id: str = Field(primary_key=True) # Mismo UUID del POS
    username: Optional[str] = Field(default=None, unique=True, index=True)
    hashed_password: Optional[str] = None
    
    # Identificadores para hardware y portales (QR / NFC / Tarjetas Físicas)
    loyalty_code: str = Field(index=True, unique=True)
    nfc_tag_id: Optional[str] = Field(default=None, index=True, unique=True)
    
    # Datos Personales Cifrados (PII)
    encrypted_name: str
    encrypted_email: Optional[str] = None
    encrypted_phone: Optional[str] = None
    encrypted_telegram_id: Optional[str] = None
    
    # Fidelidad y Finanzas
    points: int = Field(default=0)
    credit_balance: float = Field(default=0.0)
    tier: str = Field(default="regular")
    
    # Historial y Analíticas Agregadas
    total_spent: float = Field(default=0.0)
    total_visits: int = Field(default=0)
    last_visit_at: Optional[datetime] = None
    favorite_branch_id: Optional[str] = None
    
    # Preferencias y Consentimientos
    accepts_marketing_email: bool = Field(default=False)
    accepts_marketing_telegram: bool = Field(default=False)
    custom_metadata: dict = Field(default={}, sa_type=JSON)
    
    is_active: bool = Field(default=True)

# Configuración de la base de datos Central
CENTRAL_DATABASE_URL = "sqlite:///central_database.db"
engine = create_engine(CENTRAL_DATABASE_URL)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

def get_central_session():
    with Session(engine) as session:
        yield session
