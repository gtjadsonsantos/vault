"""Config flow for the Vault."""

from cmath import inf
import secrets
from typing import Any, Optional
from aioesphomeapi import Dict
from homeassistant import config_entries
import voluptuous as vol
import logging

from .const import (
    CONFIG_VAULT_ADDR,
    CONFIG_VAULT_EMAIL,
    CONFIG_VAULT_PASSWORD,
    CONFIG_VAULT_USERNAME,
    DEFAULT_CONFIG_VAULT_ADDR,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


class VaultConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for Vault."""

    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_PUSH
    VERSION = 1

    async def async_step_user(self, info: Optional[Dict[str, Any]] = None):
        """Handle a flow initialized by the user."""
        errors = {}

        id = secrets.token_hex(6)
        
        await self.async_set_unique_id(id)
        self._abort_if_unique_id_configured()

        if info is not None:
            return self.async_create_entry(title="Vault", data=info)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONFIG_VAULT_ADDR,
                        description="Address of the Vault server",
                        default=DEFAULT_CONFIG_VAULT_ADDR,
                    ): str,
                    vol.Required(
                        CONFIG_VAULT_USERNAME,
                        description="Username",
                    ): str,
                    vol.Required(
                        CONFIG_VAULT_PASSWORD,
                        description="Password",
                    ): str,
                    vol.Required(
                        CONFIG_VAULT_EMAIL,
                        description="E-mail",
                    ): str,
                }
            ),
            errors=errors,
        )
