"""
입찰가 최적화 엔진
목표 ACOS 달성을 위한 키워드별 최적 입찰가 계산 + 시간대별 보정
"""
from dataclasses import dataclass
import numpy as np
from datetime import datetime


@dataclass
class KeywordBidInput:
    keyword_id: str
    keyword_text: str
    asin: str
    current_bid: float
    price: float           # 제품 판매가
    impressions: int
    clicks: int
    spend: float
    sales: float
    orders: int


@dataclass
class BidRecommendation:
    keyword_id: str
    keyword_text: str
    current_bid: float
    recommended_bid: float
    change_pct: float
    reason: str
    expected_acos: float


# 시간대별 성과 보정 계수 (Amazon 광고 일반 패턴 기반)
HOURLY_BID_MULTIPLIERS = np.array([
    0.60, 0.50, 0.45, 0.42, 0.45, 0.55,
    0.75, 0.90, 1.00, 1.05, 1.08, 1.06,
    1.02, 0.98, 0.95, 0.97, 1.00, 1.05,
    1.10, 1.12, 1.08, 0.95, 0.80, 0.68,
])


def recommend_bids(
    keywords: list[KeywordBidInput],
    target_acos: float,        # 목표 ACOS (%)
    min_clicks_threshold: int = 5,  # 최소 클릭 수 (통계 신뢰도)
    max_bid_increase_pct: float = 50.0,
    max_bid_decrease_pct: float = 40.0,
    min_bid: float = 0.10,
    max_bid: float = 10.0,
) -> list[BidRecommendation]:
    """
    키워드별 목표 ACOS 기반 최적 입찰가를 계산한다.

    핵심 공식:
      CVR = orders / clicks
      max_CPC = target_ACOS(%) / 100 × CVR × price
      추천 입찰가 = max_CPC × 조정계수
    """
    results = []

    for kw in keywords:
        clicks = kw.clicks
        orders = kw.orders
        spend = kw.spend
        sales = kw.sales
        current_bid = kw.current_bid

        # 데이터 부족 — 보수적 유지
        if clicks < min_clicks_threshold:
            results.append(BidRecommendation(
                keyword_id=kw.keyword_id,
                keyword_text=kw.keyword_text,
                current_bid=current_bid,
                recommended_bid=current_bid,
                change_pct=0.0,
                reason=f"클릭 수 부족 ({clicks}회) — 현행 유지",
                expected_acos=_calc_acos(spend, sales),
            ))
            continue

        cvr = orders / clicks if clicks > 0 else 0
        actual_acos = _calc_acos(spend, sales)
        actual_cpc = spend / clicks if clicks > 0 else current_bid

        if cvr == 0:
            # 전환 없음 → 입찰가 인하
            new_bid = max(min_bid, current_bid * 0.7)
            reason = "전환 없음 — 입찰가 30% 인하"
        else:
            # 목표 ACOS 기반 최대 허용 CPC
            max_cpc = (target_acos / 100) * cvr * kw.price

            if actual_acos <= target_acos * 0.8:
                # 효율이 매우 좋음 → 공격적으로 올려 클릭 확보
                new_bid = min(max_bid, current_bid * 1.2)
                reason = f"ACOS {actual_acos:.1f}% (목표 대비 충분히 낮음) — 입찰가 20% 인상"
            elif actual_acos <= target_acos:
                # 목표 내 — 미세 상향
                adjustment = 1 + (target_acos - actual_acos) / target_acos * 0.15
                new_bid = min(max_bid, current_bid * adjustment)
                reason = f"ACOS {actual_acos:.1f}% (목표 내) — 소폭 인상"
            elif actual_acos <= target_acos * 1.3:
                # 목표 소폭 초과 → 최대 허용 CPC 기준으로 조정
                new_bid = min(max_bid, max(min_bid, max_cpc * 0.95))
                reason = f"ACOS {actual_acos:.1f}% (목표 소폭 초과) — 최적 CPC로 조정"
            else:
                # 목표 대폭 초과 → 적극 인하
                new_bid = min(max_bid, max(min_bid, max_cpc * 0.85))
                reason = f"ACOS {actual_acos:.1f}% (목표 대비 {actual_acos/target_acos:.1f}배) — 입찰가 인하"

        # 변동폭 제한
        max_up = current_bid * (1 + max_bid_increase_pct / 100)
        max_down = current_bid * (1 - max_bid_decrease_pct / 100)
        new_bid = max(max(min_bid, max_down), min(max_up, new_bid))

        change_pct = (new_bid - current_bid) / current_bid * 100 if current_bid > 0 else 0
        expected_acos = (actual_acos * new_bid / actual_cpc) if actual_cpc > 0 else actual_acos

        results.append(BidRecommendation(
            keyword_id=kw.keyword_id,
            keyword_text=kw.keyword_text,
            current_bid=round(current_bid, 2),
            recommended_bid=round(new_bid, 2),
            change_pct=round(change_pct, 1),
            reason=reason,
            expected_acos=round(expected_acos, 1),
        ))

    return results


def get_hourly_bid_multiplier(hour: int) -> float:
    """현재 시간대의 입찰가 보정 계수 반환 (0~23)."""
    return float(HOURLY_BID_MULTIPLIERS[hour % 24])


def apply_hourly_adjustment(base_bid: float, hour: int) -> float:
    """기준 입찰가에 시간대 보정을 적용한다."""
    return round(base_bid * get_hourly_bid_multiplier(hour), 2)


def build_keyword_bid_inputs_from_db(
    session, asin: str, days: int = 14
) -> list[KeywordBidInput]:
    """DB 데이터로 KeywordBidInput 목록을 생성한다."""
    from datetime import timedelta
    from sqlalchemy import func
    from models import AdPerformance, Keyword, Asin

    end = datetime.utcnow()
    start = end - timedelta(days=days)

    asin_obj = session.query(Asin).filter(Asin.asin == asin).first()
    price = asin_obj.price if asin_obj else 25.0

    rows = (
        session.query(
            AdPerformance.keyword_id,
            Keyword.keyword_text,
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
        .group_by(AdPerformance.keyword_id, Keyword.keyword_text, Keyword.bid)
        .all()
    )

    return [
        KeywordBidInput(
            keyword_id=r.keyword_id,
            keyword_text=r.keyword_text,
            asin=asin,
            current_bid=float(r.bid or 1.0),
            price=price,
            impressions=int(r.impressions or 0),
            clicks=int(r.clicks or 0),
            spend=float(r.spend or 0),
            sales=float(r.sales or 0),
            orders=int(r.orders or 0),
        )
        for r in rows
    ]


def _calc_acos(spend: float, sales: float) -> float:
    return round(spend / sales * 100, 1) if sales > 0 else 0.0
