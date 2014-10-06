#!/usr/bin/python

from task import Task
from package_popularity import package_popularity_table
from sql import Table
from binary import get_binary_id, get_package_id
import main
import symbol
import callgraph

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

def get_packages_by_names(names):
	packages = get_packages()
	return [name for name in names if name in packages]

def get_packages_by_prefixes(prefixes):
	packages = get_packages()
	result = []
	for package in packages:
		for p in prefixes:
			if package.startswith(p):
				result.append(package)
				break
	return result

def get_packages_by_ranks(sql, min, max):
	sql.connect_table(package_popularity_table)
	packages = get_packages()
	packages_by_ranks = sql.search_record(
				package_popularity_table,
				'rank >= ' + str(min) + ' AND rank <= ' + str(max),
				['package_name'])
	result = []
	for (name,) in packages_by_ranks:
		if name in packages:
			result.append(name)
	return result

def PackageInfo_run(jmgr, sql, args):
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

	process = subprocess.Popen(cmd + ["showpkg", args[0]], stdout=subprocess.PIPE, stderr=main.null_dev)
	(stdout, stderr) = process.communicate()
	print stdout

def PackageInfo_job_name(args):
	return "Package Info: " + args[0]

PackageInfo = Task(
	name="Package Info",
	func=PackageInfo_run,
	arg_defs=["Package Name"],
	job_name=PackageInfo_job_name)

def PackageListByNames_run(jmgr, sql, args):
	packages = get_packages_by_names(args[0].split())
	if packages:
		for i in packages:
			PackageInfo.create_job(jmgr, [i])

def PackageListByNames_job_name(args):
	return "Package List By Names: " + args[0]

PackageListByNames = Task(
	name="Package List By Names",
	func=PackageListByNames_run,
	arg_defs=["Package Names"],
	job_name=PackageListByNames_job_name)

def PackageListByPrefixes_run(jmgr, sql, args):
	packages = get_packages_by_prefixes(args[0].split())
	if packages:
		for i in packages:
			PackageInfo.create_job(jmgr, [i])

def PackageListByPrefixes_job_name(args):
	return "Package List By Prefixes: " + args[0]

PackageListByPrefixes = Task(
	name="Package List By Prefixes",
	func=PackageListByPrefixes_run,
	arg_defs=["Package Prefixes"],
	job_name=PackageListByPrefixes_job_name)

def PackageListByRanks_run(jmgr, sql, args):
	packages = get_packages_by_ranks(sql, int(args[0]), int(args[1]))
	if packages:
		for i in packages:
			PackageInfo.create_job(jmgr, [i])

def PackageListByRanks_job_name(args):
	return "Package List By Ranks: " + args[0] + " to " + args[1]

PackageListByRanks = Task(
	name="Package List By Ranks",
	func=PackageListByRanks_run,
	arg_defs=["Minimum Rank", "Maximum Rank"],
	job_name=PackageListByRanks_job_name)

def apt_options_for_source(source):
	return [
		"-o", "Dir::Etc::SourceList=" + os.path.join(main.root_dir, source),
		"-o", "Dir::Etc::SourceParts=-",
		"-o", "Dir::Cache=" + os.path.join(main.root_dir, 'apt/cache'),
		"-o", "Dir::State::Lists=" + os.path.join(main.root_dir, 'apt/lists'),
		"-o", "Dir::State::Status=" + os.path.join(main.root_dir, 'apt/status'),
	]

def update_apt(source=None):
	cmd = ["apt-get", "update"]

	if source:
		for dir in ['apt', 'apt/lists', 'apt/cache']:
			if not os.path.exists(dir):
				os.mkdir(dir)
		if not os.path.exists('apt/status'):
			open('apt/status', 'w').close()
		cmd += apt_options_for_source(source)

	print "updating APT..."
	process = subprocess.Popen(cmd, stdout = subprocess.PIPE,
			stderr = subprocess.PIPE)
	(stdout, stderr) = process.communicate()
	if process.returncode != 0:
		print "Cannot update package"

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
	(stdout, stderr) = process.communicate()
	if process.returncode != 0:
		raise Exception("Cannot download \'" + name + "\'")

	for filename in os.listdir('.'):
		if filename.endswith('.deb'):
			return filename

	raise Exception("\'" + name + "\' is not properly downloaded")

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

	os.mkdir(dir + '/refs')
	os.chdir(main.root_dir)
	return (dir, name, version)

def reference_dir(dir):
	(file, path) = tempfile.mkstemp(dir=dir + '/refs')
	os.close(file)
	ref = path[len(dir) + 6:]
	return ref

def dereference_dir(dir, ref):
	os.remove(dir + '/refs/' + ref)
	return not os.listdir(dir + '/refs')

def reference_exists(dir, ref):
	return os.path.exists(dir + '/refs/' + ref)

def remove_dir(dir):
	try:
		shutil.rmtree(dir)
	except:
		pass

def PackageUnpack_run(jmgr, sql, args):
	(dir, pkgname, version) = unpack_package(args[0])
	if not dir:
		return
	print "Unpacked", pkgname, "(" + version + ")", "to", dir

def PackageUnpack_job_name(args):
	return "Package Unpack: " + args[0]

PackageUnpack = Task(
	name="Package Unpack",
	func=PackageUnpack_run,
	arg_defs=["Package Name"],
	job_name=PackageUnpack_job_name)

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

def walk_package(dir, find_script=False):
	binaries = []
	for (root, subdirs, files) in os.walk(dir):
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

binary_list_table = Table('binary_list', [
			('pkg_id', 'INT', 'NOT NULL'),
			('bin_id', 'INT', 'NOT NULL'),
			('type', 'CHAR(3)', 'NOT NULL'),
			('callgraph', 'BOOLEAN', ''),
			('linking', 'BOOLEAN', '')],
			['pkg_id', 'bin_id'],
			[['pkg_id', 'bin_id', 'type']])

binary_link_table = Table('binary_link', [
			('pkg_id', 'INT', 'NOT NULL'),
			('lnk_id', 'INT', 'NOT NULL'),
			('target', 'INT', 'NOT NULL'),
			('linking', 'BOOLEAN', '')],
			['pkg_id', 'lnk_id'])

def run_binary_list(sql, pkgname, dir, binaries):
	pkg_id = get_package_id(sql, pkgname)
	insert_values = []
	for (bin, type, interpreter) in binaries:
		bin_id = get_binary_id(sql, bin)
		values = dict()
		values['type'] = type

		if type == 'lnk':
			link = os.readlink(dir + bin)
			target = os.path.join(os.path.dirname(bin), link)
			target_id = get_binary_id(sql, target)
			values['pkg_id'] = pkg_id
			values['lnk_id'] = bin_id
			values['target'] = target_id
			values['linking'] = False
		else:
			values['pkg_id'] = pkg_id
			values['bin_id'] = bin_id
			if type == 'scr':
				interp_id = get_binary_id(sql, interpreter)
				values['interp'] = interp_id
				values['callgraph'] = True
			else:
				values['callgraph'] = False
			values['linking'] = False

		insert_values.append(values)

	condition = 'pkg_id=\'' + str(pkg_id) + '\''
	sql.delete_record(binary_list_table, condition)
	sql.delete_record(binary_link_table, condition)
	sql.delete_record(symbol.binary_interp_table, condition)

	for values in insert_values:
		if values['type'] == 'lnk':
			sql.append_record(binary_link_table, values)
		else:
			sql.append_record(binary_list_table, values)
			if type == 'scr':
				sql.append_record(symbol.binary_interp_table, values)

	sql.commit()

def BinaryList_run(jmgr, sql, args):
	sql.connect_table(binary_list_table)
	sql.connect_table(binary_link_table)
	sql.connect_table(symbol.binary_interp_table)

	(dir, pkgname, _) = unpack_package(args[0])
	if not dir:
		return

	binaries = walk_package(dir, find_script=True)
	if not binaries:
		remove_dir(dir)
		return

	run_binary_list(sql, pkgname, dir, binaries)
	remove_dir(dir)

def BinaryList_job_name(args):
	return "Binary List: " + args[0]

BinaryList = Task(
	name="Binary List",
	func=BinaryList_run,
	arg_defs=["Package Name"],
	job_name=BinaryList_job_name)

def BinaryListByNames_run(jmgr, sql, args):
	packages = get_packages_by_names(args[0].split())
	if packages:
		for i in packages:
			BinaryList.create_job(jmgr, [i])

def BinaryListByNames_job_name(args):
	return "Binary List By Names: " + args[0]

BinaryListByNames = Task(
	name="Binary List By Names",
	func=BinaryListByNames_run,
	arg_defs=["Package Names"],
	job_name=BinaryListByNames_job_name)

def BinaryListByPrefixes_run(jmgr, sql, args):
	packages = get_packages_by_prefixes(args[0].split())
	if packages:
		for i in packages:
			BinaryList.create_job(jmgr, [i])

def BinaryListByPrefixes_job_name(args):
	return "Binary List By Prefixes: " + args[0]

BinaryListByPrefixes = Task(
	name="Binary List By Prefixes",
	func=BinaryListByPrefixes_run,
	arg_defs=["Package Prefixes"],
	job_name=BinaryListByPrefixes_job_name)

def BinaryListByRanks_run(jmgr, sql, args):
	packages = get_packages_by_ranks(sql, int(args[0]), int(args[1]))
	if packages:
		for i in packages:
			BinaryList.create_job(jmgr, [i])

def BinaryListByRanks_job_name(args):
	return "Binary List By Ranks: " + args[0] + " to " + args[1]

BinaryListByRanks = Task(
	name="Binary List By Ranks",
	func=BinaryListByRanks_run,
	arg_defs=["Minimum Rank", "Maximum Rank"],
	job_name=BinaryListByRanks_job_name)

def PackageAnalysis_run(jmgr, sql, args):
	sql.connect_table(binary_list_table)
	sql.connect_table(binary_link_table)
	sql.connect_table(symbol.binary_interp_table)

	(dir, pkgname, _) = unpack_package(args[0])
	if not dir:
		return

	binaries = walk_package(dir, find_script=True)
	if not binaries:
		remove_dir(dir)
		return

	run_binary_list(sql, pkgname, dir, binaries)

	for (bin, type, _) in binaries:
		if type == 'lnk' or type == 'scr':
			continue
		ref = reference_dir(dir)
		symbol.BinaryDependency.create_job(jmgr, [pkgname, bin, dir, ref])
		ref = reference_dir(dir)
		symbol.BinarySymbol.create_job(jmgr, [pkgname, bin, dir, ref])
		ref = reference_dir(dir)
		callgraph.BinaryCallgraph.create_job(jmgr, [pkgname, bin, dir, ref])

def PackageAnalysis_job_name(args):
	return "Full Package Analysis: " + args[0]

PackageAnalysis = Task(
	name="Full Package Analysis",
	func=PackageAnalysis_run,
	arg_defs=["Package Name"],
	job_name=PackageAnalysis_job_name)

def PackageAnalysisByNames_run(jmgr, sql, args):
	packages = get_packages_by_names(args[0].split())
	if packages:
		for i in packages:
			PackageAnalysis.create_job(jmgr, [i])

def PackageAnalysisByNames_job_name(args):
	return "Full Package Analysis By Names: " + args[0]

PackageAnalysisByNames = Task(
	name="Full Package Analysis By Names",
	func=PackageAnalysisByNames_run,
	arg_defs=["Package Names"],
	job_name=PackageAnalysisByNames_job_name)

def PackageAnalysisByPrefixes_run(jmgr, sql, args):
	packages = get_packages_by_prefixes(args[0].split())
	if packages:
		for i in packages:
			PackageAnalysis.create_job(jmgr, [i])

def PackageAnalysisByPrefixes_job_name(args):
	return "Full Package Analysis By Prefixes: " + args[0]

PackageAnalysisByPrefixes = Task(
	name="Full Package Analysis By Prefixes",
	func=PackageAnalysisByPrefixes_run,
	arg_defs=["Package Prefixes"],
	job_name=PackageAnalysisByPrefixes_job_name)

def PackageAnalysisByRanks_run(jmgr, sql, args):
	packages = get_packages_by_ranks(sql, int(args[0]), int(args[1]))
	if packages:
		for i in packages:
			PackageAnalysis.create_job(jmgr, [i])

def PackageAnalysisByRanks_job_name(args):
	return "Full Package Analysis By Ranks: " + args[0] + " to " + args[1]

PackageAnalysisByRanks = Task(
	name="Full Package Analysis By Ranks",
	func=PackageAnalysisByRanks_run,
	arg_defs=["Minimum Rank", "Maximum Rank"],
	job_name=PackageAnalysisByRanks_job_name)
