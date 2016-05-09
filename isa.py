#!/usr/bin/python

from sql import tables, Table
import sql
from task import tasks, Task

tables['instr_list'] = Table('instr_list', [
		('id', 'INT', 'NOT NULL'),
		('name', 'VARCHAR', 'NOT NULL')],
		['id'])

tables['binary_instr_usage'] = Table('binary_instr_usage', [
			('pkg_id', 'INT', 'NOT NULL'),
			('bin_id', 'INT', 'NOT NULL'),
			('func_addr', 'INT', 'NOT NULL'),
			('instr', 'INT', 'NOT NULL')],
			['pkg_id', 'bin_id', 'func_addr', 'instr'],
			[['pkg_id', 'bin_id'], ['pkg_id', 'bin_id', 'func_addr']])

tables['binary_instr_count'] = Table('binary_inst_count', [
			('pkg_id', 'INT', 'NOT NULL'),
			('bin_id', 'INT', 'NOT NULL'),
			('instr', 'INT', 'NOT NULL'),
			('count', 'INT', 'NOT NULL')],
			['pkg_id', 'bin_id', 'instr'],
			[['pkg_id', 'bin_id']])
