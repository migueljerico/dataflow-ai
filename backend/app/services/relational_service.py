import re
import uuid
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from app.core.semantics import _looks_like_id_name
from app.models.workspace import (
    MultiTableStarSchema,
    RelationshipIntegrityAudit,
    StarSchemaTableNode,
    TableRoleEnum,
)
from app.services.dataset_service import DatasetService


class RelationalService:
    @staticmethod
    def _clean_table_name(raw_name: str) -> str:
        """Limpia nombres como 'clean_order_details_dirty.csv' -> 'Order_Details'."""
        name = raw_name.replace(".csv", "").replace(".xlsx", "").replace(".parquet", "")
        name = re.sub(r"^(clean_|dirty_)+", "", name, flags=re.IGNORECASE)
        name = re.sub(r"(_dirty|_clean)+$", "", name, flags=re.IGNORECASE)
        # Sanitizar
        words = [w for w in re.split(r"[_\s\-]+", name) if w]
        if not words:
            return "Table"
        return "_".join(w.capitalize() for w in words)

    @staticmethod
    def _load_dataset_df(dataset_id: str) -> Tuple[pd.DataFrame, str]:
        """Carga el DataFrame de un dataset por ID. Si ya fue procesado por un run ETL, carga la versión limpia."""
        try:
            from app.core.storage import get_storage
            from app.services.etl_service import RUNS_CACHE

            storage = get_storage()
            for run in reversed(list(RUNS_CACHE.values())):
                if run.dataset_id == dataset_id and run.clean_filename:
                    candidates = [
                        f"{run.run_id}_{run.clean_filename}",
                        run.clean_filename,
                    ]
                    for key in candidates:
                        if storage.exists(key):
                            p = storage.get_path(key)
                            clean_df = pd.read_csv(p)
                            clean_filename = run.clean_filename
                            return clean_df, clean_filename
        except Exception:
            pass

        try:
            meta = DatasetService.get_dataset_metadata(dataset_id)
            filename = meta.filename if meta else f"Dataset_{dataset_id[:8]}"
            df = DatasetService.load_dataframe(dataset_id)
            return df, filename
        except Exception:
            return pd.DataFrame(), f"Dataset_{dataset_id[:8]}"

    @staticmethod
    def detect_table_keys_and_metrics(df: pd.DataFrame, table_name: str) -> Dict[str, Any]:
        """Identifica claves primarias candidatas, medidas cuantitativas y atributos."""
        row_count = len(df)
        pks: List[str] = []
        measures: List[str] = []
        attributes: List[str] = []

        if row_count == 0:
            return {"pks": [], "measures": [], "attributes": []}

        for col in df.columns:
            s = df[col].dropna()
            col_lower = str(col).lower()
            is_id_name = (
                _looks_like_id_name(col_lower)
                or col_lower in ("date", "datekey", "fecha", "id_fecha", "key")
                or col_lower.endswith(("key", "_key"))
            )
            nunique = s.nunique()

            # Candidata a PK: valores únicos iguales o casi iguales al total de filas y nombre tipo ID/Key/Date
            if (nunique == row_count or (row_count > 5 and nunique >= row_count * 0.99)) and is_id_name:
                pks.append(col)
            elif is_id_name:
                # Clave foránea potencial o ID
                attributes.append(col)
            else:
                # Comprobar si es numérica (medida)
                num_series = pd.to_numeric(s, errors="coerce")
                valid_num_ratio = num_series.notna().sum() / len(s) if len(s) > 0 else 0
                if valid_num_ratio >= 0.8 and nunique > 3:
                    measures.append(col)
                else:
                    attributes.append(col)

        return {"pks": pks, "measures": measures, "attributes": attributes}

    @staticmethod
    def audit_relationship(
        df_from: pd.DataFrame,
        from_table: str,
        from_col: str,
        df_to: pd.DataFrame,
        to_table: str,
        to_col: str,
    ) -> Optional[RelationshipIntegrityAudit]:
        """Evalúa si existe una relación válida y audita la integridad referencial."""
        s_fk = df_from[from_col].dropna().astype(str).str.strip()
        s_pk = set(df_to[to_col].dropna().astype(str).str.strip())

        if len(s_fk) == 0 or len(s_pk) == 0:
            return None

        matching_mask = s_fk.isin(s_pk)
        matching_count = int(matching_mask.sum())
        total_fk = len(s_fk)
        orphan_count = total_fk - matching_count
        match_pct = round((matching_count / total_fk) * 100, 2) if total_fk > 0 else 100.0
        orphan_samples = s_fk[~matching_mask].unique()[:5].tolist()

        # Se considera relación válida si al menos el 60% coincide
        if match_pct < 60.0:
            return None

        return RelationshipIntegrityAudit(
            from_table=from_table,
            from_column=from_col,
            to_table=to_table,
            to_column=to_col,
            cardinality="*:1",
            total_fk_rows=total_fk,
            matching_fk_rows=matching_count,
            orphan_fk_rows=orphan_count,
            match_percentage=match_pct,
            orphan_samples=orphan_samples,
            is_referential_clean=(orphan_count == 0),
        )

    @classmethod
    def infer_star_schema(cls, dataset_ids: List[str]) -> MultiTableStarSchema:
        """
        Infiere un Esquema de Estrella completo entre múltiples tablas cargadas:
        1. Identifica PKs, FKs y medidas por tabla.
        2. Descubre relaciones Many-to-One (*:1) y verifica integridad referencial.
        3. Clasifica la Tabla de Hechos y las Tablas de Dimensión.
        4. Construye el diagrama del modelo y el script TMDL / DAX para Power BI.
        """
        tables_data: Dict[str, Dict[str, Any]] = {}

        for ds_id in dataset_ids:
            df, filename = cls._load_dataset_df(ds_id)
            if df.empty:
                continue
            t_name = cls._clean_table_name(filename)
            keys_info = cls.detect_table_keys_and_metrics(df, t_name)
            tables_data[ds_id] = {
                "id": ds_id,
                "name": t_name,
                "filename": filename,
                "df": df,
                "pks": keys_info["pks"],
                "measures": keys_info["measures"],
                "attributes": keys_info["attributes"],
            }

        if not tables_data:
            raise ValueError("No se pudieron cargar datasets válidos para inferir el esquema estrella.")

        # Buscar relaciones entre todas las parejas de tablas
        discovered_relationships: List[RelationshipIntegrityAudit] = []
        # Conteo de veces que una tabla actúa como lado muchos (FK)
        outgoing_fk_scores: Dict[str, int] = dict.fromkeys(tables_data, 0)

        table_keys = list(tables_data.keys())
        for i, id_a in enumerate(table_keys):
            data_a = tables_data[id_a]
            df_a = data_a["df"]
            cols_a = list(df_a.columns)

            for j, id_b in enumerate(table_keys):
                if i == j:
                    continue
                data_b = tables_data[id_b]
                df_b = data_b["df"]
                pks_b = data_b["pks"]

                for pk_b in pks_b:
                    # Comprobar columnas de A que puedan ser FK hacia pk_b
                    candidate_fk_cols = [
                        ca
                        for ca in cols_a
                        if ca.lower() == pk_b.lower()
                        or ca.lower().endswith(pk_b.lower())
                        or (pk_b.lower() == "date" and "date" in ca.lower())
                    ]

                    for fk_col in candidate_fk_cols:
                        rel = cls.audit_relationship(
                            df_from=df_a,
                            from_table=data_a["name"],
                            from_col=fk_col,
                            df_to=df_b,
                            to_table=data_b["name"],
                            to_col=pk_b,
                        )
                        if rel:
                            discovered_relationships.append(rel)
                            outgoing_fk_scores[id_a] += 2

        # Determinar cuál es la Tabla de Hechos:
        # Mayor número de medidas numéricas y mayores salidas de claves foráneas
        fact_id = None
        max_fact_score = -1

        for ds_id, t_info in tables_data.items():
            f_score = (
                len(t_info["measures"]) * 3
                + outgoing_fk_scores[ds_id] * 4
                + (
                    1
                    if "order" in t_info["name"].lower()
                    or "sale" in t_info["name"].lower()
                    or "fact" in t_info["name"].lower()
                    else 0
                )
                * 10
            )
            # Desempate con número de filas
            f_score += np.log10(max(1, len(t_info["df"])))
            if f_score > max_fact_score:
                max_fact_score = f_score
                fact_id = ds_id

        if not fact_id:
            fact_id = table_keys[0]

        fact_info = tables_data[fact_id]
        fact_node = StarSchemaTableNode(
            table_id=fact_id,
            table_name=fact_info["name"],
            role=TableRoleEnum.FACT,
            row_count=len(fact_info["df"]),
            column_count=len(fact_info["df"].columns),
            primary_keys=fact_info["pks"],
            foreign_keys=[r.from_column for r in discovered_relationships if r.from_table == fact_info["name"]],
            attributes=fact_info["attributes"],
            measures=fact_info["measures"],
        )

        dim_nodes: List[StarSchemaTableNode] = []
        for ds_id, t_info in tables_data.items():
            if ds_id == fact_id:
                continue
            dim_name = t_info["name"]
            if not dim_name.lower().startswith("dim_"):
                dim_name = f"Dim_{dim_name}"
            dim_nodes.append(
                StarSchemaTableNode(
                    table_id=ds_id,
                    table_name=dim_name,
                    role=TableRoleEnum.DIMENSION,
                    row_count=len(t_info["df"]),
                    column_count=len(t_info["df"].columns),
                    primary_keys=t_info["pks"],
                    foreign_keys=[r.from_column for r in discovered_relationships if r.from_table == t_info["name"]],
                    attributes=t_info["attributes"],
                    measures=t_info["measures"],
                )
            )

        # Generar medidas DAX automáticas para la tabla de hechos
        dax_measures: Dict[str, str] = {
            "Total_Registros": f"COUNTROWS('{fact_node.table_name}')",
        }
        for m in fact_node.measures[:5]:
            dax_measures[f"Suma_{m}"] = f"SUM('{fact_node.table_name}'[{m}])"
            dax_measures[f"Promedio_{m}"] = f"AVERAGE('{fact_node.table_name}'[{m}])"

        # Generar TMDL
        tmdl_lines: List[str] = [
            "model Model",
            "\tculture: es-ES",
            "\tdefaultPowerBIDataSourceVersion: powerBI_V3",
            "",
            f"ref table '{fact_node.table_name}'",
        ]
        for d in dim_nodes:
            tmdl_lines.append(f"ref table '{d.table_name}'")

        if discovered_relationships:
            tmdl_lines.append("")
            for r in discovered_relationships:
                rel_name = f"Rel_{r.from_table}_{r.from_column}_{r.to_table}"
                tmdl_lines.append(f"relationship {rel_name}")
                tmdl_lines.append(f"\tfromColumn: {r.from_table}.{r.from_column}")
                tmdl_lines.append(f"\ttoColumn: {r.to_table}.{r.to_column}")

        tmdl_code = "\n".join(tmdl_lines) + "\n"

        # Puntuación global de integridad
        if discovered_relationships:
            global_integrity = round(
                sum(r.match_percentage for r in discovered_relationships) / len(discovered_relationships), 2
            )
        else:
            global_integrity = 100.0

        return MultiTableStarSchema(
            model_id=f"MODEL-{uuid.uuid4().hex[:8]}",
            model_name=f"StarSchema_{fact_node.table_name}",
            fact_table=fact_node,
            dimension_tables=dim_nodes,
            relationships=discovered_relationships,
            suggested_dax_measures=dax_measures,
            tmdl_definition=tmdl_code,
            referential_integrity_score=global_integrity,
        )
