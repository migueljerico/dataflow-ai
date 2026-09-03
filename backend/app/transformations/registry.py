from typing import Any, Dict, Optional

import pandas as pd
from app.core.exceptions import FunctionalException
from app.transformations.base import BaseTransformation
from app.transformations.cluster_ops import ClusterKMeansTransformation
from app.transformations.datetime_ops import ConvertDatetimeTransformation
from app.transformations.missing_ops import (
    DropColumnTransformation,
    FillMissingTransformation,
    RemoveDuplicatesTransformation,
    RenameColumnTransformation,
)
from app.transformations.numeric_ops import (
    ClampRangeTransformation,
    ConvertNumericTransformation,
    RoundNumericTransformation,
)
from app.transformations.outlier_ops import (
    DetectOutliersIQRTransformation,
    DetectOutliersZScoreTransformation,
)
from app.transformations.split_ops import SplitColumnTransformation
from app.transformations.text_ops import (
    NormalizeCaseTransformation,
    NormalizeCategoryTransformation,
    TrimTextTransformation,
)


class TransformationRegistry:
    _registry: Dict[str, BaseTransformation] = {
        "trim_text": TrimTextTransformation(),
        "normalize_case": NormalizeCaseTransformation(),
        "normalize_category": NormalizeCategoryTransformation(),
        "convert_datetime": ConvertDatetimeTransformation(),
        "convert_numeric": ConvertNumericTransformation(),
        "round_numeric": RoundNumericTransformation(),
        "clamp_range": ClampRangeTransformation(),
        "fill_missing": FillMissingTransformation(),
        "remove_duplicates": RemoveDuplicatesTransformation(),
        "rename_column": RenameColumnTransformation(),
        "drop_column": DropColumnTransformation(),
        "detect_outliers_iqr": DetectOutliersIQRTransformation(),
        "detect_outliers_zscore": DetectOutliersZScoreTransformation(),
        "cluster_kmeans": ClusterKMeansTransformation(),
        "split_column": SplitColumnTransformation(),
    }

    @classmethod
    def get_transformation(cls, operation_name: str) -> BaseTransformation:
        if operation_name not in cls._registry:
            raise FunctionalException(
                message=f"La operación de transformación '{operation_name}' no está contemplada en el catálogo permitido.",
                code="UNREGISTERED_OPERATION",
                details={"allowed_operations": list(cls._registry.keys())},
            )
        return cls._registry[operation_name]

    @classmethod
    def get(cls, operation_name: str) -> Optional[BaseTransformation]:
        return cls._registry.get(operation_name)

    @classmethod
    def list_all(cls) -> Dict[str, str]:
        return {name: t.description for name, t in cls._registry.items()}

    @classmethod
    def get_catalog_manifest(cls) -> Dict[str, Dict[str, Any]]:
        """Retorna el catálogo completo con schemas declarativos de cada operación."""
        return {name: t.get_manifest() for name, t in cls._registry.items()}

    @classmethod
    def validate_operation_and_parameters(
        cls, operation_name: str, df: pd.DataFrame, parameters: Dict[str, Any]
    ) -> BaseTransformation:
        """Valida que la operación exista en el Registry y que sus parámetros cumplan el contrato."""
        transformation = cls.get_transformation(operation_name)
        # Validar que no haya parámetros no contemplados si la transformación define allowed_parameters
        if transformation.allowed_parameters:
            for param_key in parameters.keys():
                if param_key.startswith("_"):  # Parámetros internos de auditoría omitidos
                    continue
                if param_key not in transformation.allowed_parameters:
                    raise FunctionalException(
                        message=f"Parámetro no permitido '{param_key}' para la operación '{operation_name}'.",
                        code="UNAUTHORIZED_PARAMETER",
                        details={"allowed_parameters": transformation.allowed_parameters},
                    )
        transformation.validate_parameters(df, parameters)
        return transformation
