# -*- coding: utf-8 -*-
# --------------------------------
# Copyright (c) 2015 "Capensis" [http://www.capensis.com]
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

"""This module is dedicated to CTXInfoFunder interface.

It aims to execute ctxinfo manager read and delete methods related to its own
information managers such as the perfdata manager for example.
"""

from copy import deepcopy

from canopsis.context.manager import Context
from canopsis.middleware.core import Middleware
from canopsis.ctxinfo.funder import CTXInfoFunder


class OldFunder(CTXInfoFunder):
    """In charge of binding an old collection (not generated from the Storage
        project) to context entities.

    Such old collections contain all entity fields.
    """

    def __init__(self, table=None, *args, **kwargs):
        """
        :param Storage storage: event storage to use.
        """

        super(CTXInfoFunder, self).__init__(*args, **kwargs)

        self.storage = Middleware.get_middleware(
            protocol='storage', table=table
        )
        self.context = Context()

    def _do(self, command, entity_ids, query, queryname, *args, **kwargs):
        """Execute storage command related to input entity_ids and query.

        :param command: storage command.
        :param list entity_ids: entity id(s).
        :param dict query: storage command query.
        :param str queryname: storage command query parameter.
        :return: storage command execution documents.
        :rtype: list
        """

        result = []
        # initialize query
        query = deepcopy(query) if query else {}
        # get entity id field name
        entity_id_field = self._entity_id_field()

        for entity_id in entity_ids:
            # get entity
            entity = self.context.get_entity_by_id(entity_id)
            cleaned_entity = self.context.clean(entity)
            # update query with entity information
            _query = deepcopy(query)
            _query.setdefault('$and', []).append(cleaned_entity)
            # update kwargs with query and queryname
            kwargs[queryname] = _query
            # execute the storage command
            documents = command(*args, **kwargs)
            # update entity_id in documents
            for document in documents:
                document[entity_id_field] = entity_id
            # add all documents into the result
            result += documents

        return result

    def _get(self, entity_ids, query, *args, **kwargs):

        return self._do(
            command=self.storage.find_elements,
            entity_ids=entity_ids, query=query, queryname='query',
            *args, **kwargs
        )

    def _count(self, entity_ids, query, *args, **kwargs):

        result = []

        for entity_id in entity_ids:
            self.perfdata.count(metric_id=entity_id)

        return result

    def _delete(self, entity_ids, query, *args, **kwargs):

        return self._do(
            command=self.storage.remove_elements,
            entity_ids=entity_ids, query=query, queryname='_filter',
            *args, **kwargs
        )

    def get_entity_ids(self, query=None, *args, **kwargs):

        result = []

        events = self.storage.find_elements(query=query)

        for event in events:
            entity = self.context.get_entity(event)
            entity_id = self.context.get_entity_id(entity)
            result.append(entity_id)

        return result


class EventFunder(OldFunder):
    """Funder bound to the old events collection.
    """

    __datatype__ = 'events'  #: default datatype name

    def __init__(self, table=__datatype__, *args, **kwargs):

        super(EventFunder, self).__init__(table=table, *args, **kwargs)


class EventLogFunder(OldFunder):
    """Funder bound to the old events_log collection.
    """

    __datatype__ = 'eventslog'  #: default datatype name

    def __init__(self, table='events_log', *args, **kwargs):

        super(EventLogFunder, self).__init__(table=table, *args, **kwargs)
