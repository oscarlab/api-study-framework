#!/usr/bin/python

from task import tasks, subtasks, Task
from sql import tables, Table
from id import get_package_id

import os
import sys
import re

tables['package_dependency'] = Table('package_dependency', [
		('pkg_id', 'INT', 'NOT NULL'),
		('dependency', 'INT', 'NOT NULL')],
		['pkg_id', 'dependency'], [['dependency']])

tables['package_popularity'] = Table('package_popularity', [
		('package_name', 'VARCHAR', 'NOT NULL'),
		('rank', 'INT', 'NOT NULL'),
		('inst', 'BIGINT', 'NOT NULL')],
		['rank'], [['package_name']])

def get_packages_by_names(os_target, names):
	packages = os_target.get_packages()
	return [name for name in names if name in packages]

def get_packages_by_prefixes(os_target, prefixes):
	packages = os_target.get_packages()
	result = []
	for package in packages:
		for p in prefixes:
			if package.startswith(p):
				result.append(package)
				break
	return result

def get_packages_by_ranks(os_target, sql, min, max):
	sql.connect_table(tables['package_popularity'])
	packages = os_target.get_packages()
	packages_by_ranks = sql.search_record(
				tables['package_popularity'],
				'rank >= ' + Table.stringify(min) + ' AND rank <= ' + Table.stringify(max),
				['package_name'])
	result = []
	for (name,) in packages_by_ranks:
		if name in packages:
			result.append(name)
	return result

def PackageInfo_run(jmgr, os_target, sql, args):
	sql.connect_table(tables['package_dependency'])

	pkgname = args[0]
	pkg_id = get_package_id(sql, pkgname)

	pkg_info = os_target.get_package_info(pkgname)
	pkg_deps = os_target.get_package_dependency(pkgname)

	# Clean up records
	sql.delete_record(tables['package_dependency'], 'pkg_id=\'' + Table.stringify(pkg_id) + '\'')

	for dep in pkg_deps:
		dep_id = get_package_id(sql, dep)
		values = dict()
		values['pkg_id'] = pkg_id
		values['dependency'] = dep_id
		sql.append_record(tables['package_dependency'], values)

	sql.commit()

def PackageInfo_job_name(args):
	return "Package Info and Dependency: " + args[0]

subtasks['PackageInfo'] = Task(
	name="Package Info and Dependency",
	func=PackageInfo_run,
	arg_defs=["Package Name"],
	job_name=PackageInfo_job_name)

def PackageListInfo_run(jmgr, os_target, sql, args):
	packages = get_packages_by_names(os_target, args[0].split())
	if packages:
		for pkg in packages:
			subtasks['PackageInfo'].create_job(jmgr, [pkg])

def PackageListInfo_job_name(args):
	return "Package Info List By Names: " + args[0]

tasks['PackageListInfo'] = Task(
	name="Package List Info",
	func=PackageListInfo_run,
	arg_defs=["Package Names"],
	job_name=PackageListInfo_job_name)

def PackagePopularity_run(jmgr, os_target, sql, args):
	sql.connect_table(tables['package_popularity'])

	pop = os_target.get_package_popularity()

	sql.delete_record(tables['package_popularity'])
	for values in pop:
		sql.append_record(tables['package_popularity'], values)

	sql.commit()

def PackagePopularity_job_name(args):
	return "Package Popularity"

tasks['PackagePopularity'] = Task(
		name="Package Popularity",
		func=PackagePopularity_run,
		arg_defs=[],
		job_name=PackagePopularity_job_name)
