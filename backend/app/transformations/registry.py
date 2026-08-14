from typing import Dict, Optional, Any
from app.transformations.base import BaseTransformation
from app.transformations.text_ops import TrimTextTransformation, NormalizeCaseTransformation, NormalizeCategoryTransformation
from app.transformations.datetime_ops import ConvertDatetimeTransformation
from app.transformations.numeric_ops import ConvertNumericTransformation, RoundNumericTransformation, ClampRangeTransformation
from app.transformations.missing_ops import (
    FillMissingTransformation, RemoveDuplicatesTransformation, RenameColumnTransformation, DropColumnTransformation
)
from app.core.exceptions import FunctionalException

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
    }

    @classmethod
    def get_transformation(cls, operation_name: str) -> BaseTransformation:
        if operation_name not in cls._registry:
            raise FunctionalException(
                message=f"La operación de transformación '{operation_name}' no está contemplada en el catálogo permitido.",
                code="UNREGISTERED_OPERATION",
                details={"allowed_operations": list(cls._registry.keys())}
            )
        return cls._registry[operation_name]

    @classmethod
    def get(cls, operation_name: str) -> Optional[BaseTransformation]:
        return cls._registry.get(operation_name)

    @classmethod
    def list_all(cls) -> Dict[str, str]:
        return {name: t.description for name, t in cls._registry.items()}
