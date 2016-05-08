#!/usr/bin/python

from task import tasks, subtasks, Task
from sql import tables, Table
from id import get_package_id, get_binary_id
import package
import symbol
import callgraph

import os
import sys
import re

tables['binary_list'] = Table('binary_list', [
		('pkg_id', 'INT', 'NOT NULL'),
		('bin_id', 'INT', 'NOT NULL'),
		('type', 'CHAR(3)', 'NOT NULL'),
		('callgraph', 'BOOLEAN', ''),
		('linking', 'BOOLEAN', '')],
		['pkg_id', 'bin_id'],
		[['pkg_id', 'bin_id', 'type'], ['bin_id']])

tables['binary_link'] = Table('binary_link', [
		('pkg_id', 'INT', 'NOT NULL'),
		('lnk_id', 'INT', 'NOT NULL'),
		('target', 'INT', 'NOT NULL'),
		('linking', 'BOOLEAN', '')],
		['pkg_id', 'lnk_id'],
		[['lnk_id'], ['target']])

def append_binary_list(sql, pkgname, dir, binaries):
	pkg_id = get_package_id(sql, pkgname)
	insert_values = []

	for (bin, type, interpreter) in binaries:
		bin_id = get_binary_id(sql, bin)
		values = dict()
		values['type'] = type

		if type == 'lnk':
			link = os.readlink(dir + bin)
			target = os.path.join(os.path.dirname(bin), link)
			target_id = get_binary_id(sql, target)
			values['pkg_id'] = pkg_id
			values['lnk_id'] = bin_id
			values['target'] = target_id
			values['linking'] = False
		else:
			values['pkg_id'] = pkg_id
			values['bin_id'] = bin_id
			if type == 'scr':
				interp_id = get_binary_id(sql, interpreter)
				values['interp'] = interp_id
				values['callgraph'] = True
			else:
				values['callgraph'] = False
			values['linking'] = False

		insert_values.append(values)

	condition = 'pkg_id=' + Table.stringify(pkg_id)
	sql.delete_record(tables['binary_list'], condition)
	sql.delete_record(tables['binary_link'], condition)
	sql.delete_record(tables['binary_interp'], condition)

	for values in insert_values:
		if values['type'] == 'lnk':
			sql.append_record(tables['binary_link'], values)
		else:
			sql.append_record(tables['binary_list'], values)
			if values['type'] == 'scr':
				sql.append_record(tables['binary_interp'], values)

def BinaryInfo(jmgr, os_target, sql, args):
	sql.connect_table(tables['binary_list'])
	sql.connect_table(tables['binary_link'])
	sql.connect_table(tables['binary_interp'])

	(dir, pkgname, _) = package.unpack_package(os_target, args[0])
	if not dir:
		return

	binaries = os_target.get_binaries(dir, find_script=True)
	if not binaries:
		package.remove_dir(dir)
		return

	append_binary_list(sql, pkgname, dir, binaries)

	sql.commit()
	package.remove_dir(dir)

subtasks['BinaryInfo'] = Task(
	name = "Binary List",
	func = BinaryInfo,
	arg_defs = ["Package Name"],
	job_name = lambda args: "Collect Binary Info: " + args[0])

def ListForBinaryInfo(jmgr, os_target, sql, args):
	for pkg in package.pick_packages_from_args(os_target, sql, args):
		subtasks['BinaryInfo'].create_job(jmgr, [pkg])

tasks['ListForBinaryInfo'] = Task(
	name = "List Packages to Collect Binary Info",
	func = ListForBinaryInfo,
	arg_defs = package.args_to_pick_packages)

def BinaryAnalysis(jmgr, os_target, sql, args):
	(dir, pkgname, _) = package.unpack_package(os_target, args[0])
	if not dir:
		return

	binaries = os_target.get_binaries(dir, find_script=True)
	if not binaries:
		package.remove_dir(dir)
		return

	append_binary_list(sql, pkgname, dir, binaries)

	for (bin, type, _) in binaries:
		if type == 'lnk' or type == 'scr':
			continue

		ref = package.reference_dir(dir)
		subtasks['BinarySymbol'].create_job(jmgr, [pkgname, bin, dir, ref])

		ref = package.reference_dir(dir)
		subtasks['BinaryDependency'].create_job(jmgr, [pkgname, bin, dir, ref])

		ref = package.reference_dir(dir)
		subtasks['BinaryCall'].create_job(jmgr, [pkgname, bin, dir, ref])

subtasks['BinaryAnalysis'] = Task(
	name = "Full Binary Analysis",
	func = BinaryAnalysis,
	arg_defs = ["Package Name"],
	job_name = lambda args: "Full Binary Analysis: " + args[0])

def ListForBinaryAnalysis(jmgr, os_target, sql, args):
	for pkg in package.pick_packages_from_args(os_target, sql, args):
		subtasks['BinaryAnalysis'].create_job(jmgr, [pkg])

tasks['ListForBinaryAnalysis'] = Task(
	name = "List Packages for Full Binary Analysis",
	func = ListForBinaryAnalysis,
	arg_defs = package.args_to_pick_packages)
