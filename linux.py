from os_target import OS
import apt
import popcon
import main

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

	syscalls = {}
	with open(unistd_file, 'r') as u:
		for line in u:
			match = re.match(r"^\#\s*define\s+__NR_([a-z0-9_]+)\s+([0-9]+)$", line)
			if match:
				syscalls[int(match.group(2))] = match.group(1)

	return syscalls

class Ubuntu64(OS):
	SYSCALL = 1
	FCNTL = 2
	IOCTL = 3
	PRCTL = 4
	PSEUDOFILE = 5
	LIBC = 6

	def __init__(self):
		OS.__init__(self)
		apt.update_apt(main.get_config('package_source'))

	def get_api_types(self):
		return { self.SYSCALL: 'system call',
			 self.FCNTL: 'fcntl opcode',
			 self.IOCTL: 'ioctl opcode',
			 self.PRCTL: 'prctl opcode',
			 self.PSEUDOFILE: 'system file',
			 self.LIBC: 'libc function' }

	def get_apis(self):
		return [ { 'type': self.SYSCALL, 'id': number, 'name': name }
				for number, name in get_syscalls().items() ]

	def get_packages(self):
		return apt.get_packages()

	def get_package_popularity(self):
		return popcon.get_package_popularity()

	def get_package_info(self, pkgname):
		return apt.get_package_info(pkgname)

	def get_package_dependency(self, pkgname):
		return apt.get_package_dependency(pkgname)
