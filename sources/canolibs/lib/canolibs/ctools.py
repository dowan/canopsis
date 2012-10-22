#!/usr/bin/env python
#--------------------------------
# Copyright (c) 2011 "Capensis" [http://www.capensis.com]
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

import re, logging, socket, time

legend = ['ok','warning','critical','unknown']

logger = logging.getLogger('ctools')

#############################################

def calcul_pct(data, total=None):
	if not total:
		## Get total
		total = 0
		for key in data.keys():
			value = data[key]
			total += value
	## Calc pct
	data_pct = {}
	for key in data.keys():
		value = data[key]
		data_pct[key] = round(((float(value) * 100) / float(total)), 2)

	## Fix empty value
	for key in legend:
		try:
			value = data_pct[key]
		except:
			data_pct[key] = 0

	return data_pct

#############################################
RE_PERF_DATA = re.compile("('?([0-9A-Za-z/\\\:\.%%\-{}\?_ ]*)'?=([0-9.,]*)(([A-Za-z%%/]*))(;@?([0-9.,]*):?)?(;@?([0-9.,]*):?)?(;@?([0-9.,]*):?)?(;@?([0-9.,]*):?)?(;? ?))")

def parse_perfdata(perf_data_raw):
		# 'label'=value[UOM];[warn];[crit];[min];[max]
		#   load1=0.440     ;5.000 ;10.000;0    ;

		logger.debug("Parse: %s" % perf_data_raw)

		perfs = RE_PERF_DATA.split(perf_data_raw)

		perf_data_array = []
		perf_data = {}
		i=0
		for info in perfs:
			if info == '':
				info = None

			#logger.debug(" + %s '%s'" % (i, info))
			try:
				if   info and i == 2:
					perf_data['metric'] = info
				elif info and i == 3:
					perf_data['value'] = info.replace(',','.')
				elif info and i == 4:
					perf_data['unit'] = info
				elif info and i == 7:
					perf_data['warn'] = info.replace(',','.')
				elif info and i == 9:
					perf_data['crit'] = info.replace(',','.')
				elif info and i == 11:
					perf_data['min'] = info.replace(',','.')
				elif info and i == 13:
					perf_data['max'] = info.replace(',','.')

				i+=1
				if i==15:
					try:
						logger.debug(" + %s" % perf_data)
						perf_data_clean = {}
						for key in perf_data.keys():
							if perf_data[key]:
								try:
									perf_data_clean[key] = float(perf_data[key])
								except:
									if key == 'metric' or key == 'unit':
										perf_data_clean[key] = perf_data[key]
									else:
										logger.debug("Invalid value, '%s' = '%s'" % (key, perf_data[key]))
								
								#logger.debug("   + %s: %s" % (key, perf_data_clean[key]))
					
						try:
							value = perf_data_clean['value']
							metric = perf_data_clean['metric']
							perf_data_array.append(perf_data_clean)
						except Exception, err:
							logger.warning("perf_data: Missing fields %s (%s)" % (err, perf_data_clean))
							logger.debug("perf_data: Raw: %s" % perf_data_raw)
						
					except Exception, err:
						
						logger.error("perf_data: Raw: %s" % perf_data_raw)
						logger.error("perf_data: Impossible to clean '%s': %s" % (perf_data, err))
	
					perf_data = {}
					i=0

			except Exception, err:
				logger.error("perf_data: Invalid metric %s: %s (%s)" % (i, info, err))

		return perf_data_array

#############################################

def dynmodloads(path=".", subdef=False, pattern=".*"):
	import os, sys

	loaded = {}
	path=os.path.expanduser(path)
	logger.debug("Append path '%s' ..." % path)
	sys.path.append(path)

	try:
		for mfile in os.listdir(path):
			try:
				ext = mfile.split(".")[1]
				name = mfile.split(".")[0]

				if name != "." and ext == "py" and name != '__init__':
					logger.info("Load '%s' ..." % name)
					try:

						module = __import__(name)
						loaded[name] = module
	
						if subdef:
							alldefs = dir(module)
							for mydef in alldefs:
								if mydef not in ["__builtins__", "__doc__", "__file__", "__name__", "__package__"]:
									if re.search(pattern, mydef):
										logger.debug(" + From %s import %s ..." % (name, mydef))
										#exec "from %s import %s" % (name, mydef)
										exec "loaded[mydef] = module.%s" % mydef
						
						 
						logger.debug(" + Success")
					except Exception, err:
						logger.error("\t%s" % err)
			except:
				pass
	except Exception, err:
		logger.error(err)

	return loaded

###########################################

def Str2Number(string):
	value = float(string)
	
	if int(value) == value:
		value = int(value)
		
	return value

##	Remove duplicate entry
def uniq(alist):
	set = {}
	return [set.setdefault(e,e) for e in alist if e not in set]
	
