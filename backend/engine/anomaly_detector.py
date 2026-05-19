"""
이상 감지 엔진: 성수기, 경쟁 심화, 재고 부족, 예산 조기 소진 자동 감지
알고리즘: Z-score 기반 통계적 이상 감지 + 규칙 기반 알림
"""
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
import numpy as np


class AnomalyType(str, Enum):
    SALES_SPIKE = "sales_spike"          # 매출 급등 (성수기)
    SALES_DROP = "sales_drop"            # 매출 급락
    CPC_SPIKE = "cpc_spike"              # CPC 급등 (경쟁 심화)
    BUDGET_BURNOUT = "budget_burnout"    # 예산 조기 소진 위험
    LOW_INVENTORY = "low_inventory"      # 재고 부족
    ACOS_SPIKE = "acos_spike"            # ACOS 급등
    CTR_DROP = "ctr_drop"               # CTR 급락 (광고 품질 저하)


class Severity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class Anomaly:
    asin: str
    anomaly_type: AnomalyType
    severity: Severity
    detected_at: datetime
    current_value: float
    baseline_value: float
    z_score: float
    message: str
    suggested_action: str


def detect_anomalies(
    session,
    z_threshold: float = 2.0,       # 이상치 Z-score 임계값
    lookback_days: int = 14,         # 기준선 계산 기간
    recent_hours: int = 24,          # 최근 관찰 기간
) -> list[Anomaly]:
    """
    최근 24시간 데이터를 과거 2주 기준선과 비교해 이상을 감지한다.
    """
    from models import AdPerformance, OrganicPerformance, Inventory, Asin
    from sqlalchemy import func

    now = datetime.utcnow()
    recent_start = now - timedelta(hours=recent_hours)
    baseline_start = now - timedelta(days=lookback_days)
    baseline_end = recent_start

    asins = session.query(Asin).all()
    anomalies = []

    for asin_obj in asins:
        asin = asin_obj.asin

        # ── 광고 성과 기준선 (시간당 평균) ──
        baseline = _get_hourly_stats(session, AdPerformance, asin, baseline_start, baseline_end)
        recent = _get_hourly_stats(session, AdPerformance, asin, recent_start, now)

        if baseline and recent:
            # CPC 이상 감지
            if baseline["cpc_std"] > 0:
                cpc_z = (recent["avg_cpc"] - baseline["avg_cpc"]) / baseline["cpc_std"]
                if cpc_z > z_threshold:
                    anomalies.append(Anomaly(
                        asin=asin,
                        anomaly_type=AnomalyType.CPC_SPIKE,
                        severity=Severity.WARNING if cpc_z < 3.5 else Severity.CRITICAL,
                        detected_at=now,
                        current_value=round(recent["avg_cpc"], 2),
                        baseline_value=round(baseline["avg_cpc"], 2),
                        z_score=round(cpc_z, 2),
                        message=f"CPC 급등: ${recent['avg_cpc']:.2f} (평소 ${baseline['avg_cpc']:.2f})",
                        suggested_action="경쟁사 공격 또는 성수기 가능성 — 예산 증액 또는 입찰가 재검토",
                    ))

            # ACOS 이상 감지
            if baseline["acos_std"] > 0 and recent["avg_acos"] > 0:
                acos_z = (recent["avg_acos"] - baseline["avg_acos"]) / baseline["acos_std"]
                if acos_z > z_threshold:
                    anomalies.append(Anomaly(
                        asin=asin,
                        anomaly_type=AnomalyType.ACOS_SPIKE,
                        severity=Severity.WARNING,
                        detected_at=now,
                        current_value=round(recent["avg_acos"], 1),
                        baseline_value=round(baseline["avg_acos"], 1),
                        z_score=round(acos_z, 2),
                        message=f"ACOS 급등: {recent['avg_acos']:.1f}% (평소 {baseline['avg_acos']:.1f}%)",
                        suggested_action="저효율 키워드 입찰가 즉시 인하 권장",
                    ))

            # 매출 급락 감지
            if baseline["sales_std"] > 0:
                sales_z = (recent["avg_sales"] - baseline["avg_sales"]) / baseline["sales_std"]
                if sales_z < -z_threshold:
                    anomalies.append(Anomaly(
                        asin=asin,
                        anomaly_type=AnomalyType.SALES_DROP,
                        severity=Severity.WARNING if sales_z > -3.5 else Severity.CRITICAL,
                        detected_at=now,
                        current_value=round(recent["avg_sales"], 2),
                        baseline_value=round(baseline["avg_sales"], 2),
                        z_score=round(sales_z, 2),
                        message=f"매출 급락: ${recent['avg_sales']:.2f}/h (평소 ${baseline['avg_sales']:.2f}/h)",
                        suggested_action="광고 노출 현황 확인, 재고/가격/리스팅 품질 점검",
                    ))
                elif sales_z > z_threshold * 1.5:
                    anomalies.append(Anomaly(
                        asin=asin,
                        anomaly_type=AnomalyType.SALES_SPIKE,
                        severity=Severity.INFO,
                        detected_at=now,
                        current_value=round(recent["avg_sales"], 2),
                        baseline_value=round(baseline["avg_sales"], 2),
                        z_score=round(sales_z, 2),
                        message=f"매출 급등: ${recent['avg_sales']:.2f}/h (평소 ${baseline['avg_sales']:.2f}/h)",
                        suggested_action="성수기 감지 — 예산 증액으로 추가 매출 확보 기회",
                    ))

        # ── 예산 소진 속도 감지 ──
        budget_anomaly = _check_budget_burnout(session, asin, now)
        if budget_anomaly:
            anomalies.append(budget_anomaly)

        # ── 재고 부족 감지 ──
        inv_anomaly = _check_inventory(session, asin, now)
        if inv_anomaly:
            anomalies.append(inv_anomaly)

    return sorted(anomalies, key=lambda a: ["critical", "warning", "info"].index(a.severity.value))


def _get_hourly_stats(session, model, asin: str, start: datetime, end: datetime) -> dict | None:
    from sqlalchemy import func
    from models import AdPerformance

    rows = (
        session.query(
            func.strftime("%Y-%m-%d %H", AdPerformance.timestamp).label("hour_bucket"),
            func.sum(AdPerformance.spend).label("spend"),
            func.sum(AdPerformance.sales).label("sales"),
            func.sum(AdPerformance.clicks).label("clicks"),
        )
        .filter(
            AdPerformance.asin == asin,
            AdPerformance.timestamp >= start,
            AdPerformance.timestamp < end,
        )
        .group_by(func.strftime("%Y-%m-%d %H", AdPerformance.timestamp))
        .all()
    )

    if not rows:
        return None

    spends = np.array([float(r.spend or 0) for r in rows])
    sales = np.array([float(r.sales or 0) for r in rows])
    clicks = np.array([int(r.clicks or 0) for r in rows])

    cpc_arr = np.where(clicks > 0, spends / clicks, 0)
    acos_arr = np.where(sales > 0, spends / sales * 100, 0)

    return {
        "avg_cpc": float(cpc_arr[cpc_arr > 0].mean()) if (cpc_arr > 0).any() else 0,
        "cpc_std": float(cpc_arr[cpc_arr > 0].std()) if (cpc_arr > 0).sum() > 1 else 0.1,
        "avg_sales": float(sales.mean()),
        "sales_std": float(sales.std()) if len(sales) > 1 else 0.1,
        "avg_acos": float(acos_arr[acos_arr > 0].mean()) if (acos_arr > 0).any() else 0,
        "acos_std": float(acos_arr[acos_arr > 0].std()) if (acos_arr > 0).sum() > 1 else 0.1,
    }


def _check_budget_burnout(session, asin: str, now: datetime) -> Anomaly | None:
    """당일 지출 속도로 예산 조기 소진 위험을 감지한다."""
    from sqlalchemy import func
    from models import AdPerformance, Campaign

    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    hours_elapsed = max(1, (now - today_start).seconds // 3600)

    today_spend = session.query(func.sum(AdPerformance.spend)).filter(
        AdPerformance.asin == asin,
        AdPerformance.timestamp >= today_start,
        AdPerformance.timestamp < now,
    ).scalar() or 0

    daily_budget = session.query(func.sum(Campaign.daily_budget)).filter(
        Campaign.asin == asin, Campaign.is_active == 1
    ).scalar() or 0

    if daily_budget <= 0:
        return None

    hourly_burn_rate = float(today_spend) / hours_elapsed
    projected_daily = hourly_burn_rate * 24
    burn_ratio = projected_daily / float(daily_budget)

    if burn_ratio > 1.3:
        return Anomaly(
            asin=asin,
            anomaly_type=AnomalyType.BUDGET_BURNOUT,
            severity=Severity.CRITICAL if burn_ratio > 1.6 else Severity.WARNING,
            detected_at=now,
            current_value=round(projected_daily, 2),
            baseline_value=round(float(daily_budget), 2),
            z_score=round(burn_ratio, 2),
            message=f"예산 조기 소진 위험: 예상 ${projected_daily:.2f} vs 예산 ${daily_budget:.2f}",
            suggested_action="시간별 예산 배분 조정 또는 일예산 증액",
        )
    return None


def _check_inventory(session, asin: str, now: datetime) -> Anomaly | None:
    from models import Inventory

    inv = session.query(Inventory).filter(
        Inventory.asin == asin
    ).order_by(Inventory.timestamp.desc()).first()

    if not inv:
        return None

    if inv.days_of_supply < 7:
        severity = Severity.CRITICAL
        msg = f"재고 {inv.days_of_supply:.0f}일치 남음 — 긴급 재입고 필요"
        action = "광고 예산 즉시 축소, 재입고 발주 진행"
    elif inv.days_of_supply < 14:
        severity = Severity.WARNING
        msg = f"재고 {inv.days_of_supply:.0f}일치 남음 — 재입고 검토 필요"
        action = "입찰가 소폭 인하로 매출 속도 조절"
    else:
        return None

    return Anomaly(
        asin=asin,
        anomaly_type=AnomalyType.LOW_INVENTORY,
        severity=severity,
        detected_at=now,
        current_value=float(inv.days_of_supply),
        baseline_value=30.0,
        z_score=0.0,
        message=msg,
        suggested_action=action,
    )
