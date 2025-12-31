"""Tests for the Mergington High School API"""

import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from app import app

client = TestClient(app)


class TestRoot:
    """Test root endpoint"""
    
    def test_root_redirect(self):
        """Test that root redirects to static index.html"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert response.headers["location"] == "/static/index.html"


class TestGetActivities:
    """Test get activities endpoint"""
    
    def test_get_activities(self):
        """Test getting all activities"""
        response = client.get("/activities")
        assert response.status_code == 200
        activities = response.json()
        
        # Check that we have activities
        assert isinstance(activities, dict)
        assert len(activities) > 0
        
        # Check that required activities exist
        assert "Chess Club" in activities
        assert "Programming Class" in activities
        assert "Gym Class" in activities
    
    def test_activity_structure(self):
        """Test that activities have the correct structure"""
        response = client.get("/activities")
        activities = response.json()
        
        for activity_name, activity_data in activities.items():
            assert "description" in activity_data
            assert "schedule" in activity_data
            assert "max_participants" in activity_data
            assert "participants" in activity_data
            assert isinstance(activity_data["participants"], list)


class TestSignup:
    """Test signup endpoint"""
    
    def test_signup_for_activity(self):
        """Test signing up for an activity"""
        response = client.post(
            "/activities/Chess Club/signup",
            params={"email": "newstudent@mergington.edu"}
        )
        assert response.status_code == 200
        result = response.json()
        assert "message" in result
        assert "signed up" in result["message"].lower()
    
    def test_signup_duplicate_email(self):
        """Test that duplicate signups are rejected"""
        # First signup
        client.post(
            "/activities/Chess Club/signup",
            params={"email": "duplicate@mergington.edu"}
        )
        
        # Try duplicate signup
        response = client.post(
            "/activities/Chess Club/signup",
            params={"email": "duplicate@mergington.edu"}
        )
        assert response.status_code == 400
        result = response.json()
        assert "already signed up" in result["detail"].lower()
    
    def test_signup_nonexistent_activity(self):
        """Test signing up for a non-existent activity"""
        response = client.post(
            "/activities/Nonexistent Activity/signup",
            params={"email": "test@mergington.edu"}
        )
        assert response.status_code == 404
        result = response.json()
        assert "not found" in result["detail"].lower()
    
    def test_signup_activity_full(self):
        """Test signing up when activity is full"""
        # Get an activity with limited spots
        activities = client.get("/activities").json()
        
        # Find an activity with few spots
        for activity_name, activity_data in activities.items():
            spots_available = activity_data["max_participants"] - len(activity_data["participants"])
            if spots_available == 1:
                # Fill the last spot
                response = client.post(
                    f"/activities/{activity_name}/signup",
                    params={"email": "fulltest@mergington.edu"}
                )
                assert response.status_code == 200
                
                # Try to signup when full
                response = client.post(
                    f"/activities/{activity_name}/signup",
                    params={"email": "another@mergington.edu"}
                )
                assert response.status_code == 400
                result = response.json()
                assert "full" in result["detail"].lower()
                break


class TestRemoveParticipant:
    """Test remove participant endpoint"""
    
    def test_remove_participant(self):
        """Test removing a participant from an activity"""
        # First add a participant
        client.post(
            "/activities/Tennis Club/signup",
            params={"email": "removetest@mergington.edu"}
        )
        
        # Then remove them
        response = client.post(
            "/activities/Tennis Club/remove",
            params={"email": "removetest@mergington.edu"}
        )
        assert response.status_code == 200
        result = response.json()
        assert "removed" in result["message"].lower()
    
    def test_remove_nonexistent_participant(self):
        """Test removing a participant who isn't signed up"""
        response = client.post(
            "/activities/Programming Class/remove",
            params={"email": "notregistered@mergington.edu"}
        )
        assert response.status_code == 400
        result = response.json()
        assert "not signed up" in result["detail"].lower()
    
    def test_remove_from_nonexistent_activity(self):
        """Test removing a participant from a non-existent activity"""
        response = client.post(
            "/activities/Nonexistent Activity/remove",
            params={"email": "test@mergington.edu"}
        )
        assert response.status_code == 404
        result = response.json()
        assert "not found" in result["detail"].lower()
    
    def test_remove_existing_participant(self):
        """Test removing an existing participant"""
        # Get current participants from an activity
        activities = client.get("/activities").json()
        activity_with_participants = None
        existing_email = None
        
        for activity_name, activity_data in activities.items():
            if len(activity_data["participants"]) > 0:
                activity_with_participants = activity_name
                existing_email = activity_data["participants"][0]
                break
        
        if activity_with_participants and existing_email:
            response = client.post(
                f"/activities/{activity_with_participants}/remove",
                params={"email": existing_email}
            )
            assert response.status_code == 200
            result = response.json()
            assert "removed" in result["message"].lower()


class TestIntegration:
    """Integration tests for the complete workflow"""
    
    def test_signup_and_remove_workflow(self):
        """Test complete workflow of signing up and removing"""
        test_email = "integration@mergington.edu"
        test_activity = "Art Studio"
        
        # Check initial state
        initial = client.get("/activities").json()
        initial_count = len(initial[test_activity]["participants"])
        
        # Sign up
        response = client.post(
            f"/activities/{test_activity}/signup",
            params={"email": test_email}
        )
        assert response.status_code == 200
        
        # Verify signup
        after_signup = client.get("/activities").json()
        assert len(after_signup[test_activity]["participants"]) == initial_count + 1
        assert test_email in after_signup[test_activity]["participants"]
        
        # Remove
        response = client.post(
            f"/activities/{test_activity}/remove",
            params={"email": test_email}
        )
        assert response.status_code == 200
        
        # Verify removal
        after_removal = client.get("/activities").json()
        assert len(after_removal[test_activity]["participants"]) == initial_count
        assert test_email not in after_removal[test_activity]["participants"]
