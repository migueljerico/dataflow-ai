"""
Regresión v1.16.0 — casing inteligente en split_column y normalize_case.

Bug corregido: en v1.15.2 split_column aplicaba .title() crudo a cada segmento y
corrompía los valores reales del dataset Messy_Employee:
    DevOps-California → Devops / HR-California → Hr
Además, el script reproducible emitía .str.title(), divergiendo del motor.

Estos tests verifican:
1. Preservación de siglas (HR) y camelCase (DevOps) al dividir Department_Region.
2. Compuestos con guion de cualquier longitud (HR-New) no tratados como código.
3. Fidelidad exacta motor ↔ script generado (compile + exec).
4. Flujo E2E vía API con el patrón del dataset real.
"""

import io
import os
import tempfile

import pandas as pd
import pytest
from app.core.exceptions import FunctionalException
from app.models.etl import TransformationStep
from app.services.script_generator import ScriptGeneratorService
from app.transformations.casing import smart_title_text
from app.transformations.split_ops import SplitColumnTransformation
from app.transformations.text_ops import NormalizeCaseTransformation
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

REAL_WORLD_VALUES = [
    "DevOps-California",
    "HR-New York",
    "Cloud Tech-Texas",
    "Sales-Florida",
    "Admin-Nevada",
    "Finance-Illinois",
]


def _make_df(values):
    return pd.DataFrame({"Employee_ID": [f"EMP{i}" for i in range(len(values))], "Department_Region": values})


class TestSmartCasing:
    def test_preserva_siglas_y_camelcase(self):
        assert smart_title_text("HR-California") == "HR-California"
        assert smart_title_text("DevOps-California") == "DevOps-California"
        assert smart_title_text("Cloud Tech-New York") == "Cloud Tech-New York"

    def test_compuesto_corto_no_es_codigo(self):
        # 'HR-New' (6 chars) antes caía en la rama de código y salía 'HR-NEW'
        assert smart_title_text("HR-New York") == "HR-New York"

    def test_codigos_con_digitos_se_preservan_en_mayusculas(self):
        assert smart_title_text("PED-201") == "PED-201"

    def test_acronimos_de_negocio(self):
        assert smart_title_text("TALLERES ROBLES SLU") == "Talleres Robles SLU"

    def test_minusculas_se_normalizan_con_acronimos(self):
        assert smart_title_text("hr-nevada") == "HR-Nevada"
        assert smart_title_text("devops-california") == "Devops-California"  # ambigüedad documentada

    def test_todos_mayusculas_largas_se_capitalizan(self):
        assert smart_title_text("FINANCE-ILLINOIS") == "Finance-Illinois"

    def test_nan_y_vacio_se_preservan(self):
        assert pd.isna(smart_title_text(float("nan")))
        assert smart_title_text("   ") == ""

    def test_normalize_case_no_corrompe_department_region(self):
        t = NormalizeCaseTransformation()
        df = _make_df(REAL_WORLD_VALUES)
        out, _ = t.apply(df, {"column": "Department_Region", "mode": "title"})
        assert out["Department_Region"].tolist() == REAL_WORLD_VALUES


class TestSplitColumnTransformation:
    def test_split_valores_reales(self):
        t = SplitColumnTransformation()
        df = _make_df(REAL_WORLD_VALUES)
        out, affected = t.apply(
            df,
            {"column": "Department_Region", "separator": "-", "new_columns": ["Department", "Region"], "keep_original": False},
        )
        assert affected == len(df)
        assert out["Department"].tolist() == ["DevOps", "HR", "Cloud Tech", "Sales", "Admin", "Finance"]
        assert out["Region"].tolist() == ["California", "New York", "Texas", "Florida", "Nevada", "Illinois"]
        assert "Department_Region" not in out.columns

    def test_split_nan_y_sin_separador(self):
        t = SplitColumnTransformation()
        df = pd.DataFrame({"Department_Region": ["HR-Texas", None, "Salesonly", ""]})
        out, _ = t.apply(df, {"column": "Department_Region", "separator": "-", "new_columns": ["Department", "Region"]})
        departments = out["Department"].tolist()
        assert departments[0] == "HR" and departments[2] == "Salesonly"
        assert pd.isna(departments[1]) and pd.isna(departments[3])
        assert out.loc[0, "Region"] == "Texas"
        assert out["Region"].iloc[1:].isna().all()

    def test_split_keep_original(self):
        t = SplitColumnTransformation()
        df = _make_df(["HR-Texas"])
        out, _ = t.apply(
            df, {"column": "Department_Region", "separator": "-", "new_columns": ["Department", "Region"], "keep_original": True}
        )
        assert "Department_Region" in out.columns

    def test_validaciones(self):
        t = SplitColumnTransformation()
        df = _make_df(["HR-Texas"])
        with pytest.raises(FunctionalException):
            t.apply(df, {"column": "NoExiste", "separator": "-"})
        with pytest.raises(FunctionalException):
            t.apply(df, {"column": "Department_Region", "separator": ""})
        with pytest.raises(FunctionalException):
            t.apply(df, {"column": "Department_Region", "separator": "-", "new_columns": ["SoloUna"]})
        with pytest.raises(FunctionalException):
            t.apply(df, {"column": "Department_Region", "separator": "-", "new_columns": ["Department_Region", "Region"]})
        df["Department"] = "x"
        with pytest.raises(FunctionalException):
            t.apply(df, {"column": "Department_Region", "separator": "-", "new_columns": ["Department", "Region"]})

    def test_deriva_nombres_por_defecto(self):
        t = SplitColumnTransformation()
        df = _make_df(["HR-Texas"])
        out, _ = t.apply(df, {"column": "Department_Region", "separator": "-"})
        assert "Department" in out.columns and "Region" in out.columns


class TestScriptGeneratorFidelity:
    def _run_script(self, steps, csv_text):
        script = ScriptGeneratorService.generate_python_script("messy.csv", steps)
        compile(script, "<string>", "exec")
        tmp_in = os.path.join(tempfile.mkdtemp(), "messy.csv")
        tmp_out = tmp_in.replace(".csv", "_clean.csv")
        with open(tmp_in, "w", encoding="utf-8") as f:
            f.write(csv_text)
        ns = {}
        exec(script, ns)  # noqa: S102 — script generado determinista por el propio motor
        ns["run_etl_pipeline"](tmp_in, tmp_out)
        return pd.read_csv(tmp_out)

    def test_split_generado_conserva_devops_y_hr(self):
        steps = [
            TransformationStep(
                step_id="STEP-001",
                operation="split_column",
                column="Department_Region",
                parameters={
                    "column": "Department_Region",
                    "separator": "-",
                    "new_columns": ["Department", "Region"],
                    "keep_original": False,
                },
                reason="Dividir compuesta",
                confidence=0.98,
                risk="low",
                affected_rows_estimate=6,
            )
        ]
        csv_text = "Employee_ID,Department_Region\n" + "\n".join(f"EMP{i},{v}" for i, v in enumerate(REAL_WORLD_VALUES)) + "\n"
        out = self._run_script(steps, csv_text)
        assert out["Department"].tolist() == ["DevOps", "HR", "Cloud Tech", "Sales", "Admin", "Finance"]
        assert out["Region"].tolist() == ["California", "New York", "Texas", "Florida", "Nevada", "Illinois"]

    def test_script_es_fiel_al_motor(self):
        steps = [
            TransformationStep(
                step_id="STEP-001",
                operation="normalize_case",
                column="Department_Region",
                parameters={"column": "Department_Region", "mode": "title"},
                reason="Normalizar",
                confidence=0.9,
                risk="low",
                affected_rows_estimate=6,
            ),
            TransformationStep(
                step_id="STEP-002",
                operation="split_column",
                column="Department_Region",
                parameters={
                    "column": "Department_Region",
                    "separator": "-",
                    "new_columns": ["Department", "Region"],
                    "keep_original": False,
                },
                reason="Dividir",
                confidence=0.98,
                risk="low",
                affected_rows_estimate=6,
            ),
        ]
        values = REAL_WORLD_VALUES + ["hr-nevada", "FINANCE-ILLINOIS"]
        csv_text = "Employee_ID,Department_Region\n" + "\n".join(f"EMP{i},{v}" for i, v in enumerate(values)) + "\n"
        script_out = self._run_script(steps, csv_text)

        df = pd.read_csv(io.StringIO(csv_text))
        nc = NormalizeCaseTransformation()
        df, _ = nc.apply(df, {"column": "Department_Region", "mode": "title"})
        sp = SplitColumnTransformation()
        df, _ = sp.apply(
            df,
            {"column": "Department_Region", "separator": "-", "new_columns": ["Department", "Region"], "keep_original": False},
        )
        assert df["Department"].tolist() == script_out["Department"].tolist()
        assert df["Region"].tolist() == script_out["Region"].tolist()


class TestE2EDepartmentRegion:
    def test_flujo_api_con_valores_del_dataset_real(self):
        csv_text = (
            "Employee_ID,First_Name,Age,Department_Region,Status,Join_Date,Salary,Remote_Work\n"
            "EMP1,Bob,25,DevOps-California,Active,4/2/2021,59767.65,TRUE\n"
            "EMP2,Alice,,HR-New York,Active,7/10/2020,65304.66,FALSE\n"
            "EMP3,Eva,30,Cloud Tech-Texas,Pending,12/7/2023,N/A,TRUE\n"
            "EMP4,Frank,40,Sales-Florida,Inactive,1/5/2022,109324.61,FALSE\n"
        )
        up = client.post(
            "/api/v1/datasets/upload", files={"file": ("messy_department.csv", io.BytesIO(csv_text.encode()), "text/csv")}
        )
        assert up.status_code == 201
        dataset_id = up.json()["dataset_id"]

        plan_res = client.post("/api/v1/plans/propose", json={"dataset_id": dataset_id})
        assert plan_res.status_code == 201
        plan = plan_res.json()
        split_steps = [s for s in plan["steps"] if s["operation"] == "split_column" and s["column"] == "Department_Region"]
        assert len(split_steps) == 1
        assert split_steps[0]["parameters"]["separator"] == "-"
        assert split_steps[0]["parameters"]["new_columns"] == ["Department", "Region"]

        appr = client.post(f"/api/v1/plans/{plan['plan_id']}/approve", json={"steps": plan["steps"]})
        assert appr.status_code == 200 and appr.json()["status"] == "completed"
        run_id = appr.json()["run_id"]

        dl = client.get(f"/api/v1/runs/{run_id}/download")
        assert dl.status_code == 200
        out = pd.read_csv(io.BytesIO(dl.content))
        assert "Department_Region" not in out.columns
        assert set(out["Department"].dropna().unique()) == {"DevOps", "HR", "Cloud Tech", "Sales"}
        assert set(out["Region"].dropna().unique()) == {"California", "New York", "Texas", "Florida"}
