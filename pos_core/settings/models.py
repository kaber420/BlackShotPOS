from typing import Optional
from sqlmodel import SQLModel, Field

class BusinessSettings(SQLModel, table=True):
    id: Optional[int] = Field(default=1, primary_key=True)
    name: str = Field(default="Blackshot Coffee", description="Nombre del negocio")
    address: Optional[str] = Field(default=None, description="Dirección física")
    phone: Optional[str] = Field(default=None, description="Teléfono de contacto")
    tax_rate: float = Field(default=0.16, description="Tasa de impuesto (ej. 0.16 para 16%)")
    currency_symbol: str = Field(default="$", description="Símbolo de moneda")
    currency_code: str = Field(default="MXN", description="Código de moneda")
    locale: str = Field(default="es-MX", description="Localización para formatos (ej. es-MX, en-US)")
    ticket_footer: Optional[str] = Field(default="¡Gracias por su preferencia!", description="Pie de página del ticket")
    
    # Bridge Auth
    bridge_enabled: bool = Field(default=False, description="Activa el acceso remoto vía Bridge")
    bridge_public_key: Optional[str] = Field(default=None, description="Llave pública RS256 para validación del Bridge")

class BusinessSettingsUpdate(SQLModel):
    name: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    tax_rate: Optional[float] = None
    currency_symbol: Optional[str] = None
    currency_code: Optional[str] = None
    locale: Optional[str] = None
    ticket_footer: Optional[str] = None
    bridge_enabled: Optional[bool] = None
    bridge_public_key: Optional[str] = None
