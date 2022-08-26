"""The Vault integration."""

from ast import Pass
import requests
import logging

from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.auth.models import Credentials
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.helpers import (
    device_registry,
    storage,
    network
)
from homeassistant.auth.const import (
    GROUP_ID_ADMIN
    
)

from .const import (
    ATTR_COORDINATOR,
    ATTR_HOMEASSISTNAT_TOKEN,
    ATTR_VAULT_CACHE_LOGIN,
    CONFIG_VAULT_ADDR,
    CONFIG_VAULT_EMAIL,
    CONFIG_VAULT_PASSWORD,
    CONFIG_VAULT_USERNAME,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(minutes=2)

async def async_setup_entry( hass: HomeAssistant, config_entry: ConfigEntry ) -> bool:
    """Set up entry."""

    hass.data.setdefault(DOMAIN, { } )
    hass.data[DOMAIN][config_entry.entry_id] = {}
    hass.data[DOMAIN][config_entry.entry_id][CONFIG_VAULT_ADDR] = config_entry.data["addr"]
    hass.data[DOMAIN][config_entry.entry_id][CONFIG_VAULT_USERNAME] = config_entry.data["username"]
    hass.data[DOMAIN][config_entry.entry_id][CONFIG_VAULT_PASSWORD] = config_entry.data["password"]
    hass.data[DOMAIN][config_entry.entry_id][CONFIG_VAULT_EMAIL] = config_entry.data["email"]
    hass.data[DOMAIN][config_entry.entry_id][ATTR_VAULT_CACHE_LOGIN] = None
    hass.data[DOMAIN][config_entry.entry_id][ATTR_HOMEASSISTNAT_TOKEN] = None
    
    coordinator = VaultCoordinator(hass,config_entry)

    await coordinator.async_config_entry_first_refresh()
    await coordinator.async_create_access_token()
    dr = device_registry.async_get(hass)

    dr.async_get_or_create(
        config_entry_id=config_entry.entry_id,
        identifiers={(const.DOMAIN, coordinator.id )},
        name="Vault",
        model="Vault",
        sw_version="1.00",
        manufacturer="@jadson179",
    )

    await coordinator.async_sync_data_with_vault()

    return True

class VaultCoordinator(DataUpdateCoordinator):
    def __init__(self, hass:HomeAssistant, config_entry:ConfigEntry):
        
        self.id = config_entry.unique_id
        self.hass = hass
        self.authenticated = False

        super().__init__(hass, _LOGGER, name=const.DOMAIN,update_interval=SCAN_INTERVAL)
    
    async def _async_update_data(self):
        await self.hass.async_add_executor_job(self._authetication)
        return True

    async def authetication(self):
        await self.hass.async_add_executor_job(self._authetication)

    def _authetication(self):
        try:
            url = f"{self.config_entry.data[CONFIG_VAULT_ADDR]}/v1/auth/userpass/login/{self.config_entry.data[CONFIG_VAULT_USERNAME]}"
            payload = {"password": self.config_entry.data[CONFIG_VAULT_PASSWORD]}            
            headers = {"Content-Type": "application/json"}
            response = requests.request("POST", url, json=payload, headers=headers)
            
            self.hass.data[DOMAIN][self.config_entry.entry_id][ATTR_VAULT_CACHE_LOGIN] = response.json()
            self.authenticated = True

            _LOGGER.info(f"Response Status Code: {response.status_code}")
            _LOGGER.info(f"Response Body: {response.text}")
        except: 
            _LOGGER.error(f"Response Status Code: {response.status_code}")
            _LOGGER.error(f"Response Body: {response.text}")
    
    async def async_create_access_token(self):

        store = storage.Store(hass=self.hass,version=1,key=DOMAIN)
        data = await store.async_load()

        if data is None:
            data = {}

        user = None
        if "vault_user" in data:

            user = await self.hass.auth.async_get_user(data["vault_user"])
            credential = Credentials(
                auth_provider_type="homeassistant",
                auth_provider_id=None,
                data={"username": "admin"},
                is_new=False
            )
            user.credentials.append(credential)

        if user is None:

            user = await self.hass.auth.async_create_system_user(
                "Vault", group_ids=[GROUP_ID_ADMIN]
            )
            data["vault_user"] = user.id
            await store.async_save(data)
        
        refresh_token = await self.hass.auth.async_create_refresh_token(
            user,
            #Vault will be fine as long as we restart once every 5 years
            access_token_expiration=timedelta(days=365 * 10),
            client_name="vault"    
        )
        
        # Create long lived access token
        self.hass.data[DOMAIN][self.config_entry.entry_id][ATTR_HOMEASSISTNAT_TOKEN] = self.hass.auth.async_create_access_token(refresh_token)

        # Clear all other refresh tokens
        #for token in list(user.refresh_tokens.values()):
        #    if token.id != refresh_token.id:
        #        await self.hass.auth.async_remove_refresh_token(token)

    async def async_sync_data_with_vault(self):
        await self.hass.async_add_executor_job(self._sync_data_with_vault)

    def _sync_data_with_vault(self):
        try:
            vault_token = self.hass.data[DOMAIN][self.config_entry.entry_id][ATTR_VAULT_CACHE_LOGIN]["auth"]["client_token"]
            email = self.hass.data[DOMAIN][self.config_entry.entry_id][CONFIG_VAULT_EMAIL]
            homeassistant_token = self.hass.data[DOMAIN][self.config_entry.entry_id][ATTR_HOMEASSISTNAT_TOKEN]
            homeassistant_external_url = network._get_external_url(self.hass)

            url = f"{self.config_entry.data[CONFIG_VAULT_ADDR]}/v1/smarthomes/data/{email}"
            
            payload = { 
                "data": 
                    { "url": homeassistant_external_url, "token": homeassistant_token }
                }            
            
            headers = {
                "Content-Type": "application/json",
                "X-Vault-Token": vault_token 
            }
            
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            _LOGGER.info("Success in synchronization of data with Vault")
        except network.NoURLAvailableError: 
            _LOGGER.error("An URL to the Home Assistant instance is not available")

        except requests.HTTPError as error:
            _LOGGER.error(f"HTTPError: {error}")

        except BaseException as error:
            _LOGGER.error(f"Failed in synchronization of data with Vault: {error}")
