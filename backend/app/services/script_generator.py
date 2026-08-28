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
