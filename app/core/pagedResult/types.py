from typing import TypeVar, Generic, List, Type
from pydantic import BaseModel, Field

# Define el TypeVar para el tipo de ítem que se paginará
T = TypeVar('T')

class PagedResult(BaseModel, Generic[T]):
    """
    Estructura Genérica de Respuesta Paginada (Pydantic ViewModel). 📚

    Este modelo actúa como el 'sobre' estandarizado para todas las respuestas
    de tipo Query (lectura) que manejan colecciones de datos (endpoints GET /).
    Es un elemento clave en la capa de Presentación para asegurar una
    experiencia de paginación uniforme en toda la API.

    La clase utiliza la funcionalidad Genérica de Pydantic, donde:
    - **T** representa el Pydantic `modelResponse` de la entidad específica
      (ej: `ClientResponse` o `HousekeeperResponse`).
    - La notación de uso será: `response_model=PagedResult[ClientResponse]`.

    Los campos `skip` y `limit` de la Query de entrada se transforman
    en los campos de salida orientados al usuario (`pageNumber`, `pageSize`, etc.)
    gracias a la lógica implementada en el `GetItemsHandler`.
    """
    items: List[T] = Field(description="El array de entidades paginadas para la página actual.")
    pageNumber: int = Field(description="El número de página actual (basado en 1).")
    pageSize: int = Field(description="El tamaño máximo de la página (el 'limit' solicitado).")
    totalPages: int = Field(description="El número total de páginas disponibles.")
    totalCount: int = Field(description="El conteo total de todos los registros que coinciden con los criterios de filtrado.")
    hasPreviousPage: bool = Field(description="True si `pageNumber` > 1.")
    hasNextPage: bool = Field(description="True si `pageNumber` < `totalPages`.")

    # Pydantic V2 necesita una configuración especial para genéricos
    # (Aunque en la v2 a menudo no es estrictamente necesario, es una buena práctica de compatibilidad)
    class Config:
        arbitrary_types_allowed = True