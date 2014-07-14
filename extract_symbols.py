#!/usr/bin/python
import subprocess
import sys
import re


# When the scope is D (Defined) , the libpath is the path where symbols is defined
# When the scope is U (Undefined) , the libpath gives the path where it is actually defined

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
			if (parts[3] == 'FUNC' or parts[3] == 'IFUNC') and (parts[4] == 'GLOBAL' or parts[4] == 'WEAK'):
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
	#print "Total number of functions in " + binaryname + " are " , count
	return symbol_list

# getDependencies function will return list of dependencies that binary depends on.
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

        dependency_list = []
        for libpath in process3.stdout:
                if (libpath != "" and len(libpath) > 1): #check this later
			dependency_list.append(libpath.strip())
                        count += 1
	#for i in dependency_list:
	#	print i
        #print "No of dependencies:",count
	
        return dependency_list

# getDependentSymbols will return list of all symbols of the dependencies that binary depend on.
def getDependentSymbols( binaryname ):
	
	count = 0;
	
	dependency_list = getDependencies(binaryname)
	lib_symbol_list = []
	for libpath in dependency_list:
		temp_list = []
		temp_list = getSymbols(libpath)
		lib_symbol_list += temp_list
		#print "Length of ",libpath," is ",len(temp_list)
		count += 1
	#for symbols in lib_symbol_list:
              #symbols.displaySymbol()

	#print "Length of Main list  is: ",len(lib_symbol_list)
	#print "No of dependencies:",count
	return lib_symbol_list
#print "Before function call"

def getSymbolInfo( binaryname ):
	
	symbol_list = []
	dependency_symlist = []
	final_list = []
	symbol_list = getSymbols(binaryname)
	
	#Below is the binary which is the interpretor and is statically linked , so for this special case just return its symbols.	
	if binaryname == '/lib64/ld-linux-x86-64.so.2':
		return symbol_list
	dependency_symlist = getDependentSymbols(binaryname)

	for symbol in symbol_list:
		for dependency_sym in dependency_symlist:

			if symbol.scope == 'U':
				if ((symbol.name == dependency_sym.name) and (dependency_sym.scope == 'D')):
					sym = Symbol(symbol.name,symbol.scope,dependency_sym.version,dependency_sym.libpath)
					final_list.append(sym)
					break
					 	
			else:
					final_list.append(symbol)
					break
	#for symbols in final_list:
        #      symbols.displaySymbol()
	#print "Length of Symbol list  is: ",len(symbol_list)
	#print "Length of Dependency list  is: ",len(dependency_symlist)
	#print "Length of Final list  is: ",len(final_list)
	return final_list

#The getALlSymbolInfo function extracts all symbols of binary including it's dependency symbols(over-estimation)
def getAllSymbolInfo( binaryname ):

	final_list = getSymbolInfo(binaryname)
	initial_count = len(final_list)
        dependency_list = getDependencies(binaryname)
	final_list_nodups = []

	for dependency in dependency_list:
		temp_list = []
		temp_list = getSymbolInfo(dependency)
		#print "Length of ",dependency," is ",len(temp_list)
		final_list += temp_list


	#Code for duplicate elimination from symbol list	
	for symbols in final_list:
		count = 1
		for i in final_list_nodups:
			if (symbols.name == i.name and symbols.scope == i.scope and symbols.version == i.version and symbols.libpath == i.libpath):
				count += 1	
				break
		if count == 1:
		    final_list_nodups.append(symbols)	
	
	for symbols in final_list_nodups:
              symbols.displaySymbol()

	print "Number of dependencies is ",len(dependency_list)
	print "Length of Original list is ",initial_count
	print "Length of final list after over estimating is ",len(final_list)
	print "Length of final list after over estimating without duplicates is ",len(final_list_nodups)
	return final_list_nodups     


	
if __name__ == "__main__":
	#getSymbols(sys.argv[1]);
	#getDependencies(sys.argv[1]);
	#getSymbolInfo(sys.argv[1]);
	getAllSymbolInfo(sys.argv[1]);

