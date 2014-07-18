#!/usr/bin/python
import subprocess
import sys
import re


class CallStat:

   total_func_count = 0
   def __init__(self, func_name, called_func, calls_no,system_call,syscall_no):
      self.func_name = func_name
      self.called_func = called_func
      self.calls_no = calls_no
      self.system_call = system_call
      self.syscall_no = syscall_no
      CallStat.total_func_count  += 1
   
   def displayCount(self):
     print "Total Functions %d" % CallStat.total_func_count

   def displayCallStat(self):
	#print "Name:%50s\tScope:%2s\tVersion:%10s\tLibPath:%40s" %(self.name,self.scope,self.version,self.libpath)
	print "-----------------------------------------------------------------------------------------------------------------------"
	print "Caller function:%50s\tSystem call Made?:%6s\tCallee Functions :%10s\n" %(self.func_name,self.system_call,self.calls_no)
	
	print "***Callee functions"
	for func in self.called_func:
		print func
	if len(self.syscall_no) != 0:
		print '\t\tSystem call list'
		for no in self.syscall_no:
			print no
	print "-----------------------------------------------------------------------------------------------------------------------"			

def getData( binaryname ):

	process = subprocess.Popen(["objdump", "-d", binaryname, "-j" , ".text"],
                             stdout=subprocess.PIPE
                           	)
	linenbr = 1
	name = ''
	func_list = []
	sys_call_list = []
	previous_line = ''
	pattern1 = 'callq'
	pattern2 = 'syscall'
	pattern3 = 'mov'
	call_list = []	
	syscall = ''
	for line in process.stdout:
		
		if line.strip() == '' and linenbr < 7:#intial parts of objdump output which we won't care
			continue
                if len(line.split()) == 2 and len(line.split()[0]) == 16 :
			#start building class object , initialize new class object 	
			match = re.search(r"\<(\w+)\>", line.split()[1])
			if match:
				name = match.group(1)
				#print match.group(1)
		elif len(line.strip()) > 0:
			#prepare function list
			#syscall  no 
 			#store previous line in case of system calls
			#func_list = []
			#sys_call_list = []
			if pattern1 in line:
				i = line.find(pattern1)
				match = re.search(r"\<([a-zA-Z0-9_@]+)\>", line[i:].strip())
				if match:
					func_list.append(match.group(0))
					#print match.group(1)	
			if pattern2 in line:
				syscall = 'YES'
				#find system call number from previous instruction
				if pattern3 in previous_instr:
					i = previous_instr.find(pattern3)
					sys_call_list.append(previous_instr[i+len(pattern3):].strip().split(',')[0])

		elif line.strip() == '':
			#may be end of function
			#store all values in class objects , reinitalize every thing
			if syscall != 'YES':
				syscall = 'NO'
			call_stat = CallStat(name,func_list,len(func_list),syscall,sys_call_list)
			call_list.append(call_stat)
			#Reinitialize the variables again
			func_list = []
        		sys_call_list = []	
					
		previous_instr = line
		linenbr += 1
		


	#for last function , below code is required			
	call_stat = CallStat(name,func_list,len(func_list),syscall,sys_call_list)
        call_list.append(call_stat)
	
	for item in call_list:
		item.displayCallStat()

	
	#for symbols in symbol_list:
		#symbols.displaySymbol()
	#print "Total number of functions in " + binaryname + " are " , count
	#return symbol_list
	
if __name__ == "__main__":
	getData(sys.argv[1]);

