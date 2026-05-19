from sqlalchemy import (
    Column, String, Float, Integer, DateTime, ForeignKey, Enum, Index
)
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime
import enum

Base = declarative_base()


class MatchType(str, enum.Enum):
    EXACT = "exact"
    PHRASE = "phrase"
    BROAD = "broad"


class CampaignType(str, enum.Enum):
    AUTO = "auto"
    MANUAL = "manual"


class KeywordStatus(str, enum.Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    NEGATIVE = "negative"


class KeywordEfficiency(str, enum.Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNCLASSIFIED = "unclassified"


class Asin(Base):
    __tablename__ = "asin_master"

    asin = Column(String(10), primary_key=True)
    title = Column(String(500), nullable=False)
    price = Column(Float, nullable=False)
    category = Column(String(100))
    marketplace = Column(String(5), default="US")
    created_at = Column(DateTime, default=datetime.utcnow)

    campaigns = relationship("Campaign", back_populates="asin_ref")
    inventory_records = relationship("Inventory", back_populates="asin_ref")
    organic_records = relationship("OrganicPerformance", back_populates="asin_ref")


class Campaign(Base):
    __tablename__ = "campaigns"

    campaign_id = Column(String(50), primary_key=True)
    asin = Column(String(10), ForeignKey("asin_master.asin"), nullable=False)
    campaign_type = Column(Enum(CampaignType), nullable=False)
    daily_budget = Column(Float, nullable=False)
    is_active = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)

    asin_ref = relationship("Asin", back_populates="campaigns")
    keywords = relationship("Keyword", back_populates="campaign_ref")
    performance_records = relationship("AdPerformance", back_populates="campaign_ref")


class Keyword(Base):
    __tablename__ = "keywords"

    keyword_id = Column(String(50), primary_key=True)
    campaign_id = Column(String(50), ForeignKey("campaigns.campaign_id"), nullable=False)
    asin = Column(String(10), ForeignKey("asin_master.asin"), nullable=False)
    keyword_text = Column(String(200), nullable=False)
    match_type = Column(Enum(MatchType), nullable=False)
    bid = Column(Float, nullable=False)
    status = Column(Enum(KeywordStatus), default=KeywordStatus.ACTIVE)
    efficiency = Column(Enum(KeywordEfficiency), default=KeywordEfficiency.UNCLASSIFIED)
    created_at = Column(DateTime, default=datetime.utcnow)

    campaign_ref = relationship("Campaign", back_populates="keywords")
    performance_records = relationship("AdPerformance", back_populates="keyword_ref")


class AdPerformance(Base):
    __tablename__ = "ad_performance"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, nullable=False)
    asin = Column(String(10), ForeignKey("asin_master.asin"), nullable=False)
    campaign_id = Column(String(50), ForeignKey("campaigns.campaign_id"), nullable=False)
    keyword_id = Column(String(50), ForeignKey("keywords.keyword_id"), nullable=True)
    impressions = Column(Integer, default=0)
    clicks = Column(Integer, default=0)
    spend = Column(Float, default=0.0)
    sales = Column(Float, default=0.0)
    orders = Column(Integer, default=0)

    campaign_ref = relationship("Campaign", back_populates="performance_records")
    keyword_ref = relationship("Keyword", back_populates="performance_records")

    __table_args__ = (
        Index("ix_ad_performance_timestamp_asin", "timestamp", "asin"),
    )


class OrganicPerformance(Base):
    __tablename__ = "organic_performance"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, nullable=False)
    asin = Column(String(10), ForeignKey("asin_master.asin"), nullable=False)
    organic_sales = Column(Float, default=0.0)
    total_sales = Column(Float, default=0.0)

    asin_ref = relationship("Asin", back_populates="organic_records")

    __table_args__ = (
        Index("ix_organic_performance_timestamp_asin", "timestamp", "asin"),
    )


class Inventory(Base):
    __tablename__ = "inventory"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, nullable=False)
    asin = Column(String(10), ForeignKey("asin_master.asin"), nullable=False)
    quantity = Column(Integer, default=0)
    daily_sales_rate = Column(Float, default=0.0)
    days_of_supply = Column(Float, default=0.0)

    asin_ref = relationship("Asin", back_populates="inventory_records")

    __table_args__ = (
        Index("ix_inventory_timestamp_asin", "timestamp", "asin"),
    )
