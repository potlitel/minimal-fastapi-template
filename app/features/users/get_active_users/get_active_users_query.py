from app.core.crud_utils import IRequest

# NOTA: Hereda de IRequest (que incluye user_id y db)
class GetActiveUsersQuery(IRequest):
    """
    Query específica para solicitar la lista de usuarios activos.
    No requiere campos de datos adicionales, ya que el filtro es la propia intención.
    """
    skip: int = 0
    limit: int = 10 