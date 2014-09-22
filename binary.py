#!/usr/bin/python

from sql import Table

import os
import sys
import re

binary_id_table = Table('binary_id', [
			('id', 'INT', 'NOT NULL'),
			('binary_name', 'VARCHAR', 'UNIQUE'),
			('callgraph_generated', 'BOOLEAN', ''),
			('dep_generated', 'BOOLEAN', ''),
			('footprint_generated', 'BOOLEAN', '')],
			['id'])

def get_binary_id(sql, binary_name):
	sql.connect_table(binary_id_table)

	retry = True
	while retry:
		results = sql.search_record(binary_id_table, 'binary_name=\'' + binary_name + '\'', ['id'])
		if results:
			id = results[0][0]
			break

		results = sql.search_record(binary_id_table, None, ['MAX(id)'])
		if results[0][0] is None:
			id = 1
		else:
			id = int(results[0][0]) + 1

		values = dict()
		values['id'] = id
		values['binary_name'] = binary_name
		values['callgraph_generated'] = False
		values['dep_generated'] = False
		values['footprint_generated'] = False
		retry = False
		try:
			sql.append_record(binary_id_table, values)
			sql.commit()
		except:
			retry = True
			pass

	return id

def update_binary_callgraph(sql, bin_id):
	values = dict()
	values['callgraph_generated'] = False
	sql.update_record(binary_id_table, values, 'id=\'' + str(bin_id) + '\'')

def update_binary_dep(sql, bin_id):
	values = dict()
	values['dep_generated'] = False
	sql.update_record(binary_id_table, values, 'id=\'' + str(bin_id) + '\'')
