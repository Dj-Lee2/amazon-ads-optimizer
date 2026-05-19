import React, { useState } from "react";
import ReactDOM from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import Dashboard from "./pages/Dashboard";
import Optimizer from "./pages/Optimizer";

const queryClient = new QueryClient({
  defaultOptions: { queries: { refetchInterval: 60000, staleTime: 30000 } },
});

const NAV_ITEMS = [
  { id: "dashboard", label: "퍼포먼스 대시보드" },
  { id: "optimizer", label: "최적화 엔진" },
];

function App() {
  const [page, setPage] = useState("dashboard");

  return (
    <div>
      {/* 글로벌 네비게이션 */}
      <nav style={{
        background: "#1b2045", padding: "0 24px",
        display: "flex", alignItems: "center", gap: 4,
      }}>
        <span style={{ color: "white", fontWeight: 800, fontSize: 16, marginRight: 24, padding: "16px 0" }}>
          Amazon Ads Optimizer
        </span>
        {NAV_ITEMS.map((item) => (
          <button
            key={item.id}
            onClick={() => setPage(item.id)}
            style={{
              background: "none", border: "none", cursor: "pointer",
              color: page === item.id ? "white" : "rgba(255,255,255,0.6)",
              fontWeight: page === item.id ? 700 : 500,
              fontSize: 14, padding: "18px 16px",
              borderBottom: page === item.id ? "3px solid #8ca2e7" : "3px solid transparent",
            }}
          >
            {item.label}
          </button>
        ))}
      </nav>

      {/* 페이지 렌더링 */}
      {page === "dashboard" && <Dashboard />}
      {page === "optimizer" && <Optimizer />}
    </div>
  );
}

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(
  <QueryClientProvider client={queryClient}>
    <App />
  </QueryClientProvider>
);
