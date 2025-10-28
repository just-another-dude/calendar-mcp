"""
Token Manager for OpenAI Platform Integration
Handles automatic OAuth token refresh for production use.
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Optional
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

logger = logging.getLogger(__name__)

class TokenManager:
    """Manages OAuth tokens for OpenAI Platform integration with automatic refresh."""

    def __init__(self, token_file: str = "openai_platform_token.json"):
        self.token_file = token_file
        self._cached_credentials: Optional[Credentials] = None
        self._last_refresh: Optional[datetime] = None

    def load_token_info(self) -> Optional[dict]:
        """Load token information from file."""
        if not os.path.exists(self.token_file):
            logger.warning(f"Token file {self.token_file} not found")
            return None

        try:
            with open(self.token_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load token file: {e}")
            return None

    def save_token_info(self, token_info: dict) -> bool:
        """Save token information to file."""
        try:
            with open(self.token_file, 'w') as f:
                json.dump(token_info, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Failed to save token file: {e}")
            return False

    def create_credentials_from_token(self, access_token: str) -> Optional[Credentials]:
        """Create Google credentials from access token, with refresh capability."""
        token_info = self.load_token_info()

        if not token_info:
            logger.warning("No token info available for refresh")
            # Use environment variables to create complete credentials even without stored token info
            client_id = os.getenv('GOOGLE_CLIENT_ID')
            client_secret = os.getenv('GOOGLE_CLIENT_SECRET')

            if client_id and client_secret:
                logger.info("Creating credentials using environment variables")
                return Credentials(
                    token=access_token,
                    refresh_token=None,  # Will be None for fresh tokens, but field is present
                    token_uri="https://oauth2.googleapis.com/token",
                    client_id=client_id,
                    client_secret=client_secret,
                    scopes=['https://www.googleapis.com/auth/calendar']
                )
            else:
                logger.error("No token info and missing OAuth environment variables")
                # Create basic credentials without refresh capability as last resort
                return Credentials(token=access_token)

        try:
            # Create credentials with refresh capability
            credentials = Credentials(
                token=access_token,
                refresh_token=token_info.get('refresh_token'),
                token_uri="https://oauth2.googleapis.com/token",
                client_id=token_info.get('client_id'),
                client_secret=token_info.get('client_secret'),
                scopes=['https://www.googleapis.com/auth/calendar']
            )

            # Set expiry if available
            expires_at_str = token_info.get('expires_at')
            if expires_at_str:
                try:
                    expires_at = datetime.fromisoformat(expires_at_str.replace('Z', '+00:00'))
                    credentials.expiry = expires_at
                except Exception as e:
                    logger.warning(f"Could not parse expiry time: {e}")

            return credentials

        except Exception as e:
            logger.error(f"Failed to create credentials: {e}")
            return None

    def get_valid_credentials(self, access_token: str) -> Optional[Credentials]:
        """Get valid credentials, refreshing if necessary."""

        # Check if we can reuse cached credentials
        if (self._cached_credentials and
            self._cached_credentials.valid and
            self._cached_credentials.token == access_token):
            return self._cached_credentials

        # Create credentials from the provided token
        credentials = self.create_credentials_from_token(access_token)

        if not credentials:
            return None

        # Check if token needs refresh
        if not credentials.valid:
            if credentials.refresh_token:
                try:
                    logger.info("Token expired, attempting refresh...")
                    credentials.refresh(Request())

                    if credentials.valid:
                        logger.info("Token refreshed successfully")

                        # Update stored token info
                        self.update_stored_token(credentials)

                        # Cache the refreshed credentials
                        self._cached_credentials = credentials
                        self._last_refresh = datetime.utcnow()

                        return credentials
                    else:
                        logger.error("Token refresh failed - credentials still invalid")
                        return None

                except Exception as e:
                    logger.error(f"Token refresh failed: {e}")
                    return None
            else:
                logger.warning("Token expired and no refresh token available")
                return None

        # Cache valid credentials
        self._cached_credentials = credentials
        return credentials

    def update_stored_token(self, credentials: Credentials) -> bool:
        """Update stored token information after refresh."""
        token_info = self.load_token_info()

        if not token_info:
            logger.warning("No existing token info to update")
            return False

        # Update with new token information
        token_info.update({
            "access_token": credentials.token,
            "expires_at": credentials.expiry.isoformat() if credentials.expiry else None,
            "refreshed_at": datetime.utcnow().isoformat()
        })

        return self.save_token_info(token_info)

    def get_token_status(self) -> dict:
        """Get current token status information."""
        token_info = self.load_token_info()

        if not token_info:
            return {
                "status": "no_token_file",
                "message": "No token file found"
            }

        access_token = token_info.get('access_token')
        expires_at_str = token_info.get('expires_at')
        refresh_token = token_info.get('refresh_token')

        status = {
            "has_access_token": bool(access_token),
            "has_refresh_token": bool(refresh_token),
            "token_file": self.token_file
        }

        if expires_at_str:
            try:
                expires_at = datetime.fromisoformat(expires_at_str.replace('Z', '+00:00'))
                now = datetime.utcnow().replace(tzinfo=expires_at.tzinfo)

                status.update({
                    "expires_at": expires_at.isoformat(),
                    "expires_in_seconds": (expires_at - now).total_seconds(),
                    "is_expired": expires_at <= now
                })
            except Exception as e:
                status["expiry_parse_error"] = str(e)

        return status

# Global token manager instance
token_manager = TokenManager()

def get_production_credentials(access_token: str) -> Optional[Credentials]:
    """Get valid credentials for production use, with automatic refresh."""
    return token_manager.get_valid_credentials(access_token)