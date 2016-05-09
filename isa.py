#!/usr/bin/python

from task import tasks, subtasks, Task
from sql import tables, Table
from id import get_binary_id, get_package_id
import package
import main

import os
import sys
import re

tables['instr_list'] = Table('instr_list', [
		('id', 'INT', 'NOT NULL'),
		('name', 'VARCHAR', 'NOT NULL')],
		['id'])

tables['binary_instr_usage'] = Table('binary_instr_usage', [
			('pkg_id', 'INT', 'NOT NULL'),
			('bin_id', 'INT', 'NOT NULL'),
			('func_addr', 'INT', 'NOT NULL'),
			('instr', 'VARCHAR(15)', 'NOT NULL'),
			('count', 'INT', 'NOT NULL')],
			['pkg_id', 'bin_id', 'func_addr', 'instr'],
			[['pkg_id', 'bin_id'], ['pkg_id', 'bin_id', 'func_addr']])

def BinaryInstr(jmgr, os_target, sql, args):
	sql.connect_table(tables['binary_call'])
	sql.connect_table(tables['binary_call_unknown'])
	sql.connect_table(tables['binary_instr_usage'])

	pkgname = args[0]
	bin = args[1]
	dir = args[2]
	pkg_id = get_package_id(sql, pkgname)

	if len(args) > 3:
		ref = args[3]
		if not package.reference_exists(dir, ref):
			dir = None
			ref = None
	else:
		ref = None

	unpacked = False
	if not dir:
		(dir, pkgname, _) = package.unpack_package(os_target, args[0])
		if not dir:
			return
		unpacked = True

	exc = None
	try:
		if not os.path.exists(dir + bin):
			raise Exception('path ' + dir + bin + ' does not exist')

		bin_id = get_binary_id(sql, bin)
		os_target.analysis_binary_instr(sql, dir, bin, pkg_id, bin_id)

		condition = 'pkg_id=' + Table.stringify(pkg_id) + ' and bin_id=' + Table.stringify(bin_id)
		sql.update_record(tables['binary_list'], {'callgraph': False}, condition)
		sql.commit()

	except Exception as err:
		exc = sys.exc_info()

	if (ref and package.dereference_dir(dir, ref)) or unpacked:
		package.remove_dir(dir)
	if exc:
		raise exc[1], None, exc[2]


subtasks['BinaryInstr'] = Task(
	name = "Collect Binary Instruction Usage",
	func = BinaryInstr,
	arg_defs = ["Package Name", "Binary Path", "Unpack Path"],
	job_name = lambda args: "Collect Binary Instruction Usage: " + args[1] + " in " + args[0])

def BinaryInstrInfo(jmgr, os_target, sql, args):
	(dir, pkgname, _) = package.unpack_package(os_target, args[0])
	if not dir:
		return

	binaries = os_target.get_binaries(dir)
	if not binaries:
		package.remove_dir(dir)
		return

	for (bin, type, _) in binaries:
		if type == 'lnk':
			continue
		ref = package.reference_dir(dir)
		subtasks['BinaryInstr'].create_job(jmgr, [pkgname, bin, dir, ref])

tasks['BinaryInstrInfo'] = Task(
	name = "Collect Binary Instruction Usage",
	func = BinaryInstrInfo,
	arg_defs = ["Package Name"],
	job_name = lambda args: "Collect Binary Instruction Usage: " + args[0])

def ListForBinaryInstrInfo(jmgr, os_target, sql, args):
	for pkg in package.pick_packages_from_args(os_target, sql, args):
		tasks['BinaryInstrInfo'].create_job(jmgr, [pkg])

tasks['ListForBinaryInstrInfo'] = Task(
	name = "List Packages to Collect Binary Instruction Usage",
	func = ListForBinaryInstrInfo,
	arg_defs = package.args_to_pick_packages)
