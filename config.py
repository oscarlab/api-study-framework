#!/usr/bin/python

config = {
	'os_target':		'linux.Ubuntu64',
	'package_source':	'sources.list',
	'package_arch':		'amd64',
	'package_options':	{
		'APT::Archives::MaxAge': '30',
		'APT::Archives::MinAge': '2',
		'APT::Archives::MaxSize': '500',
	},

	'sql_engine':		'postgresql.PostgreSQL',
	'postgresql_host':	'localhost',
	'postgresql_user':	'syspop',
	'postgresql_pass':	'syspop',
	'postgresql_db':	'api_compat_study',
}
