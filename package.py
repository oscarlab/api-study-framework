#!/usr/bin/python

from task import Task
from package_popularity import package_popularity_table

import os
import sys
import re
import subprocess

def get_packages():
	process = subprocess.Popen(["apt-cache", "pkgnames"],
			stdout=subprocess.PIPE)
	(stdout, stderr) = process.communicate()
	return stdout.split()

def get_packages_by_names(names):
	packages = get_packages()
	return [name for name in names if name in packages]

def get_packages_by_prefixes(prefixes):
	packages = get_packages()
	result = []
	for package in packages:
		for p in prefixes:
			if package.startswith(p):
				result.append(package)
				break
	return result

def get_packages_by_ranks(sql, min, max):
	sql.connect_table(package_popularity_table)
	packages = get_packages()
	packages_by_ranks = sql.search_record(
				package_popularity_table,
				'RANK >= ' + min + ' AND RANK <= ' + max,
				['PACKAGE_NAME'])
	return [name for name in packages if name in packages_by_ranks]

def PackageInfo_run(jmgr, sql, args):
	process = subprocess.Popen(["apt-cache", "showpkg", args[0]],
			stdout=subprocess.PIPE)
	(stdout, stderr) = process.communicate()
	print stdout

def PackageInfo_job_name(args):
	return "Package Info: " + args[0]

PackageInfo = Task(
	name="Package Info",
	func=PackageInfo_run,
	arg_defs=["Package Name"],
	job_name=PackageInfo_job_name)

def PackageListByNames_run(jmgr, sql, args):
	packages = get_packages_by_names(args[0].split())
	if packages:
		for i in packages:
			PackageInfo.create_job(jmgr, [i])

def PackageListByNames_job_name(args):
	return "Package List By Names: " + args[0]

PackageListByNames = Task(
	name="Package List By Names",
	func=PackageListByNames_run,
	arg_defs=["Package Names"],
	job_name=PackageListByNames_job_name)

def PackageListByPrefixes_run(jmgr, sql, args):
	packages = get_packages_by_prefixes(args[0].split())
	if packages:
		for i in packages:
			PackageInfo.create_job(jmgr, [i])

def PackageListByPrefixes_job_name(args):
	return "Package List By Prefixes: " + args[0]

PackageListByPrefixes = Task(
	name="Package List By Prefixes",
	func=PackageListByPrefixes_run,
	arg_defs=["Package Prefixes"],
	job_name=PackageListByPrefixes_job_name)

def PackageListByRanks_run(jmgr, sql, args):
	packages = get_packages_by_ranks(int(args[0]), int(args[1]))
	if packages:
		for i in packages:
			PackageInfo.create_job(jmgr, [i])

def PackageListByRanks_job_name(args):
	return "Package List By Ranks: " + args[0] + " to " + args[1]

PackageListByRanks = Task(
	name="Package List By Ranks",
	func=PackageListByRanks_run,
	arg_defs=["Minimum Rank", "Maximum Rank"],
	job_name=PackageListByRanks_job_name)
