"""
Mock 데이터 생성기: 뷰티 카테고리 셀러, 5개 ASIN, 미국 마켓플레이스
90일치 시계열 광고/판매/재고 데이터를 현실적인 분포로 생성한다.
"""
import uuid
import random
import numpy as np
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from models import (
    Asin, Campaign, Keyword, AdPerformance, OrganicPerformance, Inventory,
    CampaignType, MatchType, KeywordStatus, KeywordEfficiency,
)


SEED = 42
random.seed(SEED)
np.random.seed(SEED)

ASINS_CONFIG = [
    {"asin": "B001SKIN01", "title": "Hydrating Vitamin C Serum 30ml - Brightening Face Serum with Hyaluronic Acid", "price": 28.99, "ctr_base": 0.012, "cvr_base": 0.09},
    {"asin": "B001SKIN02", "title": "Retinol Moisturizer Face Cream - Anti-Aging Night Cream with Peptides 50ml", "price": 35.99, "ctr_base": 0.010, "cvr_base": 0.07},
    {"asin": "B001SKIN03", "title": "Niacinamide Face Toner 200ml - Pore Minimizing Facial Toner with Zinc", "price": 19.99, "ctr_base": 0.015, "cvr_base": 0.11},
    {"asin": "B001SKIN04", "title": "SPF 50 Daily Sunscreen 60ml - Lightweight Non-Greasy Sun Protection", "price": 22.99, "ctr_base": 0.008, "cvr_base": 0.06},
    {"asin": "B001SKIN05", "title": "Collagen Eye Cream 20ml - Under Eye Treatment for Dark Circles & Puffiness", "price": 42.99, "ctr_base": 0.009, "cvr_base": 0.08},
]

KEYWORD_POOL = [
    ["vitamin c serum", "face serum brightening", "vitamin c face serum", "brightening serum",
     "hyaluronic acid serum", "vitamin c serum for face", "anti aging serum", "glow serum",
     "skin brightening serum", "korean serum", "vitamin c moisturizer", "niacinamide serum",
     "face serum anti aging", "serum for dark spots", "vitamin c skin care"],
    ["retinol cream", "anti aging face cream", "night cream retinol", "retinol moisturizer",
     "peptide cream", "anti wrinkle cream", "face cream night", "age defying cream",
     "retinol skin care", "night moisturizer", "anti aging moisturizer", "wrinkle cream",
     "retinol serum cream", "face cream for wrinkles", "anti aging night cream"],
    ["niacinamide toner", "face toner pore", "pore minimizing toner", "niacinamide skin care",
     "facial toner", "toner for oily skin", "zinc niacinamide", "pore toner",
     "toner for large pores", "niacinamide moisturizer", "skin toner", "clarifying toner",
     "toner skin care", "niacinamide face care", "pore care toner"],
    ["sunscreen spf 50", "face sunscreen", "daily sunscreen", "lightweight sunscreen",
     "non greasy sunscreen", "sunscreen for face", "spf moisturizer", "sun protection face",
     "mineral sunscreen", "chemical sunscreen", "sunscreen skin care", "face spf",
     "broad spectrum sunscreen", "everyday sunscreen", "korean sunscreen"],
    ["eye cream", "under eye cream", "dark circle cream", "eye treatment",
     "collagen eye cream", "anti puffiness eye cream", "eye care cream", "eye serum cream",
     "under eye treatment", "eye wrinkle cream", "dark circles treatment", "eye moisturizer",
     "puffy eyes cream", "best eye cream", "eye cream anti aging"],
]

HOURLY_MULTIPLIERS = np.array([
    0.2, 0.1, 0.08, 0.07, 0.08, 0.15,
    0.35, 0.65, 0.85, 0.95, 1.0, 0.98,
    0.92, 0.88, 0.85, 0.87, 0.90, 0.95,
    1.0, 1.05, 1.0, 0.85, 0.60, 0.35,
])
HOURLY_MULTIPLIERS /= HOURLY_MULTIPLIERS.mean()


def _seasonal_multiplier(date: datetime) -> float:
    """월별 시즌 계수: 연말/연초 성수기 반영"""
    month = date.month
    seasonal = {
        1: 0.85, 2: 0.80, 3: 0.90, 4: 0.95,
        5: 1.00, 6: 0.95, 7: 0.90, 8: 0.95,
        9: 1.00, 10: 1.05, 11: 1.30, 12: 1.40,
    }
    return seasonal.get(month, 1.0)


def generate_all(session: Session, days: int = 90) -> None:
    """전체 Mock 데이터를 생성해 DB에 저장한다."""
    print("=== Mock 데이터 생성 시작 ===")

    asins = _create_asins(session)
    campaigns, keywords = _create_campaigns_and_keywords(session, asins)
    session.flush()

    end_dt = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
    start_dt = end_dt - timedelta(days=days)

    _create_performance_data(session, asins, campaigns, keywords, start_dt, end_dt)
    _create_inventory_data(session, asins, start_dt, end_dt)

    session.commit()
    print("=== Mock 데이터 생성 완료 ===")


def _create_asins(session: Session) -> list[Asin]:
    asins = []
    for cfg in ASINS_CONFIG:
        obj = Asin(
            asin=cfg["asin"],
            title=cfg["title"],
            price=cfg["price"],
            category="Beauty",
            marketplace="US",
        )
        session.merge(obj)
        asins.append(cfg)
    print(f"  ASIN {len(asins)}개 생성")
    return asins


def _create_campaigns_and_keywords(
    session: Session, asins: list[dict]
) -> tuple[list[dict], list[dict]]:
    campaigns_meta = []
    keywords_meta = []

    for idx, asin_cfg in enumerate(asins):
        asin = asin_cfg["asin"]
        keywords_for_asin = KEYWORD_POOL[idx]

        # Auto Campaign
        auto_id = f"CAMP_AUTO_{asin}"
        session.merge(Campaign(
            campaign_id=auto_id,
            asin=asin,
            campaign_type=CampaignType.AUTO,
            daily_budget=round(random.uniform(15, 40), 2),
        ))
        campaigns_meta.append({"campaign_id": auto_id, "asin": asin, "type": "auto"})

        # Manual Campaign
        manual_id = f"CAMP_MANUAL_{asin}"
        session.merge(Campaign(
            campaign_id=manual_id,
            asin=asin,
            campaign_type=CampaignType.MANUAL,
            daily_budget=round(random.uniform(20, 60), 2),
        ))
        campaigns_meta.append({"campaign_id": manual_id, "asin": asin, "type": "manual"})

        for kw_idx, kw_text in enumerate(keywords_for_asin):
            for match_type in [MatchType.EXACT, MatchType.PHRASE]:
                kw_id = f"KW_{asin}_{kw_idx:03d}_{match_type.value}"
                bid = round(random.uniform(0.5, 2.5), 2)
                session.merge(Keyword(
                    keyword_id=kw_id,
                    campaign_id=manual_id,
                    asin=asin,
                    keyword_text=kw_text,
                    match_type=match_type,
                    bid=bid,
                    status=KeywordStatus.ACTIVE,
                    efficiency=KeywordEfficiency.UNCLASSIFIED,
                ))
                keywords_meta.append({
                    "keyword_id": kw_id,
                    "asin": asin,
                    "campaign_id": manual_id,
                    "ctr": asin_cfg["ctr_base"] * random.uniform(0.5, 2.0),
                    "cvr": asin_cfg["cvr_base"] * random.uniform(0.5, 1.5),
                    "cpc": bid * random.uniform(0.7, 1.2),
                    "price": asin_cfg["price"],
                })

    print(f"  캠페인 {len(campaigns_meta)}개, 키워드 {len(keywords_meta)}개 생성")
    return campaigns_meta, keywords_meta


def _create_performance_data(
    session: Session,
    asins: list[dict],
    campaigns: list[dict],
    keywords: list[dict],
    start_dt: datetime,
    end_dt: datetime,
) -> None:
    ad_perf_rows = []
    organic_rows = []

    current = start_dt
    total_hours = int((end_dt - start_dt).total_seconds() / 3600)
    print(f"  시계열 데이터 생성 중... ({total_hours}시간)")

    # 키워드별 성과를 ASIN+캠페인으로 그룹화
    kw_by_campaign: dict[str, list[dict]] = {}
    for kw in keywords:
        kw_by_campaign.setdefault(kw["campaign_id"], []).append(kw)

    asin_cfg_map = {a["asin"]: a for a in asins}

    hour_idx = 0
    while current < end_dt:
        hour_mult = HOURLY_MULTIPLIERS[current.hour]
        season_mult = _seasonal_multiplier(current)
        weekday_mult = 1.1 if current.weekday() >= 5 else 1.0  # 주말 가중치

        hourly_asin_ad_sales: dict[str, list[float]] = {}

        for camp in campaigns:
            asin = camp["asin"]
            asin_cfg = asin_cfg_map[asin]
            camp_kws = kw_by_campaign.get(camp["campaign_id"], [])

            if not camp_kws:
                continue

            # 캠페인 레벨 총 impressions (자동/수동 구분)
            base_impr = 6000 if camp["type"] == "manual" else 2000
            total_impr = int(
                base_impr * hour_mult * season_mult * weekday_mult
                * np.random.lognormal(0, 0.3)
            )

            # 키워드별로 분배
            impr_split = np.random.dirichlet(np.ones(len(camp_kws))) * total_impr

            for kw, kw_impr in zip(camp_kws, impr_split):
                impr = max(0, int(kw_impr))
                if impr == 0:
                    continue

                clicks = int(impr * kw["ctr"] * np.random.lognormal(0, 0.2))
                clicks = min(clicks, impr)
                spend = round(clicks * kw["cpc"] * np.random.lognormal(0, 0.1), 2)
                # 포아송 분포로 소량 클릭에서도 전환 발생
                expected_orders = max(0, clicks * kw["cvr"])
                orders = int(np.random.poisson(expected_orders)) if expected_orders > 0 else 0
                orders = min(orders, max(clicks, 1))
                sales = round(orders * kw["price"] * random.uniform(0.95, 1.05), 2)

                ad_perf_rows.append(AdPerformance(
                    timestamp=current,
                    asin=asin,
                    campaign_id=camp["campaign_id"],
                    keyword_id=kw["keyword_id"],
                    impressions=impr,
                    clicks=clicks,
                    spend=spend,
                    sales=sales,
                    orders=orders,
                ))
                hourly_asin_ad_sales.setdefault(asin, []).append(sales)

        # 자연 매출 (광고 매출의 헤일로 효과 반영)
        for asin_cfg in asins:
            asin_id = asin_cfg["asin"]
            # 이번 시간대 해당 ASIN의 광고 매출 집계
            ad_sales_this_hour = sum(hourly_asin_ad_sales.get(asin_id, []))
            halo_ratio = random.uniform(1.2, 2.5)
            organic_sales = round(ad_sales_this_hour * halo_ratio * hour_mult * season_mult, 2)
            total_sales = round(ad_sales_this_hour + organic_sales, 2)

            organic_rows.append(OrganicPerformance(
                timestamp=current,
                asin=asin_id,
                organic_sales=organic_sales,
                total_sales=total_sales,
            ))

        if hour_idx % 500 == 0:
            session.bulk_save_objects(ad_perf_rows)
            session.bulk_save_objects(organic_rows)
            ad_perf_rows.clear()
            organic_rows.clear()

        current += timedelta(hours=1)
        hour_idx += 1

    if ad_perf_rows:
        session.bulk_save_objects(ad_perf_rows)
    if organic_rows:
        session.bulk_save_objects(organic_rows)

    print(f"  광고 성과 데이터 저장 완료")


def _create_inventory_data(
    session: Session,
    asins: list[dict],
    start_dt: datetime,
    end_dt: datetime,
) -> None:
    inventory_rows = []
    initial_stock = {a["asin"]: random.randint(200, 500) for a in asins}

    current = start_dt
    while current < end_dt:
        for asin_cfg in asins:
            asin = asin_cfg["asin"]
            daily_rate = random.uniform(3, 15)
            qty = max(0, int(initial_stock[asin] - daily_rate * (current - start_dt).days))
            days_of_supply = qty / daily_rate if daily_rate > 0 else 999

            inventory_rows.append(Inventory(
                timestamp=current,
                asin=asin,
                quantity=qty,
                daily_sales_rate=round(daily_rate, 2),
                days_of_supply=round(days_of_supply, 1),
            ))
        current += timedelta(days=1)

    session.bulk_save_objects(inventory_rows)
    print(f"  재고 데이터 {len(inventory_rows)}건 저장 완료")
