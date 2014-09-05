#!/usr/bin/python

import urllib
import urllib2
import re
import sqlite3

def getdata():
	con = getConnection()
        curr = con.cursor()
	data = urllib2.urlopen("http://popcon.debian.org/by_no-files");

	for line in data:
		#Ignore comments
		if not line.startswith('#'):
			#End of the file/webpage confined for this webpage
			if line.startswith('-'):
				break
			else:
        			result = line.strip().split()
        			curr.execute('insert into DEBIAN_POPULARITY_RESULTS values (?,?,?,?,?,?,?)', (result[0],result[1],result[2],result[3],result[4],result[5],result[6]))
	con.commit()
	con.close()

def getConnection():
        return sqlite3.connect('debian_popularity.db')

if __name__ == '__main__':
    getdata()
