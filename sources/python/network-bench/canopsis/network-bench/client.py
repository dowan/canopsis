# -*- coding: utf-8 -*-
# --------------------------------
# Copyright (c) 2016 "Capensis" [http://www.capensis.com]
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

from b3j0f.conf import Configurable
import zmq
from time import time
from hash import HashGenerator


@Configurable(paths='bench/architecture.conf')
class Client(object):
    def __init__(self, host=None, port=None, *args, **kwargs):
        super(Client, self).__init__(*args, **kwargs)

        self.host = host
        self.port = port

        self.context = zmq.Context()
        self.zmq_socket = self.context.socket(zmq.PUSH)
        self.zmq_socket.connect("tcp://{0}:{1}".format(self.host, self.port))

        self.hash_generator = HashGenerator()

    def send(self, message):

        print('envoi pour l\'envoi d\'un message')
        send_list = []
        send_list.append(self.hash_generator.get_hash(message))
        send_list.append(time())
        self.zmq_socket.send_pyobj(send_list)
        print('pour l\'envoi d\'un message gone')


    def receive(self, message):
        print('envoi pour la reception d\'un message')
        receive_list=[]
        receive_list.append(self.hash_generator.get_hash(message))
        receive_list.append(time())
        self.zmq_socket.send_pyobj(receive_list)
        print('pour la reception d\'un message gone')


