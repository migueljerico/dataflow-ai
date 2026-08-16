"""
Fixtures globales de aislamiento para la suite de tests.

Cada test ejecuta contra un UPLOAD_DIR temporal y con todas las caches en
memoria vacías, de modo que:
- No se acumulan archivos residuales en backend/uploads/ en cada ejecución.
- No hay fugas de estado entre tests (planes, datasets, runs de otros tests).
"""
import pytest

from app.core.config import settings
from app.services.dataset_service import DATASET_CACHE, EMPTY_ROWS_PURGED_CACHE
from app.services.etl_service import PLANS_CACHE, RUNS_CACHE
from app.services.profiler_service import PROFILING_CACHE
from app.services.quality_service import QUALITY_CACHE
from app.services.analytics_service import ANALYTICS_CACHE

ALL_CACHES = (
    DATASET_CACHE,
    EMPTY_ROWS_PURGED_CACHE,
    PLANS_CACHE,
    RUNS_CACHE,
    PROFILING_CACHE,
    QUALITY_CACHE,
    ANALYTICS_CACHE,
)


@pytest.fixture(autouse=True)
def isolated_runtime_state(tmp_path, monkeypatch):
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()
    monkeypatch.setattr(settings, "UPLOAD_DIR", upload_dir)

    for cache in ALL_CACHES:
        cache.clear()

    yield

    for cache in ALL_CACHES:
        cache.clear()
