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
			['rank'],
			[['package_name']])

popcon_urls = [
	"http://popcon.ubuntu.com/by_inst",
	"http://popcon.debian.org/by_inst",
]

def package_popularity_run(jmgr, sql, args):
	sql.connect_table(package_popularity_table)

	popularity = dict()
	sum = {'package_name': 'Total', 'rank': 999999, 'inst': 0, 'vote': 0}

	for url in popcon_urls:
		data = urllib2.urlopen(url)
		for line in data:
			# Ignore comments
			if line.startswith('#'):
				continue
			# End of the file/webpage confined for this webpage
			if line.startswith('-'):
				line = next(data)
				results = line.strip().split()
				sum['inst'] += int(results[2])
				sum['vote'] += int(results[3])
				break

			results = line.strip().split()
			if len(results) < 4:
				continue
			package_name = results[1]

			if re.search(r'[^A-Za-z0-_\+\-\.]', package_name):
				continue

			if package_name in popularity:
				values = popularity[package_name]
				values['inst'] += int(results[2])
				values['vote'] += int(results[3])
			else:
				values = dict()
				values['inst'] = int(results[2])
				values['vote'] = int(results[3])
				popularity[package_name] = values

	packages = []
	for (package_name, values) in popularity.items():
		values['package_name'] = package_name
		packages.append(values)

	def inst_cmp(x, y):
		return cmp(x['inst'], y['inst'])

	packages = sorted(packages, inst_cmp, reverse=True)

	sql.delete_record(package_popularity_table)
	rank = 1
	for values in packages:
			values['rank'] = rank
			rank += 1
			sql.append_record(package_popularity_table, values)
	sql.append_record(package_popularity_table, sum)
	sql.commit()

def package_popularity_job_name(args):
	return "Package Popularity"

PackagePopularity = Task(
		name="Package Popularity",
		func=package_popularity_run,
		arg_defs=[],
		job_name=package_popularity_job_name)

def get_packages_by_ranks(sql, min, max):
	sql.connect_table(package_popularity_table)
	results = sql.search_record(package_popularity_table,
			'rank >= ' + Table.stringify(min) + ' AND rank <= ' + Table.stringify(max),
			['package_name'])
	if results:
		for r in results:
			yield r[0]
