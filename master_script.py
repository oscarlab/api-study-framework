#!/usr/bin/python
import os
import fnmatch
import sys
import subprocess
import re
import shutil
from datetime import datetime
from multiprocessing import Lock, Process, Queue,current_process
import multiprocessing
rootPath = '/filer/home/nafees4all/Documents/syscall_popularity/projects1' 
pattern = '*.deb'
sym = 'Package:'
def worker(work_queue):

	while not work_queue.empty():
		print "Process ID:",multiprocessing.current_process()
		count = 0
		fullpath = work_queue.get()
		process = subprocess.Popen(["dpkg", "--info",fullpath],stdout=subprocess.PIPE)
		for line in process.stdout:
			match = re.search(r"Package:(.*)",line)	       
			if match:
				pckg_name =  match.group(1).strip()
				print pckg_name
				continue
			match1 = re.search(r"Version:(.*)",line)
			if match1:
				version_nm = match1.group(1).strip()
				break
		match = re.search(r'([^/]*.deb)',fullpath)
		if match:
			root = fullpath.replace(match.group(0),'')
		dirname = "temp_" + pckg_name + "_" + version_nm
		path=os.path.join(root,dirname)	
		os.mkdir(path)		
		process = subprocess.call(["dpkg", "-x",fullpath,path])
		process1 = subprocess.Popen("./shellscript.sh %s" %(str(path)),shell=True,stdout=subprocess.PIPE,executable = '/bin/bash')	
		while True:
			line = process1.stdout.readline()	
			if line != '' :
				process2 = subprocess.call(["./extract_symbols.py", line.strip()])
				process = subprocess.call(["./getcallgraph.py", line.strip()])
				count += 1
			else:
				break
		if count == 0:
			print 'No ELF binaries present for ',pckg_name
		else:
			print 'Number of ELF binaries for %s are %d '%(pckg_name,count)
		shutil.rmtree(path)

def main():
	workers = 10
	work_queue = Queue()
	processes = []
	for root, dirs, files in os.walk(rootPath):
		for filename in fnmatch.filter(files, pattern):
			fullpath = root+"/"+filename	
			work_queue.put(fullpath)
	for w in range(workers):
		p = Process(target=worker, args=(work_queue,))
		p.start()
		processes.append(p)

	for p in processes:
		p.join()
			
if __name__ == "__main__":
	startTime = datetime.now()
	print startTime
	main()	
        print "Time taken:"
        print(datetime.now()-startTime)

