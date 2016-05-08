#!/usr/bin/python

from binary import get_binary_id, get_package_id
import main
from task import tasks, Task

import os
import sys
import re
import subprocess
import shutil
import stat
import tempfile
import struct
import string

package_exclude_rules = [
		r'^linux-image',
		r'^linux-headers',
		r'.+-dev$',
		r'.+-dbg$',
		r'.+-debug$',
		r'.+-doc(s)?(-.+)?$'
	]

def get_packages():
	package_source = main.get_config('package_source')
	package_arch = main.get_config('package_arch')
	package_options = main.get_config('package_options')

	cmd = ["apt-cache"]

	if package_source:
		cmd += apt_options_for_source(package_source)
	if package_arch:
		cmd += ["-o", "APT::Architectures=" + package_arch]
	if package_options:
		for (opt, val) in package_options.items():
			cmd += ["-o", opt + "=" + val]

	process = subprocess.Popen(cmd + ["pkgnames"], stdout=subprocess.PIPE, stderr=main.null_dev)
	(stdout, stderr) = process.communicate()
	packages = []
	for name in stdout.split():
		excluded = False
		for rule in package_exclude_rules:
			if re.match(rule, name):
				excluded = True
				break
		if not excluded:
			packages.append(name)
	process.wait()
	return packages

def get_package_info(pkgname):
	package_source = main.get_config('package_source')
	package_arch = main.get_config('package_arch')
	package_options = main.get_config('package_options')

	cmd = ["apt-cache"]

	if package_source:
		cmd += apt_options_for_source(package_source)
	if package_arch:
		cmd += ["-o", "APT::Architectures=" + package_arch]
	if package_options:
		for (opt, val) in package_options.items():
			cmd += ["-o", opt + "=" + val]

	has_source = False
	arch = 'all'
	process = subprocess.Popen(cmd + ["showpkg", pkgname], stdout=subprocess.PIPE, stderr=main.null_dev)
	for line in process.stdout:
		m = re.match('\s*Architecture:\s*(\S+)', line)
		if m:
			arch = m.group(1)
	if process.wait() != 0:
		return False

	extensions = [".c", ".cpp", ".c++", ".cxx", ".cc", ".cp"]
	dir = None
	process = None
	try:
		dir = download_package_source(pkgname)
		for (root, subdirs, files) in os.walk(dir):
			for f in files:
				args = None
				if f.endswith(".tar"):
					args = "-tf"
				elif f.endswith(".tar.gz") or f.endswith(".tgz"):
					args = "-tzf"
				elif f.endswith(".tar.bz2"):
					args = "-tjf"
				elif f.endswith(".tar.xz"):
					args = "-tJf"
				if args is None:
					continue
				process = subprocess.Popen(["tar", args, root + "/" + f], stdout=subprocess.PIPE, stderr=main.null_dev)
				for line in process.stdout:
					line = line.strip()
					for ext in extensions:
						if line.endswith(ext):
							has_source = True
							raise Exception(pkgname + " contains source")
	except Exception as e:
		print str(e)
		pass

	if process:
		process.kill()
	if dir:
		remove_dir(dir)

	return {'arch': arch, 'opensource': has_source };

def get_package_dependency(pkgname):
	package_source = main.get_config('package_source')
	package_arch = main.get_config('package_arch')
	package_options = main.get_config('package_options')

	cmd = ["apt-cache"]

	if package_source:
		cmd += apt_options_for_source(package_source)
	if package_arch:
		cmd += ["-o", "APT::Architectures=" + package_arch]
	if package_options:
		for (opt, val) in package_options.items():
			cmd += ["-o", opt + "=" + val]

	process = subprocess.Popen(cmd + ["depends", pkgname], stdout=subprocess.PIPE, stderr=main.null_dev)
	stdout = process.communicate()[0]
	deps = []
	for line in stdout.split('\n'):
		m = re.match('\s*\|?Depends:\s+(\S+)', line)
		if m:
			if m.group(1) not in deps:
				deps.append(m.group(1))

	return deps

def apt_options_for_source(source):
	return [
		"-o", "Dir::Etc::SourceList=" + os.path.join(main.root_dir, source),
		"-o", "Dir::Etc::SourceParts=-",
		"-o", "Dir::Cache=" + os.path.join(main.root_dir, 'apt/cache'),
		"-o", "Dir::State::Lists=" + os.path.join(main.root_dir, 'apt/lists'),
		"-o", "Dir::State::Status=" + os.path.join(main.root_dir, 'apt/status'),
	]

def update_apt(source=None, force=False):
	cmd = ["apt-get", "update"]

	if source:
		for dir in ['apt', 'apt/lists', 'apt/cache']:
			if not os.path.exists(dir):
				os.mkdir(dir)
				force = True
		if not os.path.exists('apt/status'):
			open('apt/status', 'w').close()
		cmd += apt_options_for_source(source)

	if not force:
		return

	print "updating APT..."
	process = subprocess.Popen(cmd, stdout = subprocess.PIPE,
			stderr = subprocess.PIPE)
	(stdout, stderr) = process.communicate()
	if process.returncode != 0:
		print "Cannot update package"

def UpdateApt(jmgr, os_target, sql, args):
	update_apt(main.get_config('package_source'), True)

tasks['UpdateApt'] = Task(
	name = "Update APT repository",
	func = UpdateApt)

def download_from_apt(name, source=None, arch=None, options=None):
	cmd = ["apt-get", "download"]

	if source:
		cmd += apt_options_for_source(source)
	if arch:
		cmd += ["-o", "APT::Architectures=" + arch]
	if options:
		for (opt, val) in options.items():
			cmd += ["-o", opt + "=" + val]

	process = subprocess.Popen(cmd + [name], stdout=subprocess.PIPE, stderr=main.null_dev)
	stdout = process.communicate()[0]
	if process.returncode != 0:
		raise Exception("Cannot download \'" + name + "\'")

	for filename in os.listdir('.'):
		if filename.endswith('.deb'):
			return filename

	raise Exception("\'" + name + "\' is not properly downloaded")

def download_source_from_apt(name, source=None, arch=None, options=None, unpack=False):
	cmd = ["apt-get", "source"]

	if not unpack:
		cmd += ["--download-only"]

	if source:
		cmd += apt_options_for_source(source)
	if arch:
		cmd += ["-o", "APT::Architectures=" + arch]
	if options:
		for (opt, val) in options.items():
			cmd += ["-o", opt + "=" + val]

	process = subprocess.Popen(cmd + [name], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	(stdout, stderr) = process.communicate()
	if process.returncode != 0:
		print stderr
		raise Exception("Cannot download \'" + name + "\'")

def unpack_package(name):
	package_source = main.get_config('package_source')
	package_arch = main.get_config('package_arch')
	package_options = main.get_config('package_options')

	dir = tempfile.mkdtemp('', '', main.get_temp_dir())
	os.chdir(dir)

	try:
		filename = download_from_apt(name, package_source,
				package_arch, package_options)
		result = re.match('([^_]+)_([^_]+)_([^.]+).deb', filename)
		if not result:
			raise Exception("\'" + name + "\' is not properly downloaded")
		name = result.group(1)
		version = result.group(2)
		arch = result.group(3)
		result = subprocess.call(["dpkg", "-x", filename, "."], stdout=main.null_dev, stderr=main.null_dev)
		if result != 0:
			raise Exception("Cannot unpack \'" + name + "\'")
	except:
		os.chdir(main.root_dir)
		remove_dir(dir)
		raise

	os.chdir(main.root_dir)
	return (dir, name, version)

def download_package_source(name, unpack=False):
	package_source = main.get_config('package_source')
	package_arch = main.get_config('package_arch')
	package_options = main.get_config('package_options')

	dir = tempfile.mkdtemp('', '', main.get_temp_dir())
	os.chdir(dir)

	try:
		download_source_from_apt(name, package_source,
			package_arch, package_options, unpack)
	except:
		os.chdir(main.root_dir)
		remove_dir(dir)
		raise

	os.mkdir(dir + '/refs')
	os.chdir(main.root_dir)
	return dir

def check_elf(path):
	process = subprocess.Popen(["readelf", "--file-header", "-W", path], stdout=subprocess.PIPE, stderr=main.null_dev)

	for line in process.stdout:
		results = re.match(r"([^\:]+)\: +(.+)", line.strip())
		if results:
			key = results.group(1)
			val = results.group(2)
			if key == 'Class':
				if val != 'ELF64':
					return False
				else:
					break

	if process.wait() != 0:
		return False

	process = subprocess.Popen(["readelf", "--section-headers", "-W", path], stdout=subprocess.PIPE, stderr=main.null_dev)

	has_text = False
	for line in process.stdout:
		parts = line[6:].strip().split()

		# a valid elf needs to have a .text section (or it could be debug object)
		if parts and parts[0] == '.text':
			has_text = True

	if process.wait() != 0:
		return False

	return has_text

def which(file):
	for prefix in os.environ["PATH"].split(":"):
		path = os.path.join(prefix, file)
		if os.path.exists(path):
			return path
	return None

def check_script(path):
	binary = open(path, 'rb')
	interpreter = ''
	try:
		ch1 = struct.unpack('s', binary.read(1))[0]
		ch2 = struct.unpack('s', binary.read(1))[0]

		if ch1 != '#' or ch2 != '!':
			binary.close()
			return None

		while True:
			ch = struct.unpack('s', binary.read(1))[0]
			if ch == '\r' or ch == '\n':
				break
			if ch not in string.printable:
				binary.close()
				return None
			interpreter += ch

		parts = interpreter.strip().split()
		if parts[0] == '/usr/bin/env':
			interpreter = which(parts[1])
		else:
			interpreter = parts[0]
	except:
		interpreter = None

	binary.close()
	return interpreter

def get_binaries(dir, find_script=False):
	binaries = []
	for (root, subdirs, files) in os.walk(dir):
		if not os.access(root, os.X_OK):
			try:
				os.chmod(root, 0755)
			except:
				continue

		rel_root = root[len(dir) + 1:]
		for f in files:
			path = root + '/' + f
			rel_path = '/' + rel_root + '/' + f
			s = os.lstat(path)
			if re.match('[0-9A-Za-z\_\-\+\.]+\.so[0-9\.]*', f):
				if stat.S_ISLNK(s.st_mode):
					binaries.append((rel_path, 'lnk', None))
					continue
				if check_elf(path):
					binaries.append((rel_path, 'lib', None))
				continue
			if stat.S_ISLNK(s.st_mode):
				continue
			if s.st_mode & (stat.S_IXUSR|stat.S_IXGRP|stat.S_IXOTH):
				if check_elf(path):
					binaries.append((rel_path, 'exe', None))
					continue
				if find_script:
					interpreter = check_script(path)
					if interpreter:
						binaries.append((rel_path, 'scr', interpreter))
				continue
			if find_script:
				ext = os.path.splitext(rel_path)
				if ext in ['.py', '.sh', 'pl', '.PL']:
					interpreter = check_script(path)
					if interpreter:
						binaries.append((rel_path, 'scr', interpreter))

	return binaries
