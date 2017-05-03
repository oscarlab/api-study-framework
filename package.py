#!/usr/bin/python

from task import tasks, subtasks, Task
from sql import tables, Table
from id import get_package_id, get_binary_id
from binary import append_binary_list

import os
import sys
import re
import shutil
import tempfile

tables['package_info'] = Table('package_info', [
		('pkg_id', 'INT', 'NOT NULL'),
		('arch', 'VARCHAR', 'NOT NULL'),
		('version', 'VARCHAR', 'NOT NULL'),
		('uri', 'VARCHAR', 'NOT NULL'),
		('hash', 'VARCHAR', 'NOT NULL'),
		('opensource', 'BOOLEAN', 'NOT NULL')],
		['pkg_id', 'arch'], [])

tables['package_dependency'] = Table('package_dependency', [
		('pkg_id', 'INT', 'NOT NULL'),
		('dependency', 'INT', 'NOT NULL')],
		['pkg_id', 'dependency'], [['dependency']])

tables['package_popularity'] = Table('package_popularity', [
		('package_name', 'VARCHAR', 'NOT NULL'),
		('rank', 'INT', 'NOT NULL'),
		('inst', 'BIGINT', 'NOT NULL')],
		['rank'], [['package_name']])

def get_packages_by_names(os_target, names):
	packages = os_target.get_packages()
	return [name for name in names if name in packages]

def get_packages_by_prefixes(os_target, prefixes):
	result = []
	for pkg in os_target.get_packages():
		for p in prefixes:
			if pkg.startswith(p):
				result.append(pkg)
				break
	return result

def get_packages_by_ranks(os_target, sql, min, max):
	sql.connect_table(tables['package_popularity'])
	packages = os_target.get_packages()
	packages_by_ranks = sql.search_record(
				tables['package_popularity'],
				'rank >= ' + Table.stringify(min) + ' AND rank <= ' + Table.stringify(max),
				['package_name'])
	result = []
	for (name,) in packages_by_ranks:
		if name in packages:
			result.append(name)
	return result

def unpack_package(os_target, pkgname):
	(dir, pkgname, version) = os_target.unpack_package(pkgname)
	os.mkdir(dir + '/refs')
	return (dir, pkgname, version)

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

def PackageInfo(jmgr, os_target, sql, args):
	sql.connect_table(tables['package_info'])
	sql.connect_table(tables['package_dependency'])

	pkgname = args[0]
	pkg_id = get_package_id(sql, pkgname)

	pkg_info = os_target.get_package_info(pkgname)
	pkg_deps = os_target.get_package_dependency(pkgname)

	# Clean up records
	sql.delete_record(tables['package_info'], 'pkg_id=\'' + Table.stringify(pkg_id) + '\'')
	sql.delete_record(tables['package_dependency'], 'pkg_id=\'' + Table.stringify(pkg_id) + '\'')

	pkg_info['pkg_id'] = pkg_id
	sql.append_record(tables['package_info'], pkg_info)

	for dep in pkg_deps:
		dep_id = get_package_id(sql, dep)
		values = dict()
		values['pkg_id'] = pkg_id
		values['dependency'] = dep_id
		sql.append_record(tables['package_dependency'], values)

	sql.commit()

subtasks['PackageInfo'] = Task(
	name = "Collect Package Info and Dependency",
	func = PackageInfo,
	arg_defs = ["Package Name"],
	job_name = lambda args: "Package Info and Dependency: " + args[0])

def PackageAnalysis(jmgr, os_target, sql, args):
	(dir, pkgname, _) = unpack_package(os_target, args[0])
	if not dir:
		return

	subtasks['PackageInfo'].run_job(jmgr, [pkgname])

	binaries = os_target.get_binaries(dir, find_script=True)
	if not binaries:
		remove_dir(dir)
		return

	append_binary_list(sql, pkgname, dir, binaries)

	#Hold an extra reference, so that we don't try to destroy the directory unless it really has no references.
	global_ref = reference_dir(dir)

	for (bin, type, _) in binaries:
		if type == 'lnk' or type == 'scr':
			continue

		ref = reference_dir(dir)
		subtasks['BinarySymbol'].run_job(jmgr, [pkgname, bin, dir, ref])

		ref = reference_dir(dir)
		subtasks['BinaryDependency'].run_job(jmgr, [pkgname, bin, dir, ref])

		ref = reference_dir(dir)
		subtasks['BinaryCall'].run_job(jmgr, [pkgname, bin, dir, ref])

		ref = reference_dir(dir)
		subtasks['BinaryInstr'].run_job(jmgr, [pkgname, bin, dir, ref])

	remove_dir(dir)

subtasks['PackageAnalysis'] = Task(
	name = "Package Analysis",
	func = PackageAnalysis,
	arg_defs = ["Package Name"],
	job_name = lambda args: "Package Analysis: " + args[0])


def pick_packages_from_args(os_target, sql, args):
	all_packages = []

	if args[0]:
		packages = get_packages_by_names(os_target, args[0].split())
		for pkg in packages:
			if pkg not in all_packages:
				all_packages.append(pkg)

	if args[1]:
		packages = get_packages_by_prefixes(os_target, args[1].split())
		for pkg in packages:
			if pkg not in all_packages:
				all_packages.append(pkg)

	if args[2] or args[3]:
		try:
			min_rank = int(args[2])
		except:
			min_rank = 0
		try:
			max_rank = int(args[3])
		except:
			max_rank = 999999

		packages = get_packages_by_ranks(os_target, sql, min_rank, max_rank)
		for pkg in packages:
			if pkg not in all_packages:
				all_packages.append(pkg)

	return all_packages

args_to_pick_packages = ['package names', 'package prefixes', 'min ranks', 'max ranks']

def ListForPackageAnalysis(jmgr, os_target, sql, args):
	for pkg in pick_packages_from_args(os_target, sql, args):
		subtasks['PackageAnalysis'].create_job(jmgr, [pkg])

tasks['ListForPackageAnalysis'] = Task(
	name = "Analyze Selected Package(s)",
	func = ListForPackageAnalysis,
	arg_defs = args_to_pick_packages,
	order = 10)


def EmitCorpus(jmgr, os_target, sql, args):
	(dir, pkgname, _) = unpack_package(os_target, args[0])
	if not dir:
		return

	corpusDir = '/filer/corpus/'+str(pkgname)
	if os.path.exists(corpusDir):
		shutil.rmtree(corpusDir)
	os.mkdir(corpusDir)

	binaries = os_target.get_binaries(dir, find_script=True)
	if not binaries:
		remove_dir(dir)
		return

	append_binary_list(sql, pkgname, dir, binaries)

	#Hold an extra reference, so that we don't try to destroy the directory unless it really has no references.
	global_ref = reference_dir(dir)

	for (bin, type, _) in binaries:
		if type == 'lnk' or type == 'scr':
			continue

		bin_id = get_binary_id(sql, bin)
		corpusFileName = corpusDir+"/"+str(bin_id)
		os_target.emit_corpus(dir + bin, corpusFileName)

	remove_dir(dir)

subtasks['EmitCorpus'] = Task(
	name = "Emit the word2vec corpus",
	func = EmitCorpus,
	arg_defs = ["Package Name"],
	job_name = lambda args: "Emit Corpus: " + args[0])

def ListForEmitCorpus(jmgr, os_target, sql, args):
	for pkg in pick_packages_from_args(os_target, sql, args):
		subtasks['EmitCorpus'].create_job(jmgr, [pkg])

tasks['ListForEmitCorpus'] = Task(
	name = "Collect Corpus",
	func = ListForEmitCorpus,
	arg_defs = args_to_pick_packages,
	order = 44)

def PackagePopularity(jmgr, os_target, sql, args):
	sql.connect_table(tables['package_popularity'])

	pop = os_target.get_package_popularity()

	sql.delete_record(tables['package_popularity'])
	for values in pop:
		sql.append_record(tables['package_popularity'], values)

	sql.commit()

tasks['PackagePopularity'] = Task(
		name = "Collect Package Popularity",
		func = PackagePopularity,
		order = 0)
