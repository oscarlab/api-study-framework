#!/usr/bin/python
import subprocess
import sys
import re

class Symbol:

   symbols_count = 0
   def __init__(self, name, scope, version,libpath):
      self.name = name
      self.scope = scope
      self.version = version
      self.libpath = libpath
      Symbol.symbols_count  += 1
   
   def displayCount(self):
     print "Total Symobls %d" % Symbol.symbols_count

   def displaySymbol(self):
	print "Name:%50s\tScope:%2s\tVersion:%10s\tLibPath:%40s" %(self.name,self.scope,self.version,self.libpath)

def getSymbols( binaryname ):
	process = subprocess.Popen(["readelf", "--dyn-syms","-W", binaryname],
                             stdout=subprocess.PIPE
                           	)
	count = 0
	symbol_list = []
	for line in process.stdout:
		parts = line.split()
		if len(parts) > 7:
			if parts[3] == 'FUNC' and (parts[4] == 'GLOBAL' or parts[4] == 'WEAK'):
					match = re.search('@', parts[7])
					if match:
						#Replace multiple occurences of @ with single @
						parts[7] = re.sub(r'@+','@',parts[7])
			   			nam , ver = parts[7].split("@")
					else:
						nam = parts[7]
						ver = 0
					if parts[6] == 'UND':

						sym = Symbol(nam,'U',ver,binaryname)
						symbol_list.append(sym)
						#sym.displaySymbol()
						#sym.displayCount()	
						count += 1
					elif parts[6].isdigit():

						sym = Symbol(nam,'D',ver,binaryname)
                                        	symbol_list.append(sym)         
                                        	#sym.displaySymbol()
						#sym.displayCount()
						count += 1

	#for symbols in symbol_list:
		#symbols.displaySymbol()
	print "Total number of functions in " + binaryname + " are " , count
	return symbol_list;


def getDependencies( binaryname ):
	
	filter1 = "s/^.* => //"
	filter2 = "s/ (0x.*//"
	count = 0;
	process1 = subprocess.Popen(["ldd",binaryname],
                             stdout=subprocess.PIPE
                           )
	process2 = subprocess.Popen(["sed", filter1],
                        stdin=process1.stdout,
                        stdout=subprocess.PIPE,stderr=subprocess.PIPE)

	process3 = subprocess.Popen(["sed", filter2],
                        stdin=process2.stdout,
                        stdout=subprocess.PIPE,stderr=subprocess.PIPE)

	lib_symbol_list = []
	for libpath in process3.stdout:
		if (libpath != "" and len(libpath) > 1): #check this later
			temp_list = []
			temp_list = getSymbols(libpath.strip())
			lib_symbol_list += temp_list
			#print "Length of ",libpath," is ",len(temp_list)
			count += 1
	for symbols in lib_symbol_list:
              symbols.displaySymbol()

	print "Length of Main list  is: ",len(lib_symbol_list)
	print "No of dependencies:",count
	return;
print "Before function call"
if __name__ == "__main__":
	#getSymbols(sys.argv[1]);
	getDependencies(sys.argv[1]);

