import pytest
from src.algorithm.matcher import find_matches

def test_find_matches_exact_address():
    companions = [
        {
            "id": 1, 
            "departureAddress": "Paris", 
            "arrivalAddress": "Lyon"
        },
        {
            "id": 2, 
            "departureAddress": "Marseille", 
            "arrivalAddress": "Nice"
        },
    ]
    passengers = [
        {
            "id": 10, 
            "departureAddress": "Paris", 
            "arrivalAddress": "Lyon"
        },
    ]
    
    matches = find_matches(companions, passengers)
    assert len(matches) == 1
    assert matches[0]["passenger_journey_id"] == 10
    assert matches[0]["companion_journey_id"] == 1

def test_find_matches_no_match():
    companions = [
        {
            "id": 1, 
            "departureAddress": "Paris", 
            "arrivalAddress": "Lyon"
        },
    ]
    passengers = [
        {
            "id": 10, 
            "departureAddress": "Lille", 
            "arrivalAddress": "Paris"
        },
    ]
    
    matches = find_matches(companions, passengers)
    assert len(matches) == 0

def test_find_matches_multiple_matches():
    companions = [
        {"id": 1, "departureAddress": "A", "arrivalAddress": "B"},
        {"id": 2, "departureAddress": "A", "arrivalAddress": "B"},
    ]
    passengers = [
        {"id": 10, "departureAddress": "A", "arrivalAddress": "B"},
    ]
    
    matches = find_matches(companions, passengers)
    # The current logic will match the passenger with both companions, as it's 1-to-many
    assert len(matches) == 2
    assert matches[0]["companion_journey_id"] == 1
    assert matches[1]["companion_journey_id"] == 2
