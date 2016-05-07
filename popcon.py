#!/usr/bin/python

import os
import sys
import re
import urllib2

popcon_urls = [
	"http://popcon.ubuntu.com/by_inst",
	"http://popcon.debian.org/by_inst",
]

def get_package_popularity():
	popularity = dict()
	sum = {'package_name': 'Total', 'rank': 999999, 'inst': 0}

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
			else:
				values = dict()
				values['inst'] = int(results[2])
				popularity[package_name] = values

	packages = []
	for (package_name, values) in popularity.items():
		values['package_name'] = package_name
		packages.append(values)

	def inst_cmp(x, y):
		return cmp(x['inst'], y['inst'])

	packages = sorted(packages, inst_cmp, reverse=True)
	rank = 1
	for i in range(len(packages)):
		packages[i]['rank'] = rank
		rank += 1

	packages.append(sum)
	return packages
