#!/usr/bin/python
import subprocess
import sys
import re

class Symbol:

   symbols_count = 0
   def __init__(self, name, scope, version):
      self.name = name
      self.scope = scope
      self.version = version
      Symbol.symbols_count  += 1
   
   def displayCount(self):
     print "Total Symobls %d" % Symbol.symbols_count

   def displaySymbol(self):
      print "Name : ", self.name,  "\t, Scope: ", self.scope ,"\t\t, Version: ", self.version


binaryname = sys.argv[1]
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
			   		nam , ver = parts[7].split("@")
				else:
					nam = parts[7]
					ver = 0
				if parts[6] == 'UND':

					sym = Symbol(nam,'U',ver)
					symbol_list.append(sym)
					sym.displaySymbol()
					sym.displayCount()	
					count += 1
				elif parts[6].isdigit():

					sym = Symbol(nam,'D',ver)
                                        symbol_list.append(sym)         
                                        sym.displaySymbol()
					sym.displayCount()
					count += 1

print "Total number of functions in " + binaryname + " are " , count

