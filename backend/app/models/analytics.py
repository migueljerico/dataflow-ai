from typing import List, Optional

from pydantic import BaseModel


class BusinessKPI(BaseModel):
    id: str
    title: str
    value: str
    numeric_value: Optional[float] = None
    change_direction: Optional[str] = None  # 'positive', 'negative', 'neutral'
    subtitle: str
    category: str  # 'operaciones', 'financiero', 'calidad', 'general'


class CategoryDistribution(BaseModel):
    category_name: str
    count: int
    percentage: float
    secondary_metric_name: Optional[str] = None
    secondary_metric_value: Optional[float] = None


class ExecutiveAnalyticsReport(BaseModel):
    run_id: str
    dataset_name: str
    domain: str  # 'contact_center', 'sales', 'people_analytics', 'general'
    kpis: List[BusinessKPI]
    executive_summary: str
    strategic_recommendations: List[str]
    category_breakdown: Optional[List[CategoryDistribution]] = None
