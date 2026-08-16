import os
import uuid
import csv
import pandas as pd
import numpy as np
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Tuple, List
from fastapi import UploadFile

from app.core.config import settings
from app.core.exceptions import FunctionalException
from app.models.dataset import DatasetMetadata, FileTypeEnum, ProcessingStateEnum

DATASET_CACHE: Dict[str, DatasetMetadata] = {}
EMPTY_ROWS_PURGED_CACHE: Dict[str, int] = {}

class DatasetService:
    @staticmethod
    def _detect_csv_delimiter(file_path: Path) -> str:
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                sample = f.read(4096)
                if not sample.strip():
                    raise FunctionalException(
                        message="El archivo CSV está vacío.",
                        code="EMPTY_FILE"
                    )
                sniffer = csv.Sniffer()
                dialect = sniffer.sniff(sample, delimiters=[',', ';', '\t', '|'])
                return dialect.delimiter
        except Exception:
            return ','

    @staticmethod
    def _clean_empty_rows(df: pd.DataFrame) -> Tuple[pd.DataFrame, int]:
        """
        Elimina de forma vectorizada filas donde todas las columnas sean nulas,
        vacías o contengan solo espacios/marcadores de ausencia.
        """
        if df.empty:
            return df, 0
        initial_count = len(df)

        # En pandas >= 3 astype(str) conserva los NaN como missing (no como "nan"),
        # por lo que hay que tratarlos explícitamente junto a los tokens inválidos
        stripped = df.astype(str).apply(lambda col: col.str.strip())
        invalid_tokens = {"", "nan", "None", "null", "undefined"}
        token_invalid = ~stripped.isna() & stripped.isin(invalid_tokens)
        row_all_invalid = (stripped.isna() | token_invalid).all(axis=1)

        cleaned_df = df[~row_all_invalid].reset_index(drop=True)
        dropped_count = initial_count - len(cleaned_df)
        return cleaned_df, dropped_count

    @staticmethod
    async def process_uploaded_file(file: UploadFile) -> DatasetMetadata:
        filename = file.filename or "uploaded_file"
        file_ext = Path(filename).suffix.lower()
        
        if file_ext not in settings.ALLOWED_EXTENSIONS:
            raise FunctionalException(
                message=f"Formato no soportado ('{file_ext}'). Por favor, sube un archivo CSV o XLSX.",
                code="INVALID_FILE_TYPE",
                details={"allowed_extensions": list(settings.ALLOWED_EXTENSIONS)}
            )

        content = await file.read()
        file_size = len(content)

        if file_size == 0:
            raise FunctionalException(
                message="El archivo subido está vacío (0 bytes).",
                code="EMPTY_FILE"
            )

        if file_size > settings.MAX_FILE_SIZE_BYTES:
            max_mb = settings.MAX_FILE_SIZE_BYTES / (1024 * 1024)
            actual_mb = round(file_size / (1024 * 1024), 2)
            raise FunctionalException(
                message=f"El archivo supera el límite de {max_mb} MB (tamaño recibido: {actual_mb} MB).",
                code="FILE_TOO_LARGE",
                details={"max_size_bytes": settings.MAX_FILE_SIZE_BYTES, "actual_size_bytes": file_size}
            )

        dataset_id = str(uuid.uuid4())
        safe_filename = f"{dataset_id}_{Path(filename).name}"
        saved_path = settings.UPLOAD_DIR / safe_filename

        with open(saved_path, "wb") as f:
            f.write(content)

        file_type = FileTypeEnum.CSV if file_ext == ".csv" else FileTypeEnum.XLSX
        warnings: List[str] = []

        try:
            if file_type == FileTypeEnum.CSV:
                delimiter = DatasetService._detect_csv_delimiter(saved_path)
                full_df = pd.read_csv(saved_path, sep=delimiter, encoding="utf-8", on_bad_lines="skip")
            else:
                excel_file = pd.ExcelFile(saved_path)
                sheet_names = excel_file.sheet_names
                if len(sheet_names) > 1:
                    warnings.append(f"El archivo Excel contiene {len(sheet_names)} hojas. Se procesará la primera hoja ('{sheet_names[0]}').")
                full_df = pd.read_excel(saved_path, sheet_name=0)

            # Limpiar filas completamente vacías y registrar el conteo
            full_df, empty_dropped = DatasetService._clean_empty_rows(full_df)
            EMPTY_ROWS_PURGED_CACHE[dataset_id] = empty_dropped

            if empty_dropped > 0:
                warnings.append(f"Se detectaron y eliminaron {empty_dropped} fila(s) completamente vacías o malformadas (,,,,,,,).")
                if file_type == FileTypeEnum.CSV:
                    full_df.to_csv(saved_path, index=False, encoding="utf-8")
                else:
                    full_df.to_excel(saved_path, index=False)

        except Exception as exc:
            if saved_path.exists():
                os.remove(saved_path)
            raise FunctionalException(
                message=f"No se pudo leer la estructura del archivo '{filename}'. Asegúrate de que sea un archivo CSV o Excel válido.",
                code="FILE_PARSING_ERROR",
                details={"technical_error": str(exc)}
            )

        row_count, col_count = full_df.shape
        columns = [str(col) for col in full_df.columns]

        if row_count == 0:
            if saved_path.exists():
                os.remove(saved_path)
            raise FunctionalException(
                message="El archivo no contiene filas de datos válidas.",
                code="NO_ROWS_FOUND"
            )

        if col_count == 0:
            if saved_path.exists():
                os.remove(saved_path)
            raise FunctionalException(
                message="El archivo no contiene columnas estructuradas.",
                code="NO_COLUMNS_FOUND"
            )

        if row_count > settings.MAX_RECOMMENDED_ROWS:
            warnings.append(f"El dataset contiene {row_count:,} filas (máximo recomendado para MVP: {settings.MAX_RECOMMENDED_ROWS:,}).")

        if col_count > settings.MAX_RECOMMENDED_COLS:
            warnings.append(f"El dataset contiene {col_count} columnas (máximo recomendado para MVP: {settings.MAX_RECOMMENDED_COLS}).")

        metadata = DatasetMetadata(
            dataset_id=dataset_id,
            filename=filename,
            file_type=file_type,
            size_bytes=file_size,
            row_count=row_count,
            column_count=col_count,
            columns=columns,
            created_at=datetime.now(timezone.utc),
            status=ProcessingStateEnum.VALIDATED,
            warnings=warnings
        )

        DATASET_CACHE[dataset_id] = metadata
        return metadata

    @staticmethod
    def get_dataset_metadata(dataset_id: str) -> DatasetMetadata:
        if dataset_id in DATASET_CACHE:
            return DATASET_CACHE[dataset_id]

        matching_files = list(settings.UPLOAD_DIR.glob(f"{dataset_id}_*"))
        if matching_files:
            target_file = matching_files[0]
            orig_filename = target_file.name[len(dataset_id)+1:]
            file_ext = target_file.suffix.lower()
            file_type = FileTypeEnum.CSV if file_ext == ".csv" else FileTypeEnum.XLSX
            
            try:
                if file_type == FileTypeEnum.CSV:
                    delimiter = DatasetService._detect_csv_delimiter(target_file)
                    df = pd.read_csv(target_file, sep=delimiter, encoding="utf-8", on_bad_lines="skip")
                else:
                    df = pd.read_excel(target_file, sheet_name=0)
                
                df, _ = DatasetService._clean_empty_rows(df)
                row_count, col_count = df.shape
                metadata = DatasetMetadata(
                    dataset_id=dataset_id,
                    filename=orig_filename,
                    file_type=file_type,
                    size_bytes=target_file.stat().st_size,
                    row_count=row_count,
                    column_count=col_count,
                    columns=[str(c) for c in df.columns],
                    created_at=datetime.now(timezone.utc),
                    status=ProcessingStateEnum.VALIDATED,
                    warnings=[]
                )
                DATASET_CACHE[dataset_id] = metadata
                return metadata
            except Exception:
                pass

        raise FunctionalException(
            message=f"No se encontró ningún dataset con el ID '{dataset_id}'. Por favor, vuelve a subir el archivo.",
            code="DATASET_NOT_FOUND",
            status_code=404
        )

    @staticmethod
    def get_saved_filepath(dataset_id: str) -> Path:
        metadata = DatasetService.get_dataset_metadata(dataset_id)
        matching_files = list(settings.UPLOAD_DIR.glob(f"{dataset_id}_*"))
        if matching_files:
            return matching_files[0]
        
        safe_filename = f"{dataset_id}_{Path(metadata.filename).name}"
        target_path = settings.UPLOAD_DIR / safe_filename
        if not target_path.exists():
            raise FunctionalException(
                message=f"El archivo físico del dataset '{dataset_id}' no está disponible.",
                code="FILE_NOT_FOUND_ON_DISK",
                status_code=404
            )
        return target_path

    @staticmethod
    def load_dataframe(dataset_id: str) -> pd.DataFrame:
        metadata = DatasetService.get_dataset_metadata(dataset_id)
        filepath = DatasetService.get_saved_filepath(dataset_id)

        if metadata.file_type == FileTypeEnum.CSV:
            delimiter = DatasetService._detect_csv_delimiter(filepath)
            df = pd.read_csv(filepath, sep=delimiter, encoding="utf-8", on_bad_lines="skip")
        else:
            df = pd.read_excel(filepath, sheet_name=0)

        df, _ = DatasetService._clean_empty_rows(df)
        return df

    @staticmethod
    def get_empty_rows_purged(dataset_id: str) -> int:
        return EMPTY_ROWS_PURGED_CACHE.get(dataset_id, 0)
