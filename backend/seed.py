"""DB 초기화 및 Mock 데이터 시드 스크립트. 한 번만 실행."""
from db import engine, SessionLocal
from models import Base
from data_providers.mock_generator import generate_all

if __name__ == "__main__":
    print("테이블 생성 중...")
    Base.metadata.create_all(bind=engine)

    with SessionLocal() as session:
        generate_all(session, days=90)

    print("완료! 이제 uvicorn main:app 으로 서버를 시작하세요.")
