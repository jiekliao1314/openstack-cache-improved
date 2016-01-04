#!/usr/bin/env python

#liaojie

"""
used for manage the compute node image cache
"""

from __future__ import print_function

import functools
import optparse
import os
import sys
import time
import exceptions

from oslo_utils import timeutils

from glanceclient.common import utils

# If ../glance/__init__.py exists, add ../ to Python search path, so that
# it will override what happens to be installed in /usr/(local/)lib/python...
possible_topdir = os.path.normpath(os.path.join(os.path.abspath(sys.argv[0]),
                                   os.pardir,
                                   os.pardir))
if os.path.exists(os.path.join(possible_topdir, 'glance', '__init__.py')):
    sys.path.insert(0, possible_topdir)

from glance.common import exception
import glance.image_cache.client
from glance.version import version_info as version


from glance.host_imagecache import base
from oslo_utils import encodeutils 

SUCCESS = 0
FAILURE = 1

def cache_all(options, args):
    """
    %(prog)s cache-all [options]

    download image cache for all compute nodes
    """
    #FIXME:as below
    """
    glanceclient.exc.CommandError: You must provide a username via either --os-username or env[OS_USERNAME]
    """
    #TODO:Add the progress of download
    #liaojie test-time
    with open("/root/cache-start-time.result","w") as f:
        import datetime
        start_time_str=datetime.datetime.now().strftime("%Y-%m-%d-%H:%M:%S")
        f.write("cache start time=="+start_time_str+"\n")

    cachemanager=base.ImageCacheManager(options)
    cachemanager.cache_all(args)

def cache_host(options, args):
    """
    download image cache for specified host
    """
    raise exceptions.NotImplementedError

def env(*vars, **kwargs):
    """Search for the first defined of possibly many env vars.

    Returns the first environment variable defined in vars, or
    returns the default defined in kwargs.
    """
    for v in vars:
        value = os.environ.get(v, None)
        if value:
            return value
    return kwargs.get('default', '')


def create_options(parser):
    """Set up the CLI and config-file options that may be
    parsed and program commands.

    :param parser: The option parser
    """
    #TODO:Add or remove some options
    parser.add_option('--os-username',
                        default=env('OS_USERNAME'),
                        help='Defaults to env[OS_USERNAME].')


    parser.add_option('--os-user-id',
                        default=env('OS_USER_ID'),
                        help='Defaults to env[OS_USER_ID].')

    parser.add_option('--os-user-domain-id',
                        default=env('OS_USER_DOMAIN_ID'),
                        help='Defaults to env[OS_USER_DOMAIN_ID].')

    parser.add_option('--os-user-domain-name',
                        default=env('OS_USER_DOMAIN_NAME'),
                        help='Defaults to env[OS_USER_DOMAIN_NAME].')

    parser.add_option('--os-project-id',
                        default=env('OS_PROJECT_ID'),
                        help='Another way to specify tenant ID. '
                             'This option is mutually exclusive with '
                             ' --os-tenant-id. '
                             'Defaults to env[OS_PROJECT_ID].')

    parser.add_option('--os-project-name',
                        default=env('OS_PROJECT_NAME'),
                        help='Another way to specify tenant name. '
                             'This option is mutually exclusive with '
                             ' --os-tenant-name. '
                             'Defaults to env[OS_PROJECT_NAME].')

    parser.add_option('--os-project-domain-id',
                        default=env('OS_PROJECT_DOMAIN_ID'),
                        help='Defaults to env[OS_PROJECT_DOMAIN_ID].')

    parser.add_option('--os-project-domain-name',
                        default=env('OS_PROJECT_DOMAIN_NAME'),
                        help='Defaults to env[OS_PROJECT_DOMAIN_NAME].')

    parser.add_option('--os-password',
                        default=env('OS_PASSWORD'),
                        help='Defaults to env[OS_PASSWORD].')


    parser.add_option('--os-tenant-id',
                        default=env('OS_TENANT_ID'),
                        help='Defaults to env[OS_TENANT_ID].')


    parser.add_option('--os-tenant-name',
                        default=env('OS_TENANT_NAME'),
                        help='Defaults to env[OS_TENANT_NAME].')


    parser.add_option('--os-auth-url',
                        default=env('OS_AUTH_URL'),
                        help='Defaults to env[OS_AUTH_URL].')

    parser.add_option('--os-auth-token',
                        default=env('OS_AUTH_TOKEN'),
                        help='Defaults to env[OS_AUTH_TOKEN].')

    parser.add_option('--os-region-name',
                        default=env('OS_REGION_NAME'),
                        help='Defaults to env[OS_REGION_NAME].')

    parser.add_option('--os-endpoint-type',
                        default=env('OS_ENDPOINT_TYPE'),
                        help='Defaults to env[OS_ENDPOINT_TYPE].')

    parser.add_option('--verbose',
                        default=False, action="store_true",
                        help="Print more verbose output")

    parser.add_option('--get-schema',
                        default=False, action="store_true",
                        dest='get_schema',
                        help='Ignores cached copy and forces retrieval '
                             'of schema that generates portions of the '
                             'help text. Ignored with API version 1.')

    parser.add_option('--timeout',
                        default=600,
                        help='Number of seconds to wait for a response')

    parser.add_option('--no-ssl-compression',
                        dest='ssl_compression',
                        default=True, action='store_false',
                        help='Disable SSL compression when using https.')

    parser.add_option('--force',
                        dest='force',
                        default=False, action='store_true',
                        help='Prevent select actions from requesting '
                        'user confirmation.')
    
    parser.add_option('--insecure',
                        default=False,
                        action='store_true',
                        help='Explicitly allow glanceclient to perform '
                        '\"insecure SSL\" (https) requests. The server\'s '
                        'certificate will not be verified against any '
                        'certificate authorities. This option should '
                        'be used with caution.')

    parser.add_option('--os-cert',
                        help='Path of certificate file to use in SSL '
                        'connection. This file can optionally be '
                        'prepended with the private key.')

    parser.add_option('--cert-file',
                        dest='os_cert',
                        help='DEPRECATED! Use --os-cert.')

    parser.add_option('--os-key',
                        help='Path of client key to use in SSL '
                        'connection. This option is not necessary '
                        'if your key is prepended to your cert file.')

    parser.add_option('--os-cacert',
                        metavar='<ca-certificate-file>',
                        dest='os_cacert',
                        default=env('OS_CACERT'),
                        help='Path of CA TLS certificate(s) used to '
                        'verify the remote server\'s certificate. '
                        'Without this option glance looks for the '
                        'default system CA certificates.')

    
def parse_options(parser, cli_args):
    """
    Returns the parsed CLI options, command to run and its arguments, merged
    with any same-named options found in a configuration file

    :param parser: The option parser
    """
    if not cli_args:
        cli_args.append('-h')  # Show options in usage output...

    (options, args) = parser.parse_args(cli_args)

    # HACK(sirp): Make the parser available to the print_help method
    # print_help is a command, so it only accepts (options, args); we could
    # one-off have it take (parser, options, args), however, for now, I think
    # this little hack will suffice
    options.__parser = parser

    if not args:
        parser.print_usage()
        sys.exit(0)

    command_name = args.pop(0)
    command = lookup_command(parser, command_name)

    return (options, command, args)


def print_help(options, args):
    """
    Print help specific to a command
    """
    if len(args) != 1:
        sys.exit("Please specify a command")

    parser = options.__parser
    command_name = args.pop()
    command = lookup_command(parser, command_name)

    print(command.__doc__ % {'prog': os.path.basename(sys.argv[0])})


def lookup_command(parser, command_name):
    BASE_COMMANDS = {'help': print_help}

    CACHE_COMMANDS = {
        'cache-all': cache_all,
        'cache-host': cache_host,
    }

    commands = {}
    for command_set in (BASE_COMMANDS, CACHE_COMMANDS):
        commands.update(command_set)

    try:
        command = commands[command_name]
    except KeyError:
        parser.print_usage()
        sys.exit("Unknown command: %(cmd_name)s" % {'cmd_name': command_name})

    return command


def user_confirm(prompt, default=False):
    """Yes/No question dialog with user.

    :param prompt: question/statement to present to user (string)
    :param default: boolean value to return if empty string
                    is received as response to prompt

    """
    if default:
        prompt_default = "[Y/n]"
    else:
        prompt_default = "[y/N]"

    answer = raw_input("%s %s " % (prompt, prompt_default))

    if answer == "":
        return default
    else:
        return answer.lower() in ("yes", "y")


def main():
    usage = """
%prog <command> [options] [args]

Commands:

    help <command> Output help for one of the commands below

    cache-all                   download image cache for all compute nodes

    cache-host                  download image cache for host
"""

    version_string = version.cached_version_string()
    oparser = optparse.OptionParser(version=version_string,
                                    usage=usage.strip())
    create_options(oparser)
    (options, command, args) = parse_options(oparser, sys.argv[1:])

    try:
        start_time = time.time()
        result = command(options, args)
        end_time = time.time()
        if options.verbose:
            print("Completed in %-0.4f sec." % (end_time - start_time))
        sys.exit(result)
    except (RuntimeError, NotImplementedError) as e:
        print("ERROR: ", e)

if __name__ == '__main__':
    main()
