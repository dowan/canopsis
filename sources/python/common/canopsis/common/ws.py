# -*- coding: utf-8 -*-
# --------------------------------
# Copyright (c) 2014 "Capensis" [http://www.capensis.com]
#
# This file is part of Canopsis.
#
# Canopsis is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Canopsis is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with Canopsis.  If not, see <http://www.gnu.org/licenses/>.
# ---------------------------------

from inspect import getargspec

from canopsis.common.utils import ensure_iterable, isiterable

from json import loads, dumps
from bottle import request, HTTPError, HTTPResponse
from functools import wraps
import traceback
import logging


def adapt_canopsis_data_to_ember(data):
    """
    Transform canopsis data to ember data (in changing ``id`` to ``cid``).

    :param data: data to transform
    """

    if isinstance(data, dict):
        if 'id' in data:
            data['cid'] = data['id']
            del data['id']
        if 'eid' in data:
            data['id'] = data['eid']
        for item in data.values():
            adapt_canopsis_data_to_ember(item)
    elif isiterable(data, is_str=False):
        for item in data:
            adapt_canopsis_data_to_ember(item)


def adapt_ember_data_to_canopsis(data):

    if isinstance(data, dict):
        if 'id' in data:
            data['eid'] = data['id']
        if 'cid' in data:
            data['id'] = data['cid']
            del data['cid']
        for item in data.values():
            adapt_ember_data_to_canopsis(item)
    elif isiterable(data, is_str=False):
        for item in data:
            adapt_ember_data_to_canopsis(item)


def response(data, adapt=True):
    """
    Construct a REST response from input data.

    :param data: data to convert into a REST response.
    :param kwargs: service function parameters.
    :param bool adapt: adapt Canopsis data to Ember (default: True)
    """

    # calculate result_data and total related to data type
    if isinstance(data, tuple):
        result_data = ensure_iterable(data[0])
        total = data[1]

    else:
        result_data = None if data is None else ensure_iterable(data)
        total = 0 if result_data is None else len(result_data)

    if adapt:
        # apply transformation for client
        adapt_canopsis_data_to_ember(result_data)

    result = {
        'total': total,
        'data': result_data,
        'success': True
    }

    return result


def route_name(operation_name, *parameters):
    """
    Get the right route related to input operation_name
    """

    result = '/{0}'.format(operation_name.replace('_', '-'))

    for parameter in parameters:
        result = '{0}/:{1}'.format(result, parameter)

    return result


class route(object):
    """
    Decorator which add ws routes to a callable object.

    Example::

        @route(get, payload='c')
        def entities(a, b, c=None, d=None):
            ...

        Fill ``a``, ``b``, ``d`` parameters in entities function and provide
        the three urls:

            - '/entities/a/:b'
            - '/entities/a/:b'
            - '/entities/a/:b/:d'

        And manage ``c`` such as a request body parameter.
    """

    def __init__(
        self, op, name=None, raw_body=False, payload=None, wsgi_params=None,
        response=response, adapt=True
    ):
        """
        :param op: ws operation for routing a function
        :param str name: ws name
        :param bool raw_body: if True, will set kwargs body to raw request body
        :param payload: body parameter names (won't be generated in routes)
        :type payload: str or list of str
        :param function response: response to apply on decorated function
            result
        :param dict wsgi_params: wsgi parameters which will be given to the
            wsgi such as a keyword
        :param bool adapt: Adapt Canopsis<->Ember data (default: True)
        """

        super(route, self).__init__()

        # logger is initialized by WebServer
        self.logger = logging.getLogger('webserver')

        self.op = op
        self.name = name
        self.raw_body = raw_body
        self.payload = ensure_iterable(payload)
        self.response = response
        self.wsgi_params = wsgi_params
        self.adapt = adapt

    def __call__(self, function):

        # generate an interceptor
        @wraps(function)
        def interceptor(*args, **kwargs):
            self.logger.info('Request: {} - {} - {}, {} (params: {})'.format(
                self.op.__name__.upper(),
                self.url,
                dumps(args), dumps(kwargs),
                dumps(dict(request.params)))
            )

            if self.raw_body:
                kwargs['body'] = request.body

            else:
                # add body parameters in kwargs
                for body_param in self.payload:
                    # TODO: remove reference from bottle
                    param = request.params.get(body_param)
                    # if param exists, add it into kwargs in deserializing it
                    if param is not None:
                        try:
                            kwargs[body_param] = loads(param)

                        except ValueError:  # error while deserializing
                            # get the str value and cross fingers ...
                            kwargs[body_param] = param

            if self.adapt:
                # adapt ember data to canopsis data
                adapt_ember_data_to_canopsis(args)
                adapt_ember_data_to_canopsis(kwargs)

            try:
                result_function = function(*args, **kwargs)

            except HTTPResponse as r:
                raise r

            except Exception as e:
                # if an error occured, get a failure message
                result = {
                    'total': 0,
                    'success': False,
                    'data': {
                        'traceback': traceback.format_exc(),
                        'type': str(type(e)),
                        'msg': str(e)
                    }
                }

            else:
                if not isinstance(result_function, HTTPError):
                    result = self.response(result_function, adapt=self.adapt)

                else:
                    result = result_function

            return result

        # add routes
        argspec = getargspec(function)
        args, defaults = argspec.args, argspec.defaults
        result = self.apply_route_on_function(interceptor, args, defaults)

        return result

    def apply_route_on_function(self, function, args=None, defaults=None):
        """
        Automatically apply routes parameterized by input function and return
        the intercepted function.

        :param callable function: function from where generate ws redirection
        :param list args: list of function arg names
        :param list defaults: list of function arg default values
        """

        # get the right function name
        function_name = function.__name__ if self.name is None else self.name

        if args is None:
            argspec = getargspec(function)
            args, defaults = argspec.args, argspec.defaults

        # get defaults len for dynamic programming concerns
        len_defaults = 0 if defaults is None else len(defaults)

        # list of optional header parameters
        optional_header_params = []

        # identify optional parameters without body parameters
        for i in range(len_defaults):
            opt_param = args[- (i + 1)]
            # if opt_param is not defined somewhere else
            if not self.already_defined(function_name, opt_param):
                optional_header_params.append(opt_param)

        optional_header_params.reverse()

        # remove payload parameters already defined in the route name
        self.payload = [
            param for param in self.payload
            if ':{0}/'.format(param) not in function_name]

        # get required header parameters
        required_header_params = args[:len(args) - len_defaults]
        required_header_params = [
            param
            for param in required_header_params
            if not self.already_defined(function_name, param)
        ]

        wsgi_params = {} if self.wsgi_params is None else self.wsgi_params

        # add routes with optional parameters
        for i in range(len(optional_header_params) + 1):
            header_params = required_header_params + optional_header_params[:i]
            self.url = route_name(function_name, *header_params).rstrip('/')
            function = self.op(self.url, **wsgi_params)(function)

            function = self.op('{0}/'.format(self.url), **wsgi_params)(function)

        return function

    def already_defined(self, route_name, param):
        """
        Check if param is already defined somewhere else
        """

        in_payload = param in self.payload
        in_route_name = ':{0}/'.format(param) in route_name

        return in_payload or in_route_name
