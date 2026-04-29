import os
from typing import Optional

def delete_local_image(url: Optional[str]):
    """Elimina físicamente un archivo de imagen si es local."""
    if not url or not url.startswith("/uploads/"):
        return
    filename = url.replace("/uploads/", "")
    # Evitar salir del directorio por seguridad
    if "/" in filename or ".." in filename:
        return
    file_path = os.path.join("data/img", filename)
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
        except Exception as e:
            print(f"Error borrando archivo {file_path}: {e}")
