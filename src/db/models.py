# This file permit to modelized the DB (schema).
import sqlalchemy as sa
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class CompanionJourney(Base):
    __tablename__ = 'companion_journeys'

    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    userId = sa.Column(sa.Integer, nullable=False)
    departureTime = sa.Column(sa.DateTime, nullable=False)
    arrivalTime = sa.Column(sa.DateTime, nullable=False)
    departureAddress = sa.Column(sa.Text, nullable=False)
    arrivalAddress = sa.Column(sa.Text, nullable=False)
    departureLon = sa.Column(sa.Numeric(11, 8), nullable=False)
    departureLat = sa.Column(sa.Numeric(10, 8), nullable=False)
    arrivalLon = sa.Column(sa.Numeric(11, 8), nullable=False)
    arrivalLat = sa.Column(sa.Numeric(10, 8), nullable=False)
    created_at = sa.Column(sa.DateTime)
    updated_at = sa.Column(sa.DateTime)

class PassengerJourney(Base):
    __tablename__ = 'passenger_journeys'

    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    userId = sa.Column(sa.Integer, nullable=False)
    departureTime = sa.Column(sa.DateTime, nullable=False)
    arrivalTime = sa.Column(sa.DateTime, nullable=False)
    departureAddress = sa.Column(sa.Text, nullable=False)
    arrivalAddress = sa.Column(sa.Text, nullable=False)
    departureLon = sa.Column(sa.Numeric(11, 8), nullable=False)
    departureLat = sa.Column(sa.Numeric(10, 8), nullable=False)
    arrivalLon = sa.Column(sa.Numeric(11, 8), nullable=False)
    arrivalLat = sa.Column(sa.Numeric(10, 8), nullable=False)
    created_at = sa.Column(sa.DateTime)
    updated_at = sa.Column(sa.DateTime)

class FoundJourney(Base):
    __tablename__ = 'found_journeys'

    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    companionJourneyId = sa.Column(sa.Integer, sa.ForeignKey('companion_journeys.id'), nullable=False)
    passengerJourneyId = sa.Column(sa.Integer, sa.ForeignKey('passenger_journeys.id'), nullable=False)
    status = sa.Column(sa.String, nullable=False, default="WAITING")
    created_at = sa.Column(sa.DateTime)
    updated_at = sa.Column(sa.DateTime)
