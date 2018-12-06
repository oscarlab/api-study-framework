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
import namesgenerator
from threading import Timer
def InlineASMAnalysis(jmgr, os_target, sql, args):
	cmd = ['docker', 'run', '--rm', '-v', '/filer/bin:/filer', '-w',
		'/filer', '--network=host', 'aakshintala/ubuntu-compiler:gcc', '/filer/run-inlineasm.sh']

	p = subprocess.Popen(cmd + [args[0]], stdout=subprocess.PIPE, stderr=null_dev)
	(stdout, stderr) = p.communicate()
	p.wait()
	if p.returncode != 0:
		print stderr
		logging.error(stderr)
		raise Exception("Cannot run Inline ASM Analysis")

subtasks['InlineASMAnalysis'] = Task(
	name = "Inline ASM Analysis:",
	func = InlineASMAnalysis,
	arg_defs = ["Package Name"],
	job_name = lambda args: "Inline ASM Analysis: " + args[0])

def ListForInlineASM(jmgr, os_target, sql, args):
	for pkg in package.pick_packages_from_args(os_target, sql, args):
		subtasks['InlineASMAnalysis'].create_job(jmgr, [pkg])

tasks['ListForInlineASM'] = Task(
	name = "Collect data about Inline ASM",
	func = ListForInlineASM,
	arg_defs = package.args_to_pick_packages,
	order = 43)
def kill_and_remove(name):
	for action in ('kill','rm'):
		logging.error(name)
		p=subprocess.Popen('docker %s %s'%(action,name),stdout=subprocess.PIPE,stderr=null_dev)
		if p.wait()!=0:
			raise Exception("Cannot kill")
def PackageCompilationGCC(jmgr, os_target, sql, args):
	container_name=namesgenerator.get_random_name()

#	cmd = ['docker', 'run', '--rm', '-v', '/filer/bin:/filer', '-w',
#		'/filer', '--network=host', 'aakshintala/ubuntu-compiler:gcc', '/filer/run-compile-gcc.sh']
	cmd = ['timeout','-s','SIGKILL','300','docker', 'run', '--rm','--name',container_name, '-v', '/filer/bin:/filer', '-w',
		'/filer', '--network=host', 'aakshintala/ubuntu-compiler:gcc', '/filer/run-compile-gcc.sh']
	logging.error(container_name)
	p = subprocess.Popen(cmd + [args[0]], stdout=subprocess.PIPE, stderr=null_dev)
	(stdout, stderr) = p.communicate()
	if p.wait()==-9:
		kill_and_remove(container_name)
		logging.error("Cannot compile-timeout")
		raise Exception("Cannot compile-GCC timeout")
	if p.returncode != 0:
		print stderr
		logging.error(stderr)
		raise Exception("Cannot compile - GCC")

subtasks['PackageCompilationGCC'] = Task(
	name = "Package Compilation - GCC",
	func = PackageCompilationGCC,
	arg_defs = ["Package Name"],
	job_name = lambda args: "Package Compilation - GCC: " + args[0])

def ListForPackageCompiltationGCC(jmgr, os_target, sql, args):
	completed=[]
	with open('completed','r') as f:
		for line in f:
			filename=line.split("\n")[0]
			completed.append(filename)
	for pkg in package.pick_packages_from_args(os_target, sql, args):
		if pkg in completed:
			continue
		subtasks['PackageCompilationGCC'].create_job(jmgr, [pkg])

tasks['ListForPackageCompiltationGCC'] = Task(
	name = "Compile Selected Package(s) - GCC",
	func = ListForPackageCompiltationGCC,
	arg_defs = package.args_to_pick_packages,
	order = 41)

def PackageCompilationLLVM(jmgr, os_target, sql, args):
	cmd = ['docker', 'run', '--rm', '-v', '/filer/bin:/filer', '-w',
		'/filer', '--network=host', 'aakshintala/ubuntu-compiler', '/filer/run-compile.sh']

	p = subprocess.Popen(cmd + [args[0]], stdout=subprocess.PIPE, stderr=null_dev)
	(stdout, stderr) = p.communicate()
	p.wait()
	if p.returncode != 0:
		print stderr
		logging.error(stderr)
		raise Exception("Cannot compile - LLVM")

subtasks['PackageCompilationLLVM'] = Task(
	name = "Package Compilation - LLVM",
	func = PackageCompilationLLVM,
	arg_defs = ["Package Name"],
	job_name = lambda args: "Package Compilation - LLVM: " + args[0])

def ListForPackageCompiltationLLVM(jmgr, os_target, sql, args):
	for pkg in package.pick_packages_from_args(os_target, sql, args):
		subtasks['PackageCompilationLLVM'].create_job(jmgr, [pkg])

tasks['ListForPackageCompiltationLLVM'] = Task(
	name = "Compile Selected Package(s) - LLVM",
	func = ListForPackageCompiltationLLVM,
	arg_defs = package.args_to_pick_packages,
	order = 40)


if __name__ == "__main__":
	cmd = ['docker', 'run', '--rm', '-v', '/filer/bin:/filer', '-w',
	'/filer', '--network=host', 'aakshintala/ubuntu-compiler', '/filer/run-compile.sh']

	p = subprocess.Popen(cmd +[sys.argv[1]], stdout=subprocess.PIPE, stderr=null_dev)
	(stdout, stderr) = p.communicate()
	for line in stdout.split("\n"):
		print line
	p.wait()
	if p.returncode != 0:
		print stderr
		logging.error(stderr)
		raise Exception("Cannot compile using llvm")

	cmd = ['docker', 'run', '--rm', '-v', '/filer/bin:/filer', '-w',
			'/filer', '--network=host', 'aakshintala/ubuntu-compiler:gcc', '/filer/run-compile-gcc.sh']

	p = subprocess.Popen(cmd +[sys.argv[1]], stdout=subprocess.PIPE, stderr=null_dev)
	(stdout, stderr) = p.communicate()
	for line in stdout.split("\n"):
		print line
	p.wait()
	if p.returncode != 0:
		print stderr
		logging.error(stderr)
		raise Exception("Cannot compile using gcc")
