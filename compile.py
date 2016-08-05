#! /usr/bin/python2

from task import tasks, subtasks, Task
from sql import tables, Table
from id import get_package_id
from binary import append_binary_list

import package
import os
import sys
import re
import tempfile

def PackageCompilation(jmgr, os_target, sql, args):
	cmd = ["docker" "run -v /filer/bin:/filer -w /filer --network=host -it bpjain/ubuntu-compiler /filer/run-compile.sh"]


subtasks['PackageCompilation'] = Task(
	name = "Package Compilation",
	func = PackageCompilation,
	arg_defs = ["Package Name"],
	job_name = lambda args: "Package Compilation: " + args[0])

def ListForPackageCompiltation(jmgr, os_target, sql, args):
	for pkg in package.pick_packages_from_args(os_target, sql, args):
		subtasks['PackageCompilation'].create_job(jmgr, [pkg])

tasks['ListForPackageCompiltation'] = Task(
	name = "Compile Selected Package(s)",
	func = ListForPackageCompiltation,
	arg_defs = package.args_to_pick_packages,
	order = 40)