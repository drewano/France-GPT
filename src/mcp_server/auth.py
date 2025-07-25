import os
import logging
import time
from typing import Generator, Union
import httpx


from src.core.config import BearerAuthConfig, OAuth2ClientCredentialsConfig


class OAuth2ClientCredentialsAuth(httpx.Auth):
    def __init__(self, config: OAuth2ClientCredentialsConfig, logger: logging.Logger):
        self.config = config
        self.logger = logger
        self._access_token: str | None = None
        self._token_expiry_time: float = 0.0

    def _get_new_token(self):
        client_id = os.getenv(self.config.client_id_env_var)
        client_secret = os.getenv(self.config.client_secret_env_var)

        if not client_id or not client_secret:
            self.logger.error(
                "Client ID or client secret not found in environment variables."
            )
            return

        try:
            response = httpx.post(
                self.config.token_url,
                data={
                    "grant_type": "client_credentials",
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "scope": self.config.scope,
                },
                timeout=10.0,  # Add a timeout to prevent hanging requests
            )
            response.raise_for_status()
            token_data = response.json()
            self._access_token = token_data["access_token"]
            expires_in = token_data.get("expires_in", 3600)
            self._token_expiry_time = time.time() + expires_in - 60  # 60 seconds buffer
            self.logger.info("Successfully fetched new OAuth2 token.")
        except httpx.RequestError as e:
            self.logger.error(f"Error requesting OAuth2 token: {e}")
            self._access_token = None
            self._token_expiry_time = 0.0
        except KeyError:
            self.logger.error("Access token not found in OAuth2 response.")
            self._access_token = None
            self._token_expiry_time = 0.0

    def auth_flow(
        self, request: httpx.Request
    ) -> Generator[httpx.Request, httpx.Response, None]:
        if not self._access_token or time.time() >= self._token_expiry_time:
            self.logger.info(
                "OAuth2 token expired or not present, requesting new token..."
            )
            self._get_new_token()

        if self._access_token:
            request.headers["Authorization"] = f"Bearer {self._access_token}"
        else:
            self.logger.warning(
                "No OAuth2 access token available, proceeding without authentication."
            )
        yield request


class BearerAuth(httpx.Auth):
    def __init__(self, api_key: str):
        self.api_key = api_key

    def auth_flow(
        self, request: httpx.Request
    ) -> Generator[httpx.Request, httpx.Response, None]:
        request.headers["Authorization"] = f"Bearer {self.api_key}"
        yield request


def create_auth_handler(
    auth_config: Union[BearerAuthConfig, OAuth2ClientCredentialsConfig],
    logger: logging.Logger,
) -> httpx.Auth | None:
    if isinstance(auth_config, BearerAuthConfig):
        api_key = os.getenv(auth_config.api_key_env_var)
        if not api_key:
            logger.error(
                f"API key not found for environment variable: {auth_config.api_key_env_var}"
            )
            return None
        return BearerAuth(api_key)
    elif isinstance(auth_config, OAuth2ClientCredentialsConfig):
        return OAuth2ClientCredentialsAuth(auth_config, logger)
    else:
        logger.warning(f"Unsupported authentication type: {type(auth_config)}")
        return None
