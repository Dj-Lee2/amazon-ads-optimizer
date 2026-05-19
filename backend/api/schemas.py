from pydantic import BaseModel
from datetime import datetime


class AsinInfo(BaseModel):
    asin: str
    title: str
    price: float
    category: str


class PerformanceSummary(BaseModel):
    asin: str
    period_start: datetime
    period_end: datetime
    total_impressions: int
    total_clicks: int
    total_spend: float
    ad_sales: float
    total_sales: float
    organic_sales: float
    orders: int
    acos: float
    tacos: float
    roas: float
    ctr: float
    cvr: float


class KeywordSummary(BaseModel):
    keyword_id: str
    keyword_text: str
    match_type: str
    impressions: int
    clicks: int
    spend: float
    sales: float
    orders: int
    acos: float
    ctr: float
    cvr: float
    current_bid: float
    efficiency: str


class InventoryInfo(BaseModel):
    asin: str
    quantity: int
    daily_sales_rate: float
    days_of_supply: float
    status: str


class HourlyTrend(BaseModel):
    timestamp: datetime
    spend: float
    sales: float
    clicks: int
    impressions: int


class DailySummary(BaseModel):
    date: str
    total_sales: float
    ad_sales: float
    ad_spend: float
    tacos: float
    roas: float
    orders: int
