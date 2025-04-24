# Google Calendar MCP Server (Python)

This project implements a Python-based MCP (Model Context Protocol) server that acts as an interface between Large Language Models (LLMs) and the Google Calendar API. It enables LLMs to perform calendar operations via natural language requests.

## Features

*   **Authentication:** Secure Google Calendar API access using OAuth 2.0 (Desktop App Flow with token storage/refresh).
*   **Core Calendar Actions:**
    *   Find/List calendars (`find_calendars`).
    *   Create calendars (`create_calendar`).
    *   Find events with basic and advanced filtering (`find_events`).
    *   Create detailed events (`create_event`).
    *   Quick-add events from text (`quick_add_event`).
    *   Update events (`update_event`).
    *   Delete events (`delete_event`).
    *   Add attendees to events (`add_attendee`).
*   **Advanced Scheduling & Analysis:**
    *   Check attendee response status (`check_attendee_status`).
    *   Query free/busy information for multiple calendars (`find_availability`).
    *   Find mutual free slots and schedule meetings automatically (`find_mutual_availability_and_schedule`).
    *   Project occurrences of recurring events within a time window (`project_recurring_events`).
    *   Analyze daily event counts and durations (`analyze_busyness`).
*   **Server:** FastAPI-based server exposing actions via a RESTful API.

## Setup

1.  **Prerequisites:**
    *   Python 3.8+ installed.
    *   Git installed.
    *   Access to a Google Cloud Platform project.

2.  **Clone Repository:**
    ```bash
    git clone <repository-url> # Replace with your repo URL
    cd <repository-directory>
    ```

3.  **Google Cloud Setup:**
    *   Go to the [Google Cloud Console](https://console.cloud.google.com/).
    *   Create a new project or select an existing one.
    *   Enable the **Google Calendar API** for your project.
    *   Go to "APIs & Services" > "Credentials".
    *   Click "Create Credentials" > "OAuth client ID".
    *   Select "**Desktop app**" as the Application type. This is important as it affects the credential format.
    *   Give it a name (e.g., "Calendar MCP Server Local").
    *   Click "Create". A window will pop up showing your **Client ID** and **Client Secret**. **Copy these values now.** You will need them for the `.env` file. **You do NOT need to download the JSON file** offered for other application types.
    *   Go to the "OAuth consent screen" tab.
        *   Set User Type to "External" (unless you have a Workspace account).
        *   Fill in the required app information (App name, User support email, Developer contact information).
        *   Click "Save and Continue".
        *   On the "Scopes" page, click "Add or Remove Scopes", search for `calendar`, and add the `.../auth/calendar` scope (or `.../auth/calendar.readonly` if preferred). Click "Update".
        *   Click "Save and Continue".
        *   On the "Test users" page, click "Add Users" and add the Google Account email address you will use to authenticate with the calendar. Click "Add".
        *   Click "Save and Continue" and review the summary.
        *   Click "Back to Dashboard". Your app might be in "Testing" mode, which means tokens expire after 7 days. You can later submit for verification for longer-lived tokens.
    *   Go back to "APIs & Services" > "Credentials" and click on the name of the OAuth 2.0 Client ID you created.
    *   Under "Authorized redirect URIs", click "Add URI" and enter `http://localhost:8080/oauth2callback` (or adjust the port if you changed `OAUTH_CALLBACK_PORT` in `.env`). Click "Save".

4.  **Environment Configuration:**
    *   Create a file named `.env` in the project root directory (this file is ignored by git).
    *   Copy the contents of `.env.example` into `.env`.
    *   Paste the **Client ID** and **Client Secret** you copied from Google Cloud into the `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` variables in `.env`.
    *   Review the `TOKEN_FILE_PATH` variable. This defines where the application will **save the user's access and refresh tokens** after they successfully authenticate for the first time (defaults to `.gcp-saved-tokens.json`). This file will be created automatically; you do not create it yourself.
    *   Adjust `OAUTH_CALLBACK_PORT` or `CALENDAR_SCOPES` in `.env` only if needed.

5.  **Install Dependencies:**
    *   It's highly recommended to use a virtual environment:
        ```bash
        python -m venv venv
        source venv/bin/activate  # On Windows use `venv\Scripts\activate`
        ```
    *   Install the required packages:
        ```bash
        pip install -r requirements.txt
        ```

## Running the Server

1.  **First Run (Authentication):**
    *   Ensure your virtual environment is activated (if using one: `source venv/bin/activate` or `venv\Scripts\activate`).
    *   Run the server using the provided script:
        ```bash
        python run_server.py
        ```
    *   The server (via `src/server.py`) will attempt to load existing tokens. If none are found or they are invalid, it will:
        *   Print an authorization URL to the console.
        *   Automatically open your web browser to that URL.
        *   Ask you to log in to your Google Account (the one added as a test user) and grant permission (consent) for the requested scopes.
        *   After you grant permission, Google will redirect your browser to the local callback URL (`http://localhost:8080/oauth2callback` by default).
        *   The local server running temporarily will capture the authorization code.
        *   The `auth.py` script will exchange the code for tokens and save them automatically to the file specified by `TOKEN_FILE_PATH` in your `.env` file (`.gcp-saved-tokens.json` by default). **This token file is specific to your user and should not be shared or committed to Git.**
        *   The FastAPI server will then continue starting up, typically on `http://localhost:8000`.

2.  **Subsequent Runs:**
    *   Ensure your virtual environment is activated (if using one).
    *   Simply run the server script again:
        ```bash
        python run_server.py
        ```
    *   It should now load the saved tokens from the file and start without requiring browser authentication, unless the tokens have expired (e.g., after 7 days if the app is in testing mode) or were revoked.

## MCP Client Configuration

To use this server with an MCP client (like Cursor), you need to configure the client so it knows how to launch and communicate with this server. This usually involves editing a JSON configuration file (e.g., `mcp.json`).

Below is an example configuration entry. You'll need to adapt the `command` and potentially the `args` based on your Python environment setup (global vs. virtual environment) and the full path to your project.

**Example `mcp.json` Entry:**

```json
{
  "tools": {
    "google_calendar": { // Choose a unique name for the tool
      "command": "python", // Or the full path to your python.exe if needed
      "args": [
        "-u", // Ensures unbuffered output, often helpful
        "C:/path/to/your/calendar-mcp/run_server.py" // *** IMPORTANT: Replace with the ACTUAL FULL PATH to run_server.py ***
      ],
      // Optional: Specify environment variables if needed
      // "env": {
      //   "PYTHONPATH": "C:/path/to/your/calendar-mcp"
      // },
      "timeout": 30000, // Example timeout in milliseconds
      "api": "http://localhost:8000" // Address where the server runs
    }
    // ... other tool configurations ...
  }
}
```

**Key Points:**

*   **`google_calendar`:** Choose a descriptive name for your tool.
*   **`command`:** Typically `python` if it's in your PATH, or the full path to the specific `python.exe` (especially if using a virtual environment).
*   **`args`:** The crucial part is providing the full, absolute path to `run_server.py`.
*   **`api`:** Ensure this matches the host and port where Uvicorn runs the FastAPI app (default is `http://localhost:8000`).
*   **Secrets:** Note that your Google Client ID and Client Secret remain in the project's `.env` file, not in this MCP configuration.
*   **Path Separators:** Use forward slashes (`/`) or escaped backslashes (`\\`) for paths in JSON.

Consult your specific MCP client's documentation for the exact configuration file location and syntax.

## Development

*   (Add details about testing, contribution guidelines later)

## Next Steps

*   Implement core calendar action endpoints (Task 2).
*   Implement advanced features (Task 3).
*   Add testing (Task 4). 