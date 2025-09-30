from httpx import AsyncClient
import pytest
from typing import Dict

from app.models import User

# --- DATOS DE PRUEBA CONSTANTES ---
# Utilizamos un ID constante y conocido, ya que el fixture de rollback garantiza el aislamiento.
# USER_ID_TO_TEST = "c1f2e3d4-4a5b-6c7d-8e9f-0a1b2c3d4e5f" 

# Datos de prueba (Asegúrate de que user_id sea un UUID válido si tu DB lo requiere)
USER_DATA = {
    "username": "new_tester",
    "email": "new.tester@example.com",
    "password": "testpassword",
    "user_id": "c1f2e3d4-4a5b-6c7d-8e9f-0a1b2c3d4e5f" 
}
UPDATE_DATA = {"email": "updated@example.com"}
USER_ID_TO_TEST = USER_DATA["user_id"] # Usaremos este ID para el GET/PUT/DELETE


@pytest.mark.asyncio
async def test_01_create_and_read_user(
    client: AsyncClient, 
    default_user_headers: Dict[str, str],
    default_user # 👈 Añadido para forzar la inserción del usuario de autenticación
):
    """Verifica la creación (POST) con AUTH y la lectura (GET)."""
    
    # 1. Crear (POST) - Requiere headers de autenticación (usuario 'default_user' debe existir)
    response = await client.post(
        "/users/", 
        json=USER_DATA,
        headers=default_user_headers # <--- Autenticación
    )
    assert response.status_code == 201
    
    # 2. Leer (GET) y validar. Asumo que la lectura no requiere auth para simplificar el test.
    response = await client.get(f"/users/{USER_ID_TO_TEST}")
    assert response.status_code == 200
    assert response.json()["email"] == USER_DATA["email"]


@pytest.mark.asyncio
async def test_02_update_user(
    client: AsyncClient, 
    default_user_headers: Dict[str, str],
    default_user # 👈 Añadido para forzar la inserción del usuario de autenticación
):
    """Verifica la actualización (PUT) con autenticación."""
    
    # SETUP: Crear el ítem (con autenticación)
    # Esta petición es la que fallaba si 'default_user' no se cargaba previamente.
    await client.post(
        "/users/", 
        json=USER_DATA, 
        headers=default_user_headers
    )

    # 1. Actualizar (PUT) - Requiere headers de autenticación
    response = await client.put(
        f"/users/{USER_ID_TO_TEST}", 
        json=UPDATE_DATA,
        headers=default_user_headers # <--- Autenticación
    )
    assert response.status_code == 200
    
    # 2. Verificar que la actualización persiste
    verify_response = await client.get(f"/users/{USER_ID_TO_TEST}")
    assert verify_response.json()["email"] == UPDATE_DATA["email"]


@pytest.mark.asyncio
async def test_03_delete_user_and_verify_404(
    client: AsyncClient, 
    default_user_headers: Dict[str, str],
    default_user # 👈 Añadido para forzar la inserción del usuario de autenticación
):
    """Verifica la eliminación (DELETE) con autenticación y la validación 404."""
    
    # SETUP: Crear el ítem
    await client.post(
        "/users/", 
        json=USER_DATA,
        headers=default_user_headers
    )

    # 1. Eliminar (DELETE) - Requiere headers de autenticación
    response = await client.delete(
        f"/users/{USER_ID_TO_TEST}",
        headers=default_user_headers # <--- Autenticación
    )
    assert response.status_code == 204 # Éxito: No Content

    # 2. VERIFICAR: La lectura debe fallar (404)
    verify_response = await client.get(f"/users/{USER_ID_TO_TEST}")
    assert verify_response.status_code == 404
    
    # 3. VERIFICAR: Un segundo DELETE también debe fallar con 404 (validación del Handler)
    delete_response_again = await client.delete(
        f"/users/{USER_ID_TO_TEST}",
        headers=default_user_headers
    )
    assert delete_response_again.status_code == 404