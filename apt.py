#!/usr/bin/python

from id import get_binary_id, get_package_id
from task import tasks, Task
import package
from utils import get_config, null_dev, root_dir, get_temp_dir

import os
import sys
import re
import logging
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
	package_source = get_config('package_source')
	package_arch = get_config('package_arch')
	package_options = get_config('package_options')

	cmd = ["apt-cache"]

	if package_source:
		cmd += apt_options_for_source(package_source)
	if package_arch:
		cmd += ["-o", "APT::Architectures=" + package_arch]
	if package_options:
		for (opt, val) in package_options.items():
			cmd += ["-o", opt + "=" + val]

	process = subprocess.Popen(cmd + ["pkgnames"], stdout=subprocess.PIPE, stderr=null_dev)
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
	package_source = get_config('package_source')
	package_arch = get_config('package_arch')
	package_options = get_config('package_options')

	cmd = []
	if package_source:
		cmd += apt_options_for_source(package_source)
	if package_arch:
		cmd += ["-o", "APT::Architectures=" + package_arch]
	if package_options:
		for (opt, val) in package_options.items():
			cmd += ["-o", opt + "=" + val]

	process = subprocess.Popen(["apt-get"] + cmd + ["download", "--print-uris", pkgname], stdout=subprocess.PIPE, stderr=null_dev)
	(stdout, _) = process.communicate()
	for line in stdout.split('\n'):
		m = re.match('\'([^\']+)\'\s+[^\s_]+_([^\s_]+)_([^\s_]+).deb\s+\d+\s+(\S+)', line)
		if m:
			uri = m.group(1)
			version = m.group(2)
			arch = m.group(3)
			hash = m.group(4)

	has_source = False
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
				process = subprocess.Popen(["tar", args, root + "/" + f], stdout=subprocess.PIPE, stderr=null_dev)
				for line in process.stdout:
					line = line.strip()
					for ext in extensions:
						if line.endswith(ext):
							has_source = True
	except Exception as e:
		logging.info(str(e))
		pass

	if process:
		process.kill()
	if dir:
		package.remove_dir(dir)

	return {'arch': arch, 'version': version, 'uri': uri, 'opensource': has_source, 'hash': hash}

def get_package_dependency(pkgname):
	package_source = get_config('package_source')
	package_arch = get_config('package_arch')
	package_options = get_config('package_options')

	cmd = ["apt-cache"]

	if package_source:
		cmd += apt_options_for_source(package_source)
	if package_arch:
		cmd += ["-o", "APT::Architectures=" + package_arch]
	if package_options:
		for (opt, val) in package_options.items():
			cmd += ["-o", opt + "=" + val]

	process = subprocess.Popen(cmd + ["depends", pkgname], stdout=subprocess.PIPE, stderr=null_dev)
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
		"-o", "Dir::Etc::SourceList=" + os.path.join(root_dir, source),
		"-o", "Dir::Etc::SourceParts=-",
		"-o", "Dir::Cache=" + os.path.join(root_dir, 'apt/cache'),
		"-o", "Dir::State::Lists=" + os.path.join(root_dir, 'apt/lists'),
		"-o", "Dir::State::Status=" + os.path.join(root_dir, 'apt/status'),
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

	logging.info("updating APT...")
	process = subprocess.Popen(cmd, stdout = subprocess.PIPE,
			stderr = subprocess.PIPE)
	(stdout, stderr) = process.communicate()
	if process.returncode != 0:
		logging.info("Cannot update package")

def UpdateApt(jmgr, os_target, sql, args):
	update_apt(get_config('package_source'), True)

tasks['UpdateApt'] = Task(
		name = "Update APT repository",
		func = UpdateApt,
		order = 99)

def download_from_apt(name, source=None, arch=None, options=None):
	cmd = ["apt-get", "download"]

	if source:
		cmd += apt_options_for_source(source)
	if arch:
		cmd += ["-o", "APT::Architectures=" + arch]
	if options:
		for (opt, val) in options.items():
			cmd += ["-o", opt + "=" + val]

	process = subprocess.Popen(cmd + [name], stdout=subprocess.PIPE, stderr=null_dev)
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
		logging.error(stderr)
		raise Exception("Cannot download \'" + name + "\'")

def unpack_package(name):
	package_source = get_config('package_source')
	package_arch = get_config('package_arch')
	package_options = get_config('package_options')

	dir = tempfile.mkdtemp('', '', get_temp_dir())
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
		result = subprocess.call(["dpkg", "-x", filename, "."], stdout=null_dev, stderr=null_dev)
		if result != 0:
			raise Exception("Cannot unpack \'" + name + "\'")
	except:
		os.chdir(root_dir)
		package.remove_dir(dir)
		raise

	os.chdir(root_dir)
	return (dir, name, version)

def download_package_source(name, unpack=False):
	package_source = get_config('package_source')
	package_arch = get_config('package_arch')
	package_options = get_config('package_options')

	dir = tempfile.mkdtemp('', '', get_temp_dir())
	os.chdir(dir)

	try:
		download_source_from_apt(name, package_source,
			package_arch, package_options, unpack)
	except:
		os.chdir(root_dir)
		package.remove_dir(dir)
		raise

	os.mkdir(dir + '/refs')
	os.chdir(root_dir)
	return dir

def check_elf(path):
	process = subprocess.Popen(["readelf", "--file-header", "-W", path], stdout=subprocess.PIPE, stderr=null_dev)

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

	process = subprocess.Popen(["readelf", "--section-headers", "-W", path], stdout=subprocess.PIPE, stderr=null_dev)

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
