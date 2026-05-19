from fastapi import APIRouter, Depends, Query, Body
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from db import get_db
from engine import (
    optimize_budget, build_asin_metrics_from_db, OptimizationGoal,
    recommend_bids, build_keyword_bid_inputs_from_db,
    classify_keywords, train_model, build_keyword_features_from_db,
    detect_anomalies,
)

router = APIRouter(prefix="/api/v1/optimize")


# ── 예산 최적화 ────────────────────────────────────────────

class BudgetOptimizeRequest(BaseModel):
    total_budget: float = 300.0
    goal: str = "total_sales"
    days: int = 30


class AllocationOut(BaseModel):
    asin: str
    allocated_budget: float
    expected_ad_sales: float
    expected_total_sales: float
    expected_profit: float
    change_pct: float


class BudgetOptimizeResponse(BaseModel):
    goal: str
    total_budget: float
    allocations: list[AllocationOut]
    expected_total_ad_sales: float
    expected_total_sales: float
    expected_total_profit: float
    solver_status: str
    improvement_pct: float


@router.post("/budget", response_model=BudgetOptimizeResponse)
def optimize_budget_endpoint(
    req: BudgetOptimizeRequest = Body(...),
    db: Session = Depends(get_db),
):
    try:
        goal = OptimizationGoal(req.goal)
    except ValueError:
        goal = OptimizationGoal.TOTAL_SALES

    metrics = build_asin_metrics_from_db(db, days=req.days)
    result = optimize_budget(metrics, req.total_budget, goal)

    return BudgetOptimizeResponse(
        goal=result.goal,
        total_budget=result.total_budget,
        allocations=[
            AllocationOut(
                asin=a.asin,
                allocated_budget=a.allocated_budget,
                expected_ad_sales=a.expected_ad_sales,
                expected_total_sales=a.expected_total_sales,
                expected_profit=a.expected_profit,
                change_pct=a.change_pct,
            )
            for a in result.allocations
        ],
        expected_total_ad_sales=result.expected_total_ad_sales,
        expected_total_sales=result.expected_total_sales,
        expected_total_profit=result.expected_total_profit,
        solver_status=result.solver_status,
        improvement_pct=result.improvement_pct,
    )


@router.get("/budget/preview")
def budget_preview(
    total_budget: float = Query(default=300.0),
    days: int = Query(default=30),
    db: Session = Depends(get_db),
):
    """각 목표별 최적화 결과를 미리보기로 반환 (시뮬레이터용)."""
    metrics = build_asin_metrics_from_db(db, days=days)
    results = {}
    for goal in OptimizationGoal:
        r = optimize_budget(metrics, total_budget, goal)
        results[goal.value] = {
            "expected_total_sales": r.expected_total_sales,
            "expected_total_ad_sales": r.expected_total_ad_sales,
            "expected_total_profit": r.expected_total_profit,
            "improvement_pct": r.improvement_pct,
            "solver_status": r.solver_status,
        }
    return results


# ── 입찰가 최적화 ────────────────────────────────────────────

class BidRecOut(BaseModel):
    keyword_id: str
    keyword_text: str
    current_bid: float
    recommended_bid: float
    change_pct: float
    reason: str
    expected_acos: float


@router.get("/bids", response_model=list[BidRecOut])
def optimize_bids(
    asin: str = Query(...),
    target_acos: float = Query(default=25.0, ge=5.0, le=100.0),
    days: int = Query(default=14),
    db: Session = Depends(get_db),
):
    kw_inputs = build_keyword_bid_inputs_from_db(db, asin=asin, days=days)
    recs = recommend_bids(kw_inputs, target_acos=target_acos)

    return [
        BidRecOut(
            keyword_id=r.keyword_id,
            keyword_text=r.keyword_text,
            current_bid=r.current_bid,
            recommended_bid=r.recommended_bid,
            change_pct=r.change_pct,
            reason=r.reason,
            expected_acos=r.expected_acos,
        )
        for r in recs
    ]


# ── 키워드 분류 ────────────────────────────────────────────

class KeywordClassOut(BaseModel):
    keyword_id: str
    keyword_text: str
    efficiency: str
    confidence: float
    reason: str
    action: str


@router.get("/keywords/classify", response_model=list[KeywordClassOut])
def classify_keywords_endpoint(
    asin: Optional[str] = Query(default=None),
    days: int = Query(default=30),
    db: Session = Depends(get_db),
):
    features = build_keyword_features_from_db(db, asin=asin, days=days)
    results = classify_keywords(features)

    return [
        KeywordClassOut(
            keyword_id=r.keyword_id,
            keyword_text=r.keyword_text,
            efficiency=r.efficiency,
            confidence=r.confidence,
            reason=r.reason,
            action=r.action,
        )
        for r in results
    ]


@router.post("/keywords/train")
def train_keyword_model(
    days: int = Query(default=60),
    db: Session = Depends(get_db),
):
    features = build_keyword_features_from_db(db, days=days)
    result = train_model(features)
    return result


# ── 이상 감지 ────────────────────────────────────────────

class AnomalyOut(BaseModel):
    asin: str
    anomaly_type: str
    severity: str
    current_value: float
    baseline_value: float
    z_score: float
    message: str
    suggested_action: str


@router.get("/anomalies", response_model=list[AnomalyOut])
def get_anomalies(
    z_threshold: float = Query(default=2.0, ge=1.0, le=4.0),
    db: Session = Depends(get_db),
):
    anomalies = detect_anomalies(db, z_threshold=z_threshold)
    return [
        AnomalyOut(
            asin=a.asin,
            anomaly_type=a.anomaly_type.value,
            severity=a.severity.value,
            current_value=a.current_value,
            baseline_value=a.baseline_value,
            z_score=a.z_score,
            message=a.message,
            suggested_action=a.suggested_action,
        )
        for a in anomalies
    ]
