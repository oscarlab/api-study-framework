#!/usr/bin/python

import os
import sys
import re
import logging
import importlib

config = None
def get_config(key, default=None):
	global config
	if config is None:
		config_module = importlib.import_module('config')
		config = config_module.config

	if key in config:
		return config[key]
	return default

temp_dir = None
def get_temp_dir():
	global temp_dir
	if not temp_dir:
		temp_dir = get_config('temp_dir', '/tmp/syspop-' + str(os.getuid()))
		try:
			os.mkdir(temp_dir)
			logging.info("Create temp dir: " + temp_dir)
		except OSError:
			pass
	return temp_dir

root_dir = os.getcwd()
null_dev = open(os.devnull, 'w')
