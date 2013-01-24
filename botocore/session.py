# Copyright (c) 2012 Mitch Garnaat http://garnaat.org/
# Copyright 2012 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish, dis-
# tribute, sublicense, and/or sell copies of the Software, and to permit
# persons to whom the Software is furnished to do so, subject to the fol-
# lowing conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
# OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABIL-
# ITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT
# SHALL THE AUTHOR BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.
#
"""
This module contains the main interface to the botocore package, the
Session object.
"""

import logging
import platform
import os
import copy
import botocore.config
import botocore.credentials
import botocore.base
import botocore.service
from . import __version__


EnvironmentVariables = {
    'profile': 'BOTO_DEFAULT_PROFILE',
    'region': 'BOTO_DEFAULT_REGION',
    'data_path': 'BOTO_DATA_PATH',
    'config_file': 'AWS_CONFIG_FILE',
    'access_key': 'AWS_ACCESS_KEY_ID',
    'secret_key': 'AWS_SECRET_ACCESS_KEY'
    }
"""
A dictionary mapping logical names to specific environment variable
names.  When creating a new Session object, you can pass in your own
dictionary to remap the logical names to the environment variable names
you want to use for your application.  The logical variable names are:

* profile - Default profile name you want to use.
* region - Default region name to use, if not otherwise specified.
* data_path - Additional directories to search for data files.
* config_file - Location of a Boto config file.
* access_key - The AWS access key part of your credentials.
* secret_key - The AWS secret key part of your credentials.
"""


class Session(object):
    """
    The Session object collects together useful functionality
    from `botocore` as well as important data such as configuration
    information and credentials into a single, easy-to-use object.

    :ivar available_profiles: A list of profiles defined in the config
        file associated with this session.
    :ivar profile: The current profile.
    """

    FmtString = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

    def __init__(self, env_vars=None):
        """
        Create a new Session object.

        :type env_vars: dict
        :param env_vars: A dictionary that is used to override some or all
            of the environment variables associated with this session.  The
            key/value pairs defined in this dictionary will override the
            corresponding variables defined in `EnvironmentVariables`.
        """
        self.env_vars = copy.copy(EnvironmentVariables)
        if env_vars:
            self.env_vars.update(env_vars)
        self.user_agent_name = 'Boto'
        self.user_agent_version = __version__
        self._profile = os.environ.get(self.env_vars['profile'], 'default')
        self._config = None
        self._credentials = None

    @property
    def available_profiles(self):
        profiles = []
        self.get_config()
        for key in self._config.keys():
            if not key.startswith('_'):
                profiles.append(key)
        return profiles

    @property
    def profile(self):
        return self._profile

    @profile.setter
    def profile(self, profile):
        if profile != self._profile:
            self._credentials = None
        self._profile = profile

    def get_envvar(self, logical_name):
        """
        Retrieve the value associated with the specified logical_name
        from the environment.

        :type logical_name: str
        :param logical_name: The logical name of the environment variable
            you want to retrieve.  This name will be mapped to the
            appropriate environment variable name for this session.

            * profile - Default profile name you want to use.
            * region - Default region name to use, if not otherwise specified.
            * data_path - Additional directories to search for data files.
            * config_file - Location of a Boto config file.
            * access_key - The AWS access key part of your credentials.
            * secret_key - The AWS secret key part of your credentials.

        :returns: str value of variable of None if not defined.
        """
        value = None
        if logical_name in self.env_vars:
            value = os.environ.get(self.env_vars[logical_name], None)
        return value

    def get_config(self):
        """
        Returns the configuration associated with this session.  If
        the configuration has not yet been loaded, it will be loaded
        using the current `profile` attribute value.  If it has already been
        loaded, the cached configuration will be returned.

        :raises: ConfigNotFound, ConfigParseError
        """
        if self._config is None:
            self._config = botocore.config.get_config(self)
        return self._config.get(self._profile, None)

    def set_credentials(self, access_key, secret_key):
        """
        Create the :class:`botocore.credential.Credential` object
        associated with this session using the supplied AccessKey and SecretKey

        :type access_key: str
        :param access_key: The access key part of the credentials.

        :type secret_key: str
        :param secret_key: The secret key part of the credentials.
        """
        self._credentials = botocore.credentials.Credentials(access_key,
                                                             secret_key)

    def get_credentials(self, metadata=None):
        """
        Return the :class:`botocore.credential.Credential` object
        associated with this session.  If the credentials have not
        yet been loaded, this will attempt to load them.  If they
        have already been loaded, this will return the cached
        credentials.

        :type metadata: dict
        :param metadata: This parameter allows you to pass in
            EC2 instance metadata containing IAM Role credentials.
            This metadata will be used rather than retrieving the
            metadata from the metadata service.  This is mainly used
            for unit testing.
        """
        if self._credentials is None:
            cfg = self.get_config()
            self._credentials = botocore.credentials.get_credentials(cfg,
                                                                     metadata)
        return self._credentials

    def user_agent(self):
        """
        Return a string suitable for use as a User-Agent header.
        The string will be of the form:

        <agent_name>/<agent_version> Python/<py_ver> <plat_name>/<plat_ver>

        Where:

         - agent_name is the value of the `user_agent_name` attribute
           of the session object (`Boto` by default).
         - agent_version is the value of the `user_agent_version`
           attribute of the session object (the botocore version by default).
           by default.
         - py_ver is the version of the Python interpreter beng used.
         - plat_name is the name of the platform (e.g. Darwin)
         - plat_ver is the version of the platform

        """
        return '%s/%s Python/%s %s/%s' % (self.user_agent_name,
                                          self.user_agent_version,
                                          platform.python_version(),
                                          platform.system(),
                                          platform.release())

    def get_data(self, data_path):
        """
        Retrieve the data associated with `data_path`.

        :type data_path: str
        :param data_path: The path to the data you wish to retrieve.
        """
        return botocore.base.get_data(self, data_path)

    def get_service_data(self, service_name, provider_name='aws'):
        """
        Retrieve the fully merged data associated with a service.
        """
        return botocore.base.get_service_data(self, service_name,
                                              provider_name)

    def get_service(self, service_name, provider_name='aws'):
        """
        Get information about a service.

        :type service_name: str
        :param service_name: The name of the service (e.g. 'ec2')

        :type provider_name: str
        :param provider_name: The name of the provider.  Defaults
            to 'aws'.

        :returns: :class:`botocore.service.Service`
        """
        return botocore.service.get_service(self, service_name, provider_name)

    def set_debug_logger(self):
        """
        Convenience function to quickly configure full debug output
        to go to the console.
        """
        log = logging.getLogger('botocore')
        log.setLevel(logging.DEBUG)

        # create console handler and set level to debug
        ch = logging.StreamHandler()
        ch.setLevel(logging.DEBUG)

        # create formatter
        formatter = logging.Formatter(self.FmtString)

        # add formatter to ch
        ch.setFormatter(formatter)

        # add ch to logger
        log.addHandler(ch)

    def set_file_logger(self, log_level, path):
        """
        Convenience function to quickly configure any level of logging
        to a file.

        :type log_level: int
        :param log_level: A log level as specified in the `logging` module

        :type path: string
        :param path: Path to the log file.  The file will be created
            if it doesn't already exist.
        """
        log = logging.getLogger('botocore')
        log.setLevel(log_level)

        # create console handler and set level to debug
        ch = logging.FileHandler(path)
        ch.setLevel(log_level)

        # create formatter
        formatter = logging.Formatter(self.FmtString)

        # add formatter to ch
        ch.setFormatter(formatter)

        # add ch to logger
        log.addHandler(ch)


def get_session(env_vars=None):
    """
    Return a new session  object.
    """
    return Session(env_vars)
