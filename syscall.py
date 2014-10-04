#!/usr/bin/python

from task import Task
from sql import Table

import os
import sys
import re

def get_syscalls():
	files = [
		'/usr/include/x86_64-linux-gnu/asm/unistd_64.h',
		'/usr/include/asm/unistd_64.h',
	]

	unistd_file = None
	for f in files:
		if os.path.exists(f):
			unistd_file = f
			break
	if not unistd_file:
		raise Exception("Cannot find unistd file")

	with open(unistd_file, 'r') as u:
		syscalls = {}
		for line in u:
			match = re.match(r"^\#\s*define\s+__NR_([a-z0-9_]+)\s+([0-9]+)$", line)
			if match:
				syscalls[int(match.group(2))] = match.group(1)
		return syscalls

syscalls = get_syscalls()

syscall_table = Table('syscall', [
			('number', 'INT', 'NOT NULL'),
			('name', 'VARCHAR(40)', 'NOT NULL')],
			['number'])

def syscall_run(jmgr, sql, args):
	sql.connect_table(syscall_table)
	sql.delete_record(syscall_table)

	for (number, name) in syscalls.items():
		values = dict()
		values['number'] = number
		values['name'] = name

		sql.append_record(syscall_table, values)
	sql.commit()

def syscall_job_name(args):
	return "List Syscalls"

ListSyscall = Task(
		name="List Syscalls",
		func=syscall_run,
		arg_defs=[],
		job_name=syscall_job_name)

if __name__ == "__main__":
	for (number, name) in syscalls.items():
		print '%d:' % number, name
