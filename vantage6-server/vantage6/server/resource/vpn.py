import base64
import hashlib
import logging
import os
import re
from http import HTTPStatus

import requests
from flask import request
from flask.globals import g
from flask_restful import Api
from requests_oauthlib import OAuth2Session

from vantage6.common import logger_name
from vantage6.server.exceptions import VPNConfigException, VPNPortalAuthException
from vantage6.server.resource import with_node, ServicesResources
from vantage6.server.resource.common.input_schema import VPNConfigUpdateInputSchema

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
            log.exception(e)
            return {
                "msg": "VPN server unreachable. Please contact your server"
                " administrator"
            }, HTTPStatus.SERVICE_UNAVAILABLE

        return {"ovpn_config": ovpn_config}, HTTPStatus.OK

    def _is_server_configured(self) -> bool:
        """Check if vpn server is available in configuration"""
        if "vpn_server" not in self.config:
            log.warning(
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
        self.check_config()
        endpoints = self._find_endpoints(self.config["url"])

        self.api_url = endpoints["api_endpoint"]
        self.authorization_url = endpoints["authorization_endpoint"]
        self.token_url = endpoints["token_endpoint"]

        # Base portal url is api url minus /api/v3
        self.portal_url = self.api_url[: -len("/api/v3")]
        self.authorization_response = None
        log.debug(
            f"Found eduvpn endpoints:\n"
            f"api: {self.api_url}\n"
            f"authorization: {self.authorization_url}\n"
            f"token: {self.token_url}\n"
        )

        log.debug(f"Portal url: {self.portal_url}")

        # The redirect url is never called, but needs to be the same as the url
        # set in the eduvpn server for this particular client.
        self.session = OAuth2Session(
            vpn_config["client_id"],
            scope="config",
            redirect_uri=vpn_config["redirect_url"],
        )

    def _find_endpoints(self, url: str) -> dict[str, str]:
        well_known_url = url + "/.well-known/vpn-user-portal"
        response = requests.get(well_known_url)

        well_known = response.json()
        v3_endpoints = well_known["api"]["http://eduvpn.org/api#3"]

        return v3_endpoints

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
        self._set_access_token()

        # get the user's profile id
        log.debug("Getting EduVPN profile information")
        profile = self.get_profile()
        profile_id = profile["info"]["profile_list"][0]["profile_id"]

        # get the OVPN configuration for the selected user profile
        log.debug("Obtaining OpenVPN configuration template")
        ovpn_config = self.connect(profile_id)

        return ovpn_config

    def _set_access_token(self) -> None:
        """Obtain an access token to enable access to EduVPN API"""
        if self.session.token:
            log.debug("EduVPN access token already acquired")
            return
        # set PKCE data (code challenge and code verifier)
        log.debug("Setting PKCE challenge")
        self._set_pkce()
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

        authorize_url, _ = self.session.authorization_url(
            self.authorization_url,
            code_challenge_method="S256",
            code_challenge=self.code_challenge,
        )
        log.debug(f"authorize_url: {authorize_url}")

        # Log in to eduvpn, receiving the authorization endpoint as redirect

        post_data = {
            "userName": self.config["portal_username"],
            "userPass": self.config["portal_userpass"],
            "_user_pass_auth_redirect_to": authorize_url,
            "authRedirectTo": authorize_url,
        }

        # Referer doesn't matter so much but is a required header
        headers = {
            "Referer": self.portal_url + "/home",
        }

        response = self.session.post(
            f"{self.portal_url}/_user_pass_auth/verify",
            data=post_data,
            headers=headers,
            allow_redirects=False,
        )

        # Now follow redirect to call authorization route, but prevent redirect. By preventing the
        # redirect, the authorization code can be used in the current session
        # which allows us to use the PKCE code verifier without having to save
        # it in e.g. database or session state.
        response = self.session.get(authorize_url, allow_redirects=False)

        log.debug(f"Authorization response headers: {response.headers}")
        log.debug(f"Authorization response{response}")
        self.authorization_response = response.headers["Location"]

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

    def _get_token(self) -> dict:
        """
        Use authorization code to obtain a token from the EduVPN portal. It seems that the
        vpn client can either be considered a confidential or a public client.

        Returns
        -------
        Dict:
            EduVPN portal token
        """

        errors = []
        token = None
        for include_client_id in [True, False]:
            try:
                token = self.session.fetch_token(
                    self.token_url,
                    authorization_response=self.authorization_response,
                    client_id=self.config["client_id"],
                    client_secret=self.config["client_secret"],
                    code_verifier=self.code_verifier,
                    include_client_id=include_client_id,
                )
                break
            except Exception as e:
                errors.append(e)
                continue

        if token is None:
            raise Exception(f"Failed to fetch token. Errors: {errors}")

        return token

    def get_profile(self) -> dict:
        """
        Call the profile_list route of EduVPN API

        Returns
        -------
        Dict
            Response content of the EduVPN /profile_list route
        """
        response = self.session.get(f"{self.api_url}/info")
        return response.json()

    def connect(self, profile_id: str) -> str:
        """Retrieve a vpn certificate

        Parameters
        ----------
        profile_id: str
            An EduVPN user's profile_id obtained from the /info` route

        Returns
        -------
        str
            OpenVPN configuration file content (without key pair)
        """
        params = {"profile_id": profile_id}
        response = self.session.post(self.api_url + "/connect", data=params)
        return response.content.decode("utf-8")
