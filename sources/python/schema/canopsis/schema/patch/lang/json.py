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

from canopsis.schema.patch.core import registerpatch
from canopsis.schema.lang.json import JsonSchema
from canopsis.schema.patch.core import Patch
from canopsis.schema.transformation.core import Transformation

import jsonpatch
import json


@registerpatch(JsonSchema)
class JSONPatch(Patch):

    def process(self, data):
        """define the correct process to return the patch 
        in the correct form and apply it on data"""

        filtre = self.filtre(schema)

        patch = self.patch(schema)
        pa = []

        for element in patch:
            pa.append(patch[element])

        p = jsonpatch.JsonPatch(pa)
        result = p.apply(data)

        return result

    def save(self, data):
        inplace = self.JsonSchema['sup']

        if inplace == 'true':
            output = self.output(data)

            with open('output', "w") as f:
                jdon.dump(data, output, sort_keys = True, indent = 2, separators = (',', ':'))