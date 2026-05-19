import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer, PieChart, Pie, Cell,
} from "recharts";
import {
  fetchPerformanceSummary, fetchDailyPerformance,
  fetchKeywords, fetchInventory,
} from "../api/client";

const COLORS = ["#4b6dd5", "#22c55e", "#f59e0b", "#ef4444", "#8b5cf6"];

const KpiCard = ({ label, value, unit = "", color = "#4b6dd5", sub }) => (
  <div style={{
    background: "white", borderRadius: 12, padding: "20px 24px",
    boxShadow: "0 1px 4px rgba(0,0,0,0.08)", flex: 1, minWidth: 160,
  }}>
    <div style={{ fontSize: 13, color: "#6b7280", marginBottom: 8 }}>{label}</div>
    <div style={{ fontSize: 28, fontWeight: 700, color }}>
      {unit === "$" ? `$${value}` : `${value}${unit}`}
    </div>
    {sub && <div style={{ fontSize: 12, color: "#9ca3af", marginTop: 4 }}>{sub}</div>}
  </div>
);

const StatusBadge = ({ status }) => {
  const styles = {
    ok: { bg: "#dcfce7", color: "#16a34a", label: "정상" },
    low: { bg: "#fef9c3", color: "#ca8a04", label: "부족" },
    critical: { bg: "#fee2e2", color: "#dc2626", label: "긴급" },
  };
  const s = styles[status] || styles.ok;
  return (
    <span style={{
      background: s.bg, color: s.color, borderRadius: 6,
      padding: "2px 10px", fontSize: 12, fontWeight: 600,
    }}>{s.label}</span>
  );
};

const EffBadge = ({ eff }) => {
  const styles = {
    high: { bg: "#dcfce7", color: "#16a34a", label: "고효율" },
    medium: { bg: "#e0e7ff", color: "#4338ca", label: "보통" },
    low: { bg: "#fee2e2", color: "#dc2626", label: "저효율" },
    unclassified: { bg: "#f3f4f6", color: "#6b7280", label: "미분류" },
  };
  const s = styles[eff] || styles.unclassified;
  return (
    <span style={{
      background: s.bg, color: s.color, borderRadius: 6,
      padding: "2px 8px", fontSize: 11, fontWeight: 600,
    }}>{s.label}</span>
  );
};

export default function Dashboard() {
  const [selectedAsin, setSelectedAsin] = useState("B001SKIN01");
  const [days, setDays] = useState(30);

  const { data: summary = [] } = useQuery({
    queryKey: ["summary", days],
    queryFn: () => fetchPerformanceSummary(days),
  });
  const { data: daily = [] } = useQuery({
    queryKey: ["daily", selectedAsin, days],
    queryFn: () => fetchDailyPerformance(selectedAsin, days),
  });
  const { data: keywords = [], isLoading: kwLoading } = useQuery({
    queryKey: ["keywords", selectedAsin, days],
    queryFn: () => fetchKeywords(selectedAsin, days),
  });
  const { data: inventory = [] } = useQuery({
    queryKey: ["inventory"],
    queryFn: fetchInventory,
  });

  const selected = summary.find((s) => s.asin === selectedAsin) || {};

  const asinTitles = {
    B001SKIN01: "Vitamin C Serum",
    B001SKIN02: "Retinol Cream",
    B001SKIN03: "Niacinamide Toner",
    B001SKIN04: "SPF 50 Sunscreen",
    B001SKIN05: "Collagen Eye Cream",
  };

  const pieData = summary.map((s, i) => ({
    name: asinTitles[s.asin] || s.asin,
    value: s.ad_sales,
    color: COLORS[i % COLORS.length],
  }));

  const highKws = keywords.filter((k) => k.efficiency === "high").slice(0, 5);
  const lowKws = keywords.filter((k) => k.efficiency === "low").slice(0, 5);

  return (
    <div style={{ padding: 24, maxWidth: 1400, margin: "0 auto" }}>
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 24 }}>
        <div>
          <h1 style={{ fontSize: 24, fontWeight: 700, color: "#1b2045" }}>Amazon Ads Optimizer</h1>
          <p style={{ color: "#6b7280", fontSize: 14, marginTop: 4 }}>광고 성과 실시간 모니터링 대시보드</p>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          {[7, 30, 60, 90].map((d) => (
            <button
              key={d}
              onClick={() => setDays(d)}
              style={{
                padding: "6px 16px", borderRadius: 8, border: "none", cursor: "pointer",
                background: days === d ? "#4b6dd5" : "#e5e7eb",
                color: days === d ? "white" : "#374151", fontWeight: 600, fontSize: 13,
              }}
            >{d}일</button>
          ))}
        </div>
      </div>

      {/* ASIN 선택 탭 */}
      <div style={{ display: "flex", gap: 8, marginBottom: 24, flexWrap: "wrap" }}>
        {Object.entries(asinTitles).map(([asin, title]) => (
          <button
            key={asin}
            onClick={() => setSelectedAsin(asin)}
            style={{
              padding: "8px 16px", borderRadius: 8, border: "2px solid",
              borderColor: selectedAsin === asin ? "#4b6dd5" : "#e5e7eb",
              background: selectedAsin === asin ? "#eff2ff" : "white",
              color: selectedAsin === asin ? "#4b6dd5" : "#374151",
              cursor: "pointer", fontWeight: 600, fontSize: 13,
            }}
          >{title}</button>
        ))}
      </div>

      {/* KPI 카드 */}
      <div style={{ display: "flex", gap: 16, marginBottom: 24, flexWrap: "wrap" }}>
        <KpiCard label="총 매출" value={(selected.total_sales || 0).toLocaleString()} unit="$" color="#4b6dd5" />
        <KpiCard label="광고 매출" value={(selected.ad_sales || 0).toLocaleString()} unit="$" color="#22c55e" />
        <KpiCard label="광고비" value={(selected.total_spend || 0).toLocaleString()} unit="$" color="#f59e0b" />
        <KpiCard label="TACOS" value={selected.tacos || 0} unit="%" color={(selected.tacos || 0) > 20 ? "#ef4444" : "#4b6dd5"} sub="총매출 대비 광고비 비율" />
        <KpiCard label="ROAS" value={selected.roas || 0} unit="x" color="#8b5cf6" sub="광고비 대비 광고 매출" />
        <KpiCard label="ACOS" value={selected.acos || 0} unit="%" color={(selected.acos || 0) > 30 ? "#ef4444" : "#22c55e"} sub="광고비 / 광고 매출" />
      </div>

      {/* 차트 섹션 */}
      <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: 20, marginBottom: 24 }}>
        {/* 일별 매출 차트 */}
        <div style={{ background: "white", borderRadius: 12, padding: 20, boxShadow: "0 1px 4px rgba(0,0,0,0.08)" }}>
          <h3 style={{ fontSize: 15, fontWeight: 700, color: "#1b2045", marginBottom: 16 }}>일별 매출 트렌드</h3>
          <ResponsiveContainer width="100%" height={260}>
            <LineChart data={daily}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" />
              <XAxis dataKey="date" tick={{ fontSize: 11 }} tickFormatter={(d) => d.slice(5)} />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip formatter={(v) => `$${v.toLocaleString()}`} />
              <Legend />
              <Line type="monotone" dataKey="total_sales" name="총 매출" stroke="#4b6dd5" strokeWidth={2} dot={false} />
              <Line type="monotone" dataKey="ad_sales" name="광고 매출" stroke="#22c55e" strokeWidth={2} dot={false} />
              <Line type="monotone" dataKey="ad_spend" name="광고비" stroke="#f59e0b" strokeWidth={2} dot={false} strokeDasharray="4 2" />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* ASIN별 광고 매출 파이 차트 */}
        <div style={{ background: "white", borderRadius: 12, padding: 20, boxShadow: "0 1px 4px rgba(0,0,0,0.08)" }}>
          <h3 style={{ fontSize: 15, fontWeight: 700, color: "#1b2045", marginBottom: 16 }}>ASIN별 광고 매출 비중</h3>
          <ResponsiveContainer width="100%" height={260}>
            <PieChart>
              <Pie data={pieData} cx="50%" cy="50%" outerRadius={90} dataKey="value" label={({ name, percent }) => `${(percent * 100).toFixed(0)}%`} labelLine={false}>
                {pieData.map((entry, i) => (
                  <Cell key={i} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip formatter={(v) => `$${v.toLocaleString()}`} />
              <Legend formatter={(v) => v} />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* TACOS 차트 */}
      <div style={{ background: "white", borderRadius: 12, padding: 20, boxShadow: "0 1px 4px rgba(0,0,0,0.08)", marginBottom: 24 }}>
        <h3 style={{ fontSize: 15, fontWeight: 700, color: "#1b2045", marginBottom: 16 }}>일별 TACOS / ROAS 추이</h3>
        <ResponsiveContainer width="100%" height={200}>
          <BarChart data={daily}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" />
            <XAxis dataKey="date" tick={{ fontSize: 11 }} tickFormatter={(d) => d.slice(5)} />
            <YAxis yAxisId="left" tick={{ fontSize: 11 }} />
            <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 11 }} />
            <Tooltip />
            <Legend />
            <Bar yAxisId="left" dataKey="tacos" name="TACOS (%)" fill="#4b6dd5" opacity={0.8} />
            <Line yAxisId="right" type="monotone" dataKey="roas" name="ROAS (x)" stroke="#ef4444" strokeWidth={2} dot={false} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* 키워드 & 재고 하단 섹션 */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 20 }}>
        {/* 고효율 키워드 */}
        <div style={{ background: "white", borderRadius: 12, padding: 20, boxShadow: "0 1px 4px rgba(0,0,0,0.08)" }}>
          <h3 style={{ fontSize: 15, fontWeight: 700, color: "#16a34a", marginBottom: 12 }}>고효율 키워드 TOP 5</h3>
          {kwLoading ? <p style={{ color: "#9ca3af" }}>로딩 중...</p> : highKws.length === 0 ? <p style={{ color: "#9ca3af" }}>데이터 없음</p> : (
            <table style={{ width: "100%", fontSize: 12 }}>
              <thead>
                <tr style={{ color: "#6b7280" }}>
                  <td style={{ paddingBottom: 8 }}>키워드</td>
                  <td style={{ paddingBottom: 8, textAlign: "right" }}>ACOS</td>
                  <td style={{ paddingBottom: 8, textAlign: "right" }}>매출</td>
                </tr>
              </thead>
              <tbody>
                {highKws.map((kw) => (
                  <tr key={kw.keyword_id} style={{ borderTop: "1px solid #f3f4f6" }}>
                    <td style={{ padding: "6px 0", color: "#1b2045", fontWeight: 500 }}>{kw.keyword_text}</td>
                    <td style={{ textAlign: "right", color: "#16a34a" }}>{kw.acos}%</td>
                    <td style={{ textAlign: "right", color: "#374151" }}>${kw.sales.toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {/* 저효율 키워드 */}
        <div style={{ background: "white", borderRadius: 12, padding: 20, boxShadow: "0 1px 4px rgba(0,0,0,0.08)" }}>
          <h3 style={{ fontSize: 15, fontWeight: 700, color: "#dc2626", marginBottom: 12 }}>저효율 키워드 TOP 5</h3>
          {kwLoading ? <p style={{ color: "#9ca3af" }}>로딩 중...</p> : lowKws.length === 0 ? <p style={{ color: "#9ca3af" }}>데이터 없음</p> : (
            <table style={{ width: "100%", fontSize: 12 }}>
              <thead>
                <tr style={{ color: "#6b7280" }}>
                  <td style={{ paddingBottom: 8 }}>키워드</td>
                  <td style={{ paddingBottom: 8, textAlign: "right" }}>ACOS</td>
                  <td style={{ paddingBottom: 8, textAlign: "right" }}>지출</td>
                </tr>
              </thead>
              <tbody>
                {lowKws.map((kw) => (
                  <tr key={kw.keyword_id} style={{ borderTop: "1px solid #f3f4f6" }}>
                    <td style={{ padding: "6px 0", color: "#1b2045", fontWeight: 500 }}>{kw.keyword_text}</td>
                    <td style={{ textAlign: "right", color: "#dc2626" }}>{kw.acos}%</td>
                    <td style={{ textAlign: "right", color: "#374151" }}>${kw.spend.toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {/* 재고 현황 */}
        <div style={{ background: "white", borderRadius: 12, padding: 20, boxShadow: "0 1px 4px rgba(0,0,0,0.08)" }}>
          <h3 style={{ fontSize: 15, fontWeight: 700, color: "#1b2045", marginBottom: 12 }}>재고 현황</h3>
          <table style={{ width: "100%", fontSize: 12 }}>
            <thead>
              <tr style={{ color: "#6b7280" }}>
                <td style={{ paddingBottom: 8 }}>ASIN</td>
                <td style={{ paddingBottom: 8, textAlign: "right" }}>잔여일</td>
                <td style={{ paddingBottom: 8, textAlign: "center" }}>상태</td>
              </tr>
            </thead>
            <tbody>
              {inventory.map((inv) => (
                <tr key={inv.asin} style={{ borderTop: "1px solid #f3f4f6" }}>
                  <td style={{ padding: "6px 0", color: "#374151", fontWeight: 500 }}>{asinTitles[inv.asin] || inv.asin}</td>
                  <td style={{ textAlign: "right", color: inv.days_of_supply < 14 ? "#dc2626" : "#374151" }}>
                    {inv.days_of_supply.toFixed(0)}일
                  </td>
                  <td style={{ textAlign: "center" }}><StatusBadge status={inv.status} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
