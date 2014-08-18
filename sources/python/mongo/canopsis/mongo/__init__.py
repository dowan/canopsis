# -*- coding: utf-8 -*-
#--------------------------------
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

__version__ = '0.1'

from canopsis.storage import Storage, DataBase
from canopsis.common.utils import isiterable

from pymongo import MongoClient, ASCENDING

from pymongo.errors import TimeoutError, OperationFailure, ConnectionFailure,\
    DuplicateKeyError


class MongoDataBase(DataBase):
    """
    Manage access to a mongodb.
    """

    __protocol__ = 'mongo'  #: register this class to protocol 'mongo'

    def __init__(
        self, host=MongoClient.HOST, port=MongoClient.PORT, *args, **kwargs
    ):

        super(MongoDataBase, self).__init__(
            port=port, host=host, *args, **kwargs)

    def _connect(self, *args, **kwargs):

        result = None

        connection_args = {}

        # if self host is given
        if self.host:
            connection_args['host'] = self.host

        if self.port:
            connection_args['port'] = self.port

        self.logger.debug('Trying to connect to %s' % (connection_args))

        connection_args['j'] = self.journaling
        connection_args['w'] = 1 if self.safe else 0

        if self.ssl:
            connection_args.update({
                'ssl': self.ssl,
                'ssl_keyfile': self.ssl_key,
                'ssl_certfile': self.ssl_cert
            })

        try:
            result = MongoClient(**connection_args)

        except ConnectionFailure as e:
            self.logger.error(
                'Raised {2} during connection attempting to {0}:{1}.'.
                format(self.host, self.port, e))

        else:
            self._database = result[self.db]

            if (self.user, self.pwd) != (None, None):

                authenticate = self._database.authenticate(
                    self.user, self.pwd)
                if authenticate:
                    self.logger.info("Connected on {0}:{1}".format(
                        self.host, self.port))

                else:
                    self.logger.error(
                        'Impossible to authenticate {0} on {1}:{2}'.format(
                            self.host, self.port))
                    self.disconnect()
                    result = None

            else:
                self.logger.debug("Connected on {0}:{1}".format(
                    self.host, self.port))

        return result

    def _disconnect(self, *args, **kwargs):

        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def connected(self, *args, **kwargs):

        result = self._conn is not None and self._conn.alive()

        return result

    def size(self, table=None, criteria=None, *args, **kwargs):

        result = 0

        _backend = self._get_backend(backend=table)

        try:
            result = self._database.command("collstats", _backend)['size']

        except Exception as e:
            self.logger.warning(
                "Impossible to read Collection Size: {0}".format(e))
            result = None

        return result

    def drop(self, table=None):

        if table is None:
            for collection_name in self._database.collection_names(
                    include_system_collections=False):
                self.drop(table=collection_name)

        else:
            self._get_backend(backend=table).remove()

    def _get_backend(self, backend=None, *args, **kwargs):
        """
        Get a reference to a specific backend where name is input backend.
        If input backend is None, self.backend is used.

        :param backend: backend name. If None, self.backend is used.
        :type backend: basestring

        :returns: backend reference.

        :raises: NotImplementedError
        .. seealso: DataBase.set_backend(self, backend)
        """

        if getattr(self, '_database', None) is None:
            raise DataBase.DataBaseError(
                '{0} is not connected'.format(self))

        result = self._database[backend]

        return result


def len_cursor(cursor):
    """
    Mongo cursor len function
    """

    return cursor.count(True)


class MongoStorage(MongoDataBase, Storage):

    __register__ = True  #: register this class to middleware

    ID = '_id'  #: ID mongo

    @property
    def indexes(self):
        if not hasattr(self, '_indexes'):
            self._indexes = []
        return self._indexes

    @indexes.setter
    def indexes(self, value):
        self._indexes = value

    def _connect(self, *args, **kwargs):

        result = super(MongoStorage, self)._connect(*args, **kwargs)

        if result:
            self.indexes = self._get_indexes()

            table = self.get_table()
            self._backend = self._database[table]

            for index in self.indexes:
                self._backend.ensure_index(index)

        return result

    def drop(self, *args, **kwargs):
        """
        Drop self table.
        """

        super(MongoStorage, self).drop(table=self.get_table(), *args, **kwargs)

    def get_elements(
        self, ids=None, limit=0, skip=0, sort=None, *args, **kwargs
    ):

        query = {}

        if ids is not None:
            if isiterable(ids):
                query[MongoStorage.ID] = {'$in': ids}
            else:
                query[MongoStorage.ID] = ids

        cursor = self._find(query)

        if limit:
            cursor.limit(limit)
        if skip:
            cursor.skip(skip)
        if sort is not None:
            MongoStorage._update_sort(sort)
            cursor.sort(sort)

        result = self._get_generic_result(cursor, ids)

        return result

    def remove_elements(self, ids, *args, **kwargs):

        self._remove({MongoStorage.ID: {'$in': ids}})

    def put_element(self, _id, element, *args, **kwargs):

        self._update(
            _id={MongoStorage.ID: _id}, document={'$set': element},
            multi=False)

    def bool_compare_and_swap(self, _id, oldvalue, newvalue):

        return self.val_compare_and_swap(_id, oldvalue, newvalue) == newvalue

    def val_compare_and_swap(self, _id, oldvalue, newvalue):

        try:
            result = self._run_command(
                'find_and_modify',
                query={MongoStorage.ID: _id, 'value': oldvalue},
                update={'$set': {'value': newvalue}},
                upsert=True)

        except DuplicateKeyError:
            result = None

        return oldvalue if not result else newvalue

    def _get_index(self, _filter):
        """
        Get the right index related to input filter.
        """

        result = None

        max_correspondance = 0

        for index in self.indexes:
            correspondance = 0

            for index_value in index:
                if index_value[0] in _filter:
                    correspondance += 1
                else:
                    break

            if correspondance > max_correspondance:
                result = index
                max_correspondance = correspondance

        return result

    def _get_generic_result(self, cursor, ids=None):
        """
        Get generic result depending on input cursor and ids.
        If ids is not iterable, then result if the first cursor result.
        Iterable of cursor otherwise.
        """

        result = None
        # Return the element if only one element was requested
        # Otherwise, return a list of the requested elements
        if ids is None or isiterable(ids, is_str=False):
            result = list(cursor)

        else:
            # result is the only one value or None if no value exist
            result = result[0] if result else None

        return result

    def _element_id(self, element):

        return element[MongoStorage.ID]

    def _get_indexes(self):
        """
        Get collection indexes. Must be overriden.
        """

        result = [
            [(MongoStorage.ID, ASCENDING)]
        ]

        return result

    def _manage_query_error(self, result_query):
        """
        Manage mongo query error.
        """

        result = None

        if isinstance(result_query, dict):

            error = result_query.get("writeConcernError", None)

            if error is not None:
                self.logger.error(' error in writing document: {0}'.format(
                    error))

            error = result_query.get("writeError")

            if error is not None:
                self.logger.error(' error in writing document: {0}'.format(
                    error))

        else:

            result = result_query

        return result

    def _insert(self, document):

        result = self._run_command(command='insert', doc_or_docs=document)

        return result

    def _update(self, _id, document, multi=True):

        result = self._run_command(
            command='update', spec=_id, document=document,
            upsert=True, multi=multi)

        return result

    def _find(self, document=None, projection=None):

        result = self._run_command(command='find', spec=document,
            projection=projection)

        return result

    def _remove(self, document):

        result = self._run_command(command='remove', spec_or_id=document)

        return result

    def _count(self, document=None):

        cursor = self._find(document=document)

        result = cursor.count(False)

        return result

    def _run_command(self, command, **kwargs):
        """
        Run a specific command on a given backend.

        :param command: command to run
        :type command: str

        :param backend: backend to use
        :type backend: str
        """

        result = None

        try:
            backend = self._get_backend(backend=self.get_table())
            backend_command = getattr(backend, command)
            w = 1 if self.safe else 0
            result = backend_command(w=w, wtimeout=self.out_timeout, **kwargs)

            self._manage_query_error(result)

        except TimeoutError:
            self.logger.warning(
                'Try to run command {0}({1}) on {2} attempts left'
                .format(command, kwargs, backend))

        except OperationFailure as of:
            self.logger.error('{0} during running command {1}({2}) of in {3}'
                .format(of, command, kwargs, backend))

        return result
