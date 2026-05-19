import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  Legend, ResponsiveContainer, RadarChart, Radar, PolarGrid,
  PolarAngleAxis, PolarRadiusAxis,
} from "recharts";
import {
  postBudgetOptimize, fetchBudgetPreview,
  fetchBidRecommendations, fetchAnomalies,
  fetchKeywordClassification, postTrainKeywordModel,
} from "../api/client";

const ASIN_TITLES = {
  B001SKIN01: "Vitamin C Serum",
  B001SKIN02: "Retinol Cream",
  B001SKIN03: "Niacinamide Toner",
  B001SKIN04: "SPF 50 Sunscreen",
  B001SKIN05: "Collagen Eye Cream",
};

const SeverityBadge = ({ severity }) => {
  const map = {
    critical: { bg: "#fee2e2", color: "#dc2626", label: "긴급" },
    warning: { bg: "#fef9c3", color: "#ca8a04", label: "경고" },
    info: { bg: "#dbeafe", color: "#2563eb", label: "정보" },
  };
  const s = map[severity] || map.info;
  return (
    <span style={{
      background: s.bg, color: s.color, borderRadius: 6,
      padding: "2px 10px", fontSize: 12, fontWeight: 700,
    }}>{s.label}</span>
  );
};

const EffBadge = ({ eff }) => {
  const map = {
    high: { bg: "#dcfce7", color: "#16a34a", label: "고효율" },
    medium: { bg: "#e0e7ff", color: "#4338ca", label: "보통" },
    low: { bg: "#fee2e2", color: "#dc2626", label: "저효율" },
  };
  const s = map[eff] || { bg: "#f3f4f6", color: "#6b7280", label: "미분류" };
  return (
    <span style={{
      background: s.bg, color: s.color, borderRadius: 6,
      padding: "2px 8px", fontSize: 11, fontWeight: 600,
    }}>{s.label}</span>
  );
};

const Section = ({ title, children, accent = "#4b6dd5" }) => (
  <div style={{
    background: "white", borderRadius: 12, padding: 24,
    boxShadow: "0 1px 4px rgba(0,0,0,0.08)", marginBottom: 24,
    borderLeft: `4px solid ${accent}`,
  }}>
    <h3 style={{ fontSize: 16, fontWeight: 700, color: "#1b2045", marginBottom: 16 }}>{title}</h3>
    {children}
  </div>
);

// ── 예산 최적화 섹션 ──────────────────────────────────────────
function BudgetOptimizer() {
  const [budget, setBudget] = useState(300);
  const [goal, setGoal] = useState("total_sales");
  const [result, setResult] = useState(null);

  const { data: preview, isLoading: previewLoading } = useQuery({
    queryKey: ["budgetPreview", budget],
    queryFn: () => fetchBudgetPreview(budget),
    enabled: budget > 0,
  });

  const mutation = useMutation({
    mutationFn: () => postBudgetOptimize({ total_budget: budget, goal, days: 30 }),
    onSuccess: (data) => setResult(data),
  });

  const goalLabels = {
    total_sales: "총 매출 최대화",
    total_profit: "총 이익 최대화",
    roas: "ROAS 최대화",
    ad_sales: "광고 매출 최대화",
  };

  const chartData = result
    ? result.allocations.map((a) => ({
        name: ASIN_TITLES[a.asin] || a.asin,
        현재예산: +(budget / result.allocations.length).toFixed(0),
        최적예산: a.allocated_budget,
        예상매출: a.expected_total_sales,
      }))
    : [];

  return (
    <Section title="예산 최적화 (Budget Optimizer)" accent="#4b6dd5">
      <div style={{ display: "flex", gap: 16, marginBottom: 20, flexWrap: "wrap", alignItems: "flex-end" }}>
        <div>
          <label style={{ fontSize: 13, color: "#6b7280", display: "block", marginBottom: 4 }}>
            총 일 예산 ($)
          </label>
          <input
            type="number"
            value={budget}
            min={50}
            max={5000}
            step={50}
            onChange={(e) => setBudget(Number(e.target.value))}
            style={{
              padding: "8px 12px", borderRadius: 8, border: "1px solid #e5e7eb",
              fontSize: 15, width: 120, fontWeight: 600,
            }}
          />
        </div>

        <div>
          <label style={{ fontSize: 13, color: "#6b7280", display: "block", marginBottom: 4 }}>
            최적화 목표
          </label>
          <select
            value={goal}
            onChange={(e) => setGoal(e.target.value)}
            style={{
              padding: "8px 12px", borderRadius: 8, border: "1px solid #e5e7eb",
              fontSize: 14, minWidth: 160,
            }}
          >
            {Object.entries(goalLabels).map(([v, l]) => (
              <option key={v} value={v}>{l}</option>
            ))}
          </select>
        </div>

        <button
          onClick={() => mutation.mutate()}
          disabled={mutation.isPending}
          style={{
            padding: "9px 24px", borderRadius: 8, border: "none",
            background: mutation.isPending ? "#9ca3af" : "#4b6dd5",
            color: "white", fontWeight: 700, cursor: "pointer", fontSize: 14,
          }}
        >
          {mutation.isPending ? "계산 중..." : "최적화 실행"}
        </button>
      </div>

      {/* 목표별 미리보기 */}
      {preview && (
        <div style={{ display: "flex", gap: 10, marginBottom: 20, flexWrap: "wrap" }}>
          {Object.entries(preview).map(([g, r]) => (
            <div
              key={g}
              onClick={() => setGoal(g)}
              style={{
                border: `2px solid ${goal === g ? "#4b6dd5" : "#e5e7eb"}`,
                borderRadius: 10, padding: "10px 16px", cursor: "pointer",
                background: goal === g ? "#eff2ff" : "white", flex: 1, minWidth: 150,
              }}
            >
              <div style={{ fontSize: 12, color: "#6b7280" }}>{goalLabels[g]}</div>
              <div style={{ fontSize: 18, fontWeight: 700, color: "#1b2045", marginTop: 4 }}>
                ${(r.expected_total_sales || 0).toLocaleString()}
              </div>
              <div style={{ fontSize: 11, color: r.improvement_pct >= 0 ? "#16a34a" : "#dc2626" }}>
                {r.improvement_pct >= 0 ? "+" : ""}{r.improvement_pct}% 개선 예상
              </div>
            </div>
          ))}
        </div>
      )}

      {/* 최적화 결과 */}
      {result && (
        <>
          <div style={{ display: "flex", gap: 12, marginBottom: 16, flexWrap: "wrap" }}>
            {[
              { label: "예상 총 매출", value: `$${result.expected_total_sales.toLocaleString()}` },
              { label: "예상 광고 매출", value: `$${result.expected_total_ad_sales.toLocaleString()}` },
              { label: "예상 이익", value: `$${result.expected_total_profit.toLocaleString()}` },
              { label: "개선율", value: `+${result.improvement_pct}%`, color: "#16a34a" },
            ].map((item) => (
              <div key={item.label} style={{
                background: "#f8faff", borderRadius: 8, padding: "10px 16px", flex: 1,
              }}>
                <div style={{ fontSize: 12, color: "#6b7280" }}>{item.label}</div>
                <div style={{ fontSize: 20, fontWeight: 700, color: item.color || "#1b2045" }}>
                  {item.value}
                </div>
              </div>
            ))}
          </div>

          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" />
              <XAxis dataKey="name" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip formatter={(v) => `$${v}`} />
              <Legend />
              <Bar dataKey="최적예산" fill="#4b6dd5" />
              <Bar dataKey="예상매출" fill="#22c55e" />
            </BarChart>
          </ResponsiveContainer>

          {/* ASIN별 배분 상세 */}
          <table style={{ width: "100%", fontSize: 13, marginTop: 16 }}>
            <thead>
              <tr style={{ color: "#6b7280", borderBottom: "2px solid #f3f4f6" }}>
                <td style={{ padding: "8px 0" }}>ASIN</td>
                <td style={{ textAlign: "right" }}>배정 예산</td>
                <td style={{ textAlign: "right" }}>예상 총매출</td>
                <td style={{ textAlign: "right" }}>예상 이익</td>
                <td style={{ textAlign: "right" }}>변화율</td>
              </tr>
            </thead>
            <tbody>
              {result.allocations.map((a) => (
                <tr key={a.asin} style={{ borderBottom: "1px solid #f3f4f6" }}>
                  <td style={{ padding: "8px 0", fontWeight: 600 }}>{ASIN_TITLES[a.asin] || a.asin}</td>
                  <td style={{ textAlign: "right" }}>${a.allocated_budget}</td>
                  <td style={{ textAlign: "right" }}>${a.expected_total_sales.toLocaleString()}</td>
                  <td style={{ textAlign: "right", color: a.expected_profit >= 0 ? "#16a34a" : "#dc2626" }}>
                    ${a.expected_profit.toLocaleString()}
                  </td>
                  <td style={{
                    textAlign: "right", fontWeight: 700,
                    color: a.change_pct >= 0 ? "#16a34a" : "#dc2626",
                  }}>
                    {a.change_pct >= 0 ? "+" : ""}{a.change_pct}%
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </Section>
  );
}

// ── 입찰가 최적화 섹션 ──────────────────────────────────────────
function BidOptimizer() {
  const [asin, setAsin] = useState("B001SKIN01");
  const [targetAcos, setTargetAcos] = useState(25);

  const { data: recs = [], isLoading, refetch } = useQuery({
    queryKey: ["bids", asin, targetAcos],
    queryFn: () => fetchBidRecommendations(asin, targetAcos),
    enabled: false,
  });

  const increases = recs.filter((r) => r.change_pct > 0);
  const decreases = recs.filter((r) => r.change_pct < 0);
  const unchanged = recs.filter((r) => r.change_pct === 0);

  return (
    <Section title="입찰가 최적화 (Bid Optimizer)" accent="#22c55e">
      <div style={{ display: "flex", gap: 16, marginBottom: 16, alignItems: "flex-end", flexWrap: "wrap" }}>
        <div>
          <label style={{ fontSize: 13, color: "#6b7280", display: "block", marginBottom: 4 }}>ASIN 선택</label>
          <select value={asin} onChange={(e) => setAsin(e.target.value)}
            style={{ padding: "8px 12px", borderRadius: 8, border: "1px solid #e5e7eb", fontSize: 14 }}>
            {Object.entries(ASIN_TITLES).map(([k, v]) => (
              <option key={k} value={k}>{v}</option>
            ))}
          </select>
        </div>
        <div>
          <label style={{ fontSize: 13, color: "#6b7280", display: "block", marginBottom: 4 }}>
            목표 ACOS: <strong>{targetAcos}%</strong>
          </label>
          <input type="range" min={10} max={60} step={5} value={targetAcos}
            onChange={(e) => setTargetAcos(Number(e.target.value))}
            style={{ width: 200 }} />
        </div>
        <button onClick={() => refetch()} disabled={isLoading}
          style={{
            padding: "9px 24px", borderRadius: 8, border: "none",
            background: isLoading ? "#9ca3af" : "#22c55e",
            color: "white", fontWeight: 700, cursor: "pointer",
          }}>
          {isLoading ? "계산 중..." : "입찰가 계산"}
        </button>
      </div>

      {recs.length > 0 && (
        <>
          <div style={{ display: "flex", gap: 12, marginBottom: 16 }}>
            {[
              { label: "인상 추천", count: increases.length, color: "#16a34a" },
              { label: "인하 추천", count: decreases.length, color: "#dc2626" },
              { label: "현행 유지", count: unchanged.length, color: "#6b7280" },
            ].map((s) => (
              <div key={s.label} style={{ background: "#f8faff", borderRadius: 8, padding: "10px 20px", flex: 1 }}>
                <div style={{ fontSize: 12, color: "#6b7280" }}>{s.label}</div>
                <div style={{ fontSize: 24, fontWeight: 700, color: s.color }}>{s.count}개</div>
              </div>
            ))}
          </div>

          <div style={{ maxHeight: 320, overflowY: "auto" }}>
            <table style={{ width: "100%", fontSize: 12 }}>
              <thead style={{ position: "sticky", top: 0, background: "white" }}>
                <tr style={{ color: "#6b7280", borderBottom: "2px solid #f3f4f6" }}>
                  <td style={{ padding: "8px 0" }}>키워드</td>
                  <td style={{ textAlign: "right" }}>현재</td>
                  <td style={{ textAlign: "right" }}>추천</td>
                  <td style={{ textAlign: "right" }}>변화</td>
                  <td style={{ paddingLeft: 12 }}>사유</td>
                </tr>
              </thead>
              <tbody>
                {recs.map((r) => (
                  <tr key={r.keyword_id} style={{ borderBottom: "1px solid #f9fafb" }}>
                    <td style={{ padding: "6px 0", fontWeight: 500 }}>{r.keyword_text}</td>
                    <td style={{ textAlign: "right" }}>${r.current_bid}</td>
                    <td style={{ textAlign: "right", fontWeight: 700 }}>${r.recommended_bid}</td>
                    <td style={{
                      textAlign: "right", fontWeight: 700,
                      color: r.change_pct > 0 ? "#16a34a" : r.change_pct < 0 ? "#dc2626" : "#6b7280",
                    }}>
                      {r.change_pct > 0 ? "+" : ""}{r.change_pct}%
                    </td>
                    <td style={{ paddingLeft: 12, color: "#6b7280", fontSize: 11 }}>{r.reason}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </Section>
  );
}

// ── 이상 감지 섹션 ──────────────────────────────────────────
function AnomalyPanel() {
  const { data: anomalies = [], isLoading, refetch } = useQuery({
    queryKey: ["anomalies"],
    queryFn: () => fetchAnomalies(2.0),
    refetchInterval: 300000, // 5분마다 자동 갱신
  });

  const typeLabels = {
    sales_spike: "매출 급등",
    sales_drop: "매출 급락",
    cpc_spike: "CPC 급등",
    budget_burnout: "예산 소진 위험",
    low_inventory: "재고 부족",
    acos_spike: "ACOS 급등",
    ctr_drop: "CTR 급락",
  };

  return (
    <Section title="이상 감지 알림 (Anomaly Detection)" accent="#ef4444">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
        <span style={{ color: "#6b7280", fontSize: 13 }}>
          {anomalies.length === 0 ? "감지된 이상 없음" : `${anomalies.length}개 이상 감지됨`}
        </span>
        <button onClick={() => refetch()} style={{
          padding: "6px 14px", borderRadius: 6, border: "1px solid #e5e7eb",
          background: "white", cursor: "pointer", fontSize: 12,
        }}>새로고침</button>
      </div>

      {isLoading ? (
        <p style={{ color: "#9ca3af" }}>감지 중...</p>
      ) : anomalies.length === 0 ? (
        <div style={{
          background: "#f0fdf4", border: "1px solid #bbf7d0", borderRadius: 8,
          padding: 16, color: "#16a34a", fontSize: 14, textAlign: "center",
        }}>
          모든 지표가 정상 범위 내에 있습니다.
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {anomalies.map((a, i) => (
            <div key={i} style={{
              border: `1px solid ${a.severity === "critical" ? "#fca5a5" : a.severity === "warning" ? "#fde68a" : "#bfdbfe"}`,
              borderRadius: 8, padding: "12px 16px",
              background: a.severity === "critical" ? "#fff5f5" : a.severity === "warning" ? "#fffbeb" : "#eff6ff",
            }}>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
                <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                  <SeverityBadge severity={a.severity} />
                  <span style={{ fontWeight: 700, fontSize: 13 }}>
                    {ASIN_TITLES[a.asin] || a.asin} — {typeLabels[a.anomaly_type] || a.anomaly_type}
                  </span>
                </div>
                {a.z_score > 0 && (
                  <span style={{ fontSize: 11, color: "#9ca3af" }}>Z={a.z_score}</span>
                )}
              </div>
              <p style={{ fontSize: 13, color: "#374151", marginBottom: 4 }}>{a.message}</p>
              <p style={{ fontSize: 12, color: "#4b6dd5", fontWeight: 600 }}>
                → {a.suggested_action}
              </p>
            </div>
          ))}
        </div>
      )}
    </Section>
  );
}

// ── 키워드 분류 섹션 ──────────────────────────────────────────
function KeywordClassifier() {
  const [asin, setAsin] = useState("B001SKIN01");
  const qc = useQueryClient();

  const { data: classified = [], isLoading, refetch } = useQuery({
    queryKey: ["classify", asin],
    queryFn: () => fetchKeywordClassification(asin),
    enabled: false,
  });

  const trainMutation = useMutation({
    mutationFn: () => postTrainKeywordModel(60),
    onSuccess: (data) => {
      alert(`모델 훈련 완료: ${JSON.stringify(data)}`);
      qc.invalidateQueries(["classify"]);
    },
  });

  const high = classified.filter((k) => k.efficiency === "high");
  const low = classified.filter((k) => k.efficiency === "low");
  const medium = classified.filter((k) => k.efficiency === "medium");

  return (
    <Section title="키워드 효율 분류 (ML Classification)" accent="#8b5cf6">
      <div style={{ display: "flex", gap: 12, marginBottom: 16, flexWrap: "wrap", alignItems: "flex-end" }}>
        <div>
          <label style={{ fontSize: 13, color: "#6b7280", display: "block", marginBottom: 4 }}>ASIN</label>
          <select value={asin} onChange={(e) => setAsin(e.target.value)}
            style={{ padding: "8px 12px", borderRadius: 8, border: "1px solid #e5e7eb", fontSize: 14 }}>
            {Object.entries(ASIN_TITLES).map(([k, v]) => (
              <option key={k} value={k}>{v}</option>
            ))}
          </select>
        </div>
        <button onClick={() => refetch()} disabled={isLoading}
          style={{
            padding: "9px 20px", borderRadius: 8, border: "none",
            background: "#8b5cf6", color: "white", fontWeight: 700, cursor: "pointer",
          }}>
          {isLoading ? "분류 중..." : "키워드 분류"}
        </button>
        <button onClick={() => trainMutation.mutate()} disabled={trainMutation.isPending}
          style={{
            padding: "9px 20px", borderRadius: 8, border: "1px solid #8b5cf6",
            background: "white", color: "#8b5cf6", fontWeight: 700, cursor: "pointer",
          }}>
          {trainMutation.isPending ? "훈련 중..." : "ML 모델 재훈련"}
        </button>
      </div>

      {classified.length > 0 && (
        <>
          <div style={{ display: "flex", gap: 12, marginBottom: 16 }}>
            {[
              { label: "고효율", count: high.length, color: "#16a34a" },
              { label: "보통", count: medium.length, color: "#4338ca" },
              { label: "저효율", count: low.length, color: "#dc2626" },
            ].map((s) => (
              <div key={s.label} style={{ background: "#f8faff", borderRadius: 8, padding: "10px 20px", flex: 1 }}>
                <div style={{ fontSize: 12, color: "#6b7280" }}>{s.label}</div>
                <div style={{ fontSize: 24, fontWeight: 700, color: s.color }}>{s.count}개</div>
              </div>
            ))}
          </div>

          <div style={{ maxHeight: 300, overflowY: "auto" }}>
            <table style={{ width: "100%", fontSize: 12 }}>
              <thead style={{ position: "sticky", top: 0, background: "white" }}>
                <tr style={{ color: "#6b7280", borderBottom: "2px solid #f3f4f6" }}>
                  <td style={{ padding: "8px 0" }}>키워드</td>
                  <td style={{ textAlign: "center" }}>효율</td>
                  <td style={{ textAlign: "right" }}>신뢰도</td>
                  <td style={{ paddingLeft: 12 }}>추천 액션</td>
                </tr>
              </thead>
              <tbody>
                {classified.map((k) => (
                  <tr key={k.keyword_id} style={{ borderBottom: "1px solid #f9fafb" }}>
                    <td style={{ padding: "6px 0", fontWeight: 500 }}>{k.keyword_text}</td>
                    <td style={{ textAlign: "center" }}><EffBadge eff={k.efficiency} /></td>
                    <td style={{ textAlign: "right" }}>{(k.confidence * 100).toFixed(0)}%</td>
                    <td style={{ paddingLeft: 12, color: "#6b7280", fontSize: 11 }}>{k.action}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </Section>
  );
}

// ── 메인 Optimizer 페이지 ──────────────────────────────────────────
export default function Optimizer() {
  return (
    <div style={{ padding: 24, maxWidth: 1200, margin: "0 auto" }}>
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 24, fontWeight: 700, color: "#1b2045" }}>최적화 엔진</h1>
        <p style={{ color: "#6b7280", fontSize: 14, marginTop: 4 }}>
          AI · 수리최적화 기반 광고 자동 최적화
        </p>
      </div>

      <AnomalyPanel />
      <BudgetOptimizer />
      <BidOptimizer />
      <KeywordClassifier />
    </div>
  );
}
