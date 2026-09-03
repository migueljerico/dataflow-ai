"""
Modelos de reportes ejecutivos programados y notificaciones webhook (v1.16.0).

Gobernanza: la programación de exportaciones y los webhooks los configura
explícitamente el usuario (Human-in-the-Loop). El motor solo genera el reporte
determinista y entrega la notificación; nunca decide por su cuenta.
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field

from app.models.etl import utc_now


class ReportFormatEnum(str, Enum):
    HTML = "html"
    PDF = "pdf"


class WebhookTriggerEnum(str, Enum):
    ALWAYS = "always"
    CRITICAL_DRIFT = "critical_drift"


class ReportScheduleCreate(BaseModel):
    run_id: str = Field(..., description="Ejecución ETL cuyo reporte ejecutivo se exportará")
    report_format: ReportFormatEnum = Field(ReportFormatEnum.PDF, description="Formato del reporte (html o pdf)")
    interval_minutes: int = Field(60, ge=5, le=1440, description="Intervalo de regeneración en minutos (5-1440)")
    webhook_url: Optional[str] = Field(
        None, description="URL HTTPS pública que recibirá la notificación (validada contra SSRF)"
    )
    trigger: WebhookTriggerEnum = Field(
        WebhookTriggerEnum.CRITICAL_DRIFT,
        description="Condición de envío: 'always' en cada regeneración o 'critical_drift' solo con drift crítico",
    )
    lang: str = Field("es", description="Idioma del reporte (es, en)")


class ReportSchedule(BaseModel):
    schedule_id: str
    run_id: str
    dataset_id: str
    report_format: ReportFormatEnum
    interval_minutes: int
    webhook_url: Optional[str] = None
    trigger: WebhookTriggerEnum = WebhookTriggerEnum.CRITICAL_DRIFT
    lang: str = "es"
    enabled: bool = True
    created_at: datetime = Field(default_factory=utc_now)
    next_run_at: Optional[datetime] = None
    last_executed_at: Optional[datetime] = None
    last_status: Optional[str] = Field(None, description="Resultado de la última ejecución programada")
    last_drift_status: Optional[str] = Field(None, description="overall_drift_status del último reporte generado")
    last_error: Optional[str] = None
    executions_count: int = 0
    deliveries_count: int = 0
    last_report_key: Optional[str] = Field(None, description="Clave de almacenamiento del último reporte generado")


class WebhookDeliveryResult(BaseModel):
    delivered: bool
    reason: str
    http_status: Optional[int] = None
    error: Optional[str] = None


class ScheduleExecutionLog(BaseModel):
    schedule_id: str
    executed_at: datetime = Field(default_factory=utc_now)
    report_format: ReportFormatEnum
    drift_status: Optional[str] = None
    report_key: Optional[str] = None
    webhook: Optional[WebhookDeliveryResult] = None
    error: Optional[str] = None


class ReportScheduleListResponse(BaseModel):
    schedules: List[ReportSchedule]
    total: int
