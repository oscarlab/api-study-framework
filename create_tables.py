#!/usr/bin/python
import sqlite3

conn = sqlite3.connect('syscall_popularity.db')
print "Opened database successfully";

conn.execute('''CREATE TABLE PACKAGE_METADATA
       (PACKAGE_NAME  TEXT   NOT NULL,
       VERSION        TEXT    NOT NULL,
       ARCHITECTURE   TEXT    ,
       SIZE        INT,
       PRIORITY         TEXT,
       PRIMARY KEY (PACKAGE_NAME, VERSION));''')

print "PACKAGE_METADATA created successfully";

conn.execute('''CREATE TABLE PACKAGE_BINARY_INFO
       (PACKAGE_NAME  TEXT   NOT NULL,
       PACKAGE_VERSION        TEXT    NOT NULL,
       BINARY_NAME   TEXT);''')    
      
print "PACKAGE_BINARY_INFO created successfully";
    
conn.execute('''CREATE TABLE BINARY_DEPENDENCIES
       (BINARY_NAME  TEXT   NOT NULL,
       DEPENDENCY_NAME   TEXT);''')

print "BINARY_DEPENDENCIES TABLE INFO created successfully";


conn.execute('''CREATE TABLE SYMBOLS_INFO
       (BINARY_NAME  TEXT   NOT NULL,
       SYMBOL       TEXT    ,
       SCOPE   TEXT);''')

print "SYMBOL INFO TABLE INFO created successfully";

conn.execute('''CREATE TABLE SYSCALL_INFO
       (BINARY_NAME  TEXT   NOT NULL,
       FUNC_NAME       TEXT    ,
       SYSCALL_NO  TEXT,	
       SYSCALL_NAME   TEXT);''')


print "SYSCALL INFO TABLE INFO created successfully";

conn.execute('''CREATE TABLE CALLER_FUNC_INFO
       (BINARY_NAME  TEXT   NOT NULL,
       CALLER_FUNC       TEXT    ,
       CALLEE_FUNC   TEXT);''')


print "CALLER_FUNC_INFO TABLE INFO created successfully";


conn.close()
