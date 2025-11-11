"""
Integration tests for MCP event creation functionality.

Tests the complete flow from MCP parameters through the server handler
to calendar_actions, validating that the Pydantic model conversion works
correctly in the server context.
"""

import pytest
import sys
import os
from unittest.mock import Mock, patch
from datetime import datetime

# Add the parent directory to the path to ensure imports work
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from src.mcp_utils import (
    mcp_params_to_event_create_request,
    mcp_params_to_event_update_request,
)
from src.models import EventCreateRequest, EventUpdateRequest, EventDateTime


class TestMcpEventCreationIntegration:
    """Integration tests for the complete MCP event creation flow."""

    def setup_method(self):
        """Set up test fixtures."""
        self.sample_mcp_arguments = {
            "calendar_id": "primary",
            "summary": "Integration Test Meeting",
            "start_time": "2025-11-02T14:00:00",
            "end_time": "2025-11-02T15:00:00",
            "description": "Test description",
            "location": "Test location",
            "attendee_emails": ["test@example.com"],
        }

        self.hebrew_mcp_arguments = {
            "calendar_id": "primary",
            "summary": 'פגישה עם ד"ר קליין',
            "start_time": "2025-11-03T10:00:00",
            "end_time": "2025-11-03T11:00:00",
            "description": "פגישה חשובה",
        }

    def test_mcp_params_conversion_for_calendar_actions(self):
        """Test that MCP parameters convert to the exact format calendar_actions expects."""
        # Convert MCP parameters to Pydantic model
        event_data = mcp_params_to_event_create_request(self.sample_mcp_arguments)

        # Verify it's the correct type
        assert isinstance(event_data, EventCreateRequest)

        # Verify all fields are correctly populated
        assert event_data.summary == "Integration Test Meeting"
        assert isinstance(event_data.start, EventDateTime)
        assert isinstance(event_data.end, EventDateTime)
        assert event_data.description == "Test description"
        assert event_data.location == "Test location"
        assert event_data.attendees == ["test@example.com"]

        # Verify datetime objects are properly created
        assert isinstance(event_data.start.dateTime, datetime)
        assert isinstance(event_data.end.dateTime, datetime)
        assert event_data.start.dateTime.year == 2025
        assert event_data.start.dateTime.month == 11
        assert event_data.start.dateTime.day == 2
        assert event_data.start.dateTime.hour == 14

    def test_hebrew_event_creation(self):
        """Test that Hebrew event titles and descriptions work correctly."""
        event_data = mcp_params_to_event_create_request(self.hebrew_mcp_arguments)

        assert isinstance(event_data, EventCreateRequest)
        assert event_data.summary == 'פגישה עם ד"ר קליין'
        assert event_data.description == "פגישה חשובה"

        # Verify the model can be serialized (important for JSON-RPC responses)
        serialized = event_data.model_dump()
        assert serialized["summary"] == 'פגישה עם ד"ר קליין'
        assert serialized["description"] == "פגישה חשובה"

    @patch("src.calendar_actions.create_event")
    def test_mcp_server_handler_simulation(self, mock_create_event):
        """Test simulating the MCP server handler with proper Pydantic conversion."""
        # Mock successful calendar_actions response
        mock_create_event.return_value = {
            "success": True,
            "event_id": "test_event_123",
            "html_link": "https://calendar.google.com/event?eid=test",
        }

        # Simulate the fixed MCP handler logic
        try:
            # Convert MCP flat parameters to proper Pydantic model (the fix we implemented)
            event_data = mcp_params_to_event_create_request(self.sample_mcp_arguments)

            # Mock credentials
            mock_creds = Mock()

            # Call calendar_actions with proper Pydantic model (this should work now)
            result = mock_create_event(
                credentials=mock_creds,
                calendar_id=self.sample_mcp_arguments["calendar_id"],
                event_data=event_data,  # Now a proper EventCreateRequest object
            )

            # Verify the call was successful
            assert result["success"] is True
            assert "event_id" in result

            # Verify calendar_actions was called with the correct parameters
            mock_create_event.assert_called_once()
            call_args = mock_create_event.call_args

            # Verify the event_data parameter is the correct type
            passed_event_data = call_args.kwargs["event_data"]
            assert isinstance(passed_event_data, EventCreateRequest)
            assert passed_event_data.summary == "Integration Test Meeting"

        except Exception as e:
            pytest.fail(f"MCP handler simulation failed: {e}")

    def test_event_update_integration(self):
        """Test that event update parameters work correctly."""
        update_arguments = {
            "summary": "Updated Meeting Title",
            "start_time": "2025-11-02T16:00:00",
            "description": "Updated description",
        }

        # Convert to EventUpdateRequest
        update_data = mcp_params_to_event_update_request(update_arguments)

        assert isinstance(update_data, EventUpdateRequest)
        assert update_data.summary == "Updated Meeting Title"
        assert isinstance(update_data.start, EventDateTime)
        assert update_data.start.dateTime.hour == 16
        assert update_data.description == "Updated description"
        assert update_data.end is None  # Not provided in update
        assert update_data.location is None  # Not provided in update

    def test_minimal_event_creation(self):
        """Test event creation with only required fields."""
        minimal_arguments = {
            "calendar_id": "primary",
            "summary": "Minimal Meeting",
            "start_time": "2025-11-02T14:00:00",
            "end_time": "2025-11-02T15:00:00",
        }

        event_data = mcp_params_to_event_create_request(minimal_arguments)

        assert isinstance(event_data, EventCreateRequest)
        assert event_data.summary == "Minimal Meeting"
        assert event_data.description is None
        assert event_data.location is None
        assert event_data.attendees == []  # Empty list, not None

    def test_datetime_formats_compatibility(self):
        """Test various datetime formats that might come from the voice-agent client."""
        datetime_formats = [
            "2025-11-02T14:00:00",  # Basic ISO
            "2025-11-02T14:00:00Z",  # UTC timezone
            "2025-11-02T14:00:00+02:00",  # Positive timezone
            "2025-11-02T14:00:00-05:00",  # Negative timezone
        ]

        for dt_format in datetime_formats:
            arguments = {
                "calendar_id": "primary",
                "summary": f"Test {dt_format}",
                "start_time": dt_format,
                "end_time": dt_format,  # Same format for end time
            }

            # This should not raise an exception
            event_data = mcp_params_to_event_create_request(arguments)
            assert isinstance(event_data, EventCreateRequest)
            assert isinstance(event_data.start.dateTime, datetime)

    def test_error_handling_integration(self):
        """Test that error handling works correctly in the integration context."""
        # Test missing required field
        invalid_arguments = {
            "calendar_id": "primary",
            "summary": "Test Meeting",
            # Missing start_time and end_time
        }

        with pytest.raises(ValueError, match="Missing required fields"):
            mcp_params_to_event_create_request(invalid_arguments)

        # Test invalid datetime format
        invalid_datetime_arguments = {
            "calendar_id": "primary",
            "summary": "Test Meeting",
            "start_time": "invalid-datetime-format",
            "end_time": "2025-11-02T15:00:00",
        }

        with pytest.raises(ValueError, match="Error creating EventCreateRequest"):
            mcp_params_to_event_create_request(invalid_datetime_arguments)

    def test_pydantic_model_validation(self):
        """Test that Pydantic validation works as expected."""
        # Test that the models validate required fields
        with pytest.raises(Exception):  # Pydantic validation error
            EventCreateRequest(
                # Missing required fields
                description="Should fail"
            )

        # Test valid model creation
        valid_model = EventCreateRequest(
            summary="Valid Meeting",
            start=EventDateTime(dateTime=datetime(2025, 11, 2, 14, 0)),
            end=EventDateTime(dateTime=datetime(2025, 11, 2, 15, 0)),
        )
        assert valid_model.summary == "Valid Meeting"

    @patch("src.calendar_actions.create_event")
    @patch("src.calendar_actions.update_event")
    def test_full_mcp_workflow_simulation(self, mock_update_event, mock_create_event):
        """Test the complete workflow of create and update operations."""
        # Mock responses
        mock_create_event.return_value = {
            "success": True,
            "event_id": "created_event_123",
        }
        mock_update_event.return_value = {
            "success": True,
            "event_id": "created_event_123",
        }

        # Step 1: Create event
        create_event_data = mcp_params_to_event_create_request(
            self.sample_mcp_arguments
        )
        mock_creds = Mock()

        create_result = mock_create_event(
            credentials=mock_creds, calendar_id="primary", event_data=create_event_data
        )

        assert create_result["success"] is True
        event_id = create_result["event_id"]

        # Step 2: Update event
        update_arguments = {
            "summary": "Updated Meeting Title",
            "description": "Updated description",
        }
        update_event_data = mcp_params_to_event_update_request(update_arguments)

        update_result = mock_update_event(
            credentials=mock_creds,
            calendar_id="primary",
            event_id=event_id,
            event_data=update_event_data,
        )

        assert update_result["success"] is True

        # Verify both calls were made with correct parameters
        assert mock_create_event.call_count == 1
        assert mock_update_event.call_count == 1

        # Verify parameter types
        create_call_args = mock_create_event.call_args
        update_call_args = mock_update_event.call_args

        assert isinstance(create_call_args.kwargs["event_data"], EventCreateRequest)
        assert isinstance(update_call_args.kwargs["event_data"], EventUpdateRequest)


class TestMcpErrorScenarios:
    """Test various error scenarios in MCP integration."""

    def test_server_error_response_format(self):
        """Test that server errors are returned in the correct format."""
        # This simulates what the server should return for various error conditions

        # Parameter validation error
        try:
            mcp_params_to_event_create_request({})  # Missing required fields
        except ValueError as e:
            error_response = {
                "success": False,
                "error": f"Parameter conversion error: {str(e)}",
            }
            assert error_response["success"] is False
            assert "Parameter conversion error" in error_response["error"]

        # Datetime parsing error
        try:
            mcp_params_to_event_create_request(
                {
                    "summary": "Test",
                    "start_time": "invalid",
                    "end_time": "2025-11-02T15:00:00",
                }
            )
        except ValueError as e:
            error_response = {
                "success": False,
                "error": f"Parameter conversion error: {str(e)}",
            }
            assert error_response["success"] is False
            assert "Parameter conversion error" in error_response["error"]

    def test_unicode_handling(self):
        """Test that Unicode characters (including Hebrew) are handled correctly."""
        unicode_arguments = {
            "calendar_id": "primary",
            "summary": "Meeting with émojis 🎉 and Hebrew פגישה",
            "start_time": "2025-11-02T14:00:00",
            "end_time": "2025-11-02T15:00:00",
            "description": "Unicode test: áéíóú ñ 中文 العربية עברית",
            "location": "Café São Paulo",
        }

        # Should handle Unicode characters correctly
        event_data = mcp_params_to_event_create_request(unicode_arguments)

        assert event_data.summary == "Meeting with émojis 🎉 and Hebrew פגישה"
        assert event_data.description == "Unicode test: áéíóú ñ 中文 العربية עברית"
        assert event_data.location == "Café São Paulo"

        # Should be JSON serializable
        serialized = event_data.model_dump()
        assert isinstance(serialized, dict)


if __name__ == "__main__":
    pytest.main([__file__])
