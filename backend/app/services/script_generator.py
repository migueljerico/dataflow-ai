import json
import re
from typing import List, Optional

from app.models.etl import TransformationStep

_SAFE_COL_RE = re.compile(r"^[A-Za-z0-9_ ]+$")


def _safe_col_literal(col: str) -> str:
    return json.dumps(col)


def _validate_column_name(col: str) -> bool:
    return bool(col) and bool(_SAFE_COL_RE.match(col))


class ScriptGeneratorService:
    @staticmethod
    def generate_python_script(filename: str, steps: List[TransformationStep]) -> str:
        filename_literal = json.dumps(filename)
        clean_literal = json.dumps(f"clean_{filename}")
        code_lines = [
            "# -*- coding: utf-8 -*-",
            '"""',
            "DataFlow AI — Reproducible ETL Pipeline Script",
            "Generated automatically by DataFlow AI Engine.",
            '"""',
            "",
            "import re",
            "import json",
            "import pandas as pd",
            "import numpy as np",
            "",
            "def run_etl_pipeline(input_filepath: str, output_filepath: str):",
            '    print(f"Loading raw dataset from {input_filepath}...")',
            '    if input_filepath.endswith(".csv"):',
            '        df = pd.read_csv(input_filepath, on_bad_lines="skip")',
            "    else:",
            "        df = pd.read_excel(input_filepath)",
            "",
            "    initial_rows, initial_cols = df.shape",
            '    print(f"Dataset loaded: {initial_rows} rows, {initial_cols} columns.")',
            "",
        ]

        for idx, step in enumerate(steps, 1):
            op = step.operation
            params = step.parameters
            col = params.get("column", "")
            col_lit = _safe_col_literal(col)

            code_lines.append(f"    # Step {idx}: {step.reason} ({op})")

            if op == "trim_text":
                code_lines.append(f"    if {col_lit} in df.columns:")
                code_lines.append(
                    f'        df[{col_lit}] = df[{col_lit}].astype(str).apply(lambda x: re.sub(r"\\s+", " ", x.strip()) if pd.notna(x) and x.lower() != "nan" else x)'
                )

            elif op == "normalize_case":
                mode = params.get("mode", "title")
                code_lines.append(f"    if {col_lit} in df.columns:")
                if mode == "lower":
                    code_lines.append(f"        df[{col_lit}] = df[{col_lit}].astype(str).str.lower()")
                elif mode == "upper":
                    code_lines.append(f"        df[{col_lit}] = df[{col_lit}].astype(str).str.upper()")
                else:
                    code_lines.append(f"        df[{col_lit}] = df[{col_lit}].astype(str).str.title()")

            elif op == "normalize_category":
                mappings = params.get("mappings", {})
                code_lines.append(f"    if {col_lit} in df.columns:")
                code_lines.append(f"        df[{col_lit}] = df[{col_lit}].astype(str).replace({mappings})")

            elif op == "convert_datetime":
                target_fmt = params.get("target_format", "%Y-%m-%d")
                fmt_lit = json.dumps(target_fmt)
                code_lines.append(f"    if {col_lit} in df.columns:")
                code_lines.append(
                    f'        df[{col_lit}] = pd.to_datetime(df[{col_lit}], dayfirst=True, format="mixed", errors="coerce").dt.strftime({fmt_lit})'
                )

            elif op == "convert_numeric":
                code_lines.append(f"    if {col_lit} in df.columns:")
                code_lines.append(
                    f'        cleaned = df[{col_lit}].astype(str).str.replace("€", "").str.replace("$", "").str.replace("%", "").str.strip()'
                )
                code_lines.append(
                    '        placeholders = ["n/d", "n/a", "nd", "na", "-", "null", "none", "nan", "undefined"]'
                )
                code_lines.append(
                    '        cleaned = cleaned.apply(lambda x: np.nan if str(x).lower().strip() in placeholders or str(x).strip() == "" else x)'
                )
                code_lines.append(f'        df[{col_lit}] = pd.to_numeric(cleaned, errors="coerce")')

            elif op == "round_numeric":
                decimals = params.get("decimals", 2)
                code_lines.append(f"    if {col_lit} in df.columns:")
                code_lines.append(
                    f'        df[{col_lit}] = pd.to_numeric(df[{col_lit}], errors="coerce").round({decimals})'
                )

            elif op == "clamp_range":
                min_v = params.get("min_value")
                max_v = params.get("max_value")
                code_lines.append(f"    if {col_lit} in df.columns:")
                code_lines.append(f'        s = pd.to_numeric(df[{col_lit}], errors="coerce")')
                if min_v is not None:
                    code_lines.append(f"        s = s.apply(lambda x: {min_v} if pd.notna(x) and x < {min_v} else x)")
                if max_v is not None:
                    code_lines.append(f"        s = s.apply(lambda x: {max_v} if pd.notna(x) and x > {max_v} else x)")
                code_lines.append(f"        df[{col_lit}] = s")

            elif op == "fill_missing":
                strat = params.get("strategy", "constant")
                val = params.get("value", "Desconocido")
                val_lit = json.dumps(str(val))
                code_lines.append(f"    if {col_lit} in df.columns:")
                code_lines.append(f'        df[{col_lit}] = df[{col_lit}].replace(r"^\\s*$", np.nan, regex=True)')
                if strat == "mean":
                    code_lines.append(
                        f'        df[{col_lit}] = df[{col_lit}].fillna(pd.to_numeric(df[{col_lit}], errors="coerce").mean())'
                    )
                elif strat == "median":
                    code_lines.append(
                        f'        df[{col_lit}] = df[{col_lit}].fillna(pd.to_numeric(df[{col_lit}], errors="coerce").median())'
                    )
                else:
                    code_lines.append(f"        df[{col_lit}] = df[{col_lit}].fillna({val_lit})")

            elif op == "remove_duplicates":
                subset = params.get("subset_columns")
                if subset:
                    code_lines.append(f'    df = df.drop_duplicates(subset={subset}, keep="first")')
                else:
                    code_lines.append('    df = df.drop_duplicates(keep="first")')

            elif op == "rename_column":
                new_name = params.get("new_name") or ""
                new_lit = json.dumps(new_name)
                code_lines.append(f"    if {col_lit} in df.columns:")
                code_lines.append(f"        df = df.rename(columns={{{col_lit}: {new_lit}}})")

            elif op == "drop_column":
                code_lines.append(f"    if {col_lit} in df.columns:")
                code_lines.append(f"        df = df.drop(columns=[{col_lit}])")

            elif op == "detect_outliers_iqr":
                mult = float(params.get("multiplier", 1.5))
                action = params.get("action", "cap")
                lq = float(params.get("lower_quantile", 0.25))
                uq = float(params.get("upper_quantile", 0.75))
                code_lines.append(f"    if {col_lit} in df.columns:")
                code_lines.append(f'        _s = pd.to_numeric(df[{col_lit}], errors="coerce")')
                code_lines.append("        _v = _s.dropna()")
                code_lines.append("        if not _v.empty:")
                code_lines.append(f"            _q1 = float(_v.quantile({lq}))")
                code_lines.append(f"            _q3 = float(_v.quantile({uq}))")
                code_lines.append("            _iqr = _q3 - _q1")
                code_lines.append(f"            _lb = _q1 - ({mult} * _iqr)")
                code_lines.append(f"            _ub = _q3 + ({mult} * _iqr)")
                code_lines.append("            _mask = (_s < _lb) | (_s > _ub)")
                if action == "cap":
                    code_lines.append(
                        f"            df[{col_lit}] = _s.apply(lambda x: _lb if pd.notna(x) and x < _lb else (_ub if pd.notna(x) and x > _ub else x))"
                    )
                elif action == "nullify":
                    code_lines.append(f"            df.loc[_mask, {col_lit}] = np.nan")
                elif action == "drop":
                    code_lines.append("            df = df[~_mask].reset_index(drop=True)")
                elif action == "flag":
                    flag_col = json.dumps(f"{col}_is_outlier")
                    code_lines.append(f"            df[{flag_col}] = _mask")

            elif op == "detect_outliers_zscore":
                thresh = float(params.get("threshold", 3.0))
                action = params.get("action", "cap")
                code_lines.append(f"    if {col_lit} in df.columns:")
                code_lines.append(f'        _s = pd.to_numeric(df[{col_lit}], errors="coerce")')
                code_lines.append("        _v = _s.dropna()")
                code_lines.append("        if len(_v) >= 2 and _v.std(ddof=1) > 0:")
                code_lines.append("            _m = float(_v.mean())")
                code_lines.append("            _std = float(_v.std(ddof=1))")
                code_lines.append("            _z = (_s - _m).abs() / _std")
                code_lines.append(f"            _mask = _z > {thresh}")
                if action == "cap":
                    code_lines.append(f"            _lb = _m - ({thresh} * _std)")
                    code_lines.append(f"            _ub = _m + ({thresh} * _std)")
                    code_lines.append(
                        f"            df[{col_lit}] = _s.apply(lambda x: _lb if pd.notna(x) and x < _lb else (_ub if pd.notna(x) and x > _ub else x))"
                    )
                elif action == "nullify":
                    code_lines.append(f"            df.loc[_mask, {col_lit}] = np.nan")
                elif action == "drop":
                    code_lines.append("            df = df[~_mask].reset_index(drop=True)")
                elif action == "flag":
                    flag_col = json.dumps(f"{col}_is_outlier")
                    code_lines.append(f"            df[{flag_col}] = _mask.fillna(False)")

            elif op == "cluster_kmeans":
                feat_cols = params.get("columns", [])
                n_clusters = int(params.get("n_clusters", 3))
                out_col = params.get("output_column", "cluster_id")
                scale = bool(params.get("scale_features", True))
                out_lit = json.dumps(out_col)
                cols_lit = json.dumps(feat_cols)
                code_lines.append(f"    if all(c in df.columns for c in {cols_lit}) and len(df) > 0:")
                code_lines.append(
                    f"        _X = np.column_stack([pd.to_numeric(df[c], errors='coerce').fillna(0.0).values for c in {cols_lit}]).astype(np.float64)"
                )
                if scale:
                    code_lines.append("        if len(_X) > 1:")
                    code_lines.append("            _stds = np.std(_X, axis=0)")
                    code_lines.append("            _stds[_stds == 0] = 1.0")
                    code_lines.append("            _X = (_X - np.mean(_X, axis=0)) / _stds")
                code_lines.append("        try:")
                code_lines.append("            from sklearn.cluster import KMeans")
                code_lines.append(
                    f"            _km = KMeans(n_clusters=min({n_clusters}, len(_X)), random_state=42, n_init=10)"
                )
                code_lines.append(f"            df[{out_lit}] = _km.fit_predict(_X)")
                code_lines.append("        except ImportError:")
                code_lines.append(f"            df[{out_lit}] = np.arange(len(df)) % {n_clusters}")

            elif op == "split_column":
                sep = params.get("separator", "-")
                sep_lit = json.dumps(sep)
                new_cols = params.get("new_columns") or []
                if len(new_cols) == 2:
                    a_lit, b_lit = json.dumps(new_cols[0]), json.dumps(new_cols[1])
                else:
                    a_lit, b_lit = json.dumps(f"{col}_Part1"), json.dumps(f"{col}_Part2")
                keep = bool(params.get("keep_original", False))
                code_lines.append(f"    if {col_lit} in df.columns:")
                code_lines.append(f"        _parts = df[{col_lit}].astype(str).str.split({sep_lit}, n=1, expand=True)")
                code_lines.append(f"        df[{a_lit}] = _parts[0].str.strip().str.title()")
                code_lines.append(
                    f"        df[{b_lit}] = _parts[1].str.strip().str.title() if 1 in _parts.columns else None"
                )
                if not keep:
                    code_lines.append(f"        df = df.drop(columns=[{col_lit}])")

            code_lines.append("")

        code_lines.extend(
            [
                "    final_rows, final_cols = df.shape",
                '    print(f"ETL Execution complete: {final_rows} rows, {final_cols} columns remaining.")',
                '    if output_filepath.endswith(".csv"):',
                '        df.to_csv(output_filepath, index=False, encoding="utf-8")',
                "    else:",
                "        df.to_excel(output_filepath, index=False)",
                '    print(f"Clean dataset saved to {output_filepath}")',
                "",
                "    # Exportación opcional a Apache Parquet columnar (alto rendimiento):",
                '    # parquet_output = output_filepath.rsplit(".", 1)[0] + ".parquet"',
                "    # df.to_parquet(parquet_output, index=False)",
                "",
                'if __name__ == "__main__":',
                f"    run_etl_pipeline({filename_literal}, {clean_literal})",
            ]
        )

        return "\n".join(code_lines)

    @staticmethod
    def generate_script(
        source_filename: str, file_type: str, steps: List[TransformationStep], run_id: Optional[str] = None
    ) -> str:
        return ScriptGeneratorService.generate_python_script(source_filename, steps)
