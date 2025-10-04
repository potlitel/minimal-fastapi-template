# Esta clase hereda TODA la funcionalidad CRUD de BaseRepository
# y está tipada genéricamente para saber que maneja objetos 'Bitacora'.
from app.core.repositories.base import BaseRepository


class BitacoraRepository(BaseRepository):
    """
    Repositorio específico para la entidad Bitacora. 
    Aquí se añadirán métodos personalizados de consulta si son necesarios.
    Convención estándar en patrones de diseño para dejar un punto donde se pueda añadir lógica específica más adelante.
    (ej., get_bitcora_by_user).
    """
    pass 