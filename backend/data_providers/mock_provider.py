from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func, select

from .base import (
    DataProvider, CampaignPerformance, KeywordPerformance,
    InventoryStatus, OrganicSales,
)
from models import AdPerformance, Keyword, Inventory, OrganicPerformance, Asin


class MockDataProvider(DataProvider):
    def __init__(self, session: Session):
        self.session = session

    def get_all_asins(self) -> list[dict]:
        rows = self.session.execute(select(Asin)).scalars().all()
        return [
            {"asin": r.asin, "title": r.title, "price": r.price, "category": r.category}
            for r in rows
        ]

    def get_campaign_performance(
        self, asin: str, start: datetime, end: datetime
    ) -> list[CampaignPerformance]:
        rows = (
            self.session.query(
                AdPerformance.timestamp,
                AdPerformance.campaign_id,
                func.sum(AdPerformance.impressions).label("impressions"),
                func.sum(AdPerformance.clicks).label("clicks"),
                func.sum(AdPerformance.spend).label("spend"),
                func.sum(AdPerformance.sales).label("sales"),
                func.sum(AdPerformance.orders).label("orders"),
            )
            .filter(
                AdPerformance.asin == asin,
                AdPerformance.timestamp >= start,
                AdPerformance.timestamp < end,
            )
            .group_by(AdPerformance.timestamp, AdPerformance.campaign_id)
            .all()
        )
        return [
            CampaignPerformance(
                timestamp=r.timestamp,
                asin=asin,
                campaign_id=r.campaign_id,
                impressions=r.impressions or 0,
                clicks=r.clicks or 0,
                spend=float(r.spend or 0),
                sales=float(r.sales or 0),
                orders=r.orders or 0,
            )
            for r in rows
        ]

    def get_keyword_performance(
        self, asin: str, start: datetime, end: datetime
    ) -> list[KeywordPerformance]:
        rows = (
            self.session.query(
                AdPerformance.keyword_id,
                Keyword.keyword_text,
                Keyword.match_type,
                Keyword.bid,
                func.sum(AdPerformance.impressions).label("impressions"),
                func.sum(AdPerformance.clicks).label("clicks"),
                func.sum(AdPerformance.spend).label("spend"),
                func.sum(AdPerformance.sales).label("sales"),
                func.sum(AdPerformance.orders).label("orders"),
            )
            .join(Keyword, Keyword.keyword_id == AdPerformance.keyword_id)
            .filter(
                AdPerformance.asin == asin,
                AdPerformance.timestamp >= start,
                AdPerformance.timestamp < end,
                AdPerformance.keyword_id.isnot(None),
            )
            .group_by(
                AdPerformance.keyword_id,
                Keyword.keyword_text,
                Keyword.match_type,
                Keyword.bid,
            )
            .all()
        )
        return [
            KeywordPerformance(
                keyword_id=r.keyword_id,
                keyword_text=r.keyword_text,
                match_type=r.match_type.value if hasattr(r.match_type, "value") else str(r.match_type),
                asin=asin,
                impressions=r.impressions or 0,
                clicks=r.clicks or 0,
                spend=float(r.spend or 0),
                sales=float(r.sales or 0),
                orders=r.orders or 0,
                current_bid=float(r.bid or 0),
            )
            for r in rows
        ]

    def get_inventory(self, asin: str) -> InventoryStatus:
        row = (
            self.session.query(Inventory)
            .filter(Inventory.asin == asin)
            .order_by(Inventory.timestamp.desc())
            .first()
        )
        if not row:
            return InventoryStatus(asin=asin, quantity=0, daily_sales_rate=0, days_of_supply=0)
        return InventoryStatus(
            asin=asin,
            quantity=row.quantity,
            daily_sales_rate=row.daily_sales_rate,
            days_of_supply=row.days_of_supply,
        )

    def get_organic_sales(
        self, asin: str, start: datetime, end: datetime
    ) -> OrganicSales:
        row = (
            self.session.query(
                func.sum(OrganicPerformance.organic_sales).label("organic_sales"),
                func.sum(OrganicPerformance.total_sales).label("total_sales"),
            )
            .filter(
                OrganicPerformance.asin == asin,
                OrganicPerformance.timestamp >= start,
                OrganicPerformance.timestamp < end,
            )
            .first()
        )
        ad_row = (
            self.session.query(func.sum(AdPerformance.sales).label("ad_sales"))
            .filter(
                AdPerformance.asin == asin,
                AdPerformance.timestamp >= start,
                AdPerformance.timestamp < end,
            )
            .first()
        )
        return OrganicSales(
            asin=asin,
            period_start=start,
            period_end=end,
            organic_sales=float(row.organic_sales or 0),
            total_sales=float(row.total_sales or 0),
            ad_sales=float(ad_row.ad_sales or 0),
        )
