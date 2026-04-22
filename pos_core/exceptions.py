from fastapi import HTTPException

class BusinessLogicError(HTTPException):
    """
    Excepción base para todos los errores de reglas de negocio controlados.
    Permite al frontend procesar los errores uniformemente.
    """
    def __init__(self, detail: str, error_code: str, status_code: int = 400):
        super().__init__(status_code=status_code, detail=detail)
        self.error_code = error_code

class OrderNotFoundError(BusinessLogicError):
    def __init__(self, order_id: int):
        super().__init__(
            detail=f"No se encontró la orden con ID {order_id}",
            error_code="ORDER_NOT_FOUND",
            status_code=404
        )

class InvalidOrderStateError(BusinessLogicError):
    def __init__(self, message: str):
        super().__init__(
            detail=message,
            error_code="INVALID_ORDER_STATE",
            status_code=400
        )
