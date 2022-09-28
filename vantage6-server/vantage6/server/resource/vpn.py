# -*- coding: utf-8 -*-
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
import requests
from requests_oauthlib import OAuth2Session

from vantage6.common import logger_name
from vantage6.server.resource import with_node, ServicesResources


module_name = logger_name(__name__)
log = logging.getLogger(module_name)


def setup(api, api_base, services):
    path = "/".join([api_base, module_name])
    log.info(f'Setting up "{path}" and subdirectories')

    api.add_resource(
        VPNConfig,
        path,
        endpoint='vpn_config',
        methods=('GET',),
        resource_class_kwargs=services
    )

    api.add_resource(
        VPNConfig,
        path + '/update',
        endpoint='vpn_config_update',
        methods=('POST',),
        resource_class_kwargs=services
    )


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
            return {'msg': 'This server does not support VPN'}, \
                HTTPStatus.NOT_IMPLEMENTED

        # obtain VPN config by calling EduVPN API
        vpn_connector = EduVPNConnector(self.config['vpn_server'])

        try:
            ovpn_config = vpn_connector.get_ovpn_config()
        except requests.ConnectionError as e:
            log.critical(f'Node <{g.node.id}> tries to obtain a vpn config. '
                         'However the VPN server is unreachable!')
            log.debug(e)
            return {'msg': 'VPN server unreachable'}, \
                HTTPStatus.SERVICE_UNAVAILABLE

        return {'ovpn_config': ovpn_config}, HTTPStatus.OK

    @with_node
    def post(self):
        """ Update an OVPN configuration file
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
            return {'msg': 'This server does not support VPN'}, \
                HTTPStatus.NOT_IMPLEMENTED

        # retrieve user based on email or username
        body = request.get_json()
        vpn_config = body.get("vpn_config")
        if not vpn_config:
            return {"msg": "vpn_config is missing!"}, \
                HTTPStatus.BAD_REQUEST

        # obtain VPN config by calling EduVPN API
        vpn_connector = EduVPNConnector(self.config['vpn_server'])

        try:
            ovpn_config = vpn_connector.refresh_keypair(vpn_config)
        except requests.ConnectionError as e:
            log.critical(f'Node <{g.node.id}> tries to obtain a vpn config. '
                         'However the VPN server is unreachable!')
            log.debug(e)
            return {'msg': 'VPN server unreachable'}, \
                HTTPStatus.SERVICE_UNAVAILABLE

        return {'ovpn_config': ovpn_config}, HTTPStatus.OK

    def _is_server_configured(self) -> bool:
        """ Check if vpn server is available in configuration"""
        if 'vpn_server' not in self.config:
            log.debug(f'Node <{g.node.id}> tries to obtain a vpn config but '
                      'this server has not configured a VPN server!')
            return False
        return True


class EduVPNConnector:

    def __init__(self, vpn_config):
        """
        Provides API access to the VPN server

        Parameters
        ----------
        vpn_config : dict
            Contains the VPN server info
        """
        self.config = vpn_config
        self.session = OAuth2Session(vpn_config['client_id'])

        self.PORTAL_URL = self.config['url'][:-1] \
            if self.config['url'].endswith('/') \
            else self.config['url']
        self.API_URL = f'{self.PORTAL_URL}/api.php'

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
        profile_id = profile['profile_list']['data'][0]['profile_id']

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

        Returns
        -------
        str (ovpn format)
            Open-vpn configuration file
        """
        # get a key and certificate for the client
        log.debug("Obtaining OpenVPN key-pair")
        cert, key = self.get_key_pair()

        # add the client credentials to the ovpn file
        log.debug('Parsing VPN configuration file')
        ovpn_config = self._insert_keypair_into_config(ovpn_config, cert, key)
        return ovpn_config

    def set_access_token(self):
        """ Obtain an access token to enable access to EduVPN API """
        if self.session.token:
            log.debug("Acquiring EduVPN access token")
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

    def _set_pkce(self):
        """ Generate PKCE code verifier and challenge """
        # set PKCE verifier
        self.code_verifier = \
            base64.urlsafe_b64encode(os.urandom(40)).decode('utf-8')
        self.code_verifier = re.sub('[^a-zA-Z0-9]+', '', self.code_verifier)

        # set PKCE challenge based on the verifier
        self.code_challenge = \
            hashlib.sha256(self.code_verifier.encode('utf-8')).digest()
        self.code_challenge = \
            base64.urlsafe_b64encode(self.code_challenge).decode('utf-8')
        self.code_challenge = self.code_challenge.replace('=', '')

    def _login(self):
        """ Login to the EduVPN user portal in the requests session """
        post_data = {
            'userName': self.config['portal_username'],
            'userPass': self.config['portal_userpass'],
            '_form_auth_redirect_to': self.config['url']
        }
        self.session.post(
            f'{self.PORTAL_URL}/_form/auth/verify', data=post_data
        )

    def _authorize(self):
        """ Call authorization route of EduVPN to get authorization code """
        params = {
            'client_id': self.config['client_id'],
            'redirect_uri': self.config['redirect_url'],
            'response_type': 'code',
            'scope': 'config',
            'state': 'some_string',
            'code_challenge_method': 'S256',
            'code_challenge': self.code_challenge,
        }

        # Call authorization route, but prevent redirect. By preventing the
        # redirect, the authorization code can be used in the current session
        # which allows us to use the PKCE code verifier without having to save
        # it in e.g. database or session state.
        response = self.session.get(
            f'{self.PORTAL_URL}/_oauth/authorize',
            params=params,
            allow_redirects=False
        )

        # get the authorization token from the request headers
        redirected_uri = response.headers['Location']
        parsed_url = urlparse.urlparse(redirected_uri)
        self.code = urlparse.parse_qs(parsed_url.query)['code']

    def _get_token(self):
        """ Use authorization code to obtain a token from the EduVPN portal """
        data = {
            'code': self.code,
            'grant_type': 'authorization_code',
            'redirect_uri': self.config['redirect_url'],
            'client_id': self.config['client_id'],
            'client_secret': self.config['client_secret'],
            'code_verifier': self.code_verifier,
        }

        r = self.session.post(
            f'{self.PORTAL_URL}/oauth.php/token',
            data=data,
            auth=(self.config['client_id'], self.config['client_secret'])
        )
        return json.loads(r.content.decode('utf-8'))

    def _insert_keypair_into_config(self, ovpn_config: str, cert: str,
                                    key: str):
        """
        Insert the client's key pair into the correct place into the OVPN file
        (i.e. before the <tls-crypt> field)

        Parameters
        ----------
        config : str
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
        insert_loc = ovpn_config.find('<tls-crypt>')
        return (
            ovpn_config[:insert_loc] +
            '<cert>\n' + cert + '\n</cert>\n' +
            '<key>\n' + key + '\n</key>\n' +
            ovpn_config[insert_loc:]
        )

    def _remove_keypair(self, ovpn_config: str) -> str:
        """
        Remove the keypair from the configuration

        Returns
        -------
        str (ovpn format)
            Open-vpn configuration file without key pair
        """
        # keypair starts at '<cert>' and ends at '</key>\n'
        start_remove_pos = ovpn_config.find('<cert>')
        end_key = '</key>\n'
        end_remove_pos = ovpn_config.find(end_key)
        return (
            ovpn_config[0:start_remove_pos] +
            ovpn_config[end_remove_pos+len(end_key):]
        )

    def get_profile(self):
        """ Call the profile_list route of EduVPN API """
        response = self.session.get(f'{self.API_URL}/profile_list')
        return json.loads(response.content.decode('utf-8'))

    def get_config(self, profile_id):
        """ Call the profile_config route of EduVPN API

        Parameters
        ----------
        profile_id: str
            An EduVPN user's profile_id obtained from the /profile_list route
        """
        params = {
            'profile_id': profile_id
        }
        response_config = self.session.get(
            f'{self.API_URL}/profile_config', params=params
        )
        return response_config.content.decode('utf-8')

    def get_key_pair(self):
        """ Call the create_keypair route of EduVPN API """
        response_keypair = self.session.post(f'{self.API_URL}/create_keypair')
        ovpn_keypair = json.loads(response_keypair.content.decode('utf-8'))
        cert = ovpn_keypair['create_keypair']['data']['certificate']
        key = ovpn_keypair['create_keypair']['data']['private_key']
        return cert, key
