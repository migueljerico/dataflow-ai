from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd
from app.core.exceptions import FunctionalException
from app.transformations.base import BaseTransformation


def _kmeans_numpy(
    X: np.ndarray,
    n_clusters: int,
    max_iter: int = 100,
    random_state: int = 42,
) -> np.ndarray:
    """Implementación determinista pura de K-Means en NumPy con inicialización K-Means++."""
    n_samples, n_features = X.shape
    if n_samples < n_clusters:
        return np.arange(n_samples)

    rng = np.random.RandomState(random_state)

    # 1. Inicialización K-Means++
    centers = np.empty((n_clusters, n_features), dtype=np.float64)
    initial_idx = rng.randint(0, n_samples)
    centers[0] = X[initial_idx]

    for c_idx in range(1, n_clusters):
        # Distancia mínima de cada punto a los centros ya seleccionados
        dists = np.min([np.sum((X - centers[i]) ** 2, axis=1) for i in range(c_idx)], axis=0)
        dists_sum = np.sum(dists)
        if dists_sum > 0:
            probs = dists / dists_sum
            cumprobs = np.cumsum(probs)
            r = rng.rand()
            chosen_idx = np.searchsorted(cumprobs, r)
            chosen_idx = min(chosen_idx, n_samples - 1)
        else:
            chosen_idx = rng.randint(0, n_samples)
        centers[c_idx] = X[chosen_idx]

    # 2. Iteraciones de Lloyd
    labels = np.zeros(n_samples, dtype=np.int32)
    for _ in range(max_iter):
        # Asignación de puntos al centro más cercano
        distances = np.linalg.norm(X[:, np.newaxis, :] - centers[np.newaxis, :, :], axis=2)
        new_labels = np.argmin(distances, axis=1)

        if np.array_equal(labels, new_labels):
            break
        labels = new_labels

        # Recálculo de centroides
        for k in range(n_clusters):
            mask = labels == k
            if np.any(mask):
                centers[k] = np.mean(X[mask], axis=0)
            else:
                # Re-seed de cluster vacío con punto más distante
                farthest = np.argmax(np.min(distances, axis=1))
                centers[k] = X[farthest]

    return labels


class ClusterKMeansTransformation(BaseTransformation):
    operation_name = "cluster_kmeans"
    description = (
        "Segmenta las observaciones en K clusters deterministas basados en variables numéricas, "
        "agregando una columna de etiqueta de cluster."
    )
    risk = "low"
    reversible = True
    allowed_parameters = ["columns", "n_clusters", "output_column", "scale_features"]
    parameter_schema = {
        "columns": {
            "type": "array",
            "items": {"type": "string"},
            "required": True,
            "description": "Lista de columnas numéricas a utilizar para segmentar",
        },
        "n_clusters": {
            "type": "integer",
            "required": False,
            "default": 3,
            "description": "Número de clusters K deseados (entre 2 y 20)",
        },
        "output_column": {
            "type": "string",
            "required": False,
            "default": "cluster_id",
            "description": "Nombre de la columna donde se guardará el ID de cluster",
        },
        "scale_features": {
            "type": "boolean",
            "required": False,
            "default": True,
            "description": "Normalizar las variables (Z-score) antes de calcular distancias euclidianas",
        },
    }
    requires_human_approval = False

    def validate_parameters(self, df: pd.DataFrame, parameters: Dict[str, Any]) -> None:
        columns = parameters.get("columns")
        if not columns or not isinstance(columns, list) or len(columns) == 0:
            raise FunctionalException(
                message="El parámetro 'columns' debe ser una lista no vacía de nombres de columnas.",
                code="INVALID_PARAMETER",
            )
        for col in columns:
            if col not in df.columns:
                raise FunctionalException(
                    message=f"La columna '{col}' no existe en el dataset.",
                    code="INVALID_COLUMN",
                )

        n_clusters = parameters.get("n_clusters", 3)
        if not isinstance(n_clusters, int) or n_clusters < 2 or n_clusters > 20:
            raise FunctionalException(
                message="El parámetro 'n_clusters' debe ser un número entero entre 2 y 20.",
                code="INVALID_PARAMETER",
            )

        out_col = parameters.get("output_column", "cluster_id")
        if not isinstance(out_col, str) or not out_col.strip():
            raise FunctionalException(
                message="El parámetro 'output_column' debe ser una cadena no vacía.",
                code="INVALID_PARAMETER",
            )

    def apply(self, df: pd.DataFrame, parameters: Dict[str, Any]) -> Tuple[pd.DataFrame, int]:
        self.validate_parameters(df, parameters)
        columns: List[str] = parameters["columns"]
        n_clusters: int = int(parameters.get("n_clusters", 3))
        output_column: str = parameters.get("output_column", "cluster_id")
        scale_features: bool = bool(parameters.get("scale_features", True))

        df_copy = df.copy()
        if df_copy.empty:
            df_copy[output_column] = []
            return df_copy, 0

        # Construir matriz de características
        feature_matrices = []
        for col in columns:
            num_s = pd.to_numeric(df_copy[col], errors="coerce")
            # Imputar NaNs con mediana o 0 para cálculo de clustering
            median_val = float(num_s.median()) if pd.notna(num_s.median()) else 0.0
            feature_matrices.append(num_s.fillna(median_val).values)

        X = np.column_stack(feature_matrices).astype(np.float64)

        if scale_features and X.shape[0] > 1:
            means = np.mean(X, axis=0)
            stds = np.std(X, axis=0, ddof=0)
            stds[stds == 0] = 1.0  # Evitar división por cero si varianza nula
            X = (X - means) / stds

        labels = _kmeans_numpy(X, n_clusters=n_clusters, max_iter=100, random_state=42)
        df_copy[output_column] = labels

        return df_copy, len(df_copy)
