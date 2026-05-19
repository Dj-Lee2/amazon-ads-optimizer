import axios from "axios";

const api = axios.create({ baseURL: "/api/v1" });

export const fetchAsins = () => api.get("/asins").then((r) => r.data);
export const fetchPerformanceSummary = (days = 30) =>
  api.get("/performance/summary", { params: { days } }).then((r) => r.data);
export const fetchDailyPerformance = (asin, days = 30) =>
  api.get("/performance/daily", { params: { asin, days } }).then((r) => r.data);
export const fetchHourlyPerformance = (asin, hours = 48) =>
  api.get("/performance/hourly", { params: { asin, hours } }).then((r) => r.data);
export const fetchKeywords = (asin, days = 30) =>
  api.get("/keywords", { params: { asin, days } }).then((r) => r.data);
export const fetchInventory = () => api.get("/inventory").then((r) => r.data);

// 최적화 엔진 API
export const fetchBudgetPreview = (totalBudget, days = 30) =>
  api.get("/optimize/budget/preview", { params: { total_budget: totalBudget, days } }).then((r) => r.data);
export const postBudgetOptimize = (body) =>
  api.post("/optimize/budget", body).then((r) => r.data);
export const fetchBidRecommendations = (asin, targetAcos = 25, days = 14) =>
  api.get("/optimize/bids", { params: { asin, target_acos: targetAcos, days } }).then((r) => r.data);
export const fetchKeywordClassification = (asin, days = 30) =>
  api.get("/optimize/keywords/classify", { params: { asin, days } }).then((r) => r.data);
export const fetchAnomalies = (zThreshold = 2.0) =>
  api.get("/optimize/anomalies", { params: { z_threshold: zThreshold } }).then((r) => r.data);
export const postTrainKeywordModel = (days = 60) =>
  api.post("/optimize/keywords/train", null, { params: { days } }).then((r) => r.data);
