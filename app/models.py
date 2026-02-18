"""SQLAlchemy ORM models."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    String,
    Integer,
    Text,
    DateTime,
    Boolean,
    ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Session(Base):
    __tablename__ = "sessions"

    id = Column(String, primary_key=True, default=_uuid)
    join_code = Column(String(6), unique=True, nullable=False, index=True)
    status = Column(String, nullable=False, default="lobby")  # lobby / active / ended
    seed = Column(Integer, nullable=False)
    device_ps_json = Column(Text, nullable=False)  # JSON list of floats

    # Game settings
    device_count = Column(Integer, nullable=False, default=10)
    max_turns = Column(Integer, nullable=False, default=12)
    test_budget = Column(Integer, nullable=False, default=200)
    min_n = Column(Integer, nullable=False, default=5)
    max_n = Column(Integer, nullable=False, default=60)
    premium_scale = Column(Integer, nullable=False, default=120)
    confidence_fee_json = Column(Text, nullable=False)
    miss_penalty_json = Column(Text, nullable=False)
    require_prior_test = Column(Boolean, nullable=False, default=True)

    created_at = Column(DateTime, default=_utcnow)

    players = relationship("Player", back_populates="session", cascade="all, delete-orphan")
    events = relationship("Event", back_populates="session", cascade="all, delete-orphan")


class Player(Base):
    __tablename__ = "players"

    id = Column(String, primary_key=True, default=_uuid)
    session_id = Column(String, ForeignKey("sessions.id"), nullable=False)
    name = Column(String, nullable=False)
    rejoin_token = Column(String(32), nullable=False)  # secret token for reconnecting
    score = Column(Integer, nullable=False, default=0)
    turns_used = Column(Integer, nullable=False, default=0)
    budget_used = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=_utcnow)

    session = relationship("Session", back_populates="players")
    device_stats = relationship("DeviceStat", back_populates="player", cascade="all, delete-orphan")
    events = relationship("Event", back_populates="player")


class DeviceStat(Base):
    __tablename__ = "device_stats"

    id = Column(String, primary_key=True, default=_uuid)
    player_id = Column(String, ForeignKey("players.id"), nullable=False)
    device_id = Column(Integer, nullable=False)
    x_total = Column(Integer, nullable=False, default=0)
    n_total = Column(Integer, nullable=False, default=0)

    __table_args__ = (UniqueConstraint("player_id", "device_id", name="uq_player_device"),)

    player = relationship("Player", back_populates="device_stats")


class Event(Base):
    __tablename__ = "events"

    id = Column(String, primary_key=True, default=_uuid)
    session_id = Column(String, ForeignKey("sessions.id"), nullable=False)
    player_id = Column(String, ForeignKey("players.id"), nullable=True)
    ts = Column(DateTime, default=_utcnow)
    type = Column(String, nullable=False)  # TEST / SELL / SYSTEM
    payload_json = Column(Text, nullable=False, default="{}")
    delta_score = Column(Integer, nullable=False, default=0)

    session = relationship("Session", back_populates="events")
    player = relationship("Player", back_populates="events")
