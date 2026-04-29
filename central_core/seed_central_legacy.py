from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from sqlmodel import Session
from models import Branch, engine, create_db_and_tables
import uuid

def generate_key_pair():
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    ).decode('utf-8')
    
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode('utf-8')
    
    return private_pem, public_pem

def init_saas_db():
    print("--- Inicializando Base de Datos SaaS ---")
    create_db_and_tables()
    
    private_key, public_key = generate_key_pair()
    
    with Session(engine) as session:
        # Verificar si ya existe la sucursal de prueba
        test_branch = Branch(
            id="sucursal-demo",
            name="Sucursal de Prueba (Local)",
            base_url="http://localhost:8000/api/v1",
            private_key=private_key,
            public_key=public_key
        )
        session.add(test_branch)
        session.commit()
        
    print("\n[✓] Base de datos creada: saas_database.db")
    print("[✓] Sucursal 'sucursal-demo' registrada.")
    print("\n[!] IMPORTANTE: Copia esta Llave Pública en la configuración de tu POS local:")
    print("-" * 30)
    print(public_key)
    print("-" * 30)
    print("\n[i] Asegúrate de que 'bridge_enabled' sea true en el POS.")

if __name__ == "__main__":
    init_saas_db()
