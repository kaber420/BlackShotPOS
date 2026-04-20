from typing import Optional
from sqlmodel import SQLModel, Field
from datetime import datetime

class IoTDevice(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    device_id: str = Field(unique=True, index=True)  # Hardware ID (MAC, UUID, etc)
    token: str = Field(unique=True, index=True)     # Long-lived secret token
    name: Optional[str] = Field(default=None)        # "Pantalla Mesa 5"
    type: str = Field(default="esp32")               # "esp32", "esp8266", "sensor"
    table_id: Optional[int] = Field(default=None, foreign_key="table.id")
    is_active: bool = Field(default=True)
    
    # Health & Metadata
    battery_level: Optional[int] = Field(default=None) # 0-100
    rssi: Optional[int] = Field(default=None)          # Signal strength (dBm)
    firmware_version: Optional[str] = Field(default=None)
    
    last_seen: Optional[datetime] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
