"""
Utility functions for MCP (Model Context Protocol) parameter conversion.

This module provides helper functions to convert flat MCP parameters to
proper Pydantic models expected by calendar_actions.
"""

import datetime
from typing import Dict, Any
from dateutil import parser as dateutil_parser
from pydantic import ValidationError

from .models import EventCreateRequest, EventUpdateRequest, EventDateTime


def parse_datetime_string(datetime_str: str) -> datetime.datetime:
    """
    Parse an ISO datetime string to a datetime object.

    Args:
        datetime_str: ISO format datetime string (e.g., "2025-11-02T14:00:00")

    Returns:
        datetime.datetime object

    Raises:
        ValueError: If datetime string is invalid
    """
    try:
        return dateutil_parser.isoparse(datetime_str)
    except Exception as e:
        raise ValueError(f"Invalid datetime format '{datetime_str}': {e}") from e


def mcp_params_to_event_create_request(arguments: Dict[str, Any]) -> EventCreateRequest:
    """
    Convert MCP flat parameters to EventCreateRequest Pydantic model.

    Args:
        arguments: Dictionary with flat MCP parameters:
            - summary: Event title (required)
            - start_time: ISO datetime string (required)
            - end_time: ISO datetime string (required)
            - description: Event description (optional)
            - location: Event location (optional)
            - attendee_emails: List of email addresses (optional)

    Returns:
        EventCreateRequest: Properly structured Pydantic model

    Raises:
        ValueError: If required parameters are missing or invalid
        ValidationError: If Pydantic validation fails
    """
    # Validate required parameters
    required_fields = ["summary", "start_time", "end_time"]
    missing_fields = [field for field in required_fields if field not in arguments]
    if missing_fields:
        raise ValueError(f"Missing required fields: {missing_fields}")

    try:
        # Parse datetime strings to datetime objects
        start_dt = parse_datetime_string(arguments["start_time"])
        end_dt = parse_datetime_string(arguments["end_time"])

        # Create EventDateTime models
        start_event_dt = EventDateTime(dateTime=start_dt)
        end_event_dt = EventDateTime(dateTime=end_dt)

        # Create EventCreateRequest
        event_data = EventCreateRequest(
            summary=arguments["summary"],
            start=start_event_dt,
            end=end_event_dt,
            description=arguments.get("description"),
            location=arguments.get("location"),
            attendees=arguments.get("attendee_emails", []),
        )

        return event_data

    except ValidationError as e:
        raise ValueError(f"Pydantic validation error: {e}") from e
    except Exception as e:
        raise ValueError(f"Error creating EventCreateRequest: {e}") from e


def mcp_params_to_event_update_request(arguments: Dict[str, Any]) -> EventUpdateRequest:
    """
    Convert MCP flat parameters to EventUpdateRequest Pydantic model.

    Args:
        arguments: Dictionary with flat MCP parameters (all optional for updates):
            - summary: Event title (optional)
            - start_time: ISO datetime string (optional)
            - end_time: ISO datetime string (optional)
            - description: Event description (optional)
            - location: Event location (optional)

    Returns:
        EventUpdateRequest: Properly structured Pydantic model

    Raises:
        ValueError: If parameters are invalid
        ValidationError: If Pydantic validation fails
    """
    try:
        update_data = {}

        # Add summary if provided
        if "summary" in arguments:
            update_data["summary"] = arguments["summary"]

        # Parse and add start_time if provided
        if "start_time" in arguments:
            start_dt = parse_datetime_string(arguments["start_time"])
            update_data["start"] = EventDateTime(dateTime=start_dt)

        # Parse and add end_time if provided
        if "end_time" in arguments:
            end_dt = parse_datetime_string(arguments["end_time"])
            update_data["end"] = EventDateTime(dateTime=end_dt)

        # Add other optional fields
        if "description" in arguments:
            update_data["description"] = arguments["description"]
        if "location" in arguments:
            update_data["location"] = arguments["location"]

        # Create EventUpdateRequest
        event_update = EventUpdateRequest(**update_data)

        return event_update

    except ValidationError as e:
        raise ValueError(f"Pydantic validation error: {e}") from e
    except Exception as e:
        raise ValueError(f"Error creating EventUpdateRequest: {e}") from e


def validate_mcp_create_params(arguments: Dict[str, Any]) -> Dict[str, str]:
    """
    Validate MCP parameters for event creation and return error details.

    Args:
        arguments: Dictionary with MCP parameters

    Returns:
        Dictionary with validation errors (empty if valid)
    """
    errors = {}

    # Check required fields
    if "summary" not in arguments or not arguments["summary"]:
        errors["summary"] = "Event title (summary) is required"

    if "start_time" not in arguments:
        errors["start_time"] = "Start time is required"
    else:
        try:
            parse_datetime_string(arguments["start_time"])
        except ValueError as e:
            errors["start_time"] = str(e)

    if "end_time" not in arguments:
        errors["end_time"] = "End time is required"
    else:
        try:
            end_dt = parse_datetime_string(arguments["end_time"])
            if "start_time" in arguments:
                try:
                    start_dt = parse_datetime_string(arguments["start_time"])
                    if end_dt <= start_dt:
                        errors["end_time"] = "End time must be after start time"
                except ValueError:
                    pass  # start_time error already captured above
        except ValueError as e:
            errors["end_time"] = str(e)

    return errors
