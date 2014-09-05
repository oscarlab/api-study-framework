#!/usr/bin/python
import sqlite3

conn = sqlite3.connect('debian_popularity.db')

conn.execute('''CREATE TABLE DEBIAN_POPULARITY_RESULTS
       (RANK  TEXT,
        PACKAGE_NAME  TEXT,
        INST   INT,
        VOTE   INT,
	OLD INT,
        RECENT INT,
	NO_FILES INT);''')

print "PACKAGE created successfully";

conn.close()


    


