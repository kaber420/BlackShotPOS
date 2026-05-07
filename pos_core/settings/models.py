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
    
    # Bridge & Sync Settings
    bridge_enabled: bool = Field(default=False, description="Activa el acceso remoto vía Bridge")
    bridge_public_key: Optional[str] = Field(default=None, description="Llave pública RS256 para validación del Bridge")
    nats_url: str = Field(default="nats://localhost:4222", description="URL del servidor NATS para sincronización")
    branch_id: str = Field(default="branch_default", description="Identificador único de esta sucursal en la Central")
    
    # Menu Public Settings
    menu_title: str = Field(default="Nuestra Selección", description="Título de la carta digital")
    menu_subtitle: str = Field(default="Preparado con pasión, servido con arte.", description="Subtítulo de la carta digital")
    menu_logo_url: Optional[str] = Field(default=None, description="URL del logo para la carta")
    menu_footer_text: str = Field(default="BlackShot POS", description="Texto principal del footer")
    menu_footer_tagline: str = Field(default="Disfruta de nuestra selección premium.", description="Tagline del footer")
    menu_accent_color: str = Field(default="#6366f1", description="Color de acento para la carta")
    
    # Social Media
    menu_facebook_url: Optional[str] = Field(default=None, description="URL de Facebook")
    menu_instagram_url: Optional[str] = Field(default=None, description="URL de Instagram")
    menu_youtube_url: Optional[str] = Field(default=None, description="URL de YouTube")
    menu_twitter_url: Optional[str] = Field(default=None, description="URL de Twitter/X")
    menu_tiktok_url: Optional[str] = Field(default=None, description="URL de TikTok")
    menu_whatsapp_url: Optional[str] = Field(default=None, description="URL de WhatsApp")

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
    nats_url: Optional[str] = None
    branch_id: Optional[str] = None
    menu_title: Optional[str] = None
    menu_subtitle: Optional[str] = None
    menu_logo_url: Optional[str] = None
    menu_footer_text: Optional[str] = None
    menu_footer_tagline: Optional[str] = None
    menu_accent_color: Optional[str] = None
    menu_facebook_url: Optional[str] = None
    menu_instagram_url: Optional[str] = None
    menu_youtube_url: Optional[str] = None
    menu_twitter_url: Optional[str] = None
    menu_tiktok_url: Optional[str] = None
    menu_whatsapp_url: Optional[str] = None
