import logging
from datetime import datetime, date, timedelta, time
from typing import Optional, List, Dict, Any, Tuple
from dateutil import parser # For robust datetime parsing

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2.credentials import Credentials

from .models import (
    GoogleCalendarEvent,
    EventsResponse,
    EventCreateRequest,
    EventDateTime,
    EventAttendee,
    EventUpdateRequest,
    CalendarListResponse,
    CalendarListEntry
)

# Import analysis functions
try:
    from .analysis import project_recurring_events, ProjectedEventOccurrence, analyze_busyness
except ImportError:
    logging.error("Could not import from .analysis. Ensure structure is correct.")
    # Define dummies for type hinting
    def project_recurring_events(*args, **kwargs): return []
    def analyze_busyness(*args, **kwargs): return None # Added dummy
    class ProjectedEventOccurrence: pass

logger = logging.getLogger(__name__)

# --- Helper Function to Build Service ---

def _get_calendar_service(credentials: Credentials):
    """Builds the Google Calendar API service client."""
    try:
        service = build('calendar', 'v3', credentials=credentials)
        logger.debug("Google Calendar service client created successfully.")
        return service
    except Exception as e:
        logger.error(f"Failed to build Google Calendar service: {e}", exc_info=True)
        raise  # Re-raise the exception to be handled by the caller

# --- Calendar Action Functions ---

def find_events(
    credentials: Credentials,
    calendar_id: str = 'primary',
    time_min: Optional[datetime] = None,
    time_max: Optional[datetime] = None,
    query: Optional[str] = None,
    max_results: int = 50,
    single_events: bool = True, # Expand recurring events into instances
    order_by: str = 'startTime', # Order by start time
    iCalUID: Optional[str] = None, # Filter by iCalendar UID
    sharedExtendedProperty: Optional[str] = None, # Filter by shared extended properties (key=value or key)
    privateExtendedProperty: Optional[str] = None, # Filter by private extended properties (key=value or key)
    showDeleted: bool = False, # Show deleted events
    eventTypes: Optional[List[str]] = None # Filter by event types (e.g., ['default', 'focusTime'])
) -> Optional[EventsResponse]:
    """Finds events in a specified calendar based on various criteria.

    Args:
        credentials: Valid Google OAuth2 credentials.
        calendar_id: Calendar identifier (e.g., 'primary', email address, or calendar ID).
        time_min: Start of the time range (inclusive). If None, no lower bound.
        time_max: End of the time range (exclusive). If None, no upper bound.
        query: Free text search query.
        max_results: Maximum number of events to return.
        single_events: Whether to expand recurring events into single instances.
        order_by: The order of the events returned ('startTime' or 'updated').
        iCalUID: Specific iCalendar UID to filter by.
        sharedExtendedProperty: Filter by shared extended properties. Format "key=value" or "key".
        privateExtendedProperty: Filter by private extended properties. Format "key=value" or "key".
        showDeleted: Whether to include deleted events in the results.
        eventTypes: List of event types to return (e.g., ['default', 'focusTime', 'outOfOffice']).

    Returns:
        An EventsResponse object containing the list of events, or None if an error occurs.
    """
    service = _get_calendar_service(credentials)
    if not service:
        return None

    # Format datetime objects to RFC3339 string format required by the API
    time_min_str = time_min.isoformat() + 'Z' if time_min and time_min.tzinfo is None else (time_min.isoformat() if time_min else None)
    time_max_str = time_max.isoformat() + 'Z' if time_max and time_max.tzinfo is None else (time_max.isoformat() if time_max else None)

    # Build the arguments dictionary dynamically to avoid passing None values for optional params
    list_kwargs = {
        'calendarId': calendar_id,
        'timeMin': time_min_str,
        'timeMax': time_max_str,
        'q': query,
        'maxResults': max_results,
        'singleEvents': single_events,
        'orderBy': order_by,
        'showDeleted': showDeleted,
        # Conditionally add parameters if they are provided
        **(({'iCalUID': iCalUID}) if iCalUID else {}),
        **(({'sharedExtendedProperty': sharedExtendedProperty}) if sharedExtendedProperty else {}),
        **(({'privateExtendedProperty': privateExtendedProperty}) if privateExtendedProperty else {}),
        **(({'eventTypes': eventTypes}) if eventTypes else {}),
    }
    # Filter out None values from list_kwargs to avoid API errors for empty optional params
    list_kwargs = {k: v for k, v in list_kwargs.items() if v is not None}

    logger.info(
        f"Fetching events from calendar '{calendar_id}' with parameters: {list_kwargs}"
        # f"time_min='{time_min_str}', time_max='{time_max_str}', query='{query}', "
        # f"max_results={max_results}, single_events={single_events}, order_by='{order_by}', "
        # f"iCalUID='{iCalUID}', sharedExtendedProperty='{sharedExtendedProperty}', "
        # f"privateExtendedProperty='{privateExtendedProperty}', showDeleted={showDeleted}, "
        # f"eventTypes={eventTypes}"
    )

    try:
        events_result = service.events().list(**list_kwargs).execute()

        logger.info(f"Found {len(events_result.get('items', []))} events.")

        # Parse the result using Pydantic models for validation and structure
        events_response = EventsResponse(**events_result)
        return events_response

    except HttpError as error:
        logger.error(f"An API error occurred while finding events: {error}", exc_info=True)
        return None
    except Exception as e:
        logger.error(f"An unexpected error occurred while finding events: {e}", exc_info=True)
        return None

def create_event(
    credentials: Credentials,
    event_data: EventCreateRequest, # Use the Pydantic model for input validation
    calendar_id: str = 'primary',
    send_notifications: bool = True # Whether to send notifications to attendees
) -> Optional[GoogleCalendarEvent]:
    """Creates a new event in the specified calendar.

    Args:
        credentials: Valid Google OAuth2 credentials.
        event_data: An EventCreateRequest object containing event details.
        calendar_id: Calendar identifier.
        send_notifications: Whether to send notifications about the creation to attendees.

    Returns:
        A GoogleCalendarEvent object representing the created event, or None if an error occurs.
    """
    service = _get_calendar_service(credentials)
    if not service:
        return None

    # Construct the event body dictionary from the Pydantic model
    # Use .dict(by_alias=True, exclude_unset=True) for proper formatting
    event_body = event_data.dict(by_alias=True, exclude_unset=True)

    # Handle attendees specifically: API expects a list of {'email': email_address}
    if 'attendees' in event_body and event_body['attendees'] is not None:
        # Assuming event_data.attendees was a list of emails from EventCreateRequest
        event_body['attendees'] = [{'email': email} for email in event_data.attendees]

    logger.info(f"Creating event in calendar '{calendar_id}': {event_data.summary}")
    logger.debug(f"Event body for creation: {event_body}")

    try:
        created_event = service.events().insert(
            calendarId=calendar_id,
            body=event_body,
            sendNotifications=send_notifications
        ).execute()

        logger.info(f"Successfully created event with ID: {created_event.get('id')}")

        # Parse the created event using Pydantic model
        parsed_event = GoogleCalendarEvent(**created_event)
        return parsed_event

    except HttpError as error:
        logger.error(f"An API error occurred while creating event: {error}", exc_info=True)
        return None
    except Exception as e:
        logger.error(f"An unexpected error occurred while creating event: {e}", exc_info=True)
        return None

def quick_add_event(
    credentials: Credentials,
    text: str,
    calendar_id: str = 'primary',
    send_notifications: bool = False # Default to False for quick add?
) -> Optional[GoogleCalendarEvent]:
    """Creates an event based on a simple text string using Google's parser.

    Args:
        credentials: Valid Google OAuth2 credentials.
        text: The text description of the event (e.g., "Tennis at 5pm tomorrow").
        calendar_id: Calendar identifier.
        send_notifications: Whether to send notifications.

    Returns:
        A GoogleCalendarEvent object representing the created event, or None if an error occurs.
    """
    service = _get_calendar_service(credentials)
    if not service:
        return None

    logger.info(f"Quick adding event to calendar '{calendar_id}' with text: \"{text}\"")

    try:
        created_event = service.events().quickAdd(
            calendarId=calendar_id,
            text=text,
            sendNotifications=send_notifications
        ).execute()

        logger.info(f"Successfully quick-added event with ID: {created_event.get('id')}")

        # Parse the created event using Pydantic model
        parsed_event = GoogleCalendarEvent(**created_event)
        return parsed_event

    except HttpError as error:
        logger.error(f"An API error occurred during quick add: {error}", exc_info=True)
        # Specific error handling for invalid text?
        # Google might return 400 Bad Request if text is unparseable
        return None
    except Exception as e:
        logger.error(f"An unexpected error occurred during quick add: {e}", exc_info=True)
        return None

def update_event(
    credentials: Credentials,
    event_id: str,
    update_data: EventUpdateRequest, # Use Pydantic model for partial update data
    calendar_id: str = 'primary',
    send_notifications: bool = True # Whether to send notifications
) -> Optional[GoogleCalendarEvent]:
    """Updates an existing event using patch semantics (only specified fields are changed).

    Args:
        credentials: Valid Google OAuth2 credentials.
        event_id: The ID of the event to update.
        update_data: An EventUpdateRequest object containing fields to update.
        calendar_id: Calendar identifier.
        send_notifications: Whether to send update notifications to attendees.

    Returns:
        A GoogleCalendarEvent object representing the updated event, or None if an error occurs.
    """
    service = _get_calendar_service(credentials)
    if not service:
        return None

    # Use .dict(exclude_unset=True) to only include fields explicitly set in the request model
    # Use by_alias=True to ensure correct Google API field names (e.g., 'dateTime')
    update_body = update_data.dict(by_alias=True, exclude_unset=True)

    if not update_body:
        logger.warning(f"Update called for event {event_id} with no fields to update.")
        # Optionally, retrieve and return the existing event data?
        # For now, return None or raise an error, as no update was performed.
        # Let's retrieve the existing event to provide some feedback.
        try:
            existing_event = service.events().get(calendarId=calendar_id, eventId=event_id).execute()
            return GoogleCalendarEvent(**existing_event)
        except HttpError as e:
            logger.error(f"Failed to retrieve event {event_id} after empty update request: {e}")
            return None

    # Handle attendees if present in update_body
    # Need to decide on update semantics: replace all attendees or patch?
    # Google API patch usually replaces the entire attendees list if provided.
    if 'attendees' in update_body and update_body['attendees'] is not None:
        # Assuming EventUpdateRequest.attendees expects the full EventAttendee model structure
        # We need to convert it back to the simple list of dicts for the API
        pass # Handled by .dict(by_alias=True)
        # If EventUpdateRequest.attendees was just a list of emails, formatting would be needed:
        # update_body['attendees'] = [{'email': email} for email in update_body['attendees']]

    logger.info(f"Updating event '{event_id}' in calendar '{calendar_id}'.")
    logger.debug(f"Update body for patch: {update_body}")

    try:
        updated_event = service.events().patch(
            calendarId=calendar_id,
            eventId=event_id,
            body=update_body,
            sendNotifications=send_notifications
        ).execute()

        logger.info(f"Successfully updated event '{event_id}'.")

        # Parse the updated event using Pydantic model
        parsed_event = GoogleCalendarEvent(**updated_event)
        return parsed_event

    except HttpError as error:
        # Handle common errors like 404 Not Found
        if error.resp.status == 404:
            logger.error(f"Event '{event_id}' not found in calendar '{calendar_id}'.")
        else:
            logger.error(f"An API error occurred while updating event '{event_id}': {error}", exc_info=True)
        return None
    except Exception as e:
        logger.error(f"An unexpected error occurred while updating event '{event_id}': {e}", exc_info=True)
        return None

def delete_event(
    credentials: Credentials,
    event_id: str,
    calendar_id: str = 'primary',
    send_notifications: bool = True # Whether to send notifications
) -> bool:
    """Deletes an event.

    Args:
        credentials: Valid Google OAuth2 credentials.
        event_id: The ID of the event to delete.
        calendar_id: Calendar identifier.
        send_notifications: Whether to send deletion notifications to attendees.

    Returns:
        True if the event was deleted successfully, False otherwise.
    """
    service = _get_calendar_service(credentials)
    if not service:
        return False

    logger.info(f"Attempting to delete event '{event_id}' from calendar '{calendar_id}'.")

    try:
        service.events().delete(
            calendarId=calendar_id,
            eventId=event_id,
            sendNotifications=send_notifications
        ).execute()
        # Delete returns no content on success (204)
        logger.info(f"Successfully deleted event '{event_id}'.")
        return True

    except HttpError as error:
        # Handle common errors like 404 Not Found or 410 Gone
        if error.resp.status in [404, 410]:
            logger.error(f"Event '{event_id}' not found or already deleted in calendar '{calendar_id}'. Cannot delete.")
        else:
            logger.error(f"An API error occurred while deleting event '{event_id}': {error}", exc_info=True)
        return False
    except Exception as e:
        logger.error(f"An unexpected error occurred while deleting event '{event_id}': {e}", exc_info=True)
        return False

def add_attendee(
    credentials: Credentials,
    event_id: str,
    attendee_emails: List[str], # Simple list of emails to add
    calendar_id: str = 'primary',
    send_notifications: bool = True
) -> Optional[GoogleCalendarEvent]:
    """Adds one or more attendees to an existing event.

    Note: This replaces the entire attendee list in the event.

    Args:
        credentials: Valid Google OAuth2 credentials.
        event_id: The ID of the event to modify.
        attendee_emails: A list of email addresses to add/set as attendees.
        calendar_id: Calendar identifier.
        send_notifications: Whether to send update notifications.

    Returns:
        The updated GoogleCalendarEvent object, or None if an error occurs.
    """
    service = _get_calendar_service(credentials)
    if not service:
        return None

    logger.info(f"Attempting to add attendees {attendee_emails} to event '{event_id}' in calendar '{calendar_id}'.")

    # 1. Get the existing event
    try:
        event = service.events().get(calendarId=calendar_id, eventId=event_id).execute()
        logger.debug(f"Retrieved existing event '{event_id}' for adding attendees.")
    except HttpError as error:
        if error.resp.status == 404:
            logger.error(f"Event '{event_id}' not found in calendar '{calendar_id}'. Cannot add attendees.")
        else:
            logger.error(f"API error retrieving event '{event_id}': {error}", exc_info=True)
        return None
    except Exception as e:
        logger.error(f"Unexpected error retrieving event '{event_id}': {e}", exc_info=True)
        return None

    # 2. Modify the attendee list
    # Get current attendees, ensuring it's a list
    current_attendees = event.get('attendees', [])
    if not isinstance(current_attendees, list):
        current_attendees = [] # Ensure it's a list if API returns something unexpected

    # Create a set of current attendee emails for efficient lookup
    current_emails = {attendee.get('email') for attendee in current_attendees if attendee.get('email')}

    # Prepare the list of new attendee objects to add
    new_attendees_to_add = [
        {'email': email} for email in attendee_emails if email not in current_emails
    ]

    if not new_attendees_to_add:
        logger.warning(f"All provided attendees {attendee_emails} are already in event '{event_id}'. No update needed.")
        # Return the current event data as no changes were made
        return GoogleCalendarEvent(**event)

    # Combine current and new attendees
    updated_attendee_list = current_attendees + new_attendees_to_add

    # 3. Prepare the patch body
    patch_body = {
        'attendees': updated_attendee_list
    }

    # 4. Patch the event
    logger.debug(f"Patching event '{event_id}' with updated attendees: {patch_body}")
    try:
        updated_event = service.events().patch(
            calendarId=calendar_id,
            eventId=event_id,
            body=patch_body,
            sendNotifications=send_notifications
        ).execute()

        logger.info(f"Successfully added attendees to event '{event_id}'.")

        # Parse the updated event using Pydantic model
        parsed_event = GoogleCalendarEvent(**updated_event)
        return parsed_event

    except HttpError as error:
        logger.error(f"An API error occurred while patching event '{event_id}' with new attendees: {error}", exc_info=True)
        return None
    except Exception as e:
        logger.error(f"An unexpected error occurred while patching event '{event_id}' with new attendees: {e}", exc_info=True)
        return None

def find_calendars(
    credentials: Credentials,
    min_access_role: Optional[str] = None # e.g., 'reader', 'writer', 'owner'
) -> Optional[CalendarListResponse]:
    """Lists the calendars on the user's calendar list.

    Args:
        credentials: Valid Google OAuth2 credentials.
        min_access_role: The minimum access role for the user in the returned calendars.

    Returns:
        A CalendarListResponse object containing the list of calendars, or None if an error occurs.
    """
    service = _get_calendar_service(credentials)
    if not service:
        return None

    logger.info(f"Fetching calendar list. Min access role: {min_access_role}")

    # Paginate? For simplicity, get first page for now.
    # Add maxResults if needed.
    try:
        calendar_list = service.calendarList().list(
            minAccessRole=min_access_role
        ).execute()

        logger.info(f"Found {len(calendar_list.get('items', []))} calendars in the list.")

        # Parse the result using Pydantic model
        parsed_list = CalendarListResponse(**calendar_list)
        return parsed_list

    except HttpError as error:
        logger.error(f"An API error occurred while fetching calendar list: {error}", exc_info=True)
        return None
    except Exception as e:
        logger.error(f"An unexpected error occurred while fetching calendar list: {e}", exc_info=True)
        return None

def create_calendar(
    credentials: Credentials,
    summary: str # The title of the new calendar
) -> Optional[CalendarListEntry]: # Returns the created calendar (similar to CalendarListEntry)
    """Creates a new secondary calendar.

    Args:
        credentials: Valid Google OAuth2 credentials.
        summary: The title for the new calendar.

    Returns:
        A CalendarListEntry object representing the created calendar, or None if an error occurs.
    """
    service = _get_calendar_service(credentials)
    if not service:
        return None

    logger.info(f"Attempting to create a new calendar with summary: '{summary}'")

    calendar_body = {
        'summary': summary
        # Add other fields like description or timeZone if needed
    }

    try:
        created_calendar = service.calendars().insert(body=calendar_body).execute()
        logger.info(f"Successfully created calendar with ID: {created_calendar.get('id')}")

        # The response is a Calendar resource, parse it using CalendarListEntry model
        # (Structure is identical for relevant fields)
        parsed_calendar = CalendarListEntry(**created_calendar)
        return parsed_calendar

    except HttpError as error:
        logger.error(f"An API error occurred while creating calendar '{summary}': {error}", exc_info=True)
        return None
    except Exception as e:
        logger.error(f"An unexpected error occurred while creating calendar '{summary}': {e}", exc_info=True)
        return None

def check_attendee_status(
    credentials: Credentials,
    event_id: str,
    calendar_id: str = 'primary',
    attendee_emails: Optional[List[str]] = None
) -> Optional[Dict[str, str]]:
    """Checks the response status of attendees for a specific event.

    Args:
        credentials: Valid Google OAuth2 credentials.
        event_id: The ID of the event to check.
        calendar_id: Calendar identifier.
        attendee_emails: Optional list of specific attendee emails to check.
                         If None, checks status for all attendees.

    Returns:
        A dictionary mapping attendee emails to their response status
        (e.g., 'accepted', 'declined', 'tentative', 'needsAction'),
        or None if the event is not found or an error occurs.
    """
    service = _get_calendar_service(credentials)
    if not service:
        return None

    logger.info(f"Checking attendee status for event '{event_id}' in calendar '{calendar_id}'. Target emails: {attendee_emails or 'All'}")

    try:
        event = service.events().get(calendarId=calendar_id, eventId=event_id).execute()
        logger.debug(f"Retrieved event '{event_id}' for status check.")

    except HttpError as error:
        if error.resp.status == 404:
            logger.error(f"Event '{event_id}' not found in calendar '{calendar_id}'. Cannot check status.")
        else:
            logger.error(f"API error retrieving event '{event_id}': {error}", exc_info=True)
        return None
    except Exception as e:
        logger.error(f"Unexpected error retrieving event '{event_id}': {e}", exc_info=True)
        return None

    attendees = event.get('attendees', [])
    if not attendees:
        logger.info(f"Event '{event_id}' has no attendees.")
        return {}

    status_map: Dict[str, str] = {}
    target_emails_set = set(attendee_emails) if attendee_emails is not None else None

    for attendee in attendees:
        email = attendee.get('email')
        status = attendee.get('responseStatus')
        if not email or not status:
            continue # Skip attendees without email or status

        # If specific emails were requested, check if this attendee is one of them
        if target_emails_set is not None:
            if email in target_emails_set:
                status_map[email] = status
        else:
            # Otherwise, include all attendees
            status_map[email] = status

    logger.info(f"Attendee statuses retrieved for event '{event_id}': {len(status_map)} attendees found.")
    return status_map

def find_availability(
    credentials: Credentials,
    time_min: datetime,
    time_max: datetime,
    calendar_ids: List[str]
) -> Optional[Dict[str, Dict[str, Any]]]: # Return Dict mapping calendar_id to {'busy': List[Dict], 'errors': List[Dict]} ?
    """Finds free/busy information for a list of calendars.

    Args:
        credentials: Valid Google OAuth2 credentials.
        time_min: Start of the time range (inclusive, timezone-aware recommended).
        time_max: End of the time range (exclusive, timezone-aware recommended).
        calendar_ids: A list of calendar identifiers (email or ID) to query.

    Returns:
        A dictionary mapping each calendar ID to its free/busy information.
        The value for each calendar ID is a dictionary containing:
        - 'busy': A list of busy time intervals [{'start': datetime, 'end': datetime}].
        - 'errors': A list of errors encountered for that specific calendar (from API).
        Returns None if a major API error occurs.
    """
    service = _get_calendar_service(credentials)
    if not service:
        return None

    if not calendar_ids:
        logger.warning("find_availability called with empty calendar_ids list.")
        return {}

    # Ensure time_min and time_max are in RFC3339 format
    # Add 'Z' for UTC if timezone is naive, otherwise format appropriately
    time_min_str = time_min.isoformat() + ('Z' if time_min.tzinfo is None else '')
    time_max_str = time_max.isoformat() + ('Z' if time_max.tzinfo is None else '')

    request_body = {
        "timeMin": time_min_str,
        "timeMax": time_max_str,
        "items": [{"id": cal_id} for cal_id in calendar_ids]
        # Optional: Add groupExpansionMax, calendarExpansionMax if needed
    }

    logger.info(f"Querying free/busy information for calendars: {calendar_ids} between {time_min_str} and {time_max_str}")
    logger.debug(f"Free/busy request body: {request_body}")

    try:
        freebusy_result = service.freebusy().query(body=request_body).execute()
        logger.debug(f"Free/busy raw response: {freebusy_result}")

        # Process the response into a more usable format
        processed_results: Dict[str, Dict[str, Any]] = {}
        calendars_data = freebusy_result.get('calendars', {})

        for cal_id, data in calendars_data.items():
            busy_intervals = []
            for interval in data.get('busy', []):
                try:
                    # Parse RFC3339 strings back to datetime objects
                    start_dt = parser.isoparse(interval.get('start'))
                    end_dt = parser.isoparse(interval.get('end'))
                    busy_intervals.append({'start': start_dt, 'end': end_dt})
                except (TypeError, ValueError) as parse_error:
                    logger.warning(f"Could not parse busy interval for {cal_id}: {interval}. Error: {parse_error}")
                    # Optionally add this interval with raw strings or skip it

            processed_results[cal_id] = {
                'busy': busy_intervals,
                'errors': data.get('errors', []) # Keep API errors as is
            }

        logger.info(f"Successfully retrieved free/busy information for {len(processed_results)} calendars.")
        return processed_results

    except HttpError as error:
        logger.error(f"An API error occurred during free/busy query: {error}", exc_info=True)
        return None
    except Exception as e:
        logger.error(f"An unexpected error occurred during free/busy query: {e}", exc_info=True)
        return None

def _merge_intervals(intervals: List[Dict[str, datetime]]) -> List[Dict[str, datetime]]:
    """Merges overlapping or adjacent time intervals."""
    if not intervals:
        return []

    # Sort intervals by start time
    sorted_intervals = sorted(intervals, key=lambda x: x['start'])

    merged = [sorted_intervals[0]]

    for current in sorted_intervals[1:]:
        last_merged = merged[-1]
        # If current interval overlaps or is adjacent to the last merged one
        if current['start'] <= last_merged['end']:
            # Merge by extending the end time if current ends later
            merged[-1]['end'] = max(last_merged['end'], current['end'])
        else:
            # No overlap, add the current interval as a new one
            merged.append(current)

    return merged

def _find_first_available_slot(
    time_min: datetime,
    time_max: datetime,
    duration: timedelta,
    busy_intervals: List[Dict[str, datetime]],
    working_hours_start: Optional[time] = None,
    working_hours_end: Optional[time] = None,
) -> Optional[Tuple[datetime, datetime]]:
    """Finds the first available time slot of a given duration within a range, considering busy times and working hours."""
    current_time = time_min

    # Ensure working hours are applied correctly regardless of date part
    def is_within_working_hours(slot_start: datetime, slot_end: datetime) -> bool:
        if not working_hours_start or not working_hours_end:
            return True # No working hours constraint
        # Check if the slot STARTS and ENDS within working hours on its day
        # Naive comparison assumes datetimes are in the same timezone
        return (working_hours_start <= slot_start.time() and
                slot_end.time() <= working_hours_end and
                slot_start.date() == slot_end.date()) # Ensure slot doesn't cross midnight if working hours defined

    # Iterate through the gaps *before* each busy interval
    for busy in busy_intervals:
        free_slot_start = current_time
        free_slot_end = busy['start']
        available_duration = free_slot_end - free_slot_start

        if available_duration >= duration:
            potential_start = free_slot_start
            potential_end = potential_start + duration
            # Check if this slot fits and respects working hours
            if potential_end <= free_slot_end and is_within_working_hours(potential_start, potential_end):
                logger.debug(f"Found available slot (before busy interval): {potential_start} - {potential_end}")
                return potential_start, potential_end

        # Move current time to the end of the current busy interval for the next gap check
        current_time = max(current_time, busy['end'])

    # Check the final gap *after* the last busy interval
    free_slot_start = current_time
    free_slot_end = time_max
    available_duration = free_slot_end - free_slot_start

    if available_duration >= duration:
        potential_start = free_slot_start
        potential_end = potential_start + duration
        if potential_end <= free_slot_end and is_within_working_hours(potential_start, potential_end):
             logger.debug(f"Found available slot (after last busy interval): {potential_start} - {potential_end}")
             return potential_start, potential_end

    logger.debug("No suitable available slot found within the given constraints.")
    return None

def find_mutual_availability_and_schedule(
    credentials: Credentials,
    attendee_calendar_ids: List[str],
    time_min: datetime,
    time_max: datetime,
    duration_minutes: int,
    event_details: EventCreateRequest, # Pre-filled event details (summary, desc, etc.) excluding times
    organizer_calendar_id: str = 'primary',
    working_hours_start: Optional[time] = None, # e.g., time(9, 0)
    working_hours_end: Optional[time] = None,   # e.g., time(17, 0)
    send_notifications: bool = True
) -> Optional[GoogleCalendarEvent]:
    """Finds the first mutually available time slot for attendees and schedules an event.

    Args:
        credentials: Valid Google OAuth2 credentials.
        attendee_calendar_ids: List of calendar IDs (emails) for attendees.
        time_min: Start of the search window (timezone-aware recommended).
        time_max: End of the search window (timezone-aware recommended).
        duration_minutes: Required duration of the event in minutes.
        event_details: Pydantic model instance with event details (summary, description,
                       location, etc.) but WITHOUT start/end times. Attendees can be pre-filled
                       or will be added from attendee_calendar_ids.
        organizer_calendar_id: Calendar ID where the event will be created.
        working_hours_start: Optional start time for daily working hours constraint.
        working_hours_end: Optional end time for daily working hours constraint.
        send_notifications: Whether to send notifications for the created event.

    Returns:
        The created GoogleCalendarEvent object if a slot is found and scheduling succeeds,
        otherwise None.
    """
    service = _get_calendar_service(credentials)
    if not service:
        return None

    logger.info(f"Attempting to find mutual availability and schedule for: {attendee_calendar_ids}")
    logger.info(f"Search window: {time_min} to {time_max}, Duration: {duration_minutes} mins")

    # 1. Find availability for all attendees
    availability_data = find_availability(
        credentials=credentials,
        time_min=time_min,
        time_max=time_max,
        calendar_ids=attendee_calendar_ids
    )

    if availability_data is None:
        logger.error("Failed to retrieve availability data.")
        return None

    # 2. Aggregate and merge all busy intervals
    all_busy_intervals: List[Dict[str, datetime]] = []
    for cal_id, data in availability_data.items():
        if data.get('errors'):
            logger.warning(f"Encountered errors fetching availability for {cal_id}: {data['errors']}")
            # Decide how to handle errors: fail, proceed without this calendar, etc.
            # For now, let's log a warning and proceed, potentially scheduling over their busy time.
            # A stricter approach would be to return None here.
        all_busy_intervals.extend(data.get('busy', []))

    merged_busy = _merge_intervals(all_busy_intervals)
    logger.debug(f"Merged busy intervals: {merged_busy}")

    # 3. Find the first available slot
    duration = timedelta(minutes=duration_minutes)
    available_slot = _find_first_available_slot(
        time_min=time_min,
        time_max=time_max,
        duration=duration,
        busy_intervals=merged_busy,
        working_hours_start=working_hours_start,
        working_hours_end=working_hours_end
    )

    if not available_slot:
        logger.warning("No mutually available time slot found meeting the criteria.")
        return None

    slot_start, slot_end = available_slot
    logger.info(f"Found available slot: {slot_start} - {slot_end}")

    # 4. Prepare full event data
    # Create a copy to avoid modifying the original input
    final_event_data = event_details.copy(deep=True)

    final_event_data.start = EventDateTime(dateTime=slot_start)
    final_event_data.end = EventDateTime(dateTime=slot_end)

    # Ensure all required attendees are in the event data
    existing_attendees = {att.email for att in final_event_data.attendees} if final_event_data.attendees else set()
    for email in attendee_calendar_ids:
        if email not in existing_attendees:
            if final_event_data.attendees is None:
                final_event_data.attendees = []
            # Assuming EventCreateRequest uses a simple list of emails for input
            # If it expects EventAttendee models, adjust accordingly.
            # Based on create_event, it expects a list of emails which it converts.
            final_event_data.attendees.append(email)
            existing_attendees.add(email) # Keep track

    logger.debug(f"Final event data for creation: {final_event_data.dict(by_alias=True)}")

    # 5. Create the event
    created_event = create_event(
        credentials=credentials,
        event_data=final_event_data,
        calendar_id=organizer_calendar_id,
        send_notifications=send_notifications
    )

    if created_event:
        logger.info(f"Successfully scheduled event '{created_event.summary}' (ID: {created_event.id}) at {slot_start}")
    else:
        logger.error("Failed to create the event after finding an available slot.")

    return created_event

# --- Analysis Wrappers ---

def get_projected_recurring_events(
    credentials: Credentials,
    time_min: datetime,
    time_max: datetime,
    calendar_id: str = 'primary',
    event_query: Optional[str] = None
) -> List[ProjectedEventOccurrence]:
    """Wrapper function to find recurring events and project their occurrences.

    This calls the core logic in the analysis module.

    Args:
        credentials: Valid Google OAuth2 credentials.
        time_min: Start of the projection window (timezone-aware recommended).
        time_max: End of the projection window (timezone-aware recommended).
        calendar_id: The calendar to search within.
        event_query: Optional text query to filter master recurring events (e.g., "Birthday").

    Returns:
        A list of ProjectedEventOccurrence objects representing calculated occurrences.
    """
    logger.info(f"Action: get_projected_recurring_events called for calendar '{calendar_id}'")
    # Directly call the analysis function
    return project_recurring_events(
        credentials=credentials,
        time_min=time_min,
        time_max=time_max,
        calendar_id=calendar_id,
        event_query=event_query
    )

def get_busyness_analysis(
    credentials: Credentials,
    time_min: datetime,
    time_max: datetime,
    calendar_id: str = 'primary',
) -> Optional[Dict[date, Dict[str, Any]]]:
    """Wrapper function to analyze daily event busyness.

    This calls the core logic in the analysis module.

    Args:
        credentials: Valid Google OAuth2 credentials.
        time_min: Start of the analysis window (timezone-aware recommended).
        time_max: End of the analysis window (timezone-aware recommended).
        calendar_id: The calendar to analyze.

    Returns:
        A dictionary mapping each date to its busyness stats, or None on error.
    """
    logger.info(f"Action: get_busyness_analysis called for calendar '{calendar_id}'")
    # Directly call the analysis function
    # Add error handling if analyze_busyness itself can raise specific exceptions
    try:
        return analyze_busyness(
            credentials=credentials,
            time_min=time_min,
            time_max=time_max,
            calendar_id=calendar_id,
        )
    except Exception as e:
        # Log the specific error from the analysis function
        logger.error(f"Error during busyness analysis execution: {e}", exc_info=True)
        return None # Return None to signal error to the server endpoint

# --- Add other action functions below (create_calendar) --- 