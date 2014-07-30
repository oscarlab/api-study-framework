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
	print "Caller function:%30s\tSystem call Made?:%6s\tNumber of callee Functions :%6s\n" %(self.func_name,self.system_call,self.calls_no)
	if len(self.called_func)>0 :
		print '\n****Callee functions list:'
		for func in self.called_func:
			print func
	if len(self.syscall_no) != 0:
		systemcalllist = open('unistd_32.h','r')

		print '\n****System calls list:'
		for no in self.syscall_no:
			if is_hex(no):
				val = int(no,16)
				print "%s(%s)" %(no,sytemCallInfo[str(val)])
			else:			
				print no
		systemcalllist.close()
	print "\n\n------------------------------------------------------------------------------------------------------------------------------------\n"			
def getData( binaryname ):

	process = subprocess.Popen(["objdump", "-d", binaryname, "-j" , ".text"],
                             stdout=subprocess.PIPE
                           	)
	process1 = subprocess.Popen(["readelf", "--dyn-syms","-W", binaryname],
                             stdout=subprocess.PIPE
                                )
	linenbr = 1
	name = ''
	func_list = []
	sys_call_list = []
	pattern1 = 'callq'
	pattern2 = 'syscall'
	pattern3 = 'mov '
	pattern4 = '*ABS*' #Absolute addressing for indirect calls
	sp = '#'
	#Below symbols generally appear for indirect calls
	sym1 = '*'
	sym2 = '%'
	call_list = []	
	syscall = ''
	rax = '' # Ultimately will have syscall no at the end
	registers = ['%rax','%eax','%ax','%al']
	#Seeking the pipe to start position is difficult/not possible , so store in list
	symlist = []
        for item in process1.stdout:
                symlist.append(item.strip())

	for line in process.stdout:
		if line.strip() == '' and linenbr < 7:#intial parts of objdump output which we won't care
			continue
                if len(line.split()) == 2 and len(line.split()[0]) == 16 :
			#start building class object , initialize new class object 	
			#match = re.search(r"\<(\w+)\>", line.split()[1])
			match = re.search(r"\<(.*)\>", line.split()[1])
			if match:
				#Filter name , may contain offset information,remove noise
				name = match.group(1)
			        m = re.search(r'.0x[A-Fa-f0-9]+',name) #Remove hexadecimal offset if any eg:func+0x1234
				if m:
					name = name.replace(m.group(0),'')
						
				#print match.group(1)
		elif len(line.strip()) > 0:
			#prepare function list
			#syscall  no 
 			#store previous line in case of system calls
			#get values of mov instruction and keep in a variable
			
			if pattern3 in line:
				#if instruction contains hints which start by # , filter it
				if sp in line:
					i = line.find(sp)
					line = line[:i].strip()	

				j = line.find(pattern3)
				matched_seq = line[j+len(pattern3):].strip()
				if matched_seq.split(',')[1] in registers:
					#The value of rax is used as system call no , if syscall instr is found
					rax = matched_seq.split(',')[0]
			if pattern1 in line:
				i = line.find(pattern1)
				#Direct calls does not contain sym1 and sym2 , sym2 used infront of registers for indirect calls(AT & T syntax)
				if sym1 not in line[i:].strip() and sym2 not in line[i:].strip():
					#Direct calls - can be func or func+/-offset between angle brackets
					match = re.search(r"\<([a-zA-Z0-9_@+-]+)\>", line[i:].strip())
								
					if match:
						func_name = match.group(1)
						#Handle direct calls of form func+/- offset
						m = re.search(r'.0x[A-Fa-f0-9]+',func_name) #Remove hexadecimal offset if any eg:func+0x1234
						if m:
							func_name = func_name.replace(m.group(0),'')
							
						m = re.search('@', func_name)
						if m:
							#Replace multiple occurences of @ with single @(Example malloc@plt changes to malloc)
							func_name = re.sub(r'@+','@',func_name)
							func_name = func_name.split("@")[0]

						if func_name not in func_list:#Remove duplicate entries  
							func_list.append(func_name)
						#print match.group(1)	
				else:
					#Indirect calls
					#Absolute addressing (ABS)
					if pattern4 in line[i:].strip():
						match = re.search(r'.0x[A-Fa-f0-9]+@plt',line[i:].strip())
						if match:
							j = match.group(0).find('0x')
							addr = match.group(0)[j+2:].strip()
							m = re.search('@', addr)
							if m:
								#Replace multiple occurences of @ with single @(Example malloc@plt changes to malloc)
                                                        	addr = re.sub(r'@+','@',addr)
                                                        	addr = addr.split("@")[0]
								#print addr
							for element in symlist:	
								m = re.search(r'0+' + re.escape(addr) +r'\b',element)
								if m:
									#print element
									parts = element.split()
									m = re.search('@', parts[7])
									if m:
										parts[7] = re.sub(r'@+','@',parts[7])
										func_name  = parts[7].split("@")[0]
									else:
										func_name = parts[7]	

									if func_name not in func_list: 
                                                        			func_list.append(func_name)
									break
										

			if pattern2 in line:
				syscall = 'YES'
				#find system call number from previous instruction
				sys_call_no = rax.replace('$','')#Remove $ before hex value of system call no
				if sys_call_no not in sys_call_list:#Remove duplicate entries
					sys_call_list.append(sys_call_no)

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
			syscall = ''
			name = ''
			rax = ''	
					
		linenbr += 1
		


	#for last function parsed , below code is required
	if syscall != 'YES':
               	syscall = 'NO'			
	call_stat = CallStat(name,func_list,len(func_list),syscall,sys_call_list)
        call_list.append(call_stat)
	
	for item in call_list:
		item.displayCallStat()

def prepare():
    res = {}
    with open("systable.h","r") as text:
        for line in text:
            value, key = line.split()
            res[key] = value
    return res


def is_hex(s):
    try:
        int(s, 16)
        return True
    except ValueError:
        return False

	
if __name__ == "__main__":
	sytemCallInfo = {}
	sytemCallInfo = prepare()
	getData(sys.argv[1])

