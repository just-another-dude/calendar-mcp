import requests
import json
from typing import Optional, List, Dict, Any
from datetime import datetime
from mcp.server.fastmcp import FastMCP

# Base URL for the FastAPI server
BASE_URL = "http://127.0.0.1:8000"

def create_mcp_server():
    """Creates and configures the MCP server with tools that map to the FastAPI endpoints."""
    mcp = FastMCP("calendar-mcp")
    
    @mcp.tool()
    async def list_calendars(min_access_role: Optional[str] = None) -> str:
        """Lists the calendars on the user's calendar list.
        
        Args:
            min_access_role: Minimum access role ('reader', 'writer', 'owner').
        """
        params = {}
        if min_access_role:
            params["min_access_role"] = min_access_role
        
        response = requests.get(f"{BASE_URL}/calendars", params=params)
        if response.status_code != 200:
            return f"Error: {response.status_code} - {response.text}"
        return json.dumps(response.json(), indent=2)

    @mcp.tool()
    async def find_events(calendar_id: str, time_min: Optional[str] = None, 
                         time_max: Optional[str] = None, query: Optional[str] = None,
                         max_results: int = 50) -> str:
        """Find events in a specified calendar.
        
        Args:
            calendar_id: Calendar identifier (e.g., 'primary', email address, or calendar ID).
            time_min: Start time (inclusive, ISO format).
            time_max: End time (exclusive, ISO format).
            query: Free text search query.
            max_results: Maximum number of events to return (default 50).
        """
        params = {"max_results": max_results}
        if time_min:
            params["time_min"] = time_min
        if time_max:
            params["time_max"] = time_max
        if query:
            params["q"] = query
        
        response = requests.get(f"{BASE_URL}/calendars/{calendar_id}/events", params=params)
        if response.status_code != 200:
            return f"Error: {response.status_code} - {response.text}"
        return json.dumps(response.json(), indent=2)

    @mcp.tool()
    async def create_event(calendar_id: str, summary: str, start_time: str, 
                          end_time: str, description: Optional[str] = None,
                          location: Optional[str] = None, 
                          attendee_emails: Optional[List[str]] = None) -> str:
        """Creates a new event with detailed information.
        
        Args:
            calendar_id: Calendar identifier.
            summary: Title of the event.
            start_time: Start time in ISO format (YYYY-MM-DDTHH:MM:SS).
            end_time: End time in ISO format (YYYY-MM-DDTHH:MM:SS).
            description: Optional description for the event.
            location: Optional location for the event.
            attendee_emails: Optional list of attendee email addresses.
        """
        data = {
            "summary": summary,
            "start": {"dateTime": start_time},
            "end": {"dateTime": end_time}
        }
        
        if description:
            data["description"] = description
        if location:
            data["location"] = location
        if attendee_emails:
            data["attendees"] = attendee_emails
        
        response = requests.post(
            f"{BASE_URL}/calendars/{calendar_id}/events", 
            json=data
        )
        if response.status_code != 201:
            return f"Error: {response.status_code} - {response.text}"
        return json.dumps(response.json(), indent=2)
    
    @mcp.tool()
    async def quick_add_event(calendar_id: str, text: str) -> str:
        """Creates an event based on a simple text string using Google's natural language parser.
        
        Args:
            calendar_id: Calendar identifier.
            text: The text description of the event (e.g., "Meeting with John tomorrow at 2pm").
        """
        data = {"text": text}
        response = requests.post(
            f"{BASE_URL}/calendars/{calendar_id}/events/quickAdd", 
            json=data
        )
        if response.status_code != 201:
            return f"Error: {response.status_code} - {response.text}"
        return json.dumps(response.json(), indent=2)
    
    @mcp.tool()
    async def update_event(calendar_id: str, event_id: str, summary: Optional[str] = None, 
                          start_time: Optional[str] = None, end_time: Optional[str] = None,
                          description: Optional[str] = None, location: Optional[str] = None) -> str:
        """Updates an existing event.
        
        Args:
            calendar_id: Calendar identifier.
            event_id: Event identifier.
            summary: New title for the event.
            start_time: New start time in ISO format.
            end_time: New end time in ISO format.
            description: New description for the event.
            location: New location for the event.
        """
        data = {}
        if summary:
            data["summary"] = summary
        if start_time:
            data["start"] = {"dateTime": start_time}
        if end_time:
            data["end"] = {"dateTime": end_time}
        if description:
            data["description"] = description
        if location:
            data["location"] = location
        
        response = requests.patch(
            f"{BASE_URL}/calendars/{calendar_id}/events/{event_id}", 
            json=data
        )
        if response.status_code != 200:
            return f"Error: {response.status_code} - {response.text}"
        return json.dumps(response.json(), indent=2)
    
    @mcp.tool()
    async def delete_event(calendar_id: str, event_id: str) -> str:
        """Deletes an event.
        
        Args:
            calendar_id: Calendar identifier.
            event_id: Event identifier.
        """
        response = requests.delete(f"{BASE_URL}/calendars/{calendar_id}/events/{event_id}")
        if response.status_code != 204:
            return f"Error: {response.status_code} - {response.text}"
        return "Event successfully deleted."
    
    @mcp.tool()
    async def add_attendee(calendar_id: str, event_id: str, attendee_emails: List[str]) -> str:
        """Adds one or more attendees to an existing event.
        
        Args:
            calendar_id: Calendar identifier.
            event_id: Event identifier.
            attendee_emails: List of email addresses to add as attendees.
        """
        data = {"attendee_emails": attendee_emails}
        response = requests.post(
            f"{BASE_URL}/calendars/{calendar_id}/events/{event_id}/attendees", 
            json=data
        )
        if response.status_code != 200:
            return f"Error: {response.status_code} - {response.text}"
        return json.dumps(response.json(), indent=2)
    
    @mcp.tool()
    async def check_attendee_status(event_id: str, calendar_id: str = "primary", 
                                   attendee_emails: Optional[List[str]] = None) -> str:
        """Checks the response status for attendees of a specific event.
        
        Args:
            event_id: Event identifier.
            calendar_id: Calendar identifier (default: primary).
            attendee_emails: Optional list of specific attendees to check.
        """
        data = {
            "event_id": event_id,
            "calendar_id": calendar_id
        }
        if attendee_emails:
            data["attendee_emails"] = attendee_emails
        
        response = requests.post(f"{BASE_URL}/events/check_attendee_status", json=data)
        if response.status_code != 200:
            return f"Error: {response.status_code} - {response.text}"
        return json.dumps(response.json(), indent=2)
    
    @mcp.tool()
    async def query_free_busy(calendar_ids: List[str], time_min: str, time_max: str) -> str:
        """Queries the free/busy information for a list of calendars over a time period.
        
        Args:
            calendar_ids: List of calendar identifiers to query.
            time_min: Start of the time range (ISO format).
            time_max: End of the time range (ISO format).
        """
        data = {
            "time_min": time_min,
            "time_max": time_max,
            "items": [{"id": cal_id} for cal_id in calendar_ids]
        }
        response = requests.post(f"{BASE_URL}/freeBusy", json=data)
        if response.status_code != 200:
            return f"Error: {response.status_code} - {response.text}"
        return json.dumps(response.json(), indent=2)
    
    @mcp.tool()
    async def schedule_mutual(attendee_calendar_ids: List[str], time_min: str, 
                             time_max: str, duration_minutes: int, 
                             summary: str, description: Optional[str] = None) -> str:
        """Finds the first available time slot for multiple attendees and schedules an event.
        
        Args:
            attendee_calendar_ids: List of calendar IDs for attendees.
            time_min: Start of the search window (ISO format).
            time_max: End of the search window (ISO format).
            duration_minutes: Required duration of the event in minutes.
            summary: Title for the event.
            description: Optional description for the event.
        """
        data = {
            "attendee_calendar_ids": attendee_calendar_ids,
            "time_min": time_min,
            "time_max": time_max,
            "duration_minutes": duration_minutes,
            "event_details": {
                "summary": summary
            }
        }
        if description:
            data["event_details"]["description"] = description
        
        response = requests.post(f"{BASE_URL}/schedule_mutual", json=data)
        if response.status_code != 201:
            return f"Error: {response.status_code} - {response.text}"
        return json.dumps(response.json(), indent=2)
    
    @mcp.tool()
    async def analyze_busyness(time_min: str, time_max: str, calendar_id: str = "primary") -> str:
        """Analyzes event count and total duration per day within a specified time window.
        
        Args:
            time_min: Start of the analysis window (ISO format).
            time_max: End of the analysis window (ISO format).
            calendar_id: Calendar identifier (default: primary).
        """
        data = {
            "time_min": time_min,
            "time_max": time_max,
            "calendar_id": calendar_id
        }
        response = requests.post(f"{BASE_URL}/analyze_busyness", json=data)
        if response.status_code != 200:
            return f"Error: {response.status_code} - {response.text}"
        return json.dumps(response.json(), indent=2)
    
    @mcp.tool()
    async def create_calendar(summary: str) -> str:
        """Creates a new secondary calendar.
        
        Args:
            summary: The title for the new calendar.
        """
        data = {"summary": summary}
        response = requests.post(f"{BASE_URL}/calendars", json=data)
        if response.status_code != 201:
            return f"Error: {response.status_code} - {response.text}"
        return json.dumps(response.json(), indent=2)
    
    return mcp 