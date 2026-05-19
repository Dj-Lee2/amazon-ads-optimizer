"""
예산 최적화 엔진: 가용 예산 내 ASIN별 최적 예산 배분 계산
목적함수: Total Sales / Total Profit / ROAS / Ad Sales 최대화 (선택)
알고리즘: 선형계획법 (PuLP)
"""
from dataclasses import dataclass
from enum import Enum
from typing import Optional
import pulp
import numpy as np


class OptimizationGoal(str, Enum):
    TOTAL_SALES = "total_sales"
    TOTAL_PROFIT = "total_profit"
    ROAS = "roas"
    AD_SALES = "ad_sales"


@dataclass
class AsinMetrics:
    asin: str
    title: str
    price: float
    # 과거 성과 기반 추정치
    avg_roas: float          # 광고비 1달러당 광고 매출
    avg_tacos: float         # 총매출 대비 광고비 비율 (%)
    organic_ratio: float     # 자연매출 / 총매출 비율
    margin_rate: float       # 수익률 (%)
    current_budget: float    # 현재 일 예산
    min_budget: float        # 최소 예산 (0으로 끄지 않기 위한 하한)
    max_budget: float        # 최대 예산 상한 (과투자 방지)
    growth_score: float      # 0~1, 성장 가능성 점수


@dataclass
class BudgetAllocation:
    asin: str
    allocated_budget: float
    expected_ad_sales: float
    expected_total_sales: float
    expected_profit: float
    change_pct: float        # 현재 대비 변화율 (%)


@dataclass
class OptimizationResult:
    goal: str
    total_budget: float
    allocations: list[BudgetAllocation]
    expected_total_ad_sales: float
    expected_total_sales: float
    expected_total_profit: float
    solver_status: str
    improvement_pct: float   # 현재 대비 예상 개선율


def optimize_budget(
    asins: list[AsinMetrics],
    total_budget: float,
    goal: OptimizationGoal = OptimizationGoal.TOTAL_SALES,
    min_total_budget_usage: float = 0.85,  # 예산 최소 사용률
) -> OptimizationResult:
    """
    PuLP 선형계획법으로 ASIN별 예산 최적 배분을 계산한다.

    각 ASIN의 예상 매출 함수: Revenue(budget) = budget × ROAS
    예산 비선형 체감 효과는 성장점수로 보정.
    """
    if not asins:
        raise ValueError("최소 1개 이상의 ASIN이 필요합니다.")
    if total_budget <= 0:
        raise ValueError("총 예산은 0보다 커야 합니다.")

    n = len(asins)
    prob = pulp.LpProblem("budget_optimization", pulp.LpMaximize)

    # 결정변수: ASIN별 일 예산 (연속형)
    budgets = [
        pulp.LpVariable(f"budget_{a.asin}", lowBound=a.min_budget, upBound=a.max_budget)
        for a in asins
    ]

    # 목적함수 계수 계산
    if goal == OptimizationGoal.TOTAL_SALES:
        # 총매출 = 광고매출 + 자연매출 ≈ budget × ROAS × (1 + organic_ratio / (1 - organic_ratio))
        coeffs = [
            a.avg_roas * (1 + a.organic_ratio / max(1 - a.organic_ratio, 0.01)) * a.growth_score
            for a in asins
        ]
    elif goal == OptimizationGoal.AD_SALES:
        coeffs = [a.avg_roas * a.growth_score for a in asins]
    elif goal == OptimizationGoal.TOTAL_PROFIT:
        # 이익 = 총매출 × 마진율 - 광고비
        coeffs = [
            (a.avg_roas * (1 + a.organic_ratio / max(1 - a.organic_ratio, 0.01)) * a.margin_rate / 100 - 1)
            * a.growth_score
            for a in asins
        ]
    elif goal == OptimizationGoal.ROAS:
        # ROAS 최대화 → 가장 효율 높은 ASIN에 집중
        coeffs = [a.avg_roas * a.growth_score for a in asins]
    else:
        coeffs = [a.avg_roas for a in asins]

    # 목적함수 등록
    prob += pulp.lpSum(coeffs[i] * budgets[i] for i in range(n))

    # 제약조건 1: 총 예산 상한
    prob += pulp.lpSum(budgets) <= total_budget

    # 제약조건 2: 최소 예산 사용률 (예산을 너무 적게 쓰지 않도록)
    prob += pulp.lpSum(budgets) >= total_budget * min_total_budget_usage

    # 풀이
    prob.solve(pulp.PULP_CBC_CMD(msg=0))
    status = pulp.LpStatus[prob.status]

    # 결과 파싱
    allocations = []
    total_ad_sales = 0.0
    total_sales = 0.0
    total_profit = 0.0
    current_total_ad_sales = 0.0

    for i, a in enumerate(asins):
        alloc = max(a.min_budget, pulp.value(budgets[i]) or a.min_budget)
        ad_sales = alloc * a.avg_roas
        org_sales = ad_sales * a.organic_ratio / max(1 - a.organic_ratio, 0.01)
        t_sales = ad_sales + org_sales
        profit = t_sales * a.margin_rate / 100 - alloc
        change = (alloc - a.current_budget) / a.current_budget * 100 if a.current_budget > 0 else 0

        allocations.append(BudgetAllocation(
            asin=a.asin,
            allocated_budget=round(alloc, 2),
            expected_ad_sales=round(ad_sales, 2),
            expected_total_sales=round(t_sales, 2),
            expected_profit=round(profit, 2),
            change_pct=round(change, 1),
        ))

        total_ad_sales += ad_sales
        total_sales += t_sales
        total_profit += profit
        current_total_ad_sales += a.current_budget * a.avg_roas

    improvement = (
        (total_ad_sales - current_total_ad_sales) / current_total_ad_sales * 100
        if current_total_ad_sales > 0 else 0.0
    )

    return OptimizationResult(
        goal=goal.value,
        total_budget=total_budget,
        allocations=allocations,
        expected_total_ad_sales=round(total_ad_sales, 2),
        expected_total_sales=round(total_sales, 2),
        expected_total_profit=round(total_profit, 2),
        solver_status=status,
        improvement_pct=round(improvement, 2),
    )


def build_asin_metrics_from_db(session, days: int = 30) -> list[AsinMetrics]:
    """DB 데이터로부터 AsinMetrics를 계산해 반환한다."""
    from datetime import datetime, timedelta
    from sqlalchemy import func
    from models import AdPerformance, OrganicPerformance, Asin, Campaign

    end = datetime.utcnow()
    start = end - timedelta(days=days)

    asins = session.query(Asin).all()
    metrics = []

    for asin_obj in asins:
        asin = asin_obj.asin

        # 광고 성과 집계
        ad_row = session.query(
            func.sum(AdPerformance.spend).label("spend"),
            func.sum(AdPerformance.sales).label("ad_sales"),
        ).filter(
            AdPerformance.asin == asin,
            AdPerformance.timestamp >= start,
            AdPerformance.timestamp < end,
        ).first()

        # 자연 매출 집계
        org_row = session.query(
            func.sum(OrganicPerformance.total_sales).label("total_sales"),
            func.sum(OrganicPerformance.organic_sales).label("organic_sales"),
        ).filter(
            OrganicPerformance.asin == asin,
            OrganicPerformance.timestamp >= start,
            OrganicPerformance.timestamp < end,
        ).first()

        # 현재 예산 (캠페인 합산)
        budget_row = session.query(
            func.sum(Campaign.daily_budget).label("total_budget")
        ).filter(Campaign.asin == asin, Campaign.is_active == 1).first()

        spend = float(ad_row.spend or 0)
        ad_sales = float(ad_row.ad_sales or 0)
        total_sales = float(org_row.total_sales or 0) if org_row else ad_sales
        organic_sales = float(org_row.organic_sales or 0) if org_row else 0
        current_budget = float(budget_row.total_budget or 50) if budget_row else 50

        avg_roas = (ad_sales / spend) if spend > 0 else 2.0
        avg_tacos = (spend / total_sales * 100) if total_sales > 0 else 20.0
        organic_ratio = (organic_sales / total_sales) if total_sales > 0 else 0.5

        # 성장 점수: ROAS가 높고 TACOS가 낮을수록 높음
        roas_score = min(avg_roas / 5.0, 1.0)
        tacos_score = max(0, 1.0 - avg_tacos / 40.0)
        growth_score = round((roas_score + tacos_score) / 2, 3)

        metrics.append(AsinMetrics(
            asin=asin,
            title=asin_obj.title[:50],
            price=asin_obj.price,
            avg_roas=round(avg_roas, 3),
            avg_tacos=round(avg_tacos, 2),
            organic_ratio=round(organic_ratio, 3),
            margin_rate=30.0,  # 고정값 (실제 운영 시 원가 데이터 입력)
            current_budget=round(current_budget, 2),
            min_budget=max(5.0, current_budget * 0.3),
            max_budget=current_budget * 3.0,
            growth_score=growth_score,
        ))

    return metrics
