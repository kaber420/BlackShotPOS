from typing import Optional
from datetime import datetime, timezone
from uuid import UUID, uuid4
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import JSON, Column

class Customer(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    username: Optional[str] = Field(default=None, index=True, unique=True)
    hashed_password: Optional[str] = Field(default=None)
    
    # Identificadores para hardware y portales (QR / NFC / Tarjetas Físicas)
    loyalty_code: str = Field(default_factory=lambda: uuid4().hex[:8].upper(), index=True, unique=True)
    nfc_tag_id: Optional[str] = Field(default=None, index=True, unique=True)

    # Datos Personales Cifrados (PII)
    encrypted_name: str
    encrypted_phone: Optional[str] = Field(default=None)
    phone_hash: Optional[str] = Field(default=None, index=True, unique=True)
    encrypted_email: Optional[str] = Field(default=None)
    encrypted_telegram_id: Optional[str] = Field(default=None)

    # Fidelidad y Finanzas
    credit_balance: float = Field(default=0.0)
    points: int = Field(default=0)
    tier: str = Field(default="regular")
    
    # Historial y Analíticas Agregadas
    total_spent: float = Field(default=0.0)
    total_visits: int = Field(default=0)
    
    # Preferencias y Consentimientos
    accepts_marketing_email: bool = Field(default=False)
    accepts_marketing_telegram: bool = Field(default=False)
    
    # Infraestructura Distribuida
    organization_id: str = Field(default="default", index=True)
    is_synced: bool = Field(default=False, index=True)
    last_visit_at: datetime = Field(default_factory=datetime.utcnow)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Metadata adicional (ej: preferencias, notas)
    custom_metadata: dict = Field(default={}, sa_type=JSON)

    @property
    def name(self) -> str:
        from pos_core.crypto import CryptoService
        decrypted = CryptoService.decrypt_data(self.encrypted_name)
        if decrypted.startswith("gAAAAA"):
            return "Error de Descifrado"
        return decrypted

    @property
    def phone(self) -> Optional[str]:
        from pos_core.crypto import CryptoService
        decrypted = CryptoService.decrypt_data(self.encrypted_phone) if self.encrypted_phone else None
        if decrypted and decrypted.startswith("gAAAAA"):
            return "0000000000"
        return decrypted

    @property
    def email(self) -> Optional[str]:
        from pos_core.crypto import CryptoService
        decrypted = CryptoService.decrypt_data(self.encrypted_email) if self.encrypted_email else None
        if decrypted and decrypted.startswith("gAAAAA"):
            return "decryption-failed@blackshot.com"
        return decrypted

    @property
    def telegram_id(self) -> Optional[str]:
        from pos_core.crypto import CryptoService
        decrypted = CryptoService.decrypt_data(self.encrypted_telegram_id) if self.encrypted_telegram_id else None
        if decrypted and decrypted.startswith("gAAAAA"):
            return "decryption_failed_id"
        return decrypted

    # Relaciones
    # orders: List["Order"] = Relationship(back_populates="customer")
