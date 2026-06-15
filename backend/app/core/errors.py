from fastapi import Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel


class ErrorResponse(BaseModel):
    status: str = "failed"
    error_code: str
    failed_step: str | None = None
    message: str
    next_action: str | None = None


class AppError(Exception):
    """Application-level error that produces an honest, structured failure response."""

    def __init__(
        self,
        *,
        error_code: str,
        message: str,
        failed_step: str | None = None,
        next_action: str | None = None,
        status_code: int = status.HTTP_400_BAD_REQUEST,
    ) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.message = message
        self.failed_step = failed_step
        self.next_action = next_action
        self.status_code = status_code

    def to_response(self) -> ErrorResponse:
        return ErrorResponse(
            error_code=self.error_code,
            failed_step=self.failed_step,
            message=self.message,
            next_action=self.next_action,
        )


async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_response().model_dump(),
    )


async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Return a safe generic error for unexpected exceptions.

    The detailed exception is not exposed to the client. Logs can be added in a later phase.
    """

    _ = request, exc
    response = ErrorResponse(
        error_code="INTERNAL_SERVER_ERROR",
        failed_step="backend",
        message="MeshFlow encountered an unexpected backend error.",
        next_action="Try again later or check backend logs.",
    )
    return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=response.model_dump())
