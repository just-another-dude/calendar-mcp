"""
Google Service Account Authentication for Calendar MCP Server
Provides robust server-to-server authentication without OAuth refresh token limitations.
"""

import os
import json
import logging
from typing import Optional, Dict, Any
from google.oauth2 import service_account
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)

class ServiceAccountManager:
    """Manages Google Service Account authentication for Calendar API access."""

    def __init__(self):
        self.service_account_file = os.getenv('GOOGLE_SERVICE_ACCOUNT_FILE', 'service-account-key.json')
        self.service_account_json = os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON')
        self.scopes = ['https://www.googleapis.com/auth/calendar']
        self._cached_credentials: Optional[service_account.Credentials] = None

    def load_service_account_credentials(self) -> Optional[service_account.Credentials]:
        """Load Google Service Account credentials from file or environment variable."""

        try:
            # Try loading from environment variable first (Railway deployment)
            if self.service_account_json:
                logger.info("🔐 Loading service account credentials from environment variable")
                service_account_info = json.loads(self.service_account_json)
                credentials = service_account.Credentials.from_service_account_info(
                    service_account_info, scopes=self.scopes
                )
                logger.info("✅ Service account credentials loaded from environment")
                return credentials

            # Try loading from file (local development)
            elif os.path.exists(self.service_account_file):
                logger.info(f"🔐 Loading service account credentials from file: {self.service_account_file}")
                credentials = service_account.Credentials.from_service_account_file(
                    self.service_account_file, scopes=self.scopes
                )
                logger.info("✅ Service account credentials loaded from file")
                return credentials

            else:
                logger.warning("❌ No service account credentials found")
                logger.info(f"   - Environment variable GOOGLE_SERVICE_ACCOUNT_JSON: {'Set' if self.service_account_json else 'Not set'}")
                logger.info(f"   - Service account file {self.service_account_file}: {'Found' if os.path.exists(self.service_account_file) else 'Not found'}")
                return None

        except json.JSONDecodeError as e:
            logger.error(f"❌ Invalid JSON in service account credentials: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ Failed to load service account credentials: {e}")
            return None

    def get_service_account_credentials(self) -> Optional[service_account.Credentials]:
        """Get valid service account credentials, loading if necessary."""

        # Return cached credentials if available and valid
        if self._cached_credentials and self._cached_credentials.valid:
            return self._cached_credentials

        # Load fresh credentials
        credentials = self.load_service_account_credentials()
        if not credentials:
            return None

        # Refresh credentials if needed
        if not credentials.valid:
            try:
                logger.info("🔄 Refreshing service account credentials...")
                credentials.refresh(Request())
                logger.info("✅ Service account credentials refreshed successfully")
            except Exception as e:
                logger.error(f"❌ Failed to refresh service account credentials: {e}")
                return None

        # Cache and return valid credentials
        self._cached_credentials = credentials
        return credentials

    def impersonate_user(self, user_email: str) -> Optional[service_account.Credentials]:
        """Create impersonated credentials for a specific user (requires domain-wide delegation)."""

        base_credentials = self.get_service_account_credentials()
        if not base_credentials:
            logger.error("❌ Cannot impersonate user: no service account credentials available")
            return None

        try:
            logger.info(f"👤 Creating impersonated credentials for user: {user_email}")
            impersonated_credentials = base_credentials.with_subject(user_email)

            # Test the impersonated credentials
            if not impersonated_credentials.valid:
                impersonated_credentials.refresh(Request())

            logger.info(f"✅ Successfully created impersonated credentials for {user_email}")
            return impersonated_credentials

        except Exception as e:
            logger.error(f"❌ Failed to create impersonated credentials for {user_email}: {e}")
            logger.warning("   This usually means domain-wide delegation is not configured correctly")
            return None

    def create_calendar_service(self, user_email: Optional[str] = None) -> Optional[Any]:
        """Create a Google Calendar service client using service account authentication."""

        try:
            if user_email:
                # Use domain-wide delegation to impersonate the user
                credentials = self.impersonate_user(user_email)
                if not credentials:
                    logger.error(f"❌ Cannot create calendar service: failed to impersonate {user_email}")
                    return None
            else:
                # Use service account directly (for service account's own calendar)
                credentials = self.get_service_account_credentials()
                if not credentials:
                    logger.error("❌ Cannot create calendar service: no service account credentials")
                    return None

            logger.info("🗓️ Creating Google Calendar service...")
            service = build('calendar', 'v3', credentials=credentials)
            logger.info("✅ Google Calendar service created successfully")
            return service

        except Exception as e:
            logger.error(f"❌ Failed to create calendar service: {e}")
            return None

    def validate_service_account_setup(self) -> Dict[str, Any]:
        """Validate the service account setup and return diagnostic information."""

        diagnostic_info = {
            "service_account_available": False,
            "credentials_valid": False,
            "calendar_service_working": False,
            "details": {}
        }

        # Check if service account credentials are available
        credentials = self.load_service_account_credentials()
        if credentials:
            diagnostic_info["service_account_available"] = True
            diagnostic_info["details"]["credentials_source"] = (
                "environment_variable" if self.service_account_json else "file"
            )

            # Check if credentials are valid
            if credentials.valid:
                diagnostic_info["credentials_valid"] = True
            else:
                try:
                    credentials.refresh(Request())
                    diagnostic_info["credentials_valid"] = credentials.valid
                except Exception as refresh_error:
                    diagnostic_info["details"]["refresh_error"] = str(refresh_error)

            # Test calendar service creation
            if diagnostic_info["credentials_valid"]:
                try:
                    service = build('calendar', 'v3', credentials=credentials)
                    # Try a simple API call to verify it works
                    calendar_list = service.calendarList().list(maxResults=1).execute()
                    diagnostic_info["calendar_service_working"] = True
                    diagnostic_info["details"]["calendar_count"] = len(calendar_list.get('items', []))
                except Exception as service_error:
                    diagnostic_info["details"]["service_error"] = str(service_error)
        else:
            diagnostic_info["details"]["error"] = "No service account credentials found"

        return diagnostic_info

# Global service account manager instance
service_account_manager = ServiceAccountManager()

def get_service_account_credentials() -> Optional[service_account.Credentials]:
    """Get valid service account credentials for Calendar API access."""
    return service_account_manager.get_service_account_credentials()

def create_calendar_service_for_user(user_email: str) -> Optional[Any]:
    """Create a Calendar service for a specific user using domain-wide delegation."""
    return service_account_manager.create_calendar_service(user_email)

def create_calendar_service() -> Optional[Any]:
    """Create a Calendar service using service account credentials."""
    return service_account_manager.create_calendar_service()

def validate_service_account() -> Dict[str, Any]:
    """Validate service account setup and return diagnostic information."""
    return service_account_manager.validate_service_account_setup()