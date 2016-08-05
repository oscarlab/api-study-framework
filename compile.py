#! /usr/bin/python2

from task import tasks, subtasks, Task
from sql import tables, Table
from id import get_package_id
#from binary import append_binary_list
from utils import null_dev

import package
import os
import sys
import re
import tempfile
import subprocess
import logging

def PackageCompilation(jmgr, os_target, sql, args):

	cmd = ['docker', 'run', '--rm', '-v', '/filer/bin:/filer', '-w',
	'/filer', '--network=host', 'ubuntu-compiler-blah', '/filer/run-compile.sh']
	
	p = subprocess.Popen(cmd + [args[0]], stdout=subprocess.PIPE, stderr=null_dev)
	(stdout, stderr) = p.communicate()
	p.wait()
	if p.returncode != 0:
		print stderr
		logging.error(stderr)
		raise Exception("Cannot compile sl")


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

if __name__ == "__main__":
	cmd = ['docker', 'run', '--rm', '-v', '/filer/bin:/filer', '-w',
	'/filer', '--network=host', 'ubuntu-compiler-blah', '/filer/run-compile.sh']
	
	p = subprocess.Popen(cmd +[sys.argv[1]], stdout=subprocess.PIPE, stderr=null_dev)
	(stdout, stderr) = p.communicate()
	for line in stdout.split("\n"):
		print line
	p.wait()
	if p.returncode != 0:
		print stderr
		logging.error(stderr)
		raise Exception("Cannot compile sl")
