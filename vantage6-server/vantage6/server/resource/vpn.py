import logging
import os
import json
import base64
import hashlib
import re
import urllib.parse as urlparse

from http import HTTPStatus
from flask.globals import g
from flask import request
from flask_restful import Api
import requests
from requests_oauthlib import OAuth2Session

from vantage6.common import logger_name
from vantage6.server.resource import with_node, ServicesResources
from vantage6.server.resource.common.input_schema import VPNConfigUpdateInputSchema
from vantage6.server.exceptions import VPNConfigException, VPNPortalAuthException


module_name = logger_name(__name__)
log = logging.getLogger(module_name)


def setup(api: Api, api_base: str, services: dict) -> None:
    """
    Setup the collaboration resource.

    Parameters
    ----------
    api : Api
        Flask restful api instance
    api_base : str
        Base url of the api
    services : dict
        Dictionary with services required for the resource endpoints
    """
    path = "/".join([api_base, module_name])
    log.info(f'Setting up "{path}" and subdirectories')

    api.add_resource(
        VPNConfig,
        path,
        endpoint="vpn_config",
        methods=("GET",),
        resource_class_kwargs=services,
    )

    api.add_resource(
        VPNConfig,
        path + "/update",
        endpoint="vpn_config_update",
        methods=("POST",),
        resource_class_kwargs=services,
    )


vpn_config_schema = VPNConfigUpdateInputSchema()


# ------------------------------------------------------------------------------
# Resources / API's
# ------------------------------------------------------------------------------
class VPNConfig(ServicesResources):
    @with_node
    def get(self):
        """Get OVPN configuration file
        ---
        description: >-
          Returns the contents of an OVPN configuration file. This
          configuration allows the node to connect to the VPN server.\n

          This endpoint is not accessible for users, but only for
          authenticated nodes.

        responses:
          200:
            description: Ok
          500:
            description: Error in server VPN configuration, or in authorizing
              to VPN portal to obtain VPN configuration file
          501:
            description: This server has no VPN service
          503:
            description: The VPN server cannot be reached

        security:
            - bearerAuth: []

        tags: ["VPN"]

        """
        # check if the VPN server is configured
        if not self._is_server_configured():
            return {
                "msg": "This server does not support VPN"
            }, HTTPStatus.NOT_IMPLEMENTED

        # obtain VPN config by calling EduVPN API
        try:
            vpn_connector = EduVPNConnector(self.config["vpn_server"])
            ovpn_config = vpn_connector.get_ovpn_config()
        except VPNPortalAuthException as e:
            log.error("Could not obtain VPN configuration file")
            log.error(e)
            return {
                "msg": (
                    "Could not obtain VPN configuration because the vantage6 "
                    "server could not authorize to the VPN portal. Please "
                    "contact your server administrator."
                )
            }, HTTPStatus.INTERNAL_SERVER_ERROR
        except VPNConfigException as e:
            log.error("Could not obtain VPN configuration file")
            log.error(e)
            return {
                "msg": (
                    "Could not obtain VPN configuration because the "
                    "vantage6 server is not properly configured for VPN. "
                    "Please contact your server administrator."
                )
            }, HTTPStatus.INTERNAL_SERVER_ERROR
        except requests.ConnectionError as e:
            log.critical(
                f"Node <{g.node.id}> tries to obtain a vpn config. "
                "However the VPN server is unreachable!"
            )
            log.debug(e)
            return {
                "msg": "VPN server unreachable. Please contact your server"
                " administrator"
            }, HTTPStatus.SERVICE_UNAVAILABLE

        return {"ovpn_config": ovpn_config}, HTTPStatus.OK

    @with_node
    def post(self):
        """Update an OVPN configuration file
        ---
        description: >-
          Returns an OVPN configuration file with renewed keypair. This
          allows the node to connect to the VPN server again if the keypair was
          invalidated.\n

          This endpoint is not accessible for users, but only for
          authenticated nodes.

        requestBody:
          content:
            application/json:
              schema:
                properties:
                  vpn_config:
                    type: string
                    description: Current VPN config file contents with expired
                      keypair

        responses:
          200:
            description: Ok
          400:
            description: No VPN configuration found in request body
          500:
            description: Error in server VPN configuration, or in authorizing
              to VPN portal to obtain VPN configuration file
          501:
            description: This server has no VPN service
          503:
            description: The VPN server cannot be reached

        security:
            - bearerAuth: []

        tags: ["VPN"]

        """
        body = request.get_json()

        # validate request body
        errors = vpn_config_schema.validate(body)
        if errors:
            return {
                "msg": "Request body is incorrect",
                "errors": errors,
            }, HTTPStatus.BAD_REQUEST

        # check if the VPN server is configured
        if not self._is_server_configured():
            return {
                "msg": "This server does not support VPN"
            }, HTTPStatus.NOT_IMPLEMENTED

        # refresh keypair by calling EduVPN API
        vpn_config = body.get("vpn_config")
        try:
            vpn_connector = EduVPNConnector(self.config["vpn_server"])
            ovpn_config = vpn_connector.refresh_keypair(vpn_config)
        except VPNPortalAuthException as e:
            log.error("Could not obtain VPN configuration file")
            log.error(e)
            return {
                "msg": "Could not obtain VPN configuration because the "
                + "vantage6 server could not authorize to the VPN portal."
            }, HTTPStatus.INTERNAL_SERVER_ERROR
        except VPNConfigException as e:
            log.error("Could not obtain VPN configuration file")
            log.error(e)
            return {
                "msg": (
                    "Could not obtain VPN configuration because the "
                    "vantage6 server is not properly configured for VPN. "
                    "Please contact your server administrator."
                )
            }, HTTPStatus.INTERNAL_SERVER_ERROR
        except requests.ConnectionError as e:
            log.critical(
                f"Node <{g.node.id}> tries to obtain a VPN config. "
                "However the VPN server is unreachable!"
            )
            log.debug(e)
            return {"msg": "VPN server unreachable"}, HTTPStatus.SERVICE_UNAVAILABLE

        return {"ovpn_config": ovpn_config}, HTTPStatus.OK

    def _is_server_configured(self) -> bool:
        """Check if vpn server is available in configuration"""
        if "vpn_server" not in self.config:
            log.debug(
                f"Node <{g.node.id}> tries to obtain a vpn config but "
                "this server has not configured a VPN server!"
            )
            return False
        return True


class EduVPNConnector:
    def __init__(self, vpn_config) -> None:
        """
        Provides API access to the VPN server

        Parameters
        ----------
        vpn_config : dict
            Contains the VPN server info
        """
        self.config = vpn_config
        self.session = OAuth2Session(vpn_config["client_id"])

        self.check_config()

        self.PORTAL_URL = (
            self.config["url"][:-1]
            if self.config["url"].endswith("/")
            else self.config["url"]
        )
        self.API_URL = f"{self.PORTAL_URL}/api.php"

    def check_config(self) -> None:
        """
        Check if any keys that have to be present in the VPN configuration
        are missing. Raises an error if keys are missing.
        """
        for key in [
            "url",
            "portal_username",
            "portal_userpass",
            "client_id",
            "client_secret",
            "redirect_url",
        ]:
            if not self.config.get(key):
                raise VPNConfigException(
                    f"The '{key}' parameter has not been defined in your "
                    "vpn_server settings. Please adjust your configuration "
                    "file."
                )

    def get_ovpn_config(self) -> str:
        """
        Obtain a configuration file from the VPN server. This file contains
        all details needed for a node to connect to the VPN server.

        Returns
        -------
        str (ovpn format)
            Open-vpn configuration file
        """

        # obtain access token if not set
        self.set_access_token()

        # get the user's profile id
        log.debug("Getting EduVPN profile information")
        profile = self.get_profile()
        profile_id = profile["profile_list"]["data"][0]["profile_id"]

        # get the OVPN configuration for the selected user profile
        log.debug("Obtaining OpenVPN configuration template")
        ovpn_config = self.get_config(profile_id)

        # add the keypair
        return self._add_key_pair(ovpn_config=ovpn_config)

    def refresh_keypair(self, ovpn_config: str) -> str:
        """
        Obtain a new keypair from the VPN server and refreshes the keypair so
        that the configuration file can be used to connect the VPN server
        again.

        Parameters
        ----------
        ovpn_config: str
            Current OpenVPN configuration from which the keypair will be
            refreshed

        Returns
        -------
        str (ovpn format)
            Open-vpn configuration file
        """
        # obtain access token if not set
        self.set_access_token()

        # remove current keypair from the file
        ovpn_config = self._remove_keypair(ovpn_config)

        # add the keypair
        return self._add_key_pair(ovpn_config=ovpn_config)

    def _add_key_pair(self, ovpn_config: str) -> str:
        """
        Obtain a keypair from the VPN server and add it to the configuration

        Parameters
        ----------
        ovpn_config: str
            OpenVPN configuration without a keypair

        Returns
        -------
        str (ovpn format)
            Open-vpn configuration file content
        """
        # get a key and certificate for the client
        log.debug("Obtaining OpenVPN key-pair")
        cert, key = self.get_key_pair()

        # add the client credentials to the ovpn file
        log.debug("Parsing VPN configuration file")
        ovpn_config = self._insert_keypair_into_config(ovpn_config, cert, key)
        return ovpn_config

    def set_access_token(self) -> None:
        """Obtain an access token to enable access to EduVPN API"""
        if self.session.token:
            log.debug("EduVPN access token already acquired")
            return
        # set PKCE data (code challenge and code verifier)
        log.debug("Setting PKCE challenge")
        self._set_pkce()
        # login to the EduVPN portal
        log.debug("Logging in to EduVPN portal")
        self._login()
        # call the authorization route of EduVPN to get authorization code
        log.debug("Authorizing to EduVPN portal")
        self._authorize()
        # use authorization code to obtain token
        log.debug("Obtaining token from EduVPN portal")
        self.session.token = self._get_token()

    def _set_pkce(self) -> None:
        """Generate PKCE code verifier and challenge"""
        # set PKCE verifier
        self.code_verifier = base64.urlsafe_b64encode(os.urandom(40)).decode("utf-8")
        self.code_verifier = re.sub("[^a-zA-Z0-9]+", "", self.code_verifier)

        # set PKCE challenge based on the verifier
        self.code_challenge = hashlib.sha256(
            self.code_verifier.encode("utf-8")
        ).digest()
        self.code_challenge = base64.urlsafe_b64encode(self.code_challenge).decode(
            "utf-8"
        )
        self.code_challenge = self.code_challenge.replace("=", "")

    def _login(self) -> None:
        """Login to the EduVPN user portal in the requests session"""
        post_data = {
            "userName": self.config["portal_username"],
            "userPass": self.config["portal_userpass"],
            "_form_auth_redirect_to": self.config["url"],
        }
        response = self.session.post(
            f"{self.PORTAL_URL}/_form/auth/verify", data=post_data
        )
        # Note: if we give the wrong vpn portal password/username, this request
        # succeeds but authorization fails at next step. Only passing the wrong
        # portal url leads to an erroneous status immediately
        if not (200 <= response.status_code < 300):
            raise VPNPortalAuthException(
                "Authenticating to EduVPN failed. Please check the 'url' of "
                "your VPN server in the server your configuration file."
            )

    def _authorize(self) -> None:
        """Call authorization route of EduVPN to get authorization code"""
        params = {
            "client_id": self.config["client_id"],
            "redirect_uri": self.config["redirect_url"],
            "response_type": "code",
            "scope": "config",
            "state": "some_string",
            "code_challenge_method": "S256",
            "code_challenge": self.code_challenge,
        }

        # Call authorization route, but prevent redirect. By preventing the
        # redirect, the authorization code can be used in the current session
        # which allows us to use the PKCE code verifier without having to save
        # it in e.g. database or session state.
        response = self.session.get(
            f"{self.PORTAL_URL}/_oauth/authorize", params=params, allow_redirects=False
        )
        if not (200 <= response.status_code < 400):
            raise VPNPortalAuthException(
                "Authenticating to EduVPN failed. Please check the "
                "'client_id' and 'redirect_url' settings in your server "
                "configuration file."
            )
        elif "Location" not in response.headers:
            raise VPNPortalAuthException(
                "Authenticating to EduVPN failed. Please check the following "
                "settings of your configuration file: portal_username and "
                "portal_userpass."
            )

        # get the authorization token from the request headers
        redirected_uri = response.headers["Location"]
        parsed_url = urlparse.urlparse(redirected_uri)
        self.code = urlparse.parse_qs(parsed_url.query)["code"]

    def _get_token(self) -> dict:
        """
        Use authorization code to obtain a token from the EduVPN portal

        Returns
        -------
        Dict:
            EduVPN portal token
        """
        data = {
            "code": self.code,
            "grant_type": "authorization_code",
            "redirect_uri": self.config["redirect_url"],
            "client_id": self.config["client_id"],
            "client_secret": self.config["client_secret"],
            "code_verifier": self.code_verifier,
        }

        r = self.session.post(
            f"{self.PORTAL_URL}/oauth.php/token",
            data=data,
            auth=(self.config["client_id"], self.config["client_secret"]),
        )
        if not (200 <= r.status_code < 400):
            raise VPNPortalAuthException(
                "Authenticating to EduVPN failed. Please check the "
                "'client_secret' setting in your server configuration file."
            )
        return json.loads(r.content.decode("utf-8"))

    def _insert_keypair_into_config(self, ovpn_config: str, cert: str, key: str) -> str:
        """
        Insert the client's key pair into the correct place into the OVPN file
        (i.e. before the <tls-crypt> field)

        Parameters
        ----------
        ovpn_config : str
            The OVPN configuration information without client keys
        cert : str
            The client's certificate
        key: str
            The client's private key

        Returns
        -------
        str
            A complete OVPN config file contents, including client's key-pair
        """
        insert_loc = ovpn_config.find("<tls-crypt>")
        return (
            ovpn_config[:insert_loc]
            + "<cert>\n"
            + cert
            + "\n</cert>\n"
            + "<key>\n"
            + key
            + "\n</key>\n"
            + ovpn_config[insert_loc:]
        )

    def _remove_keypair(self, ovpn_config: str) -> str:
        """
        Remove the keypair from the configuration

        Parameters
        ----------
        ovpn_config : str
            The OVPN configuration information with the key pair

        Returns
        -------
        str (ovpn format)
            Open-vpn configuration file without key pair
        """
        # keypair starts at '<cert>' and ends at '</key>\n'
        start_remove_pos = ovpn_config.find("<cert>")
        end_key = "</key>\n"
        end_remove_pos = ovpn_config.find(end_key)
        return (
            ovpn_config[0:start_remove_pos]
            + ovpn_config[end_remove_pos + len(end_key) :]
        )

    def get_profile(self) -> dict:
        """
        Call the profile_list route of EduVPN API

        Returns
        -------
        Dict
            Response content of the EduVPN /profile_list route
        """
        response = self.session.get(f"{self.API_URL}/profile_list")
        return json.loads(response.content.decode("utf-8"))

    def get_config(self, profile_id: str) -> str:
        """Call the profile_config route of EduVPN API

        Parameters
        ----------
        profile_id: str
            An EduVPN user's profile_id obtained from the /profile_list route

        Returns
        -------
        str
            OpenVPN configuration file content (without key pair)
        """
        params = {"profile_id": profile_id}
        response_config = self.session.get(
            f"{self.API_URL}/profile_config", params=params
        )
        return response_config.content.decode("utf-8")

    def get_key_pair(self) -> tuple[str, str]:
        """
        Call the create_keypair route of EduVPN API

        Returns
        -------
        Tuple(str, str):
            The certificate and the private key that together form the key pair
        """
        response_keypair = self.session.post(f"{self.API_URL}/create_keypair")
        ovpn_keypair = json.loads(response_keypair.content.decode("utf-8"))
        cert = ovpn_keypair["create_keypair"]["data"]["certificate"]
        key = ovpn_keypair["create_keypair"]["data"]["private_key"]
        return cert, key
