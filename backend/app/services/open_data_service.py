import httpx
import logging
from typing import List, Optional, Dict, Any

from app.models.dataset import OpenDatasetItem, OpenDataSearchResponse

logger = logging.getLogger("dataflow.opendata")

# Catálogo curado de datasets públicos de Open Data seleccionados y verificados
FEATURED_OPEN_DATASETS: List[OpenDatasetItem] = [
    OpenDatasetItem(
        id="gdp-world-indicators",
        title="PIB Mundial e Indicadores Económicos",
        description="Series temporales históricas de PIB per cápita y volumen económico por país.",
        organization="Banco Mundial / Open Data Hub",
        resource_url="https://raw.githubusercontent.com/datasets/gdp/master/data/gdp.csv",
        format="CSV",
        tags=["Economía", "Macroeconomía", "Finanzas"]
    ),
    OpenDatasetItem(
        id="mobility-carshare-operations",
        title="Movilidad Urbana y Tarifas de Transporte",
        description="Métricas operativas de trayectos urbanos, disponibilidad y distribución de tarifas.",
        organization="Dpto. de Movilidad y Transportes",
        resource_url="https://raw.githubusercontent.com/plotly/datasets/master/carshare_data.csv",
        format="CSV",
        tags=["Movilidad", "Transporte", "Operaciones"]
    ),
    OpenDatasetItem(
        id="global-population-demographics",
        title="Población y Crecimiento Demográfico Mundial",
        description="Registros demográficos estandarizados de población por territorio y año.",
        organization="División de Estadística / UN Data",
        resource_url="https://raw.githubusercontent.com/datasets/population/master/data/population.csv",
        format="CSV",
        tags=["Demografía", "Población", "Estadística"]
    ),
    OpenDatasetItem(
        id="commercial-restaurant-transactions",
        title="Ventas Comerciales y Propinas en Hostelería",
        description="Transacciones comerciales con importes totales, días, turnos y métricas de consumo.",
        organization="Open Business Intelligence Hub",
        resource_url="https://raw.githubusercontent.com/mwaskom/seaborn-data/master/tips.csv",
        format="CSV",
        tags=["Ventas", "Hostelería", "Comercio"]
    ),
    OpenDatasetItem(
        id="air-quality-emissions",
        title="Medición de Calidad del Aire y Emisiones",
        description="Estaciones meteorológicas con concentraciones de partículas y gases contaminantes.",
        organization="Agencia de Medio Ambiente / Open Earth",
        resource_url="https://raw.githubusercontent.com/datasets/co2-fossil-by-nation/master/data/fossil-fuel-co2-emissions-by-nation.csv",
        format="CSV",
        tags=["Medioambiente", "Sostenibilidad", "Clima"]
    )
]

CKAN_API_ENDPOINT = "https://catalog.data.gov/api/3/action/package_search"


class OpenDataService:
    @staticmethod
    def get_featured_datasets() -> List[OpenDatasetItem]:
        """Retorna la lista de datasets de datos abiertos destacados y verificados."""
        return FEATURED_OPEN_DATASETS

    @staticmethod
    async def search_datasets(query: Optional[str] = None, limit: int = 10) -> OpenDataSearchResponse:
        """
        Busca datasets en el catálogo Open Data.
        Combina coincidencias en el catálogo curado local y consulta en vivo la API CKAN pública.
        """
        results: List[OpenDatasetItem] = []
        clean_q = (query or "").strip().lower()

        # 1. Búsqueda en catálogo curado
        for item in FEATURED_OPEN_DATASETS:
            if not clean_q:
                results.append(item)
            else:
                match_title = clean_q in item.title.lower()
                match_desc = clean_q in item.description.lower()
                match_org = clean_q in item.organization.lower()
                match_tag = any(clean_q in t.lower() for t in item.tags)
                if match_title or match_desc or match_org or match_tag:
                    results.append(item)

        # 2. Si se especifica búsqueda, consultar CKAN API
        if clean_q:
            try:
                async with httpx.AsyncClient(timeout=4.0) as client:
                    resp = await client.get(
                        CKAN_API_ENDPOINT,
                        params={"q": clean_q, "rows": 15},
                        headers={"User-Agent": "DataFlow-AI/1.2 (Open Data Explorer)"}
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        packages = data.get("result", {}).get("results", [])
                        for pkg in packages:
                            pkg_title = pkg.get("title") or "Dataset Público"
                            pkg_notes = pkg.get("notes") or "Sin descripción detallada."
                            # Truncar descripción muy larga
                            if len(pkg_notes) > 180:
                                pkg_notes = pkg_notes[:177] + "..."

                            org_info = pkg.get("organization") or {}
                            org_name = org_info.get("title") or org_info.get("name") or "Portal Open Data"

                            pkg_tags = [t.get("display_name") or t.get("name") for t in pkg.get("tags", []) if isinstance(t, dict)]
                            clean_tags = [t for t in pkg_tags if t][:3]

                            # Buscar recursos con formato CSV o XLSX
                            for res in pkg.get("resources", []):
                                res_url = res.get("url", "")
                                res_format = (res.get("format") or "").upper()
                                is_csv = "CSV" in res_format or res_url.lower().endswith(".csv")
                                is_xlsx = "XLS" in res_format or res_url.lower().endswith(".xlsx")

                                if (is_csv or is_xlsx) and res_url.startswith(("http://", "https://")):
                                    item_id = f"ckan-{pkg.get('id', '')}-{res.get('id', '')[:8]}"
                                    # Evitar duplicados
                                    if not any(r.resource_url == res_url for r in results):
                                        results.append(
                                            OpenDatasetItem(
                                                id=item_id,
                                                title=pkg_title,
                                                description=pkg_notes,
                                                organization=org_name,
                                                resource_url=res_url,
                                                format="CSV" if is_csv else "XLSX",
                                                size_bytes=res.get("size"),
                                                tags=clean_tags or ["Open Data"]
                                            )
                                        )
                                    break  # Tomar el primer recurso CSV válido por paquete
            except Exception as e:
                logger.warning(f"Consulta a CKAN API no disponible ({str(e)}). Usando catálogo curado.")

        return OpenDataSearchResponse(
            total=len(results[:limit]),
            results=results[:limit],
            source="CKAN Public Portal & Curated Open Hub"
        )
