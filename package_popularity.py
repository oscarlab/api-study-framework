#!/usr/bin/python

from task import Task
from sql import Table

import os
import sys
import re
import urllib2

package_popularity_table = Table('package_popularity', [
			('package_name', 'VARCHAR', 'NOT NULL'),
			('rank', 'INT', 'NOT NULL'),
			('inst', 'INT', 'NOT NULL'),
			('vote', 'INT', 'NOT NULL')],
			['package_name'])

def package_popularity_run(jmgr, sql, args):
	sql.connect_table(package_popularity_table)

	data = urllib2.urlopen("http://popcon.debian.org/by_inst");

	sql.delete_record(package_popularity_table)
	for line in data:
		# Ignore comments
		if not line.startswith('#'):
			# End of the file/webpage confined for this webpage
			if line.startswith('-'):
				break

			result = line.strip().split()
			values = dict()
			values['package_name'] = result[1]
			values['rank'] = int(result[0])
			values['inst'] = int(result[2])
			values['vote'] = int(result[3])

			sql.append_record(package_popularity_table, values)
	sql.commit()

def package_popularity_job_name(args):
	return "Package Popularity"

PackagePopularity = Task(
		name="Package Popularity",
		func=package_popularity_run,
		arg_defs=[],
		job_name=package_popularity_job_name)
