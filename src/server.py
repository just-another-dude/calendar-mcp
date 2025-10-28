import logging
import uvicorn
import sys
import os
from fastapi import FastAPI, HTTPException
from datetime import datetime, date, time
from typing import Optional, List, Dict, Any
import json
from dateutil import parser # Import dateutil parser

# Configure logging first to capture any startup errors
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add the parent directory to the path to ensure imports work in all environments
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)
    logger.info(f"Added {parent_dir} to Python path")

from fastapi import FastAPI, HTTPException, Body, Query, Path, Depends, Header
from fastapi.routing import APIRoute
from fastapi.openapi.utils import get_openapi
from pydantic import BaseModel, Field
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

# Import functions and models directly using absolute imports
try:
    # Use absolute imports for consistency
    from src.auth import get_credentials
    import src.calendar_actions as calendar_actions
    from src.models import (
        GoogleCalendarEvent,
        EventsResponse,
        EventCreateRequest,
        QuickAddEventRequest,
        EventUpdateRequest,
        AddAttendeeRequest,
        CalendarListResponse,
        CalendarListEntry,
        # New models for advanced actions
        CheckAttendeeStatusRequest, CheckAttendeeStatusResponse,
        FreeBusyRequest, FreeBusyResponse,
        ScheduleMutualRequest,
        ProjectRecurringRequest, ProjectRecurringResponse, ProjectedEventOccurrenceModel,
        AnalyzeBusynessRequest, AnalyzeBusynessResponse, DailyBusynessStats,
        # Specific models needed for freeBusy conversion
        CalendarBusyInfo, TimePeriod, FreeBusyError
    )
    from src.analysis import ProjectedEventOccurrence
    from src.webhook_utils import (
        webhook_validator,
        webhook_processor,
        subscription_manager,
        OpenAIWebhookForwarder
    )
    logger.info("Successfully imported modules")
except ImportError as e:
    logger.error(f"Could not import modules: {e}")
    # Continue to allow partial server functionality

app = FastAPI(
    title="Google Calendar MCP Server",
    description="MCP server for interacting with Google Calendar API.",
    version="0.1.0"
)

# --- Global State / Initialization ---
# Store credentials per user for multi-user support
# Format: {user_id: credentials}
user_credentials_cache: Dict[str, Credentials] = {}

@app.on_event("startup")
def startup_event():
    """Server startup - credentials will be loaded per user as needed."""
    logger.info("Google Calendar MCP Server starting up...")

    # Validate OAuth environment variables at startup
    required_oauth_vars = ['GOOGLE_CLIENT_ID', 'GOOGLE_CLIENT_SECRET']
    missing_vars = []

    for var in required_oauth_vars:
        value = os.getenv(var)
        if not value:
            missing_vars.append(var)
        else:
            logger.info(f"✅ {var}: Configured (length: {len(value)})")

    if missing_vars:
        logger.error(f"❌ Missing required OAuth environment variables: {', '.join(missing_vars)}")
        logger.error("🔧 Please configure these in your Railway dashboard or .env file")
        logger.warning("⚠️  Calendar operations requiring token refresh may fail")
    else:
        logger.info("✅ All required OAuth environment variables are configured")

    logger.info("Multi-user OAuth support enabled. Credentials will be loaded per user.")
    logger.info("Use 'X-User-ID' header to specify user identity in requests.")

# --- Dependency for Credentials ---
def get_user_credentials(user_id: str = Header(None, alias="X-User-ID")) -> Credentials:
    """Dependency to provide valid credentials for a specific user. Attempts refresh if invalid."""
    global user_credentials_cache

    # Use default user if no user_id provided (for backward compatibility)
    if not user_id:
        user_id = "default"
        logger.warning("No X-User-ID header provided, using 'default' user")

    # Check cache first
    if user_id in user_credentials_cache:
        cached_creds = user_credentials_cache[user_id]

        # Check if valid, try refreshing if expired or invalid
        if not cached_creds.valid:
            logger.info(f"Credentials for user '{user_id}' are invalid or expired. Attempting refresh...")
            try:
                cached_creds.refresh(Request())
                if cached_creds.valid:
                    logger.info(f"Credentials refreshed successfully for user '{user_id}'")
                    return cached_creds
                else:
                    logger.warning(f"Credential refresh succeeded but credentials still invalid for user '{user_id}'")
                    # Remove from cache and fall through to re-fetch
                    del user_credentials_cache[user_id]
            except Exception as e:
                logger.error(f"Failed to refresh credentials for user '{user_id}': {e}")
                # Remove from cache and fall through to re-fetch
                del user_credentials_cache[user_id]
        else:
            # Credentials are valid, return them
            return cached_creds

    # No cached credentials or refresh failed - fetch new ones
    logger.info(f"Fetching new credentials for user '{user_id}'")
    try:
        new_creds = get_credentials(user_id)
        if not new_creds or not new_creds.valid:
            raise HTTPException(
                status_code=401,
                detail=f"Unable to obtain valid Google API credentials for user '{user_id}'. Please complete OAuth flow."
            )

        # Cache the new credentials
        user_credentials_cache[user_id] = new_creds
        logger.info(f"Successfully obtained and cached credentials for user '{user_id}'")
        return new_creds

    except Exception as e:
        logger.error(f"Failed to fetch credentials for user '{user_id}': {e}", exc_info=True)
        raise HTTPException(
            status_code=401,
            detail=f"Google API credentials unavailable for user '{user_id}': {e}"
        )

# --- MCP Offerings Endpoint --- 

def clean_schema_refs(schema: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively replace $ref with the actual schema definition name."""
    if isinstance(schema, dict):
        if "$ref" in schema:
            ref_path = schema["$ref"]
            # Extract the schema name (e.g., '#/components/schemas/MyModel' -> 'MyModel')
            schema_name = ref_path.split('/')[-1]
            return {"type": "schema_ref", "schema_name": schema_name} # Replace ref with a marker
        return {k: clean_schema_refs(v) for k, v in schema.items()}
    elif isinstance(schema, list):
        return [clean_schema_refs(item) for item in schema]
    return schema

def map_openapi_type_to_mcp(openapi_type: str, format: Optional[str] = None) -> str:
    """Maps OpenAPI types to basic MCP types."""
    # Basic mapping, can be expanded
    if openapi_type == "string":
        if format == "date-time":
            return "datetime"
        elif format == "date":
            return "date"
        elif format == "email":
            return "email"
        # Add other string formats if needed
        return "string"
    elif openapi_type == "integer":
        return "integer"
    elif openapi_type == "number":
        return "number" # Or float?
    elif openapi_type == "boolean":
        return "boolean"
    elif openapi_type == "array":
        return "array"
    elif openapi_type == "object":
        return "object"
    return "any" # Default fallback

@app.get("/services/offerings", tags=["MCP"], operation_id="list_mcp_offerings")
def list_mcp_offerings():
    """MCP endpoint to list available tools (functions)."""
    offerings = []
    openapi_schema = app.openapi()
    schemas = openapi_schema.get("components", {}).get("schemas", {})

    for path, path_item in openapi_schema.get("paths", {}).items():
        # Skip MCP, docs, health endpoints
        if path.startswith("/services") or path in ["/docs", "/redoc", "/openapi.json", "/health"]:
            continue

        for method, operation in path_item.items():
            if method not in ["get", "post", "patch", "delete", "put"]:
                continue # Skip non-standard methods like parameters

            tool_id = operation.get("operationId") or f"{method}_{path.replace('/', '_').strip('_')}"
            summary = operation.get("summary", "No summary available")
            description = operation.get("description") or summary # Use summary if no description

            parameters = []

            # Process path and query parameters
            for param in operation.get("parameters", []):
                param_schema = param.get("schema", {})
                parameters.append({
                    "name": param.get("name"),
                    "description": param.get("description", ""),
                    "type": map_openapi_type_to_mcp(param_schema.get("type")),
                    "required": param.get("required", False)
                })

            # Process request body parameters
            request_body = operation.get("requestBody")
            if request_body:
                content = request_body.get("content", {})
                # Assume application/json
                json_content = content.get("application/json", {})
                body_schema_ref = json_content.get("schema", {}).get("$ref")
                if body_schema_ref:
                    schema_name = body_schema_ref.split('/')[-1]
                    body_schema = schemas.get(schema_name, {})
                    if body_schema.get("type") == "object" and "properties" in body_schema:
                        for prop_name, prop_details in body_schema.get("properties", {}).items():
                            is_required = prop_name in body_schema.get("required", [])
                            # Use alias if present, otherwise the property name
                            field_name = prop_details.get("alias", prop_name)
                            parameters.append({
                                "name": field_name,
                                "description": prop_details.get("description") or prop_details.get("title", ""),
                                "type": map_openapi_type_to_mcp(prop_details.get("type"), prop_details.get("format")),
                                "required": is_required
                                # TODO: Handle nested objects/arrays more thoroughly if needed
                            })
                    else:
                         # Handle cases where the body is not a direct object schema (e.g., simple type)
                         parameters.append({
                            "name": "request_body", # Generic name
                            "description": request_body.get("description", "Request body"),
                            "type": map_openapi_type_to_mcp(body_schema.get("type")), # Type of the schema itself
                            "required": request_body.get("required", True)
                        })


            # Note: This simple extraction might not capture all nuances of complex parameters.
            # Return type extraction could be added similarly by inspecting 'responses'.

            offerings.append({
                "offering_id": tool_id,  # Changed from tool_id to offering_id for MCP format
                "name": summary, # Often used as function name
                "description": description,
                "parameters": parameters
            })

    return {"offerings": offerings}

@app.get("/services/api_key", tags=["MCP"], operation_id="get_api_key")
def get_api_key():
    """MCP endpoint to get API key - not required but part of MCP protocol."""
    return {"api_key": "not-required"}

# --- Management Endpoint ---
@app.get("/health", tags=["Management"], operation_id="health_check")
def health_check():
    """Basic health check endpoint."""
    return {
        "status": "ok",
        "authentication": "multi_user_oauth_enabled",
        "server_version": "1.0.0",
        "mcp_protocol": "2024-11-05"
    }

@app.get("/token-status", tags=["Management"], operation_id="token_status")
def token_status():
    """Check production token status for OpenAI Platform integration."""
    try:
        from .token_manager import token_manager
        status = token_manager.get_token_status()

        return {
            "status": "ok",
            "token_manager": "enabled",
            "token_info": status,
            "server_version": "1.0.0"
        }
    except Exception as e:
        return {
            "status": "error",
            "token_manager": "disabled",
            "error": str(e),
            "message": "Token manager not available - using fallback authentication"
        }

# --- CalendarList Endpoints ---
@app.get(
    "/calendars",
    response_model=CalendarListResponse,
    tags=["Calendars"],
    summary="List Calendars",
    operation_id="list_calendars"
)
def list_calendars_endpoint(
    min_access_role: Optional[str] = Query(None, description="Minimum access role ('reader', 'writer', 'owner')."),
    creds: Credentials = Depends(get_user_credentials)
):
    """Lists the calendars on the user's calendar list."""
    logger.info(f"Endpoint 'list_calendars' called. Params: min_access_role='{min_access_role}'")
    result = calendar_actions.find_calendars(credentials=creds, min_access_role=min_access_role)
    if result is None:
        logger.error("Action 'find_calendars' returned None. Raising HTTPException.")
        raise HTTPException(status_code=500, detail="Failed to retrieve calendar list from Google API.")
    logger.info(f"Endpoint 'list_calendars' completed successfully. Returning {len(result.items)} calendars.")
    return result

class CreateCalendarRequest(BaseModel):
    summary: str

@app.post(
    "/calendars",
    response_model=CalendarListEntry,
    status_code=201, # Created
    tags=["Calendars"],
    summary="Create Calendar",
    operation_id="create_calendar"
)
def create_calendar_endpoint(
    request: CreateCalendarRequest,
    creds: Credentials = Depends(get_user_credentials)
):
    """Creates a new secondary calendar."""
    logger.info(f"Endpoint 'create_calendar' called. Summary: '{request.summary}'")
    result = calendar_actions.create_calendar(credentials=creds, summary=request.summary)
    if result is None:
        logger.error(f"Action 'create_calendar' for summary '{request.summary}' returned None. Raising HTTPException.")
        raise HTTPException(status_code=500, detail="Failed to create calendar via Google API.")
    logger.info(f"Endpoint 'create_calendar' completed. Calendar ID: {result.id}")
    return result

# --- Events Endpoints ---
@app.get(
    "/calendars/{calendar_id}/events",
    response_model=EventsResponse,
    tags=["Events"],
    summary="Find Events",
    operation_id="find_events"
)
def find_events_endpoint(
    calendar_id: str = Path(..., description="Calendar identifier (e.g., 'primary', email address, or calendar ID)."),
    time_min_str: Optional[str] = Query(None, alias="time_min", description="Start time (inclusive, RFC3339 format string)."),
    time_max_str: Optional[str] = Query(None, alias="time_max", description="End time (exclusive, RFC3339 format string)."),
    query: Optional[str] = Query(None, alias="q", description="Free text search query."),
    max_results: int = Query(50, ge=1, le=2500, description="Maximum results per page."),
    single_events: bool = Query(True, description="Expand recurring events."),
    order_by: str = Query('startTime', description="Order results by ('startTime' or 'updated')."),
    creds: Credentials = Depends(get_user_credentials)
):
    """Finds events in a specified calendar."""
    logger.info(f"Endpoint 'find_events' called for calendar '{calendar_id}'.")
    logger.debug(f"Raw Params: time_min_str='{time_min_str}', time_max_str='{time_max_str}', q='{query}', max_results={max_results}, single_events={single_events}, order_by='{order_by}'")

    # Manually parse time strings using dateutil.parser
    time_min_dt: Optional[datetime] = None
    time_max_dt: Optional[datetime] = None
    try:
        if time_min_str:
            time_min_dt = parser.isoparse(time_min_str)
        if time_max_str:
            time_max_dt = parser.isoparse(time_max_str)
    except ValueError as e:
        logger.error(f"Failed to parse time strings: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid time format provided: {e}")

    # Now call the action function with parsed datetime objects
    result = calendar_actions.find_events(
        credentials=creds,
        calendar_id=calendar_id,
        time_min=time_min_dt, # Pass parsed datetime
        time_max=time_max_dt, # Pass parsed datetime
        query=query,
        max_results=max_results,
        single_events=single_events,
        order_by=order_by
    )
    if result is None:
        # Distinguish between API error and just no events?
        # For now, assume None means API error.
        logger.error(f"Action 'find_events' for calendar '{calendar_id}' returned None. Raising HTTPException.")
        raise HTTPException(status_code=500, detail="Failed to retrieve events from Google API.")
    logger.info(f"Endpoint 'find_events' for calendar '{calendar_id}' completed. Found {len(result.items)} events.")
    return result

@app.post(
    "/calendars/{calendar_id}/events",
    response_model=GoogleCalendarEvent,
    status_code=201,
    tags=["Events"],
    summary="Create Detailed Event",
    operation_id="create_event"
)
def create_event_endpoint(
    event_data: EventCreateRequest,
    calendar_id: str = Path(..., description="Calendar identifier."),
    send_notifications: bool = Query(True, description="Send notifications to attendees."),
    creds: Credentials = Depends(get_user_credentials)
):
    """Creates a new event with detailed information."""
    logger.info(f"Endpoint 'create_event' called for calendar '{calendar_id}'. Summary: '{event_data.summary}'")
    logger.debug(f"Event data: {event_data.dict(exclude_unset=True)}")
    result = calendar_actions.create_event(
        credentials=creds,
        event_data=event_data,
        calendar_id=calendar_id,
        send_notifications=send_notifications
    )
    if result is None:
        logger.error(f"Action 'create_event' for calendar '{calendar_id}', summary '{event_data.summary}' returned None. Raising HTTPException.")
        raise HTTPException(status_code=500, detail="Failed to create event via Google API.")
    logger.info(f"Endpoint 'create_event' completed. Event ID: {result.id}")
    return result

@app.post(
    "/calendars/{calendar_id}/events/quickAdd",
    response_model=GoogleCalendarEvent,
    status_code=201,
    tags=["Events"],
    summary="Quick Add Event",
    operation_id="quick_add_event"
)
def quick_add_event_endpoint(
    request_data: QuickAddEventRequest,
    calendar_id: str = Path(..., description="Calendar identifier."),
    send_notifications: bool = Query(False, description="Send notifications to attendees."),
    creds: Credentials = Depends(get_user_credentials)
):
    """Creates an event from a simple text string."""
    logger.info(f"Endpoint 'quick_add_event' called for calendar '{calendar_id}'. Text: '{request_data.text}'")
    result = calendar_actions.quick_add_event(
        credentials=creds,
        text=request_data.text,
        calendar_id=calendar_id,
        send_notifications=send_notifications
    )
    if result is None:
        # Consider 400 if text was likely unparseable? Hard to know.
        logger.error(f"Action 'quick_add_event' for calendar '{calendar_id}', text '{request_data.text}' returned None. Raising HTTPException.")
        raise HTTPException(status_code=500, detail="Failed to quick-add event via Google API.")
    logger.info(f"Endpoint 'quick_add_event' completed. Event ID: {result.id}")
    return result

@app.patch(
    "/calendars/{calendar_id}/events/{event_id}",
    response_model=GoogleCalendarEvent,
    tags=["Events"],
    summary="Update Event (Patch)",
    operation_id="update_event"
)
def update_event_endpoint(
    update_data: EventUpdateRequest,
    calendar_id: str = Path(..., description="Calendar identifier."),
    event_id: str = Path(..., description="Event identifier."),
    send_notifications: bool = Query(True, description="Send notifications to attendees."),
    creds: Credentials = Depends(get_user_credentials)
):
    """Updates specified fields of an existing event."""
    logger.info(f"Endpoint 'update_event' called for event '{event_id}' in calendar '{calendar_id}'.")
    logger.debug(f"Update data: {update_data.dict(exclude_unset=True)}")
    result = calendar_actions.update_event(
        credentials=creds,
        event_id=event_id,
        update_data=update_data,
        calendar_id=calendar_id,
        send_notifications=send_notifications
    )
    if result is None:
        # update_event handles 404 logging, but we might want to return 404 here
        # Need a way for the action function to signal the error type
        # For now, assume 500 for any None return
        # Alternative: Raise custom exceptions from actions
        logger.error(f"Action 'update_event' for event '{event_id}' returned None. Raising HTTPException.")
        raise HTTPException(status_code=500, detail=f"Failed to update event '{event_id}'. Check server logs.")
    logger.info(f"Endpoint 'update_event' completed for event '{event_id}'.")
    return result

@app.delete(
    "/calendars/{calendar_id}/events/{event_id}",
    status_code=204, # No Content
    tags=["Events"],
    summary="Delete Event",
    operation_id="delete_event"
)
def delete_event_endpoint(
    calendar_id: str = Path(..., description="Calendar identifier."),
    event_id: str = Path(..., description="Event identifier."),
    send_notifications: bool = Query(True, description="Send notifications to attendees."),
    creds: Credentials = Depends(get_user_credentials)
):
    """Deletes an event."""
    logger.info(f"Endpoint 'delete_event' called for event '{event_id}' in calendar '{calendar_id}'.")
    success = calendar_actions.delete_event(
        credentials=creds,
        event_id=event_id,
        calendar_id=calendar_id,
        send_notifications=send_notifications
    )
    if not success:
        # delete_event handles 404 logging
        logger.error(f"Action 'delete_event' for event '{event_id}' returned False. Raising HTTPException.")
        raise HTTPException(status_code=500, detail=f"Failed to delete event '{event_id}'. It might not exist or an API error occurred.")
    # No body needed for 204 response
    logger.info(f"Endpoint 'delete_event' completed successfully for event '{event_id}'.")
    return None

@app.post(
    "/calendars/{calendar_id}/events/{event_id}/attendees",
    response_model=GoogleCalendarEvent,
    tags=["Events"],
    summary="Add Attendee(s)",
    operation_id="add_attendee"
)
def add_attendee_endpoint(
    request_data: AddAttendeeRequest,
    calendar_id: str = Path(..., description="Calendar identifier."),
    event_id: str = Path(..., description="Event identifier."),
    send_notifications: bool = Query(True, description="Send notifications to attendees."),
    creds: Credentials = Depends(get_user_credentials)
):
    """Adds one or more attendees to an existing event.
       Note: This retrieves the event, adds the new emails to the existing list, and patches the event.
    """
    logger.info(f"Endpoint 'add_attendee' called for event '{event_id}'. Attendees: {request_data.attendee_emails}")
    result = calendar_actions.add_attendee(
        credentials=creds,
        event_id=event_id,
        attendee_emails=request_data.attendee_emails,
        calendar_id=calendar_id,
        send_notifications=send_notifications
    )
    if result is None:
        logger.error(f"Action 'add_attendee' for event '{event_id}' returned None. Raising HTTPException.")
        raise HTTPException(status_code=500, detail=f"Failed to add attendees to event '{event_id}'. Check logs.")
    logger.info(f"Endpoint 'add_attendee' completed for event '{event_id}'.")
    return result

# --- Advanced Scheduling & Analysis Endpoints ---

@app.post(
    "/events/check_attendee_status",
    response_model=CheckAttendeeStatusResponse,
    tags=["Advanced Scheduling"],
    summary="Check Attendee Response Status",
    operation_id="check_attendee_status"
)
def check_attendee_status_endpoint(
    request: CheckAttendeeStatusRequest,
    creds: Credentials = Depends(get_user_credentials)
):
    """Checks the response status ('accepted', 'declined', etc.) for attendees of a specific event."""
    logger.info(f"Endpoint 'check_attendee_status' called for event '{request.event_id}'. Calendar: '{request.calendar_id}'. Attendees: {request.attendee_emails or 'All'}")
    status_dict = calendar_actions.check_attendee_status(
        credentials=creds,
        event_id=request.event_id,
        calendar_id=request.calendar_id,
        attendee_emails=request.attendee_emails
    )
    if status_dict is None:
        # Could be 404 if event not found, but action logs this.
        logger.error(f"Action 'check_attendee_status' for event '{request.event_id}' returned None. Raising HTTPException.")
        raise HTTPException(status_code=500, detail=f"Failed to check attendee status for event '{request.event_id}'. Event might not exist or API error.")
    logger.info(f"Endpoint 'check_attendee_status' completed for event '{request.event_id}'. Found status for {len(status_dict)} attendees.")
    return CheckAttendeeStatusResponse(status_map=status_dict)

@app.post(
    "/freeBusy",
    response_model=FreeBusyResponse,
    tags=["Advanced Scheduling"],
    summary="Query Free/Busy Information",
    operation_id="query_free_busy"
)
def query_free_busy_endpoint(
    request: FreeBusyRequest,
    creds: Credentials = Depends(get_user_credentials)
):
    """Queries the free/busy information for a list of calendars over a time period."""
    calendar_ids = [item.id for item in request.items]
    logger.info(f"Endpoint 'query_free_busy' called. Calendars: {calendar_ids}")
    logger.debug(f"Time range: {request.time_min} to {request.time_max}")

    # Call the action function (which now returns the complex dict)
    busy_info_dict = calendar_actions.find_availability(
        credentials=creds,
        time_min=request.time_min,
        time_max=request.time_max,
        calendar_ids=calendar_ids
    )

    if busy_info_dict is None:
        logger.error("Action 'find_availability' returned None. Raising HTTPException.")
        raise HTTPException(status_code=500, detail="Failed to query free/busy information via Google API.")

    # Convert the result from find_availability back into the FreeBusyResponse model structure
    response_calendars: Dict[str, CalendarBusyInfo] = {}
    for cal_id, data in busy_info_dict.items():
        response_calendars[cal_id] = CalendarBusyInfo(
            busy=[TimePeriod(start=p['start'], end=p['end']) for p in data.get('busy', [])],
            errors=[FreeBusyError(**err) for err in data.get('errors', [])] # Assuming error dict matches model
        )

    # Construct the final response model
    # Note: Google API requires timeMin/timeMax in the request but also returns them in the response
    return FreeBusyResponse(
        time_min=request.time_min, # Echo request params as per Google API response structure
        time_max=request.time_max,
        calendars=response_calendars
    )

@app.post(
    "/schedule_mutual",
    response_model=GoogleCalendarEvent,
    status_code=201, # Successfully created
    tags=["Advanced Scheduling"],
    summary="Find Mutual Availability and Schedule",
    operation_id="schedule_mutual"
)
def schedule_mutual_endpoint(
    request: ScheduleMutualRequest,
    creds: Credentials = Depends(get_user_credentials)
):
    """Finds the first available time slot for multiple attendees and schedules the provided event details."""
    logger.info(f"Endpoint 'schedule_mutual' called. Attendees: {request.attendee_calendar_ids}. Duration: {request.duration_minutes} mins.")
    logger.debug(f"Time range: {request.time_min} to {request.time_max}. Organizer: {request.organizer_calendar_id}. Event Summary: {request.event_details.summary}")
    # Parse working hours strings into time objects
    working_hours_start = None
    working_hours_end = None
    try:
        if request.working_hours_start_str:
            working_hours_start = datetime.strptime(request.working_hours_start_str, '%H:%M').time()
        if request.working_hours_end_str:
            working_hours_end = datetime.strptime(request.working_hours_end_str, '%H:%M').time()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid working hours format. Use HH:MM.")

    created_event = calendar_actions.find_mutual_availability_and_schedule(
        credentials=creds,
        attendee_calendar_ids=request.attendee_calendar_ids,
        time_min=request.time_min,
        time_max=request.time_max,
        duration_minutes=request.duration_minutes,
        event_details=request.event_details,
        organizer_calendar_id=request.organizer_calendar_id,
        working_hours_start=working_hours_start,
        working_hours_end=working_hours_end,
        send_notifications=request.send_notifications
    )

    if created_event is None:
        # Could be no slot found, or failed to create event after finding slot.
        # Action function logs the reason.
        logger.error("Action 'find_mutual_availability_and_schedule' returned None. Raising HTTPException.")
        raise HTTPException(status_code=409, detail="Could not schedule event. No suitable time slot found or event creation failed.") # 409 Conflict maybe?
    logger.info(f"Endpoint 'schedule_mutual' completed successfully. Event ID: {created_event.id}")
    return created_event

@app.post(
    "/project_recurring",
    response_model=ProjectRecurringResponse,
    tags=["Analysis"],
    summary="Project Recurring Event Occurrences",
    operation_id="project_recurring"
)
def project_recurring_endpoint(
    request: ProjectRecurringRequest,
    creds: Credentials = Depends(get_user_credentials)
):
    """Finds recurring events and projects their future occurrences within a time window."""
    logger.info(f"Endpoint 'project_recurring' called. Calendar: '{request.calendar_id}'. Query: '{request.event_query}'")
    logger.debug(f"Time range: {request.time_min} to {request.time_max}")
    # Note: calendar_actions.get_projected_recurring_events returns List[ProjectedEventOccurrence]
    # We need to convert this to List[ProjectedEventOccurrenceModel] for the response.
    occurrences: List[ProjectedEventOccurrence] = calendar_actions.get_projected_recurring_events(
        credentials=creds,
        time_min=request.time_min,
        time_max=request.time_max,
        calendar_id=request.calendar_id,
        event_query=request.event_query
    )

    # Convert ProjectedEventOccurrence (from analysis) to ProjectedEventOccurrenceModel (from models)
    response_occurrences = [
        ProjectedEventOccurrenceModel(**occ.__dict__) for occ in occurrences
    ]

    logger.info(f"Endpoint 'project_recurring' completed. Found {len(response_occurrences)} projected occurrences.")
    return ProjectRecurringResponse(projected_occurrences=response_occurrences)

@app.post(
    "/analyze_busyness",
    response_model=AnalyzeBusynessResponse,
    tags=["Analysis"],
    summary="Analyze Daily Event Count and Duration",
    operation_id="analyze_busyness"
)
def analyze_busyness_endpoint(
    request: AnalyzeBusynessRequest,
    creds: Credentials = Depends(get_user_credentials)
):
    """Analyzes event count and total duration per day within a specified time window."""
    logger.info(f"Endpoint 'analyze_busyness' called. Calendar: '{request.calendar_id}'")
    logger.debug(f"Time range: {request.time_min} to {request.time_max}")
    # We need a wrapper in calendar_actions for analyze_busyness from analysis.py
    # Let's add one now.
    busyness_dict = calendar_actions.get_busyness_analysis( # Call the wrapper function
        credentials=creds,
        time_min=request.time_min,
        time_max=request.time_max,
        calendar_id=request.calendar_id
    )

    if busyness_dict is None: # Wrapper returns None on error
         logger.error("Action 'get_busyness_analysis' returned None. Raising HTTPException.")
         raise HTTPException(status_code=500, detail="Failed to analyze busyness.")

    # Convert date keys to strings (YYYY-MM-DD) for JSON compatibility
    response_data = {
        dt.strftime('%Y-%m-%d'): DailyBusynessStats(**stats)
        for dt, stats in busyness_dict.items()
    }

    return AnalyzeBusynessResponse(busyness_by_date=response_data)

# --- Webhook Endpoints for Real-time Notifications ---

@app.post(
    "/webhooks/calendar/notifications",
    tags=["Webhooks"],
    summary="Receive Google Calendar Push Notifications",
    operation_id="receive_calendar_webhook"
)
def receive_calendar_webhook(
    request: dict = Body(...),
    x_goog_channel_id: str = Header(None, alias="X-Goog-Channel-ID"),
    x_goog_channel_token: str = Header(None, alias="X-Goog-Channel-Token"),
    x_goog_resource_id: str = Header(None, alias="X-Goog-Resource-ID"),
    x_goog_resource_state: str = Header(None, alias="X-Goog-Resource-State"),
    x_goog_resource_uri: str = Header(None, alias="X-Goog-Resource-URI"),
    x_goog_message_number: str = Header(None, alias="X-Goog-Message-Number")
):
    """
    Receives webhook notifications from Google Calendar when events change.
    This endpoint processes real-time updates for calendar events with validation and processing.
    """
    logger.info(f"Received Google Calendar webhook notification")

    # Validate webhook headers
    headers = {
        'X-Goog-Channel-ID': x_goog_channel_id,
        'X-Goog-Channel-Token': x_goog_channel_token,
        'X-Goog-Resource-ID': x_goog_resource_id,
        'X-Goog-Resource-State': x_goog_resource_state,
        'X-Goog-Resource-URI': x_goog_resource_uri,
        'X-Goog-Message-Number': x_goog_message_number
    }

    # Validate webhook
    if not webhook_validator.validate_google_webhook(headers, json.dumps(request)):
        logger.warning("Webhook validation failed")
        raise HTTPException(status_code=401, detail="Webhook validation failed")

    # Process the webhook notification
    webhook_data = {
        "channel_id": x_goog_channel_id,
        "channel_token": x_goog_channel_token,
        "resource_id": x_goog_resource_id,
        "resource_state": x_goog_resource_state,
        "resource_uri": x_goog_resource_uri,
        "message_number": x_goog_message_number,
        "body": request,
        "received_at": datetime.utcnow().isoformat()
    }

    # Process webhook with business logic
    processing_result = webhook_processor.process_google_calendar_webhook(webhook_data)

    logger.info(f"Webhook processed: {processing_result}")

    return {
        "status": "received",
        "message": "Webhook processed successfully",
        "processing_result": processing_result
    }

@app.post(
    "/webhooks/calendar/setup",
    tags=["Webhooks"],
    summary="Setup Google Calendar Push Notifications",
    operation_id="setup_calendar_webhook"
)
def setup_calendar_webhook(
    calendar_id: str = Body(..., description="Calendar ID to watch"),
    webhook_url: str = Body(..., description="Webhook URL to receive notifications"),
    channel_id: str = Body(None, description="Optional channel ID"),
    channel_token: str = Body(None, description="Optional channel token for verification"),
    creds: Credentials = Depends(get_user_credentials)
):
    """
    Sets up Google Calendar push notifications for a specific calendar.
    This creates a webhook subscription that will send real-time updates.
    """
    try:
        # Import here to avoid circular imports
        from googleapiclient.discovery import build

        service = build('calendar', 'v3', credentials=creds)

        # Generate channel ID if not provided
        import uuid
        if not channel_id:
            channel_id = str(uuid.uuid4())

        # Setup the watch request
        watch_request = {
            'id': channel_id,
            'type': 'web_hook',
            'address': webhook_url,
        }

        if channel_token:
            watch_request['token'] = channel_token

        # Execute the watch request
        response = service.events().watch(
            calendarId=calendar_id,
            body=watch_request
        ).execute()

        logger.info(f"Successfully setup webhook for calendar {calendar_id}")
        logger.info(f"Channel ID: {response.get('id')}")
        logger.info(f"Resource ID: {response.get('resourceId')}")

        # Store subscription in manager
        subscription_data = {
            "calendar_id": calendar_id,
            "channel_id": response.get('id'),
            "resource_id": response.get('resourceId'),
            "webhook_url": webhook_url,
            "expiration": response.get('expiration'),
            "channel_token": channel_token
        }
        subscription_manager.store_subscription(response.get('id'), subscription_data)

        return {
            "status": "success",
            "channel_id": response.get('id'),
            "resource_id": response.get('resourceId'),
            "expiration": response.get('expiration'),
            "webhook_url": webhook_url
        }

    except Exception as e:
        logger.error(f"Failed to setup webhook for calendar {calendar_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to setup webhook: {e}"
        )

@app.post(
    "/webhooks/calendar/stop",
    tags=["Webhooks"],
    summary="Stop Google Calendar Push Notifications",
    operation_id="stop_calendar_webhook"
)
def stop_calendar_webhook(
    channel_id: str = Body(..., description="Channel ID to stop"),
    resource_id: str = Body(..., description="Resource ID to stop"),
    creds: Credentials = Depends(get_user_credentials)
):
    """
    Stops Google Calendar push notifications for a specific channel.
    This removes the webhook subscription.
    """
    try:
        from googleapiclient.discovery import build

        service = build('calendar', 'v3', credentials=creds)

        # Setup the stop request
        stop_request = {
            'id': channel_id,
            'resourceId': resource_id
        }

        # Execute the stop request
        service.channels().stop(body=stop_request).execute()

        # Remove subscription from manager
        subscription_manager.remove_subscription(channel_id)

        logger.info(f"Successfully stopped webhook channel {channel_id}")

        return {
            "status": "success",
            "message": f"Webhook channel {channel_id} stopped successfully"
        }

    except Exception as e:
        logger.error(f"Failed to stop webhook channel {channel_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to stop webhook: {e}"
        )

@app.get(
    "/webhooks/calendar/subscriptions",
    tags=["Webhooks"],
    summary="List Active Webhook Subscriptions",
    operation_id="list_webhook_subscriptions"
)
def list_webhook_subscriptions():
    """
    Lists all active webhook subscriptions for monitoring and management.
    """
    try:
        subscriptions = subscription_manager.list_active_subscriptions()
        return {
            "status": "success",
            "subscriptions": subscriptions,
            "count": len(subscriptions)
        }
    except Exception as e:
        logger.error(f"Failed to list webhook subscriptions: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list subscriptions: {e}"
        )

@app.post(
    "/webhooks/forward/openai",
    tags=["Webhooks"],
    summary="Forward Webhook to OpenAI Platform",
    operation_id="forward_webhook_openai"
)
def forward_webhook_to_openai(
    webhook_data: dict = Body(..., description="Webhook data to forward"),
    openai_endpoint: str = Body(..., description="OpenAI endpoint URL"),
    openai_api_key: str = Body(None, description="OpenAI API key (optional)")
):
    """
    Forwards webhook notifications to the OpenAI Platform for voice agent processing.
    This enables real-time calendar updates in your voice agent.
    """
    try:
        # Use the webhook forwarder utility
        forwarder = OpenAIWebhookForwarder(openai_endpoint, openai_api_key)
        result = forwarder.forward_webhook(webhook_data)

        if result["status"] == "success":
            logger.info(f"Successfully forwarded webhook to OpenAI: {openai_endpoint}")
            return {
                "status": "success",
                "message": "Webhook forwarded to OpenAI successfully",
                "openai_response_status": result.get("openai_response_status"),
                "attempt": result.get("attempt")
            }
        else:
            logger.error(f"Failed to forward webhook: {result}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to forward webhook: {result.get('error')}"
            )

    except Exception as e:
        logger.error(f"Failed to forward webhook to OpenAI: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to forward webhook to OpenAI: {e}"
        )

# --- HTTP/SSE MCP Transport for OpenAI Integration ---

@app.get(
    "/mcp",
    tags=["MCP"],
    summary="MCP Server-Sent Events Endpoint",
    operation_id="mcp_sse_transport"
)
async def mcp_sse_transport(
    authorization: str = Header(None, alias="Authorization"),
    user_id: str = Header(None, alias="X-User-ID")
):
    """
    MCP Server-Sent Events transport endpoint for OpenAI integration.
    Handles MCP protocol over HTTP/SSE as required by OpenAI Responses API.
    """
    from fastapi.responses import StreamingResponse

    async def mcp_stream():
        # SSE connection for MCP protocol
        yield "data: {\"jsonrpc\": \"2.0\", \"method\": \"initialize\", \"params\": {\"protocolVersion\": \"2024-11-05\", \"capabilities\": {\"tools\": {}}}}\n\n"

    return StreamingResponse(mcp_stream(), media_type="text/plain")

@app.post(
    "/mcp",
    tags=["MCP"],
    summary="MCP HTTP Transport Endpoint",
    operation_id="mcp_http_transport"
)
async def mcp_http_transport(
    request: dict = Body(...),
    authorization: str = Header(None, alias="Authorization"),
    user_id: str = Header(None, alias="X-User-ID")
):
    """
    MCP HTTP transport endpoint for OpenAI integration.
    Handles MCP protocol messages over HTTP as required by OpenAI Responses API.
    """
    try:
        # Extract user credentials from OAuth token with production token management
        creds = None
        if authorization:
            # Remove "Bearer " prefix if present
            access_token = authorization.replace("Bearer ", "") if authorization.startswith("Bearer ") else authorization

            # Use production token manager for automatic refresh
            try:
                from .token_manager import get_production_credentials

                # Get credentials with automatic refresh capability
                creds = get_production_credentials(access_token)

                if not creds or not creds.valid:
                    logger.warning("OAuth token validation failed or token refresh failed")
                    return {
                        "jsonrpc": "2.0",
                        "error": {
                            "code": -32001,
                            "message": "Authentication failed - invalid or expired OAuth token. Token may need manual refresh."
                        },
                        "id": request.get("id")
                    }

                logger.info("Successfully authenticated with OAuth token for MCP request (production mode)")

            except Exception as e:
                logger.error(f"Production OAuth token processing error: {e}")

                # Fallback to complete token handling with environment variables
                try:
                    from google.oauth2.credentials import Credentials
                    from google.auth.transport.requests import Request
                    logger.info("Falling back to environment-based token authentication")

                    # Get OAuth credentials from environment variables
                    client_id = os.getenv('GOOGLE_CLIENT_ID')
                    client_secret = os.getenv('GOOGLE_CLIENT_SECRET')

                    if not client_id or not client_secret:
                        logger.error("Missing required OAuth environment variables: GOOGLE_CLIENT_ID and/or GOOGLE_CLIENT_SECRET")
                        raise Exception("OAuth environment variables not configured")

                    # Create complete credentials object with all required fields for refresh
                    creds = Credentials(
                        token=access_token,
                        refresh_token=None,  # Will be None for fresh tokens, but field is present
                        token_uri="https://oauth2.googleapis.com/token",
                        client_id=client_id,
                        client_secret=client_secret,
                        scopes=['https://www.googleapis.com/auth/calendar']
                    )

                    logger.info("Created complete credentials with OAuth environment variables")

                    # Validate token by making a test API call
                    try:
                        # Simple validation - try to refresh or validate the token
                        if not access_token or len(access_token) < 20 or not access_token.startswith('ya29.'):
                            logger.warning(f"Invalid token format: {access_token[:20]}...")
                            creds = None
                        else:
                            # Test the token by actually calling Google's API
                            from googleapiclient.discovery import build
                            service = build('calendar', 'v3', credentials=creds)

                            # Make a minimal API call to validate the token
                            try:
                                # Try to get the user's calendar list - minimal API call
                                calendar_list = service.calendarList().list(maxResults=1).execute()
                                logger.info("Token validation successful - API call succeeded")
                            except Exception as api_error:
                                logger.warning(f"Token validation failed - API call failed: {api_error}")
                                creds = None

                    except Exception as token_test_error:
                        logger.warning(f"Token validation failed: {token_test_error}")
                        creds = None

                    # Basic validation without refresh
                    if not creds or not creds.valid:
                        logger.warning("Basic OAuth token validation failed")
                        return {
                            "jsonrpc": "2.0",
                            "error": {
                                "code": -32001,
                                "message": "Authentication failed - invalid OAuth token (basic mode)"
                            },
                            "id": request.get("id")
                        }

                    logger.info("Successfully authenticated with basic OAuth token")

                except Exception as fallback_error:
                    logger.error(f"Fallback OAuth token processing also failed: {fallback_error}")
                    return {
                        "jsonrpc": "2.0",
                        "error": {
                            "code": -32001,
                            "message": f"Authentication failed - OAuth token error: {str(e)}"
                        },
                        "id": request.get("id")
                    }

        # Require authentication for all MCP operations
        if not authorization:
            logger.warning("MCP request without authorization header")
            return {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32001,
                    "message": "Authentication required - missing Authorization header"
                },
                "id": request.get("id")
            }

        if not creds or not creds.valid:
            logger.warning("MCP request with invalid or missing credentials")
            return {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32001,
                    "message": "Authentication failed - invalid or expired OAuth token"
                },
                "id": request.get("id")
            }

        # Handle MCP protocol messages (all require valid authentication)
        method = request.get("method")
        params = request.get("params", {})
        request_id = request.get("id")

        if method == "initialize":
            return handle_mcp_initialize(request_id)
        elif method == "tools/list":
            return handle_mcp_tools_list(request_id)
        elif method == "tools/call":
            return await handle_mcp_tool_call(request_id, params, creds)
        else:
            return {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32601,
                    "message": f"Method not found: {method}"
                },
                "id": request_id
            }

    except Exception as e:
        logger.error(f"MCP HTTP transport error: {e}", exc_info=True)
        return {
            "jsonrpc": "2.0",
            "error": {
                "code": -32603,
                "message": f"Internal error: {str(e)}"
            },
            "id": request.get("id")
        }

def handle_mcp_initialize(request_id):
    """Handle MCP initialize request."""
    return {
        "jsonrpc": "2.0",
        "result": {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {}
            },
            "serverInfo": {
                "name": "google-calendar-mcp",
                "version": "1.0.0"
            }
        },
        "id": request_id
    }

def handle_mcp_tools_list(request_id):
    """Handle MCP tools/list request - returns available calendar tools."""
    tools = [
        {
            "name": "list_calendars",
            "description": "Lists the calendars on the user's calendar list",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "min_access_role": {
                        "type": "string",
                        "description": "Minimum access role ('reader', 'writer', 'owner')",
                        "enum": ["reader", "writer", "owner"]
                    }
                }
            }
        },
        {
            "name": "find_events",
            "description": "Find events in a specified calendar",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "calendar_id": {"type": "string", "description": "Calendar identifier"},
                    "time_min": {"type": "string", "description": "Start time (ISO format)"},
                    "time_max": {"type": "string", "description": "End time (ISO format)"},
                    "query": {"type": "string", "description": "Free text search query"},
                    "max_results": {"type": "integer", "description": "Maximum number of events"}
                },
                "required": ["calendar_id"]
            }
        },
        {
            "name": "quick_add_event",
            "description": "Creates an event using natural language text",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "calendar_id": {"type": "string", "description": "Calendar identifier"},
                    "text": {"type": "string", "description": "Natural language event description"}
                },
                "required": ["calendar_id", "text"]
            }
        },
        {
            "name": "create_event",
            "description": "Creates a new event with detailed information",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "calendar_id": {"type": "string", "description": "Calendar identifier"},
                    "summary": {"type": "string", "description": "Event title"},
                    "start_time": {"type": "string", "description": "Start time (ISO format)"},
                    "end_time": {"type": "string", "description": "End time (ISO format)"},
                    "description": {"type": "string", "description": "Event description"},
                    "location": {"type": "string", "description": "Event location"},
                    "attendee_emails": {"type": "array", "items": {"type": "string"}, "description": "Attendee emails"}
                },
                "required": ["calendar_id", "summary", "start_time", "end_time"]
            }
        },
        {
            "name": "update_event",
            "description": "Updates an existing event",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "calendar_id": {"type": "string", "description": "Calendar identifier"},
                    "event_id": {"type": "string", "description": "Event identifier"},
                    "summary": {"type": "string", "description": "New event title"},
                    "start_time": {"type": "string", "description": "New start time (ISO format)"},
                    "end_time": {"type": "string", "description": "New end time (ISO format)"},
                    "description": {"type": "string", "description": "New description"},
                    "location": {"type": "string", "description": "New location"}
                },
                "required": ["calendar_id", "event_id"]
            }
        },
        {
            "name": "delete_event",
            "description": "Deletes an event",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "calendar_id": {"type": "string", "description": "Calendar identifier"},
                    "event_id": {"type": "string", "description": "Event identifier"}
                },
                "required": ["calendar_id", "event_id"]
            }
        },
        {
            "name": "check_free_busy",
            "description": "Queries free/busy information for calendars",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "calendar_ids": {"type": "array", "items": {"type": "string"}, "description": "Calendar IDs"},
                    "time_min": {"type": "string", "description": "Start time (ISO format)"},
                    "time_max": {"type": "string", "description": "End time (ISO format)"}
                },
                "required": ["calendar_ids", "time_min", "time_max"]
            }
        },
        {
            "name": "voice_book_appointment",
            "description": "Book appointment using natural language (optimized for voice agents)",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "natural_language_request": {"type": "string", "description": "Natural language appointment request"},
                    "calendar_id": {"type": "string", "description": "Calendar identifier", "default": "primary"},
                    "user_timezone": {"type": "string", "description": "User's timezone", "default": "UTC"}
                },
                "required": ["natural_language_request"]
            }
        },
        {
            "name": "voice_check_availability",
            "description": "Check availability using natural language (optimized for voice agents)",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "time_request": {"type": "string", "description": "Natural language time request"},
                    "calendar_id": {"type": "string", "description": "Calendar identifier", "default": "primary"},
                    "duration_minutes": {"type": "integer", "description": "Duration in minutes", "default": 60}
                },
                "required": ["time_request"]
            }
        },
        {
            "name": "voice_get_upcoming",
            "description": "Get upcoming appointments with voice-friendly responses",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "calendar_id": {"type": "string", "description": "Calendar identifier", "default": "primary"},
                    "limit": {"type": "integer", "description": "Number of events to return", "default": 5}
                }
            }
        }
    ]

    return {
        "jsonrpc": "2.0",
        "result": {
            "tools": tools
        },
        "id": request_id
    }

async def handle_mcp_tool_call(request_id, params, creds):
    """Handle MCP tools/call request - executes the specified tool."""
    try:
        tool_name = params.get("name")
        arguments = params.get("arguments", {})

        if not creds:
            return {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32002,
                    "message": "Authentication required"
                },
                "id": request_id
            }

        # Map MCP tool calls to calendar actions
        if tool_name == "list_calendars":
            result = calendar_actions.find_calendars(
                credentials=creds,
                min_access_role=arguments.get("min_access_role")
            )
        elif tool_name == "find_events":
            result = calendar_actions.find_events(
                credentials=creds,
                calendar_id=arguments["calendar_id"],
                time_min=arguments.get("time_min"),
                time_max=arguments.get("time_max"),
                query=arguments.get("query"),
                max_results=arguments.get("max_results", 50)
            )
        elif tool_name == "quick_add_event":
            # Quick add event using Google Calendar's natural language parsing
            try:
                booking_result = calendar_actions.quick_add_event(
                    credentials=creds,
                    calendar_id=arguments["calendar_id"],
                    text=arguments["text"],
                    send_notifications=arguments.get("send_notifications", False)
                )

                if booking_result:
                    # Format response consistently with voice functions
                    event_start = booking_result.start
                    if event_start and event_start.dateTime:
                        formatted_time = event_start.dateTime.strftime("%A, %B %d at %I:%M %p")
                    elif event_start and event_start.date:
                        formatted_time = f"All day on {event_start.date.strftime('%A, %B %d')}"
                    else:
                        formatted_time = "the requested time"

                    result = {
                        "success": True,
                        "message": f"Event created: {booking_result.summary or 'Appointment'} scheduled for {formatted_time}",
                        "event_id": booking_result.id,
                        "event_link": booking_result.html_link
                    }
                else:
                    result = {
                        "success": False,
                        "error": "Failed to create event via Google Calendar API"
                    }

            except Exception as e:
                result = {
                    "success": False,
                    "error": f"Calendar API error: {str(e)}"
                }
        elif tool_name == "create_event":
            result = calendar_actions.create_event(
                credentials=creds,
                calendar_id=arguments["calendar_id"],
                event_data={
                    "summary": arguments["summary"],
                    "start": {"dateTime": arguments["start_time"]},
                    "end": {"dateTime": arguments["end_time"]},
                    "description": arguments.get("description"),
                    "location": arguments.get("location"),
                    "attendees": [{"email": email} for email in arguments.get("attendee_emails", [])]
                }
            )
        elif tool_name == "update_event":
            update_data = {}
            if "summary" in arguments:
                update_data["summary"] = arguments["summary"]
            if "start_time" in arguments:
                update_data["start"] = {"dateTime": arguments["start_time"]}
            if "end_time" in arguments:
                update_data["end"] = {"dateTime": arguments["end_time"]}
            if "description" in arguments:
                update_data["description"] = arguments["description"]
            if "location" in arguments:
                update_data["location"] = arguments["location"]

            result = calendar_actions.update_event(
                credentials=creds,
                calendar_id=arguments["calendar_id"],
                event_id=arguments["event_id"],
                event_data=update_data
            )
        elif tool_name == "delete_event":
            result = calendar_actions.delete_event(
                credentials=creds,
                calendar_id=arguments["calendar_id"],
                event_id=arguments["event_id"]
            )
        elif tool_name == "check_free_busy":
            # Parse time strings to datetime objects
            time_min_dt = parser.isoparse(arguments["time_min"]) if isinstance(arguments["time_min"], str) else arguments["time_min"]
            time_max_dt = parser.isoparse(arguments["time_max"]) if isinstance(arguments["time_max"], str) else arguments["time_max"]

            result = calendar_actions.find_availability(
                credentials=creds,
                calendar_ids=arguments["calendar_ids"],
                time_min=time_min_dt,
                time_max=time_max_dt
            )
        elif tool_name == "voice_book_appointment":
            # Voice-optimized booking using natural language
            try:
                booking_result = calendar_actions.quick_add_event(
                    credentials=creds,
                    calendar_id=arguments.get("calendar_id", "primary"),
                    text=arguments["natural_language_request"]
                )

                if booking_result:
                    # Format response in voice-friendly way
                    event_start = booking_result.start
                    if event_start and event_start.dateTime:
                        formatted_time = event_start.dateTime.strftime("%A, %B %d at %I:%M %p")
                    elif event_start and event_start.date:
                        formatted_time = f"All day on {event_start.date.strftime('%A, %B %d')}"
                    else:
                        formatted_time = "the requested time"

                    result = {
                        "success": True,
                        "message": f"Perfect! I've scheduled your appointment for {formatted_time}. The event '{booking_result.summary or 'Appointment'}' has been added to your calendar.",
                        "event_id": booking_result.id,
                        "event_link": booking_result.html_link
                    }
                else:
                    result = {
                        "success": False,
                        "message": "I couldn't understand the appointment details. Could you please be more specific about the date, time, and description?"
                    }
            except Exception as e:
                result = {"success": False, "message": f"I'm sorry, I encountered an issue while booking your appointment: {str(e)}"}

        elif tool_name == "voice_check_availability":
            # Voice-optimized availability checking
            try:
                from datetime import datetime, timedelta

                time_request = arguments["time_request"].lower()
                now = datetime.utcnow()

                # Simple parsing for common phrases
                if "tomorrow" in time_request:
                    target_date = now + timedelta(days=1)
                elif "today" in time_request:
                    target_date = now
                elif "next week" in time_request:
                    target_date = now + timedelta(weeks=1)
                else:
                    target_date = now

                # Set business hours for availability check
                time_min = target_date.replace(hour=9, minute=0, second=0, microsecond=0)
                time_max = target_date.replace(hour=17, minute=0, second=0, microsecond=0)

                # Check for busy periods
                busy_periods = calendar_actions.find_availability(
                    credentials=creds,
                    calendar_ids=[arguments.get("calendar_id", "primary")],
                    time_min=time_min,
                    time_max=time_max
                )

                calendar_id = arguments.get("calendar_id", "primary")
                busy_count = 0
                if busy_periods and calendar_id in busy_periods:
                    busy_intervals = busy_periods[calendar_id].get('busy', [])
                    busy_count = len(busy_intervals)

                if busy_count == 0:
                    message = f"You're completely free on {target_date.strftime('%A, %B %d')} during business hours."
                    availability = "free"
                elif busy_count <= 2:
                    message = f"You have {busy_count} appointment(s) on {target_date.strftime('%A, %B %d')}, but there's still good availability."
                    availability = "partial"
                else:
                    message = f"You have a busy day on {target_date.strftime('%A, %B %d')} with {busy_count} appointments."
                    availability = "busy"

                result = {
                    "success": True,
                    "message": message,
                    "availability": availability,
                    "busy_periods_count": busy_count
                }
            except Exception as e:
                result = {"success": False, "message": f"I'm having trouble checking your availability: {str(e)}"}

        elif tool_name == "voice_get_upcoming":
            # Voice-optimized upcoming events
            try:
                from datetime import datetime, timedelta

                time_min = datetime.utcnow()
                time_max = time_min + timedelta(days=7)

                events_response = calendar_actions.find_events(
                    credentials=creds,
                    calendar_id=arguments.get("calendar_id", "primary"),
                    time_min=time_min,
                    time_max=time_max,
                    max_results=arguments.get("limit", 5),
                    order_by='startTime',
                    single_events=True
                )

                events = events_response.items if events_response else []

                if not events:
                    result = {
                        "success": True,
                        "message": "You don't have any appointments coming up in the next week. Your schedule is clear!",
                        "events_count": 0,
                        "events": []
                    }
                else:
                    # Format events for voice response
                    voice_events = []
                    for event in events:
                        start = event.start
                        if start and start.dateTime:
                            formatted_time = start.dateTime.strftime("%A, %B %d at %I:%M %p")
                        elif start and start.date:
                            formatted_time = f"All day on {start.date.strftime('%A, %B %d')}"
                        else:
                            formatted_time = "Time not specified"

                        voice_events.append({
                            "summary": event.summary or 'Untitled Event',
                            "start_time": formatted_time,
                            "location": event.location or '',
                            "description": (event.description or '')[:100] if event.description else ''
                        })

                    if len(events) == 1:
                        message = f"You have 1 appointment coming up: {voice_events[0]['summary']} on {voice_events[0]['start_time']}."
                    else:
                        message = f"You have {len(events)} appointments coming up. Your next one is {voice_events[0]['summary']} on {voice_events[0]['start_time']}."

                    result = {
                        "success": True,
                        "message": message,
                        "events_count": len(events),
                        "events": voice_events
                    }
            except Exception as e:
                result = {"success": False, "message": f"I'm having trouble accessing your calendar: {str(e)}"}

        else:
            return {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32601,
                    "message": f"Tool not found: {tool_name}"
                },
                "id": request_id
            }

        # Convert result to string if needed for MCP protocol
        if result is None:
            content = json.dumps({"error": "Operation failed"})
        elif isinstance(result, (dict, list)):
            content = json.dumps(result, indent=2)
        else:
            content = str(result)

        return {
            "jsonrpc": "2.0",
            "result": {
                "content": [
                    {
                        "type": "text",
                        "text": content
                    }
                ]
            },
            "id": request_id
        }

    except Exception as e:
        logger.error(f"MCP tool call error: {e}", exc_info=True)
        return {
            "jsonrpc": "2.0",
            "error": {
                "code": -32603,
                "message": f"Tool execution error: {str(e)}"
            },
            "id": request_id
        }

# --- MCP Testing Endpoint ---

@app.post(
    "/test/mcp",
    tags=["Testing"],
    summary="Test MCP Implementation",
    operation_id="test_mcp_implementation"
)
async def test_mcp_implementation(
    test_oauth_token: str = Body(..., description="Test OAuth token for Google Calendar"),
    test_tool: str = Body("list_calendars", description="Tool to test")
):
    """
    Test endpoint to verify MCP implementation works correctly with OAuth tokens.
    This simulates what OpenAI would send to the MCP server.
    """
    try:
        # Simulate MCP protocol messages
        test_requests = [
            # Initialize
            {
                "jsonrpc": "2.0",
                "method": "initialize",
                "id": "test_init",
                "params": {}
            },
            # List tools
            {
                "jsonrpc": "2.0",
                "method": "tools/list",
                "id": "test_tools",
                "params": {}
            },
            # Call a tool
            {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "id": "test_call",
                "params": {
                    "name": test_tool,
                    "arguments": {"calendar_id": "primary"} if test_tool == "find_events" else {}
                }
            }
        ]

        results = []
        for request in test_requests:
            # Make request to our MCP endpoint
            response = await mcp_http_transport(
                request=request,
                authorization=f"Bearer {test_oauth_token}",
                user_id=None
            )
            results.append({
                "request": request,
                "response": response
            })

        return {
            "status": "success",
            "message": "MCP implementation test completed",
            "results": results,
            "openai_integration_ready": True
        }

    except Exception as e:
        logger.error(f"MCP test failed: {e}", exc_info=True)
        return {
            "status": "error",
            "message": f"MCP test failed: {str(e)}",
            "openai_integration_ready": False
        }

# --- OpenAI-Optimized Endpoints for Voice Agent Integration ---

@app.post(
    "/voice/appointment/book",
    tags=["Voice Agent"],
    summary="Book Appointment via Voice Agent",
    operation_id="voice_book_appointment"
)
def voice_book_appointment(
    natural_language_request: str = Body(..., description="Natural language appointment request"),
    user_timezone: str = Body("UTC", description="User's timezone for the appointment"),
    calendar_id: str = Body("primary", description="Calendar to book in"),
    creds: Credentials = Depends(get_user_credentials)
):
    """
    Books an appointment using natural language input from voice agents.
    Optimized for OpenAI Realtime API with simplified responses.
    """
    try:
        logger.info(f"Voice booking request: {natural_language_request}")

        # Use Google's quick add feature for natural language parsing
        result = calendar_actions.quick_add_event(
            credentials=creds,
            calendar_id=calendar_id,
            text=natural_language_request
        )

        if not result:
            return {
                "success": False,
                "message": "I couldn't understand the appointment details. Could you please be more specific about the date, time, and description?",
                "suggestion": "Try saying something like 'Schedule a meeting with John tomorrow at 2 PM for one hour'"
            }

        # Format response for voice agent
        event_start = result.start

        # Parse datetime for voice-friendly response
        if event_start and event_start.dateTime:
            formatted_time = event_start.dateTime.strftime("%A, %B %d at %I:%M %p")
        elif event_start and event_start.date:
            formatted_time = f"All day on {event_start.date.strftime('%A, %B %d')}"
        else:
            formatted_time = "the requested time"

        return {
            "success": True,
            "message": f"Perfect! I've scheduled your appointment for {formatted_time}. The event '{result.summary or 'Appointment'}' has been added to your calendar.",
            "event_id": result.id,
            "event_link": result.html_link,
            "calendar_id": calendar_id
        }

    except Exception as e:
        logger.error(f"Voice booking failed: {e}")
        return {
            "success": False,
            "message": "I'm sorry, I encountered an issue while booking your appointment. Please try again or provide more specific details.",
            "error_type": "booking_error"
        }

@app.post(
    "/voice/appointment/check",
    tags=["Voice Agent"],
    summary="Check Availability via Voice Agent",
    operation_id="voice_check_availability"
)
def voice_check_availability(
    time_request: str = Body(..., description="Natural language time request"),
    duration_minutes: int = Body(60, description="Duration in minutes"),
    calendar_id: str = Body("primary", description="Calendar to check"),
    creds: Credentials = Depends(get_user_credentials)
):
    """
    Checks availability using natural language input optimized for voice agents.
    """
    try:
        logger.info(f"Voice availability check: {time_request}")

        # Parse the natural language time request
        # For now, we'll use a simple approach and could enhance with NLP libraries
        from datetime import datetime, timedelta
        import re

        # Basic parsing for common phrases
        now = datetime.utcnow()

        # Simple parsing logic (can be enhanced)
        if "tomorrow" in time_request.lower():
            target_date = now + timedelta(days=1)
        elif "today" in time_request.lower():
            target_date = now
        elif "next week" in time_request.lower():
            target_date = now + timedelta(weeks=1)
        else:
            # Default to today if we can't parse
            target_date = now

        # Set time range for availability check
        time_min = target_date.replace(hour=9, minute=0, second=0, microsecond=0)
        time_max = target_date.replace(hour=17, minute=0, second=0, microsecond=0)

        # Check for busy periods
        busy_periods = calendar_actions.find_availability(
            credentials=creds,
            calendar_ids=[calendar_id],
            time_min=time_min,
            time_max=time_max
        )

        busy_count = 0
        if busy_periods and calendar_id in busy_periods:
            busy_intervals = busy_periods[calendar_id].get('busy', [])
            busy_count = len(busy_intervals)

        if busy_count == 0:
            return {
                "success": True,
                "message": f"You appear to be completely free on {target_date.strftime('%A, %B %d')} during business hours.",
                "availability": "free",
                "suggested_times": ["9:00 AM", "10:00 AM", "11:00 AM", "2:00 PM", "3:00 PM"]
            }

        if busy_count == 0:
            message = f"You're completely free on {target_date.strftime('%A, %B %d')}."
        elif busy_count <= 2:
            message = f"You have {busy_count} appointment(s) on {target_date.strftime('%A, %B %d')}, but there's still good availability."
        else:
            message = f"You have a busy day on {target_date.strftime('%A, %B %d')} with {busy_count} appointments."

        return {
            "success": True,
            "message": message,
            "availability": "partial" if busy_count <= 3 else "busy",
            "busy_periods_count": busy_count
        }

    except Exception as e:
        logger.error(f"Voice availability check failed: {e}")
        return {
            "success": False,
            "message": "I'm having trouble checking your availability right now. Please try again.",
            "error_type": "availability_error"
        }

@app.get(
    "/voice/appointment/upcoming",
    tags=["Voice Agent"],
    summary="Get Upcoming Appointments for Voice Agent",
    operation_id="voice_get_upcoming"
)
def voice_get_upcoming_appointments(
    limit: int = Query(5, description="Number of upcoming events to return"),
    calendar_id: str = Query("primary", description="Calendar to check"),
    creds: Credentials = Depends(get_user_credentials)
):
    """
    Gets upcoming appointments with voice-friendly responses.
    """
    try:
        from datetime import datetime, timedelta

        # Get events for the next 7 days
        time_min = datetime.utcnow()
        time_max = time_min + timedelta(days=7)

        events_response = calendar_actions.find_events(
            credentials=creds,
            calendar_id=calendar_id,
            time_min=time_min,
            time_max=time_max,
            max_results=limit,
            order_by='startTime',
            single_events=True
        )

        if not events_response:
            return {
                "success": True,
                "message": "You don't have any appointments coming up in the next week. Your schedule is clear!",
                "events_count": 0,
                "events": []
            }

        events = events_response.items

        if not events:
            return {
                "success": True,
                "message": "You don't have any appointments coming up in the next week. Your schedule is clear!",
                "events_count": 0,
                "events": []
            }

        # Format events for voice response
        voice_events = []
        for event in events:
            start = event.start
            if start and start.dateTime:
                formatted_time = start.dateTime.strftime("%A, %B %d at %I:%M %p")
            elif start and start.date:
                formatted_time = f"All day on {start.date.strftime('%A, %B %d')}"
            else:
                formatted_time = "Time not specified"

            voice_events.append({
                "summary": event.summary or 'Untitled Event',
                "start_time": formatted_time,
                "location": event.location or '',
                "description": (event.description or '')[:100] if event.description else ''
            })

        # Create voice-friendly summary
        if len(events) == 1:
            message = f"You have 1 appointment coming up: {voice_events[0]['summary']} on {voice_events[0]['start_time']}."
        else:
            message = f"You have {len(events)} appointments coming up. Your next one is {voice_events[0]['summary']} on {voice_events[0]['start_time']}."

        return {
            "success": True,
            "message": message,
            "events_count": len(events),
            "events": voice_events
        }

    except Exception as e:
        logger.error(f"Voice upcoming appointments failed: {e}")
        return {
            "success": False,
            "message": "I'm having trouble accessing your calendar right now. Please try again.",
            "error_type": "calendar_access_error"
        }

@app.post(
    "/voice/appointment/cancel",
    tags=["Voice Agent"],
    summary="Cancel Appointment via Voice Agent",
    operation_id="voice_cancel_appointment"
)
def voice_cancel_appointment(
    appointment_description: str = Body(..., description="Description of appointment to cancel"),
    calendar_id: str = Body("primary", description="Calendar to search"),
    creds: Credentials = Depends(get_user_credentials)
):
    """
    Cancels an appointment based on natural language description.
    """
    try:
        from datetime import datetime, timedelta

        # Search for events matching the description
        time_min = datetime.utcnow() - timedelta(hours=1)  # Include current events
        time_max = time_min + timedelta(days=30)  # Look ahead 30 days

        events_response = calendar_actions.find_events(
            credentials=creds,
            calendar_id=calendar_id,
            time_min=time_min,
            time_max=time_max,
            query=appointment_description,  # Search query
            single_events=True
        )

        if not events_response or not events_response.items:
            return {
                "success": False,
                "message": f"I couldn't find any appointments matching '{appointment_description}'. Could you be more specific or check if the appointment exists?",
                "found_events": 0
            }

        events = events_response.items

        # If multiple events found, return them for user to choose
        if len(events) > 1:
            event_list = []
            for i, event in enumerate(events[:3]):  # Limit to 3 for voice response
                start = event.start
                if start and start.dateTime:
                    formatted_time = start.dateTime.strftime("%A, %B %d at %I:%M %p")
                elif start and start.date:
                    formatted_time = f"All day on {start.date.strftime('%A, %B %d')}"
                else:
                    formatted_time = "Time not specified"

                event_list.append(f"{i+1}. {event.summary or 'Untitled'} on {formatted_time}")

            return {
                "success": False,
                "message": f"I found {len(events)} appointments matching that description. Which one would you like to cancel? " + "; ".join(event_list),
                "found_events": len(events),
                "events": event_list,
                "requires_selection": True
            }

        # Cancel the single found event
        event = events[0]
        event_id = event.id

        success = calendar_actions.delete_event(
            credentials=creds,
            calendar_id=calendar_id,
            event_id=event_id
        )

        if success:
            start = event.start
            if start and start.dateTime:
                formatted_time = start.dateTime.strftime("%A, %B %d at %I:%M %p")
            elif start and start.date:
                formatted_time = f"All day on {start.date.strftime('%A, %B %d')}"
            else:
                formatted_time = "Time not specified"

            return {
                "success": True,
                "message": f"I've successfully cancelled '{event.summary or 'your appointment'}' scheduled for {formatted_time}.",
                "cancelled_event": event.summary or 'Untitled Event',
                "event_time": formatted_time
            }
        else:
            return {
                "success": False,
                "message": "I found the appointment but couldn't cancel it. You might not have permission to delete this event.",
                "error_type": "deletion_failed"
            }

    except Exception as e:
        logger.error(f"Voice cancellation failed: {e}")
        return {
            "success": False,
            "message": "I'm having trouble cancelling your appointment right now. Please try again.",
            "error_type": "cancellation_error"
        }

# Add other endpoints as needed

# --- Main Execution ---
if __name__ == "__main__":
    logger.info("Starting Google Calendar MCP Server...")
    # Note: Startup event runs automatically with uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 