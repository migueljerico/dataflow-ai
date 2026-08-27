import uuid

from fastapi import Request, status
from fastapi.responses import JSONResponse
import logging
import traceback

logger = logging.getLogger("dataflow.exceptions")

class FunctionalException(Exception):
    """
    Excepción funcional para mostrar mensajes claros al usuario final,
    evitando exponer trazas o errores técnicos crudos.
    """
    def __init__(self, message: str, code: str = "FUNCTIONAL_ERROR", status_code: int = status.HTTP_400_BAD_REQUEST, details: dict = None):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)

async def functional_exception_handler(request: Request, exc: FunctionalException):
    logger.warning(f"Functional error [{exc.code}] on {request.url}: {exc.message}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": True,
            "code": exc.code,
            "message": exc.message,
            "details": exc.details
        }
    )

async def global_exception_handler(request: Request, exc: Exception):
    error_id = uuid.uuid4().hex[:12]
    error_traceback = traceback.format_exc()
    logger.error(
        f"[error_id={error_id}] Unhandled server error on {request.url}: {str(exc)}\n{error_traceback}"
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": True,
            "code": "INTERNAL_SERVER_ERROR",
            "message": f"Ha ocurrido un problema interno al procesar el dataset (ID: {error_id}). Contacte con soporte si persiste.",
            "details": {"error_id": error_id},
        },
    )
