#!/usr/bin/python

import os
import sys
import re
import urllib2

popcon_urls = [
	"http://popcon.ubuntu.com/",
	"http://popcon.debian.org/",
]

def get_package_popularity():
	sum = 0
	for url in popcon_urls:
		data = urllib2.urlopen(url)
		for line in data:
			# remove HTML tags
			line = re.sub(r'<.*?>', '', line)
			m = re.search('Number of submissions considered:\s*(\d+)', line)
			if m:
				sum = sum + int(m.group(1))

	popularity = dict()

	for url in popcon_urls:
		data = urllib2.urlopen(url + "by_inst")
		for line in data:
			# Ignore comments
			if line.startswith('#'):
				continue

			if line.startswith('-'):
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

	values = dict()
	values['package_name'] = 'Total'
	values['rank'] = 1000000
	values['inst'] = sum
	packages.append(values)

	return packages

if __name__ == "__main__":
	for pkg in get_package_popularity():
		print "%d: %s (%d)" % (pkg['rank'], pkg['package_name'], pkg['inst'])

