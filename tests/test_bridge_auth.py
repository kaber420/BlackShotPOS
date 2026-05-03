import asyncio
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from saas_core.manager import manager

def generate_key_pair():
    # Generar clave privada RSA
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )
    
    # Obtener la clave privada en formato PEM
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )
    
    # Obtener la clave pública en formato PEM
    public_key = private_key.public_key()
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    
    return private_pem.decode('utf-8'), public_pem.decode('utf-8')

async def main():
    print("--- Test del Manager Central (Bridge) ---")
    private_pem, public_pem = generate_key_pair()
    
    print("\n[!] Llave pública para configurar en la sucursal (Settings de la DB):")
    print(public_pem)
    
    # Registrar sucursal en el SaaS (usamos localhost como si fuera la URL pública de la sucursal)
    branch_id = "sucursal-001"
    manager.register_branch(
        branch_id=branch_id,
        name="Sucursal Matriz",
        base_url="http://127.0.0.1:8000/api/v1",
        private_key=private_pem
    )
    
    print(f"\n[+] Sucursal '{branch_id}' registrada en SaaS Connection Manager.")
    
    token = manager.generate_bridge_token(branch_id)
    print(f"\n[+] Token Bridge generado:")
    print(f"X-Blackshot-Bridge-Auth: {token[:40]}...{token[-20:]}")
    
    print("\n[*] Para probar esto en la API real (asegúrate de que el backend esté corriendo y puente habilitado):")
    print(f"curl -X GET http://127.0.0.1:8000/api/v1/inventory/categories -H 'X-Blackshot-Bridge-Auth: {token}'")

if __name__ == "__main__":
    asyncio.run(main())
