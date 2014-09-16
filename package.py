#!/usr/bin/python

from task import Task
from package_popularity import package_popularity_table
from sql import Table

import os
import sys
import re
import subprocess
import shutil
import stat
import tempfile

def get_packages():
	process = subprocess.Popen(["apt-cache", "pkgnames"],
			stdout=subprocess.PIPE)
	(stdout, stderr) = process.communicate()
	return stdout.split()

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
	process = subprocess.Popen(["apt-cache", "showpkg", args[0]],
			stdout=subprocess.PIPE)
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

def unpack_package(name):
	cwd = os.getcwd()
	dir = tempfile.mkdtemp()
	os.chdir(dir)
	try:
		process = subprocess.Popen(["apt-get", "download", name],
				stdout = subprocess.PIPE)
		(stdout, stderr) = process.communicate()
		if process.returncode != 0:
			raise Exception("Cannot download \'" + name + "\'")
		downloaded = list(os.walk('.'))
		if len(downloaded) != 1:
			raise Exception("\'" + name + "\' is not properly downloaded")
		(root, subdirs, files) = downloaded[0]
		if len(files) != 1:
			raise Exception("\'" + name + "\' is not properly downloaded")
		filename = files[0]
		result = re.match('([^_]+)_([^_]+)_([^.]+).deb', filename)
		if not result:
			raise Exception("\'" + name + "\' is not properly downloaded")
		name = result.group(1)
		version = result.group(2)
		arch = result.group(3)
		with open(os.devnull, 'w') as devnull:
			result = subprocess.call(["dpkg", "-x", filename, "."],
					stdout=devnull)
		if result != 0:
			raise Exception("Cannot unpack \'" + name + "\'")
	except:
		os.chdir(cwd)
		shutil.rmtree(dir)
		raise
	os.mkdir('refs')
	os.chdir(cwd)
	return (dir, name, version)

def reference_dir(dir):
	(file, path) = tempfile.mkstemp(dir=dir + '/refs')
	ref = path[len(dir) + 6:]
	return ref

def dereference_dir(dir, ref):
	os.remove(dir + '/refs/' + ref)
	return not os.walk(dir + '/refs')

def PackageUnpack_run(jmgr, sql, args):
	(dir, pkgname, version) = unpack_package(args[0])
	if not dir:
		return
	print "Unpacked to", dir

def PackageUnpack_job_name(args):
	return "Package Unpack: " + args[0]

PackageUnpack = Task(
	name="Package Unpack",
	func=PackageUnpack_run,
	arg_defs=["Package Name"],
	job_name=PackageUnpack_job_name)

def check_elf(path):
	with open(os.devnull, 'w') as devnull:
		return subprocess.call(["readelf", "-h", path], stdout=devnull) == 0

def walk_package(dir):
	binaries = []
	for (root, subdirs, files) in os.walk(dir):
		rel_root = root[len(dir) + 1:]
		for f in files:
			path = root + '/' + f
			rel_path = '/' + rel_root + '/' + f
			s = os.lstat(path)
			if re.match('[0-9A-Za-z\_\-\.]+\.so[0-9\.]*', f):
				if stat.S_ISLNK(s.st_mode):
					binaries.append((rel_path, 'lnk'))
					continue
				if check_elf(path):
					binaries.append((rel_path, 'lib'))
				continue
			if stat.S_ISLNK(s.st_mode):
				continue
			if s.st_mode & (stat.S_IXUSR|stat.S_IXGRP|stat.S_IXOTH):
				if check_elf(path):
					binaries.append((rel_path, 'exe'))
				continue
	return binaries

binary_list_table = Table('binary_list', [
			('package_name', 'TEXT', 'NOT NULL'),
			('binary', 'TEXT', 'NOT NULL'),
			('real_package', 'TEXT', ''),
			('version', 'TEXT', 'NOT NULL'),
			('type', 'TEXT', 'NOT NULL')],
			['package_name', 'binary'])

binary_link_table = Table('binary_link', [
			('package_name', 'TEXT', 'NOT NULL'),
			('link', 'TEXT', 'NOT NULL'),
			('target', 'TEXT', 'NOT NULL'),
			('real_package', 'TEXT', ''),
			('version', 'TEXT', 'NOT NULL')],
			['link', 'target'])

def BinaryList_run(jmgr, sql, args):
	sql.connect_table(binary_list_table)
	sql.connect_table(binary_link_table)
	(dir, pkgname, version) = unpack_package(args[0])
	if not dir:
		return
	binaries = walk_package(dir)
	if binaries:
		for (bin, type) in binaries:
			if type == 'lnk':
				link = os.readlink(dir + bin)
				values = dict()
				values['package_name'] = args[0]
				values['link'] = bin
				values['target'] = os.path.join(os.path.dirname(bin), link)
				values['real_package'] = pkgname
				values['version'] = version

				sql.append_record(binary_link_table, values)
			else:
				values = dict()
				values['package_name'] = args[0]
				values['binary'] = bin
				values['type'] = type
				values['real_package'] = pkgname
				values['version'] = version

				sql.append_record(binary_list_table, values)
	sql.commit()
	shutil.rmtree(dir)

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
