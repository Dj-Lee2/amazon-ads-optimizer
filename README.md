# Amazon Ads Optimizer

LG Optapex 벤치마킹, Amazon 광고 자동 최적화 솔루션 (Mock 데이터 기반)

## 빠른 시작

### 1. Docker로 DB/Redis 실행
```bash
docker-compose up postgres redis -d
```

### 2. Python 백엔드 설정
```bash
cd backend
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt

# DB 초기화 및 90일치 Mock 데이터 생성 (최초 1회)
python seed.py

# 서버 실행
uvicorn main:app --reload
```

### 3. React 프론트엔드 실행
```bash
cd frontend
npm install
npm start
```

브라우저에서 http://localhost:3000 접속

## API 문서
서버 실행 후 http://localhost:8000/docs 에서 Swagger UI 확인 가능

## 주요 API 엔드포인트
| 엔드포인트 | 설명 |
|---|---|
| GET /api/v1/asins | 전체 ASIN 목록 |
| GET /api/v1/performance/summary | ASIN별 성과 요약 (KPI) |
| GET /api/v1/performance/daily?asin=B001SKIN01&days=30 | 일별 성과 트렌드 |
| GET /api/v1/performance/hourly?asin=B001SKIN01&hours=48 | 시간별 성과 |
| GET /api/v1/keywords?asin=B001SKIN01 | 키워드 효율 분석 |
| GET /api/v1/inventory | 재고 현황 |

## 프로젝트 구조
```
amazon_optimizer/
├── backend/
│   ├── models/          # SQLAlchemy DB 모델
│   ├── data_providers/  # DataProvider 인터페이스 + Mock/Real 구현체
│   ├── engine/          # 최적화 엔진 (Phase 2에서 구현)
│   ├── automation/      # 자동화 실행 엔진 (Phase 3)
│   ├── ai/              # AI 상품 최적화 (Phase 5)
│   ├── api/             # FastAPI 라우터
│   ├── main.py
│   ├── seed.py          # Mock 데이터 시드
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── pages/       # Dashboard, Keywords, Inventory, BudgetSimulator
│       └── api/         # API 클라이언트
└── docker-compose.yml
```

## 다음 구현 단계
- **Phase 2**: 예산/입찰 최적화 엔진 (`engine/budget_optimizer.py`, `engine/bid_optimizer.py`)
- **Phase 3**: 키워드 하비스팅 자동화 (`automation/campaign_manager.py`)
- **Phase 5**: AI 상품명 최적화 (`ai/title_optimizer.py`) — Claude API 활용
