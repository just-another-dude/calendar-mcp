"""
Unit tests for MCP utility functions.

Tests the parameter conversion functions that transform flat MCP parameters
to proper Pydantic models for calendar_actions.
"""

import pytest
import datetime

# Add the parent directory to the path to ensure imports work
import sys
import os

parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from src.mcp_utils import (
    parse_datetime_string,
    mcp_params_to_event_create_request,
    mcp_params_to_event_update_request,
    validate_mcp_create_params,
)
from src.models import EventCreateRequest, EventUpdateRequest, EventDateTime


class TestParseDatetimeString:
    """Test datetime string parsing functionality."""

    def test_parse_valid_iso_datetime(self):
        """Test parsing valid ISO datetime strings."""
        # Test basic ISO format
        dt_str = "2025-11-02T14:00:00"
        result = parse_datetime_string(dt_str)
        assert isinstance(result, datetime.datetime)
        assert result.year == 2025
        assert result.month == 11
        assert result.day == 2
        assert result.hour == 14
        assert result.minute == 0

    def test_parse_iso_datetime_with_timezone(self):
        """Test parsing ISO datetime with timezone."""
        dt_str = "2025-11-02T14:00:00+02:00"
        result = parse_datetime_string(dt_str)
        assert isinstance(result, datetime.datetime)
        assert result.year == 2025
        assert result.month == 11
        assert result.day == 2
        assert result.hour == 14

    def test_parse_iso_datetime_with_z_timezone(self):
        """Test parsing ISO datetime with Z timezone."""
        dt_str = "2025-11-02T14:00:00Z"
        result = parse_datetime_string(dt_str)
        assert isinstance(result, datetime.datetime)
        assert result.year == 2025

    def test_parse_invalid_datetime_format(self):
        """Test that invalid datetime formats raise ValueError."""
        with pytest.raises(ValueError, match="Invalid datetime format"):
            parse_datetime_string("invalid-datetime")

        with pytest.raises(ValueError, match="Invalid datetime format"):
            parse_datetime_string("2025-13-40T25:70:80")  # Invalid date/time values

        with pytest.raises(ValueError, match="Invalid datetime format"):
            parse_datetime_string("")  # Empty string


class TestMcpParamsToEventCreateRequest:
    """Test conversion from MCP parameters to EventCreateRequest."""

    def test_valid_create_request_minimal(self):
        """Test creating EventCreateRequest with minimal required parameters."""
        arguments = {
            "summary": "Team Meeting",
            "start_time": "2025-11-02T14:00:00",
            "end_time": "2025-11-02T15:00:00",
        }

        result = mcp_params_to_event_create_request(arguments)

        assert isinstance(result, EventCreateRequest)
        assert result.summary == "Team Meeting"
        assert isinstance(result.start, EventDateTime)
        assert isinstance(result.end, EventDateTime)
        assert result.start.dateTime.year == 2025
        assert result.start.dateTime.hour == 14
        assert result.end.dateTime.hour == 15
        assert result.description is None
        assert result.location is None
        assert result.attendees == []

    def test_valid_create_request_full(self):
        """Test creating EventCreateRequest with all optional parameters."""
        arguments = {
            "summary": "Team Meeting",
            "start_time": "2025-11-02T14:00:00",
            "end_time": "2025-11-02T15:00:00",
            "description": "Weekly team sync",
            "location": "Conference Room A",
            "attendee_emails": ["alice@example.com", "bob@example.com"],
        }

        result = mcp_params_to_event_create_request(arguments)

        assert isinstance(result, EventCreateRequest)
        assert result.summary == "Team Meeting"
        assert result.description == "Weekly team sync"
        assert result.location == "Conference Room A"
        assert result.attendees == ["alice@example.com", "bob@example.com"]

    def test_hebrew_summary(self):
        """Test creating EventCreateRequest with Hebrew title."""
        arguments = {
            "summary": 'פגישה עם ד"ר קליין',
            "start_time": "2025-11-02T14:00:00",
            "end_time": "2025-11-02T15:00:00",
        }

        result = mcp_params_to_event_create_request(arguments)

        assert isinstance(result, EventCreateRequest)
        assert result.summary == 'פגישה עם ד"ר קליין'

    def test_missing_required_fields(self):
        """Test that missing required fields raise ValueError."""
        # Missing summary
        with pytest.raises(ValueError, match="Missing required fields"):
            mcp_params_to_event_create_request(
                {"start_time": "2025-11-02T14:00:00", "end_time": "2025-11-02T15:00:00"}
            )

        # Missing start_time
        with pytest.raises(ValueError, match="Missing required fields"):
            mcp_params_to_event_create_request(
                {"summary": "Meeting", "end_time": "2025-11-02T15:00:00"}
            )

        # Missing end_time
        with pytest.raises(ValueError, match="Missing required fields"):
            mcp_params_to_event_create_request(
                {"summary": "Meeting", "start_time": "2025-11-02T14:00:00"}
            )

    def test_invalid_datetime_format(self):
        """Test that invalid datetime formats are handled."""
        arguments = {
            "summary": "Meeting",
            "start_time": "invalid-datetime",
            "end_time": "2025-11-02T15:00:00",
        }

        with pytest.raises(ValueError, match="Error creating EventCreateRequest"):
            mcp_params_to_event_create_request(arguments)

    def test_empty_attendee_emails(self):
        """Test that empty attendee_emails list is handled correctly."""
        arguments = {
            "summary": "Meeting",
            "start_time": "2025-11-02T14:00:00",
            "end_time": "2025-11-02T15:00:00",
            "attendee_emails": [],
        }

        result = mcp_params_to_event_create_request(arguments)
        assert result.attendees == []


class TestMcpParamsToEventUpdateRequest:
    """Test conversion from MCP parameters to EventUpdateRequest."""

    def test_update_request_summary_only(self):
        """Test updating only the summary."""
        arguments = {"summary": "Updated Meeting Title"}

        result = mcp_params_to_event_update_request(arguments)

        assert isinstance(result, EventUpdateRequest)
        assert result.summary == "Updated Meeting Title"
        assert result.start is None
        assert result.end is None
        assert result.description is None
        assert result.location is None

    def test_update_request_times_only(self):
        """Test updating only start and end times."""
        arguments = {
            "start_time": "2025-11-02T16:00:00",
            "end_time": "2025-11-02T17:00:00",
        }

        result = mcp_params_to_event_update_request(arguments)

        assert isinstance(result, EventUpdateRequest)
        assert result.summary is None
        assert isinstance(result.start, EventDateTime)
        assert isinstance(result.end, EventDateTime)
        assert result.start.dateTime.hour == 16
        assert result.end.dateTime.hour == 17

    def test_update_request_full(self):
        """Test updating all fields."""
        arguments = {
            "summary": "Updated Meeting",
            "start_time": "2025-11-02T16:00:00",
            "end_time": "2025-11-02T17:00:00",
            "description": "Updated description",
            "location": "New location",
        }

        result = mcp_params_to_event_update_request(arguments)

        assert isinstance(result, EventUpdateRequest)
        assert result.summary == "Updated Meeting"
        assert result.description == "Updated description"
        assert result.location == "New location"
        assert isinstance(result.start, EventDateTime)
        assert isinstance(result.end, EventDateTime)

    def test_update_request_empty(self):
        """Test creating update request with no parameters (valid for updates)."""
        arguments = {}

        result = mcp_params_to_event_update_request(arguments)

        assert isinstance(result, EventUpdateRequest)
        assert result.summary is None
        assert result.start is None
        assert result.end is None
        assert result.description is None
        assert result.location is None

    def test_update_request_invalid_datetime(self):
        """Test that invalid datetime formats are handled in updates."""
        arguments = {"start_time": "invalid-datetime"}

        with pytest.raises(ValueError, match="Error creating EventUpdateRequest"):
            mcp_params_to_event_update_request(arguments)


class TestValidateMcpCreateParams:
    """Test MCP parameter validation for event creation."""

    def test_valid_parameters(self):
        """Test that valid parameters return no errors."""
        arguments = {
            "summary": "Meeting",
            "start_time": "2025-11-02T14:00:00",
            "end_time": "2025-11-02T15:00:00",
        }

        errors = validate_mcp_create_params(arguments)
        assert errors == {}

    def test_missing_summary(self):
        """Test validation error for missing summary."""
        arguments = {
            "start_time": "2025-11-02T14:00:00",
            "end_time": "2025-11-02T15:00:00",
        }

        errors = validate_mcp_create_params(arguments)
        assert "summary" in errors
        assert "required" in errors["summary"]

    def test_empty_summary(self):
        """Test validation error for empty summary."""
        arguments = {
            "summary": "",
            "start_time": "2025-11-02T14:00:00",
            "end_time": "2025-11-02T15:00:00",
        }

        errors = validate_mcp_create_params(arguments)
        assert "summary" in errors

    def test_missing_start_time(self):
        """Test validation error for missing start_time."""
        arguments = {"summary": "Meeting", "end_time": "2025-11-02T15:00:00"}

        errors = validate_mcp_create_params(arguments)
        assert "start_time" in errors
        assert "required" in errors["start_time"]

    def test_missing_end_time(self):
        """Test validation error for missing end_time."""
        arguments = {"summary": "Meeting", "start_time": "2025-11-02T14:00:00"}

        errors = validate_mcp_create_params(arguments)
        assert "end_time" in errors
        assert "required" in errors["end_time"]

    def test_invalid_start_time_format(self):
        """Test validation error for invalid start_time format."""
        arguments = {
            "summary": "Meeting",
            "start_time": "invalid-datetime",
            "end_time": "2025-11-02T15:00:00",
        }

        errors = validate_mcp_create_params(arguments)
        assert "start_time" in errors
        assert "Invalid datetime format" in errors["start_time"]

    def test_invalid_end_time_format(self):
        """Test validation error for invalid end_time format."""
        arguments = {
            "summary": "Meeting",
            "start_time": "2025-11-02T14:00:00",
            "end_time": "invalid-datetime",
        }

        errors = validate_mcp_create_params(arguments)
        assert "end_time" in errors
        assert "Invalid datetime format" in errors["end_time"]

    def test_end_time_before_start_time(self):
        """Test validation error when end_time is before start_time."""
        arguments = {
            "summary": "Meeting",
            "start_time": "2025-11-02T15:00:00",
            "end_time": "2025-11-02T14:00:00",  # Before start_time
        }

        errors = validate_mcp_create_params(arguments)
        assert "end_time" in errors
        assert "must be after start time" in errors["end_time"]

    def test_end_time_equal_to_start_time(self):
        """Test validation error when end_time equals start_time."""
        arguments = {
            "summary": "Meeting",
            "start_time": "2025-11-02T14:00:00",
            "end_time": "2025-11-02T14:00:00",  # Same as start_time
        }

        errors = validate_mcp_create_params(arguments)
        assert "end_time" in errors
        assert "must be after start time" in errors["end_time"]

    def test_multiple_validation_errors(self):
        """Test that multiple validation errors are captured."""
        arguments = {
            "start_time": "invalid-start",
            "end_time": "invalid-end",
            # Missing summary
        }

        errors = validate_mcp_create_params(arguments)
        assert len(errors) >= 3  # summary, start_time, end_time
        assert "summary" in errors
        assert "start_time" in errors
        assert "end_time" in errors


# Integration tests with actual Pydantic models
class TestMcpUtilsIntegration:
    """Integration tests that verify the utilities work with actual Pydantic models."""

    def test_create_request_to_dict_conversion(self):
        """Test that created models can be converted to dict (for JSON serialization)."""
        arguments = {
            "summary": "Integration Test Meeting",
            "start_time": "2025-11-02T14:00:00",
            "end_time": "2025-11-02T15:00:00",
            "description": "Test description",
        }

        result = mcp_params_to_event_create_request(arguments)
        result_dict = result.model_dump()

        assert isinstance(result_dict, dict)
        assert result_dict["summary"] == "Integration Test Meeting"
        assert "start" in result_dict
        assert "end" in result_dict
        assert result_dict["description"] == "Test description"

    def test_update_request_partial_fields(self):
        """Test that update requests work with partial field updates."""
        arguments = {"description": "Updated description only"}

        result = mcp_params_to_event_update_request(arguments)
        result_dict = result.model_dump(exclude_none=True)

        # Should only contain the description field
        assert result_dict == {"description": "Updated description only"}

    def test_datetime_timezone_handling(self):
        """Test that timezone information is preserved."""
        arguments = {
            "summary": "Timezone Test",
            "start_time": "2025-11-02T14:00:00+02:00",
            "end_time": "2025-11-02T15:00:00+02:00",
        }

        result = mcp_params_to_event_create_request(arguments)

        # Verify timezone information is preserved
        assert result.start.dateTime.tzinfo is not None
        assert result.end.dateTime.tzinfo is not None


if __name__ == "__main__":
    pytest.main([__file__])
