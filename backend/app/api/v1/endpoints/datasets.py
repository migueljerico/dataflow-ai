import uuid
from pathlib import Path
from typing import List, Optional

import pandas as pd
from app.core.exceptions import FunctionalException
from app.core.storage import get_storage
from app.models.dataset import (
    DatasetFromUrlRequest,
    DatasetMetadata,
    FileTypeEnum,
    OpenDataSearchResponse,
    OpenDatasetItem,
    ProcessingStateEnum,
)
from app.services.dataset_service import DATASET_CACHE, DatasetService
from app.services.open_data_service import OpenDataService
from fastapi import APIRouter, File, Query, UploadFile, status

router = APIRouter()

SAMPLES_MAP = {
    "contact_center": {
        "id": "contact_center",
        "title": "Contact Center & Operaciones",
        "filename": "contact_center_corrupted.csv",
        "description": "KPIs operativos (AHT, Conversión, Score de Calidad, Absentismo) con fechas mezcladas y outliers.",
        "icon": "PhoneCall",
    },
    "sales": {
        "id": "sales",
        "title": "Ventas & Comercial",
        "filename": "sales_sample_corrupted.csv",
        "description": "Transacciones comerciales con precios (€, $), fechas multi-formato, clientes en mayúsculas y duplicados.",
        "icon": "ShoppingCart",
    },
    "people_analytics": {
        "id": "people_analytics",
        "title": "People Analytics & RRHH",
        "filename": "people_analytics_corrupted.csv",
        "description": "Plantilla, productividad, salarios y absentismo con fechas no estándar y anomalías de rango.",
        "icon": "Users",
    },
}


@router.get("/samples")
async def list_sample_datasets():
    """
    Listar los datasets de demostración preconfigurados para pruebas rápidas con 1 clic.
    """
    return list(SAMPLES_MAP.values())


@router.post("/samples/{sample_id}/load", response_model=DatasetMetadata, status_code=status.HTTP_201_CREATED)
async def load_sample_dataset(sample_id: str):
    """
    Cargar instantáneamente un dataset de demostración sin necesidad de subir un archivo manual.
    """
    if sample_id not in SAMPLES_MAP:
        raise FunctionalException(
            message=f"Dataset demo '{sample_id}' no encontrado. Opciones: {list(SAMPLES_MAP.keys())}",
            code="SAMPLE_NOT_FOUND",
            status_code=404,
        )

    sample_info = SAMPLES_MAP[sample_id]
    sample_filename = sample_info["filename"]

    candidate_paths = [
        Path(__file__).resolve().parents[4] / "data_samples" / sample_filename,
        Path(__file__).resolve().parents[3] / "data_samples" / sample_filename,
        Path.cwd().parent / "data_samples" / sample_filename,
        Path.cwd() / "data_samples" / sample_filename,
        Path("d:/DataFlow Project/data_samples") / sample_filename,
    ]
    sample_path = next((p for p in candidate_paths if p.exists()), None)

    if not sample_path or not sample_path.exists():
        raise FunctionalException(
            message=f"El archivo demo '{sample_filename}' no existe en el servidor.",
            code="SAMPLE_FILE_MISSING",
            status_code=404,
        )

    with open(sample_path, "rb") as f:
        content = f.read()

    dataset_id = str(uuid.uuid4())
    safe_filename = f"{dataset_id}_{sample_filename}"
    storage = get_storage()
    saved_path = storage.save_file(safe_filename, content)

    delimiter = DatasetService._detect_csv_delimiter(saved_path)
    id_dtypes = DatasetService._detect_id_columns(saved_path, delimiter=delimiter)
    df = pd.read_csv(saved_path, sep=delimiter, encoding="utf-8", dtype=id_dtypes, on_bad_lines="skip")
    df, empty_dropped = DatasetService._clean_empty_rows(df)

    warnings: List[str] = []
    if empty_dropped > 0:
        warnings.append(
            f"Se detectaron y eliminaron {empty_dropped} fila(s) completamente vacías o malformadas (,,,,,,,)."
        )
        df.to_csv(saved_path, index=False, encoding="utf-8")

    row_count, col_count = df.shape
    metadata = DatasetMetadata(
        dataset_id=dataset_id,
        filename=sample_filename,
        file_type=FileTypeEnum.CSV,
        size_bytes=len(content),
        row_count=row_count,
        column_count=col_count,
        columns=[str(c) for c in df.columns],
        status=ProcessingStateEnum.VALIDATED,
        warnings=warnings,
    )

    DATASET_CACHE[dataset_id] = metadata
    return metadata


@router.post("/upload", response_model=DatasetMetadata, status_code=status.HTTP_201_CREATED)
async def upload_dataset(file: UploadFile = File(...)):
    """
    Subir un dataset empresarial (CSV o XLSX) para validación de formato y estructura.
    """
    return await DatasetService.process_uploaded_file(file)


@router.post("/from-url", response_model=DatasetMetadata, status_code=status.HTTP_201_CREATED)
async def load_dataset_from_url(payload: DatasetFromUrlRequest):
    """
    Importar y procesar un dataset directamente desde una URL pública (HTTP/HTTPS).
    Incluye protección contra SSRF, mitigación de DNS Rebinding mediante IP Pinning,
    y streaming defensivo con límite de tamaño para proteger la memoria RAM (tmpfs) en Cloud Run.
    """
    return await DatasetService.download_and_process_url(str(payload.url))


@router.get("/open-data/featured", response_model=List[OpenDatasetItem])
async def get_featured_open_datasets():
    """
    Listar los datasets públicos de Open Data destacados y verificados para importación directa.
    """
    return OpenDataService.get_featured_datasets()


@router.get("/open-data/search", response_model=OpenDataSearchResponse)
async def search_open_datasets(query: Optional[str] = None, limit: int = Query(10, ge=1, le=50)):
    """
    Buscar datasets públicos en portales Open Data (estándar CKAN y catálogo curado).
    """
    return await OpenDataService.search_datasets(query=query, limit=limit)


@router.get("/{dataset_id}", response_model=DatasetMetadata)
async def get_dataset(dataset_id: str):
    """
    Obtener metadatos de un dataset validado.
    """
    return DatasetService.get_dataset_metadata(dataset_id)
