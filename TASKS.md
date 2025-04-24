# Google Calendar MCP Server Tasks 📋

## Task Management Guide
- Each task has a unique ID (e.g., 1, 1.1, 1.2)
- Tasks can be hierarchical (main tasks have subtasks)
- Status indicators: 
  - ○ pending
  - ⊙ in-progress
  - ● done
- Priority levels: 
  - 🔴 High - Critical tasks requiring immediate attention
  - 🟠 Medium - Important tasks but not urgent
  - 🟢 Low - Tasks that can be addressed later
- Complexity scale (0-10):
  - 0-2: Simple, straightforward tasks
  - 3-5: Moderate complexity, may need some subtasks
  - 6-8: Complex tasks requiring multiple subtasks
  - 9-10: Highly complex tasks that should be broken into multiple main tasks
- File references:
  - **Main**: Primary file the task focuses on (clickable links)
  - **Related**: Other relevant files that may be affected
  - Files in `project/path` are the internal container files

## Project Overview
Develop a Python-based MCP (Model Context Protocol) server that acts as an interface between Large Language Models (LLMs) and the Google Calendar API. The server will expose functions for basic calendar operations as well as advanced querying, analysis, and potentially predictive features, enabling sophisticated calendar management via natural language through an LLM agent.

## Sprint: Sprint 1 - Foundation & Core Actions 🏃
**Goal:** Set up the project, implement authentication, and build core calendar read/write functionalities.
**Deadline:** YYYY-MM-DD

## Main Tasks

### 1. Project Setup & Authentication 📌
**Priority:** 🔴 High  
**Status:** ● done 
**Dependencies:** None  
**Complexity:** 5/10  
**Files:**
- **Main**: 
  * `README.md`
  * `requirements.txt`
  * `config.py` (or `.env`)
  * `auth.py` (or similar module)
  * `gcp-oauth.keys.json` (User Provided)
  * `.gitignore`
- **Related**: 
  * `server.py` (or main application file)

#### Subtasks:
| ID | Title | Dependencies | Status | Complexity | Files |
|----|----|-----|-----|---|----|
| 1.1 | Initialize Project Structure | None | ● done | 2/10 | Root directory, `src/` |
| 1.2 | Setup Dependency Management | 1.1 | ● done | 2/10 | [`requirements.txt`](mdc:requirements.txt) |
| 1.3 | Configure Google Cloud Project & Credentials | None | ● done | 3/10 | External: Google Cloud Console |
| 1.4 | Implement OAuth 2.0 Flow (Desktop App) | 1.1, 1.2, 1.3 | ● done | 6/10 | [`auth.py`](mdc:src/auth.py), [`server.py`](mdc:src/server.py) |
| 1.5 | Implement Token Storage & Refresh Logic | 1.4 | ● done | 5/10 | [`auth.py`](mdc:src/auth.py), `.gcp-saved-tokens.json` |
| 1.6 | Setup Basic Logging | 1.1 | ● done | 2/10 | [`server.py`](mdc:src/server.py) |
| 1.7 | Create Initial README | 1.1 | ● done | 3/10 | [`README.md`](mdc:README.md) |
| 1.8 | Setup `.gitignore` & `.env.example` | 1.1 | ● done | 2/10 | [`.gitignore`](mdc:.gitignore), `.env.example` |

**Example Subtask Prompts:**
- 1.1: "Create the basic Python project directory structure (`src/`, `tests/`), initialize git."
  * Files: Root directory

- 1.2: "Create `requirements.txt` and add initial dependencies: `google-api-python-client`, `google-auth-oauthlib`, `google-auth-httplib2`, `fastapi`, `uvicorn`."
  * File: [`requirements.txt`](mdc:requirements.txt)

- 1.4: "Implement the Google OAuth 2.0 authorization code flow for a 'Desktop app' using `google-auth-oauthlib`. Include logic to start a temporary local server to catch the redirect URI and capture the authorization code."
  * Files: [`auth.py`](mdc:src/auth.py), [`server.py`](mdc:src/server.py) (for triggering auth)

- 1.5: "Implement functions in `auth.py` to save the obtained OAuth tokens (access and refresh) to a local file (`.gcp-saved-tokens.json`) and load them on startup. Add logic to automatically use the refresh token to get a new access token if the current one is expired."
  * File: [`auth.py`](mdc:src/auth.py)

### 2. Core Calendar Actions Implementation 📌
**Priority:** 🔴 High  
**Status:** ● done 
**Dependencies:** 1  
**Complexity:** 7/10  
**Files:**
- **Main**: 
  * `calendar_actions.py` (or `mcp_handlers.py`)
- **Related**: 
  * `server.py`
  * `auth.py`
  * `models.py` (for data structures)

#### Subtasks:
| ID | Title | Dependencies | Status | Complexity | Files |
|----|----|-----|-----|---|----|
| 2.1 | Define Basic Event Data Model | 1.1 | ● done | 2/10 | [`models.py`](mdc:src/models.py) |
| 2.2 | Implement `find_events` Function | 1.5 | ● done | 4/10 | [`calendar_actions.py`](mdc:src/calendar_actions.py) |
| 2.3 | Implement `create_event` Function (Detailed) | 1.5, 2.1 | ● done | 5/10 | [`calendar_actions.py`](mdc:src/calendar_actions.py) |
| 2.4 | Implement `quick_add_event` Function | 1.5 | ● done | 4/10 | [`calendar_actions.py`](mdc:src/calendar_actions.py) |
| 2.5 | Implement `update_event` Function | 1.5, 2.1 | ● done | 4/10 | [`calendar_actions.py`](mdc:src/calendar_actions.py) |
| 2.6 | Implement `delete_event` Function | 1.5 | ● done | 3/10 | [`calendar_actions.py`](mdc:src/calendar_actions.py) |
| 2.7 | Implement `add_attendee` Function | 1.5 | ● done | 4/10 | [`calendar_actions.py`](mdc:src/calendar_actions.py) |
| 2.8 | Implement `find_calendars` Function | 1.5 | ● done | 3/10 | [`calendar_actions.py`](mdc:src/calendar_actions.py) |
| 2.9 | Implement `create_calendar` Function | 1.5 | ● done | 3/10 | [`calendar_actions.py`](mdc:src/calendar_actions.py) |
| 2.10 | Integrate Actions with MCP Server | 2.2 - 2.9 | ● done | 5/10 | [`server.py`](mdc:src/server.py), [`calendar_actions.py`](mdc:src/calendar_actions.py) |

**Example Subtask Prompts:**
- 2.2: "Create a function `find_events(calendar_id='primary', time_min=None, time_max=None, query=None, max_results=50)` in `calendar_actions.py` that uses the authenticated Google Calendar service (`service.events().list(...)`) to retrieve events based on optional time range and text query."
  * File: [`calendar_actions.py`](mdc:src/calendar_actions.py)

- 2.3: "Create a function `create_event(calendar_id='primary', event_data: dict)` in `calendar_actions.py` that accepts a dictionary conforming to the Google Calendar API event resource structure and uses `service.events().insert(...)` to create a new event."
  * Files: [`calendar_actions.py`](mdc:src/calendar_actions.py), [`models.py`](mdc:src/models.py) (for defining `event_data` structure if needed)

- 2.10: "In `server.py`, create FastAPI endpoints (e.g., `/find_events`, `/create_event`) that call the corresponding functions in `calendar_actions.py`, handling request parsing and response formatting according to MCP specifications (details TBD)."
  * Files: [`server.py`](mdc:src/server.py), [`calendar_actions.py`](mdc:src/calendar_actions.py)

## Backlog 📝

### 3. Advanced Features Implementation 📌
**Priority:** 🟠 Medium 
**Status:** ● done  
**Dependencies:** 2 
**Complexity:** 8/10  
**Files:**
- **Main**: 
  * `calendar_actions.py`
  * `analysis.py` (potentially)
- **Related**: 
  * `server.py`
  * `models.py`

#### Subtasks:
| ID | Title | Dependencies | Status | Complexity | Files |
|----|----|-----|-----|---|----|
| 3.1 | Implement Sophisticated Event Querying | 2.2 | ● done | 6/10 | [`calendar_actions.py`](mdc:src/calendar_actions.py) |
| 3.2 | Implement `check_attendee_status` Function | 2.2 | ● done | 4/10 | [`calendar_actions.py`](mdc:src/calendar_actions.py) |
| 3.3 | Implement `find_availability` Function | 2.2 | ● done | 7/10 | [`calendar_actions.py`](mdc:src/calendar_actions.py) |
| 3.4 | Implement `find_mutual_availability_and_schedule` Workflow | 3.3, 2.3 | ● done | 7/10 | [`calendar_actions.py`](mdc:src/calendar_actions.py) |
| 3.5 | Implement Recurring Event Projection (e.g., Birthdays, Anniverseries, that sort of thing) | 2.2 | ● done | 6/10 | [`analysis.py`](mdc:src/analysis.py), [`calendar_actions.py`](mdc:src/calendar_actions.py) |
| 3.6 | Implement Non-Routine Event Analysis | 2.2 | ● done | 5/10 | [`analysis.py`](mdc:src/analysis.py), [`calendar_actions.py`](mdc:src/calendar_actions.py) |
| 3.7 | Integrate Advanced Actions with MCP Server | 3.1 - 3.6 | ● done | 4/10 | [`server.py`](mdc:src/server.py), [`calendar_actions.py`](mdc:src/calendar_actions.py) |

## Sprint: Sprint 2 - MCP Protocol Fixes 🏃
**Goal:** Fix MCP handshake protocol issues and ensure proper tool discovery.
**Deadline:** YYYY-MM-DD

## Main Tasks

### 4. Fix MCP Protocol Implementation 📌
**Priority:** 🔴 High  
**Status:** ● done  
**Dependencies:** 1, 2, 3  
**Complexity:** 6/10  
**Files:**
- **Main**: 
  * [`src/server.py`](mdc:src/server.py)
  * [`src/mcp_bridge.py`](mdc:src/mcp_bridge.py)
- **Related**: 
  * [`src/analysis.py`](mdc:src/analysis.py)
  * [`run_server.py`](mdc:run_server.py)

#### Subtasks:
| ID | Title | Dependencies | Status | Complexity | Files |
|----|----|-----|-----|---|----|
| 4.1 | Fix MCP Offerings Endpoint | None | ● done | 4/10 | [`src/server.py`](mdc:src/server.py) |
| 4.2 | Add Operation IDs to All Routes | 4.1 | ● done | 3/10 | [`src/server.py`](mdc:src/server.py) |
| 4.3 | Fix Import Error in Analysis Module | None | ● done | 2/10 | [`src/analysis.py`](mdc:src/analysis.py) |
| 4.4 | Change MCP Endpoint Path to Standard Format | 4.1 | ● done | 2/10 | [`src/server.py`](mdc:src/server.py) |
| 4.5 | Update Offerings Format to MCP Protocol Standard | 4.4 | ● done | 3/10 | [`src/server.py`](mdc:src/server.py) |
| 4.6 | Add Required MCP API Key Endpoint | 4.5 | ● done | 2/10 | [`src/server.py`](mdc:src/server.py) |
| 4.7 | Implement MCP SDK Bridge | None | ● done | 5/10 | [`src/mcp_bridge.py`](mdc:src/mcp_bridge.py) |
| 4.8 | Update Server Runner for MCP Support | 4.7 | ● done | 4/10 | [`run_server.py`](mdc:run_server.py) |
| 4.9 | Test MCP Server with Client | 4.1-4.8 | ○ pending | 3/10 | [`src/mcp_bridge.py`](mdc:src/mcp_bridge.py), [`run_server.py`](mdc:run_server.py) |
| 4.10 | Document MCP Integration | 4.9 | ○ pending | 3/10 | [`README.md`](mdc:README.md) |

**Example Subtask Prompts:**
- 4.1: "Make the MCP offerings endpoint accessible by removing the include_in_schema=False flag from the /mcp/offerings endpoint definition in server.py. Ensure that the route path matches the expected MCP protocol endpoint."
  * File: [`src/server.py`](mdc:src/server.py)

- 4.2: "Add operation_id to all FastAPI route decorators to ensure proper tool identification in the OpenAPI schema, which is used by the MCP client to discover available tools."
  * File: [`src/server.py`](mdc:src/server.py)

- 4.3: "Fix the import error in the analysis.py module by updating imports to use absolute imports (src.calendar_actions, src.models) rather than relative imports (.calendar_actions, .models) to ensure compatibility across execution contexts."
  * File: [`src/analysis.py`](mdc:src/analysis.py)

- 4.4: "Change the MCP endpoint path from /mcp/offerings to /services/offerings to match the standard MCP protocol endpoint path used by clients."
  * File: [`src/server.py`](mdc:src/server.py)

- 4.5: "Update the offerings format to use 'offering_id' instead of 'tool_id' to match the expected MCP protocol format."
  * File: [`src/server.py`](mdc:src/server.py)

- 4.6: "Add a /services/api_key endpoint that returns a mock API key, as this is part of the standard MCP protocol expected by clients."
  * File: [`src/server.py`](mdc:src/server.py)

- 4.7: "Create a bridge module that uses the MCP SDK to implement tools that communicate with the FastAPI server endpoints. This provides proper stdio-based communication for MCP clients."
  * File: [`src/mcp_bridge.py`](mdc:src/mcp_bridge.py)

- 4.8: "Update the run_server.py script to check if it's being run by an MCP client (stdin is piped) and start the MCP server in a separate thread alongside the FastAPI server."
  * File: [`run_server.py`](mdc:run_server.py)

- 4.9: "Test the MCP server with a proper MCP client to verify that the tools are properly discovered and can be invoked."
  * Files: [`src/mcp_bridge.py`](mdc:src/mcp_bridge.py), [`run_server.py`](mdc:run_server.py)

- 4.10: "Update the README.md file to document the MCP integration, including how to configure Claude Desktop or other MCP clients to use the calendar server."
  * File: [`README.md`](mdc:README.md)

### 5. MCP Client Integration Enhancements 📌
**Priority:** 🟠 Medium  
**Status:** ○ pending  
**Dependencies:** 4  
**Complexity:** 7/10  
**Files:**
- **Main**: 
  * [`src/mcp_bridge.py`](mdc:src/mcp_bridge.py)
- **Related**: 
  * [`run_server.py`](mdc:run_server.py)
  * [`README.md`](mdc:README.md)

#### Subtasks:
| ID | Title | Dependencies | Status | Complexity | Files |
|----|----|-----|-----|---|----|
| 5.1 | Add MCP Resources Support | None | ○ pending | 4/10 | [`src/mcp_bridge.py`](mdc:src/mcp_bridge.py) |
| 5.2 | Add MCP Prompts Support | None | ○ pending | 4/10 | [`src/mcp_bridge.py`](mdc:src/mcp_bridge.py) |
| 5.3 | Enhance Tool Argument Validation | None | ○ pending | 3/10 | [`src/mcp_bridge.py`](mdc:src/mcp_bridge.py) |
| 5.4 | Add Response Result Formatting | None | ○ pending | 3/10 | [`src/mcp_bridge.py`](mdc:src/mcp_bridge.py) |
| 5.5 | Implement Error Handling and Recovery | None | ○ pending | 4/10 | [`src/mcp_bridge.py`](mdc:src/mcp_bridge.py) |
| 5.6 | Create Client Installation Guide | 5.1-5.5 | ○ pending | 3/10 | [`README.md`](mdc:README.md) |

**Example Subtask Prompts:**
- 5.1: "Add support for MCP Resources to provide static data like example events, formatting templates, or help documentation to the client."
  * File: [`src/mcp_bridge.py`](mdc:src/mcp_bridge.py)

- 5.2: "Add support for MCP Prompts to provide pre-defined templates that help users accomplish specific tasks with the calendar tools."
  * File: [`src/mcp_bridge.py`](mdc:src/mcp_bridge.py)

- 5.3: "Enhance input validation for tool arguments to provide better error messages and prevent invalid API calls."
  * File: [`src/mcp_bridge.py`](mdc:src/mcp_bridge.py)

- 5.4: "Improve formatting of tool results to make them more readable for humans, especially for complex responses like event lists."
  * File: [`src/mcp_bridge.py`](mdc:src/mcp_bridge.py)

- 5.5: "Implement comprehensive error handling and recovery mechanisms for the MCP tools to handle connection issues, API errors, and other edge cases gracefully."
  * File: [`src/mcp_bridge.py`](mdc:src/mcp_bridge.py)

- 5.6: "Create a detailed guide for installing and configuring various MCP clients to use the calendar server, with specific instructions for Claude Desktop and other popular clients."
  * File: [`README.md`](mdc:README.md)

## Completed Tasks ✅