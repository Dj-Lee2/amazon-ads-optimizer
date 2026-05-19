from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, text

from db import get_db
from data_providers import MockDataProvider
from models import AdPerformance, OrganicPerformance, Inventory, Keyword, Asin
from .schemas import (
    AsinInfo, PerformanceSummary, KeywordSummary,
    InventoryInfo, HourlyTrend, DailySummary,
)

router = APIRouter(prefix="/api/v1")


def _provider(db: Session) -> MockDataProvider:
    return MockDataProvider(db)


@router.get("/asins", response_model=list[AsinInfo])
def list_asins(db: Session = Depends(get_db)):
    return _provider(db).get_all_asins()


@router.get("/performance/summary", response_model=list[PerformanceSummary])
def performance_summary(
    days: int = Query(default=30, ge=1, le=90),
    db: Session = Depends(get_db),
):
    end = datetime.utcnow()
    start = end - timedelta(days=days)
    provider = _provider(db)
    asins = provider.get_all_asins()

    results = []
    for a in asins:
        asin = a["asin"]
        camp_perf = provider.get_campaign_performance(asin, start, end)
        organic = provider.get_organic_sales(asin, start, end)

        total_impr = sum(p.impressions for p in camp_perf)
        total_clicks = sum(p.clicks for p in camp_perf)
        total_spend = sum(p.spend for p in camp_perf)
        ad_sales = sum(p.sales for p in camp_perf)
        orders = sum(p.orders for p in camp_perf)

        acos = (total_spend / ad_sales * 100) if ad_sales > 0 else 0.0
        tacos = (total_spend / organic.total_sales * 100) if organic.total_sales > 0 else 0.0
        roas = (ad_sales / total_spend) if total_spend > 0 else 0.0
        ctr = (total_clicks / total_impr * 100) if total_impr > 0 else 0.0
        cvr = (orders / total_clicks * 100) if total_clicks > 0 else 0.0

        results.append(PerformanceSummary(
            asin=asin,
            period_start=start,
            period_end=end,
            total_impressions=total_impr,
            total_clicks=total_clicks,
            total_spend=round(total_spend, 2),
            ad_sales=round(ad_sales, 2),
            total_sales=round(organic.total_sales, 2),
            organic_sales=round(organic.organic_sales, 2),
            orders=orders,
            acos=round(acos, 2),
            tacos=round(tacos, 2),
            roas=round(roas, 2),
            ctr=round(ctr, 3),
            cvr=round(cvr, 3),
        ))

    return results


@router.get("/performance/daily", response_model=list[DailySummary])
def daily_performance(
    asin: str = Query(...),
    days: int = Query(default=30, ge=1, le=90),
    db: Session = Depends(get_db),
):
    end = datetime.utcnow()
    start = end - timedelta(days=days)

    date_trunc = func.strftime("%Y-%m-%d", AdPerformance.timestamp)
    ad_rows = (
        db.query(
            date_trunc.label("date"),
            func.sum(AdPerformance.spend).label("spend"),
            func.sum(AdPerformance.sales).label("ad_sales"),
            func.sum(AdPerformance.orders).label("orders"),
        )
        .filter(
            AdPerformance.asin == asin,
            AdPerformance.timestamp >= start,
            AdPerformance.timestamp < end,
        )
        .group_by(date_trunc)
        .order_by(date_trunc)
        .all()
    )

    org_date_trunc = func.strftime("%Y-%m-%d", OrganicPerformance.timestamp)
    organic_rows = (
        db.query(
            org_date_trunc.label("date"),
            func.sum(OrganicPerformance.total_sales).label("total_sales"),
        )
        .filter(
            OrganicPerformance.asin == asin,
            OrganicPerformance.timestamp >= start,
            OrganicPerformance.timestamp < end,
        )
        .group_by(org_date_trunc)
        .all()
    )
    organic_map = {str(r.date): float(r.total_sales or 0) for r in organic_rows}

    results = []
    for r in ad_rows:
        date_str = str(r.date)
        spend = float(r.spend or 0)
        ad_sales = float(r.ad_sales or 0)
        total_sales = organic_map.get(date_str, ad_sales)
        tacos = (spend / total_sales * 100) if total_sales > 0 else 0.0
        roas = (ad_sales / spend) if spend > 0 else 0.0

        results.append(DailySummary(
            date=date_str,
            total_sales=round(total_sales, 2),
            ad_sales=round(ad_sales, 2),
            ad_spend=round(spend, 2),
            tacos=round(tacos, 2),
            roas=round(roas, 2),
            orders=int(r.orders or 0),
        ))

    return results


@router.get("/performance/hourly", response_model=list[HourlyTrend])
def hourly_performance(
    asin: str = Query(...),
    hours: int = Query(default=24, ge=1, le=168),
    db: Session = Depends(get_db),
):
    end = datetime.utcnow()
    start = end - timedelta(hours=hours)

    rows = (
        db.query(
            AdPerformance.timestamp,
            func.sum(AdPerformance.spend).label("spend"),
            func.sum(AdPerformance.sales).label("sales"),
            func.sum(AdPerformance.clicks).label("clicks"),
            func.sum(AdPerformance.impressions).label("impressions"),
        )
        .filter(
            AdPerformance.asin == asin,
            AdPerformance.timestamp >= start,
            AdPerformance.timestamp < end,
        )
        .group_by(AdPerformance.timestamp)
        .order_by(AdPerformance.timestamp)
        .all()
    )

    return [
        HourlyTrend(
            timestamp=r.timestamp,
            spend=round(float(r.spend or 0), 2),
            sales=round(float(r.sales or 0), 2),
            clicks=int(r.clicks or 0),
            impressions=int(r.impressions or 0),
        )
        for r in rows
    ]


@router.get("/keywords", response_model=list[KeywordSummary])
def keyword_performance(
    asin: str = Query(...),
    days: int = Query(default=30, ge=1, le=90),
    db: Session = Depends(get_db),
):
    end = datetime.utcnow()
    start = end - timedelta(days=days)
    kws = _provider(db).get_keyword_performance(asin, start, end)

    results = []
    for kw in kws:
        if kw.acos == 0:
            eff = "unclassified"
        elif kw.acos < 20 and kw.cvr > 8:
            eff = "high"
        elif kw.acos > 40 or (kw.clicks > 10 and kw.orders == 0):
            eff = "low"
        else:
            eff = "medium"

        results.append(KeywordSummary(
            keyword_id=kw.keyword_id,
            keyword_text=kw.keyword_text,
            match_type=kw.match_type,
            impressions=kw.impressions,
            clicks=kw.clicks,
            spend=round(kw.spend, 2),
            sales=round(kw.sales, 2),
            orders=kw.orders,
            acos=round(kw.acos, 2),
            ctr=round(kw.ctr, 3),
            cvr=round(kw.cvr, 3),
            current_bid=kw.current_bid,
            efficiency=eff,
        ))

    return sorted(results, key=lambda x: x.spend, reverse=True)


@router.get("/inventory", response_model=list[InventoryInfo])
def inventory_status(db: Session = Depends(get_db)):
    provider = _provider(db)
    asins = provider.get_all_asins()
    results = []

    for a in asins:
        inv = provider.get_inventory(a["asin"])
        if inv.is_critical:
            status = "critical"
        elif inv.is_low:
            status = "low"
        else:
            status = "ok"

        results.append(InventoryInfo(
            asin=a["asin"],
            quantity=inv.quantity,
            daily_sales_rate=inv.daily_sales_rate,
            days_of_supply=inv.days_of_supply,
            status=status,
        ))

    return results
