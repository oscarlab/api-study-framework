#!/usr/bin/python

from task import tasks, subtasks, Task
from sql import tables, Table
from id import get_binary_id, get_package_id
import package
import main

import os
import sys
import re

# tables['instr_list'] = Table('instr_list', [
# 		('opcode', 'BIGINT', 'NOT NULL'),
# 		('mnem', 'VARCHAR', 'NOT NULL'),
# 		('size', 'INT', 'NULL')],
# 		None, # NO PRIMARY KEY. TABLE WILL HAVE DUPLICATES. REMOVE LATER.
# 		[['opcode']])

# tables['prefix_counts'] = Table('prefix_counts', [
# 		('pkg_id', 'INT', 'NOT NULL'),
# 		('bin_id', 'INT', 'NOT NULL'),
# 		('func_addr', 'INT', 'NOT NULL'),
# 		('prefix', 'BIGINT', 'NOT NULL'),
# 		('count', 'INT', 'NOT NULL')],
# 		['pkg_id', 'bin_id', 'func_addr', 'prefix'],
# 		[['prefix']])

tables['binary_call_missrate'] = Table('binary_call_missrate',[
		('pkg_id', 'INT', 'NOT NULL'),
		('bin_id', 'INT', 'NOT NULL'),
		('func_addr', 'INT', 'NOT NULL'),
		('miss_rate', 'REAL', 'NULL')],
		['pkg_id', 'bin_id', 'func_addr'],
		[['pkg_id', 'bin_id'], ['pkg_id', 'bin_id', 'func_addr']])

tables['binary_opcode_usage'] = Table('binary_opcode_usage', [
		('pkg_id', 'INT', 'NOT NULL'),
		('bin_id', 'INT', 'NOT NULL'),
		('func_addr', 'INT', 'NOT NULL'),
		('prefix', 'BIGINT', 'NULL'),
		('opcode', 'BIGINT', 'NOT NULL'),
		('size', 'INT', 'NOT NULL'),
		('mnem', 'VARCHAR', 'NOT NULL'),
		('count', 'INT', 'NOT NULL')],
		['pkg_id', 'bin_id', 'func_addr', 'prefix', 'opcode', 'size', 'mnem'],
		[['pkg_id', 'bin_id'], ['pkg_id', 'bin_id', 'func_addr'], ['prefix', 'opcode', 'size']])

def BinaryInstr(jmgr, os_target, sql, args):
	sql.connect_table(tables['binary_call'])
	sql.connect_table(tables['binary_call_unknown'])
	sql.connect_table(tables['binary_opcode_usage'])
	sql.connect_table(tables['binary_call_missrate'])
	# sql.connect_table(tables['instr_list'])
	# sql.connect_table(tables['prefix_counts'])

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
		os_target.analysis_binary_instr_linear(sql, dir, bin, pkg_id, bin_id)

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
