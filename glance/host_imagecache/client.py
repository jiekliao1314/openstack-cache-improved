#jiekliao

"""
get a client of glanceclient and novaclient
"""

from __future__ import print_function

import argparse
import copy
import getpass
import json
import logging
import os
from os.path import expanduser
import sys
import traceback

from oslo_utils import encodeutils
from oslo_utils import importutils
import six.moves.urllib.parse as urlparse

from novaclient import client as novaclient

import glanceclient
from glanceclient import _i18n
from glanceclient.common import utils
from glanceclient import exc

from keystoneclient.auth.identity import v2 as v2_auth
from keystoneclient.auth.identity import v3 as v3_auth
from keystoneclient import discover
from keystoneclient.openstack.common.apiclient import exceptions as ks_exc
from keystoneclient import session

osprofiler_profiler = importutils.try_import("osprofiler.profiler")
_ = _i18n._



def _discover_auth_versions(session, auth_url):
    # discover the API versions the server is supporting base on the
    # given URL
    v2_auth_url = None
    v3_auth_url = None
    try:
        ks_discover = discover.Discover(session=session, auth_url=auth_url)
        v2_auth_url = ks_discover.url_for('2.0')
        v3_auth_url = ks_discover.url_for('3.0')
    except ks_exc.ClientException as e:
        # Identity service may not support discover API version.
        # Lets trying to figure out the API version from the original URL.
        url_parts = urlparse.urlparse(auth_url)
        (scheme, netloc, path, params, query, fragment) = url_parts
        path = path.lower()
        if path.startswith('/v3'):
            v3_auth_url = auth_url
        elif path.startswith('/v2'):
            v2_auth_url = auth_url
        else:
            # not enough information to determine the auth version
            msg = ('Unable to determine the Keystone version '
                   'to authenticate with using the given '
                   'auth_url. Identity service may not support API '
                   'version discovery. Please provide a versioned '
                   'auth_url instead. error=%s') % (e)
            raise exc.CommandError(msg)

    return (v2_auth_url, v3_auth_url)

def _get_keystone_session(**kwargs):
    ks_session = session.Session.construct(kwargs)

    # discover the supported keystone versions using the given auth url
    auth_url = kwargs.pop('auth_url', None)
    (v2_auth_url, v3_auth_url) = _discover_auth_versions(
        session=ks_session,
        auth_url=auth_url)

    # Determine which authentication plugin to use. First inspect the
    # auth_url to see the supported version. If both v3 and v2 are
    # supported, then use the highest version if possible.
    user_id = kwargs.pop('user_id', None)
    username = kwargs.pop('username', None)
    password = kwargs.pop('password', None)
    user_domain_id = kwargs.pop('user_domain_id', None)
    user_domain_name = kwargs.pop('user_domain_name', None)
    # project and tenant can be used interchangeably
    project_id = (kwargs.pop('project_id', None) or
                  kwargs.pop('tenant_id', None))
    project_name = (kwargs.pop('project_name', None) or
                    kwargs.pop('tenant_name', None))
    project_domain_id = kwargs.pop('project_domain_id', None)
    project_domain_name = kwargs.pop('project_domain_name', None)
    auth = None

    use_domain = (user_domain_id or
                  user_domain_name or
                  project_domain_id or
                  project_domain_name)
    use_v3 = v3_auth_url and (use_domain or (not v2_auth_url))
    use_v2 = v2_auth_url and not use_domain

    if use_v3:
        auth = v3_auth.Password(
            v3_auth_url,
            user_id=user_id,
            username=username,
            password=password,
            user_domain_id=user_domain_id,
            user_domain_name=user_domain_name,
            project_id=project_id,
            project_name=project_name,
            project_domain_id=project_domain_id,
            project_domain_name=project_domain_name)
    elif use_v2:
        auth = v2_auth.Password(
            v2_auth_url,
            username,
            password,
            tenant_id=project_id,
            tenant_name=project_name)
    else:
        # if we get here it means domain information is provided
        # (caller meant to use Keystone V3) but the auth url is
        # actually Keystone V2. Obviously we can't authenticate a V3
        # user using V2.
        exc.CommandError("Credential and auth_url mismatch. The given "
                         "auth_url is using Keystone V2 endpoint, which "
                         "may not able to handle Keystone V3 credentials. "
                         "Please provide a correct Keystone V3 auth_url.")

    ks_session.auth = auth
    return ks_session

def _get_endpoint_and_token(args, service_type, os_image_url='', force_auth=False):
    
    auth_token = args.os_auth_token
    auth_reqd = force_auth or not auth_token 

    if not auth_reqd:
        token = args.os_auth_token
        endpoint=os_image_url
    else:

        if not args.os_username:
            raise exc.CommandError(
                _("You must provide a username via"
                  " either --os-username or "
                  "env[OS_USERNAME]"))

        if not args.os_password:
            # No password, If we've got a tty, try prompting for it
            if hasattr(sys.stdin, 'isatty') and sys.stdin.isatty():
                # Check for Ctl-D
                try:
                    args.os_password = getpass.getpass('OS Password: ')
                except EOFError:
                    pass
            # No password because we didn't have a tty or the
            # user Ctl-D when prompted.
            if not args.os_password:
                raise exc.CommandError(
                    _("You must provide a password via "
                      "either --os-password, "
                      "env[OS_PASSWORD], "
                      "or prompted response"))

        # Validate password flow auth
        project_info = (
            args.os_tenant_name or args.os_tenant_id or (
                args.os_project_name and (
                    args.os_project_domain_name or
                    args.os_project_domain_id
                )
            ) or args.os_project_id
        )

        if not project_info:
            # tenant is deprecated in Keystone v3. Use the latest
            # terminology instead.
            raise exc.CommandError(
                _("You must provide a project_id or project_name ("
                  "with project_domain_name or project_domain_id) "
                  "via "
                  "  --os-project-id (env[OS_PROJECT_ID])"
                  "  --os-project-name (env[OS_PROJECT_NAME]),"
                  "  --os-project-domain-id "
                  "(env[OS_PROJECT_DOMAIN_ID])"
                  "  --os-project-domain-name "
                  "(env[OS_PROJECT_DOMAIN_NAME])"))

        if not args.os_auth_url:
            raise exc.CommandError(
                _("You must provide an auth url via"
                  " either --os-auth-url or "
                  "via env[OS_AUTH_URL]"))

        kwargs = {
            'auth_url': args.os_auth_url,
            'username': args.os_username,
            'user_id': args.os_user_id,
            'user_domain_id': args.os_user_domain_id,
            'user_domain_name': args.os_user_domain_name,
            'password': args.os_password,
            'tenant_name': args.os_tenant_name,
            'tenant_id': args.os_tenant_id,
            'project_name': args.os_project_name,
            'project_id': args.os_project_id,
            'project_domain_name': args.os_project_domain_name,
            'project_domain_id': args.os_project_domain_id,
            'insecure': args.insecure,
            'cacert': args.os_cacert,
            'cert': args.os_cert,
            'key': args.os_key
        }
        ks_session = _get_keystone_session(**kwargs)
        token = args.os_auth_token or ks_session.get_token()

        endpoint_type = args.os_endpoint_type or 'public'
        endpoint = ks_session.get_endpoint(
            service_type=service_type,
            interface=endpoint_type,
            region_name=args.os_region_name)

    return endpoint, token

def get_glanceclient(args, api_version=1, force_auth=False):
    service_type = 'image'

    endpoint, token = _get_endpoint_and_token(args, service_type=service_type, force_auth=force_auth)

    kwargs = {
        'token': token,
        'insecure': args.insecure,
        'timeout': args.timeout,
        'cacert': args.os_cacert,
        'cert': args.os_cert,
        'key': args.os_key,
        'ssl_compression': args.ssl_compression
    }
    client = glanceclient.Client(api_version, endpoint, **kwargs)

    return client

def get_novaclient(args, api_version=2, force_auth=False):
    #NOTE:here don't need authenticate firstly because novaclient can do it better

    username=args.os_username
    password=args.os_password
    tenant_name=args.os_tenant_name
    auth_url=args.os_auth_url

    client = novaclient.Client(api_version, 
                        username, password, tenant_name, 
                        auth_url=auth_url)  

    return client

