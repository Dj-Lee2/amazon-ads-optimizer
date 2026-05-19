"""
키워드 효율 분류 ML 모델
특성: CTR, CVR, ACOS, CPC, 검색량(Impressions), 상대 경쟁 강도
레이블: high / medium / low
알고리즘: RandomForestClassifier (학습 + 예측)
"""
from dataclasses import dataclass
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import cross_val_score
import pickle
import os

MODEL_PATH = os.path.join(os.path.dirname(__file__), "keyword_model.pkl")
SCALER_PATH = os.path.join(os.path.dirname(__file__), "keyword_scaler.pkl")


@dataclass
class KeywordFeatures:
    keyword_id: str
    keyword_text: str
    ctr: float          # 클릭률 (%)
    cvr: float          # 전환율 (%)
    acos: float         # ACOS (%)
    cpc: float          # 클릭당 비용 ($)
    impressions: int    # 총 노출
    orders: int         # 총 주문
    spend: float        # 총 지출


@dataclass
class ClassificationResult:
    keyword_id: str
    keyword_text: str
    efficiency: str          # high / medium / low
    confidence: float        # 0~1
    reason: str
    action: str              # 추천 액션


def _extract_features(kw: KeywordFeatures) -> list[float]:
    """키워드를 ML 특성 벡터로 변환."""
    # 이진 플래그
    has_orders = 1.0 if kw.orders > 0 else 0.0
    high_impression = 1.0 if kw.impressions > 500 else 0.0

    return [
        kw.ctr,
        kw.cvr,
        kw.acos if kw.acos < 200 else 200.0,  # 이상값 클리핑
        kw.cpc,
        np.log1p(kw.impressions),
        np.log1p(kw.orders),
        np.log1p(kw.spend),
        has_orders,
        high_impression,
    ]


def _rule_based_label(kw: KeywordFeatures) -> str:
    """훈련 데이터 레이블 자동 생성을 위한 규칙 기반 분류."""
    if kw.orders == 0 and kw.spend > 5:
        return "low"
    if kw.acos == 0:
        return "medium"  # 데이터 부족
    if kw.acos < 18 and kw.cvr > 7 and kw.ctr > 0.5:
        return "high"
    if kw.acos > 45 or (kw.spend > 10 and kw.orders == 0):
        return "low"
    return "medium"


def train_model(keywords: list[KeywordFeatures]) -> dict:
    """
    키워드 데이터로 분류 모델을 훈련한다.
    규칙 기반 레이블을 훈련 신호로 사용 (준지도 학습 방식).
    """
    if len(keywords) < 10:
        return {"status": "skipped", "reason": "데이터 부족 (최소 10개 필요)"}

    X = np.array([_extract_features(kw) for kw in keywords])
    y = np.array([_rule_based_label(kw) for kw in keywords])

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    clf = RandomForestClassifier(
        n_estimators=100,
        max_depth=6,
        min_samples_leaf=3,
        class_weight="balanced",
        random_state=42,
    )

    # 교차검증
    if len(keywords) >= 30:
        scores = cross_val_score(clf, X_scaled, y, cv=3, scoring="f1_macro")
        cv_score = float(scores.mean())
    else:
        cv_score = None

    clf.fit(X_scaled, y)

    # 모델 저장
    with open(MODEL_PATH, "wb") as f:
        pickle.dump(clf, f)
    with open(SCALER_PATH, "wb") as f:
        pickle.dump(scaler, f)

    label_counts = {l: int((y == l).sum()) for l in ["high", "medium", "low"]}
    return {
        "status": "trained",
        "samples": len(keywords),
        "label_distribution": label_counts,
        "cv_f1_macro": round(cv_score, 3) if cv_score else None,
    }


def classify_keywords(keywords: list[KeywordFeatures]) -> list[ClassificationResult]:
    """
    학습된 모델로 키워드를 분류한다.
    모델이 없으면 규칙 기반으로 폴백.
    """
    results = []

    # 모델 로드 시도
    use_ml = False
    if os.path.exists(MODEL_PATH) and os.path.exists(SCALER_PATH):
        try:
            with open(MODEL_PATH, "rb") as f:
                clf = pickle.load(f)
            with open(SCALER_PATH, "rb") as f:
                scaler = pickle.load(f)
            use_ml = True
        except Exception:
            use_ml = False

    for kw in keywords:
        if use_ml:
            X = np.array([_extract_features(kw)])
            X_scaled = scaler.transform(X)
            proba = clf.predict_proba(X_scaled)[0]
            classes = clf.classes_
            pred_idx = proba.argmax()
            efficiency = classes[pred_idx]
            confidence = float(proba[pred_idx])
        else:
            efficiency = _rule_based_label(kw)
            confidence = 0.8  # 규칙 기반 고정 신뢰도

        reason, action = _get_reason_and_action(kw, efficiency)

        results.append(ClassificationResult(
            keyword_id=kw.keyword_id,
            keyword_text=kw.keyword_text,
            efficiency=efficiency,
            confidence=round(confidence, 2),
            reason=reason,
            action=action,
        ))

    return results


def _get_reason_and_action(kw: KeywordFeatures, efficiency: str) -> tuple[str, str]:
    if efficiency == "high":
        reason = f"ACOS {kw.acos:.1f}%, CVR {kw.cvr:.1f}% — 우수한 전환 효율"
        action = "입찰가 인상으로 클릭 점유율 확대"
    elif efficiency == "low":
        if kw.orders == 0 and kw.spend > 0:
            reason = f"클릭 {kw.spend:.1f}$ 소진, 주문 0건"
            action = "Negative Keyword 등록 또는 일시 중지"
        else:
            reason = f"ACOS {kw.acos:.1f}% — 목표 대비 과도한 광고비"
            action = "입찰가 인하 또는 매치타입 변경"
    else:
        reason = f"ACOS {kw.acos:.1f}%, Impressions {kw.impressions:,} — 보통 효율"
        action = "현 수준 유지, 데이터 추가 축적 후 재분류"

    return reason, action


def build_keyword_features_from_db(
    session, asin: str = None, days: int = 30
) -> list[KeywordFeatures]:
    """DB에서 키워드 특성 데이터를 가져온다."""
    from datetime import datetime, timedelta
    from sqlalchemy import func
    from models import AdPerformance, Keyword

    end = datetime.utcnow()
    start = end - timedelta(days=days)

    query = (
        session.query(
            AdPerformance.keyword_id,
            Keyword.keyword_text,
            func.sum(AdPerformance.impressions).label("impressions"),
            func.sum(AdPerformance.clicks).label("clicks"),
            func.sum(AdPerformance.spend).label("spend"),
            func.sum(AdPerformance.sales).label("sales"),
            func.sum(AdPerformance.orders).label("orders"),
            Keyword.bid,
        )
        .join(Keyword, Keyword.keyword_id == AdPerformance.keyword_id)
        .filter(
            AdPerformance.timestamp >= start,
            AdPerformance.timestamp < end,
            AdPerformance.keyword_id.isnot(None),
        )
    )

    if asin:
        query = query.filter(AdPerformance.asin == asin)

    rows = query.group_by(
        AdPerformance.keyword_id, Keyword.keyword_text, Keyword.bid
    ).all()

    features = []
    for r in rows:
        impressions = int(r.impressions or 0)
        clicks = int(r.clicks or 0)
        spend = float(r.spend or 0)
        sales = float(r.sales or 0)
        orders = int(r.orders or 0)

        ctr = clicks / impressions * 100 if impressions > 0 else 0
        cvr = orders / clicks * 100 if clicks > 0 else 0
        acos = spend / sales * 100 if sales > 0 else 0
        cpc = spend / clicks if clicks > 0 else float(r.bid or 1.0)

        features.append(KeywordFeatures(
            keyword_id=r.keyword_id,
            keyword_text=r.keyword_text,
            ctr=round(ctr, 3),
            cvr=round(cvr, 3),
            acos=round(acos, 2),
            cpc=round(cpc, 3),
            impressions=impressions,
            orders=orders,
            spend=spend,
        ))

    return features
