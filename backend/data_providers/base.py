from abc import ABC, abstractmethod
from datetime import datetime
from dataclasses import dataclass


@dataclass
class CampaignPerformance:
    timestamp: datetime
    asin: str
    campaign_id: str
    impressions: int
    clicks: int
    spend: float
    sales: float
    orders: int

    @property
    def acos(self) -> float:
        return (self.spend / self.sales * 100) if self.sales > 0 else 0.0

    @property
    def ctr(self) -> float:
        return (self.clicks / self.impressions * 100) if self.impressions > 0 else 0.0

    @property
    def cvr(self) -> float:
        return (self.orders / self.clicks * 100) if self.clicks > 0 else 0.0

    @property
    def roas(self) -> float:
        return (self.sales / self.spend) if self.spend > 0 else 0.0


@dataclass
class KeywordPerformance:
    keyword_id: str
    keyword_text: str
    match_type: str
    asin: str
    impressions: int
    clicks: int
    spend: float
    sales: float
    orders: int
    current_bid: float

    @property
    def acos(self) -> float:
        return (self.spend / self.sales * 100) if self.sales > 0 else 0.0

    @property
    def ctr(self) -> float:
        return (self.clicks / self.impressions * 100) if self.impressions > 0 else 0.0

    @property
    def cvr(self) -> float:
        return (self.orders / self.clicks * 100) if self.clicks > 0 else 0.0


@dataclass
class InventoryStatus:
    asin: str
    quantity: int
    daily_sales_rate: float
    days_of_supply: float

    @property
    def is_low(self) -> bool:
        return self.days_of_supply < 14

    @property
    def is_critical(self) -> bool:
        return self.days_of_supply < 7


@dataclass
class OrganicSales:
    asin: str
    period_start: datetime
    period_end: datetime
    organic_sales: float
    total_sales: float
    ad_sales: float

    @property
    def tacos(self) -> float:
        return 0.0  # 계산은 ad_spend와 함께 호출자가 처리


class DataProvider(ABC):
    @abstractmethod
    def get_campaign_performance(
        self, asin: str, start: datetime, end: datetime
    ) -> list[CampaignPerformance]: ...

    @abstractmethod
    def get_keyword_performance(
        self, asin: str, start: datetime, end: datetime
    ) -> list[KeywordPerformance]: ...

    @abstractmethod
    def get_inventory(self, asin: str) -> InventoryStatus: ...

    @abstractmethod
    def get_organic_sales(
        self, asin: str, start: datetime, end: datetime
    ) -> OrganicSales: ...

    @abstractmethod
    def get_all_asins(self) -> list[dict]: ...
