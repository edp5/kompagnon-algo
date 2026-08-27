# This file permits to model the DB schema.
# All DateTime columns use timezone=True, which maps to TIMESTAMP WITH TIME ZONE
# in PostgreSQL. PostgreSQL normalises stored values to UTC internally, making
# cross-timezone comparisons (e.g. in _time_score()) safe and unambiguous.
# NOTE: callers are responsible for providing timezone-aware datetime values.
# NOTE: existing PostgreSQL columns (timestamp without time zone) must be
#       migrated to timestamptz in production — this ORM change alone does not
#       alter the live schema.
import sqlalchemy as sa
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class CompanionJourney(Base):
    __tablename__ = 'companion_journeys'

    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    userId = sa.Column(sa.Integer, nullable=False)
    departureTime = sa.Column(sa.DateTime(timezone=True), nullable=False)
    arrivalTime = sa.Column(sa.DateTime(timezone=True), nullable=False)
    departureAddress = sa.Column(sa.Text, nullable=False)
    arrivalAddress = sa.Column(sa.Text, nullable=False)
    departureLon = sa.Column(sa.Numeric(11, 8), nullable=False)
    departureLat = sa.Column(sa.Numeric(10, 8), nullable=False)
    arrivalLon = sa.Column(sa.Numeric(11, 8), nullable=False)
    arrivalLat = sa.Column(sa.Numeric(10, 8), nullable=False)
    created_at = sa.Column(sa.DateTime(timezone=True))
    updated_at = sa.Column(sa.DateTime(timezone=True))

class PassengerJourney(Base):
    __tablename__ = 'passenger_journeys'

    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    userId = sa.Column(sa.Integer, nullable=False)
    departureTime = sa.Column(sa.DateTime(timezone=True), nullable=False)
    arrivalTime = sa.Column(sa.DateTime(timezone=True), nullable=False)
    departureAddress = sa.Column(sa.Text, nullable=False)
    arrivalAddress = sa.Column(sa.Text, nullable=False)
    departureLon = sa.Column(sa.Numeric(11, 8), nullable=False)
    departureLat = sa.Column(sa.Numeric(10, 8), nullable=False)
    arrivalLon = sa.Column(sa.Numeric(11, 8), nullable=False)
    arrivalLat = sa.Column(sa.Numeric(10, 8), nullable=False)
    created_at = sa.Column(sa.DateTime(timezone=True))
    updated_at = sa.Column(sa.DateTime(timezone=True))

class FoundJourney(Base):
    __tablename__ = 'found_journeys'

    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    companionJourneyId = sa.Column(sa.Integer, sa.ForeignKey('companion_journeys.id'), nullable=False)
    passengerJourneyId = sa.Column(sa.Integer, sa.ForeignKey('passenger_journeys.id'), nullable=False)
    companionStatus = sa.Column(sa.String(255), nullable=False, default="waiting")
    passengerStatus = sa.Column(sa.String(255), nullable=False, default="waiting")
    created_at = sa.Column(sa.DateTime(timezone=True))
    updated_at = sa.Column(sa.DateTime(timezone=True))

    __table_args__ = (
        sa.UniqueConstraint('companionJourneyId', 'passengerJourneyId', name='uq_found_journey_pair'),
    )
