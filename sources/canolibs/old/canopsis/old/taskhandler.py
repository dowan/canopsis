#!/usr/bin/env python
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

from canopsis.old.engine import Engine

from canopsis.old.event import get_routingkey
from time import time
from json import loads


class TaskHandler(Engine):
    def __init__(self, *args, **kwargs):
        super(TaskHandler, self).__init__(*args, **kwargs)
        self.amqp_queue = self.name

    def work(self, msg, *args, **kwargs):
        self.logger.info('Received job: {0}'.format(msg))

        start = int(time())

        job = None
        output = None
        state = 3

        try:
            job = loads(msg)

        except ValueError as err:
            self.logger.error('Impossible to decode message: {0}'.format(err))
            return

        state, output = self.handle_task(job)

        end = int(time())

        event = {
            'timestamp': end,
            'connector': 'taskhandler',
            'connector_name': self.name,
            'event_type': 'check',
            'source_type': 'resource',
            'component': 'job',
            'resource': job['id'],
            'state': state,
            'state_type': 1,
            'output': output,
            'execution_time': end - start
        }

        self.amqp.publish(
            event, get_routingkey(event),
            self.amqp.exchange_name_events)

    def handle_task(self, job):
        """
            :param job: Job's informations
            :type job: dict

            :returns: (<state>, <output>)
        """

        raise NotImplementedError()
