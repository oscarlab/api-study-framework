#!/usr/bin/python
import subprocess
import sys
import re
import sqlite3

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

		print '\n****System calls list:'
		for no in self.syscall_no:
			if is_hex(no):
				val = int(no,16)
				print "%s(%s)" %(no,sytemCallInfo[str(val)])
			else:			
				print no
	print "\n\n------------------------------------------------------------------------------------------------------------------------------------\n"			
def getData( binaryname ):

	process = subprocess.Popen(["objdump", "-d", binaryname, "-j" , ".text"],
                             stdout=subprocess.PIPE
                           	)
	process1 = subprocess.Popen(["readelf", "--dyn-syms","-W", binaryname],
                             stdout=subprocess.PIPE
                                )

	process2 = subprocess.Popen(["objdump", "-s", binaryname],
                             stdout=subprocess.PIPE
                                )

	linenbr = 1
	name = ''
	func_list = []
	sys_call_list = []
	#list containing indirect addr and name of func where indirect branch exists separated by ','
	indirect_addr_list = []
	pattern1 = 'callq'
	pattern2 = 'syscall'
	pattern3 = 'mov '
	pattern4 = '*ABS*' #Absolute addressing for indirect calls
	pattern5 = 'retq'
	pattern6 = 'xor'
	sp = '#'
	#Below symbols generally appear for indirect calls
	sym1 = '*'
	sym2 = '%'
	call_list = []	
	syscall = ''
	registers = [['%rax','%eax','%ax','%al'],['%rbx','%ebx','%bx','%bl'],['%rcx','%ecx','%cx','%cl'],['%rdx','%edx','%dx','%dl'],                                              ['%rsi','%esi','%si','%sil'],['%rdi','%edi','%di','%dil'],['%rbp','%ebp','%bp','%bpl'],['%rsp','%esp','%sp','%spl'],                                          ['%r8','%r8d','%r8w','%r8b'],['%r9','%r9d','%r9w','%r9b'],['%r10','%r10d','%r10w','%r10b'],['%r11','%r11d','%r11w','%r11b'],                                  ['%r12','%r12d','%r12w','%r12b'],['%r13','%r13d','%r13w','%r13b'],['%r14','%r14d','%r14w','%r14b'],['%r15','%r15d','%r15w','%r15b']]
	#Below dict gives the mapping of register that has to be considered.For eg if group is 1 consider rbx
	main_register = {}
	for i,j in enumerate(registers):
		main_register[i] = j[0]

	#Seeking the pipe to start position is difficult/not possible , so store in list
	symlist = []
	sectionlist = []
	#List used to store address and callq functions along with retq 
	addr_funclist = []
        for item in process1.stdout:
                symlist.append(item.strip())
	for item in process2.stdout:
		sectionlist.append(item.strip())

	register_values = {}
	for i in registers:
		register_values[i[0]] = None

	for line in process.stdout:
		if line.strip() == '' and linenbr < 7:#intial parts of objdump output don't care
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
				for d in registers:
					if matched_seq.split(',')[1] in d:
						source_reg_val = matched_seq.split(',')[0].strip()
						dest_reg_val = matched_seq.split(',')[1].strip()

						for i,j in enumerate(registers):
							if dest_reg_val in j:
								d_reg = main_register[i]
								break

						if source_reg_val.startswith('$'):
							register_values[d_reg] = source_reg_val
							break
						#if source_reg is not direct value ,rather register itself or mem location
						else:
							flag = 0	
							for g in registers:
								#source is register
								if source_reg_val in g:
									flag = 1
									for i,j in enumerate(registers):
										if source_reg_val in j:
											s_reg = main_register[i]
											break
									register_values[d_reg] = register_values[s_reg]	
									break
							#source is memory location
							if flag == 0:
								register_values[d_reg] = source_reg_val
								break
			#Handling xor instructions for system calls .eg: xor eax,eax --> make eax to zero
			if re.search(r'\b'+re.escape(pattern6)+r'\b',line):
				i = line.find(pattern6)
				if line[i+ len(pattern6):].strip().split(',')[0] == line[i + len(pattern6):].strip().split(',')[1]:
					s_reg = line[i+ len(pattern6):].strip().split(',')[0]
					for i,j in enumerate(registers):
						if s_reg in j:
							d_reg = main_register[i]
							register_values[d_reg] = '$0x0'
							break

							
			if pattern1 in line:

				#Gives the address of current call instruction
				find_addr = re.search(r'^0*([A-Fa-f0-9]+):',line.strip())
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
						
						#Add the current address of instruction and function that is resolved to list
						if find_addr:
							addr_funclist.append(find_addr.group(1)+' '+func_name)
						
						
				else:
					#Indirect calls
					#Absolute addressing (ABS)
					if pattern4 in line[i:].strip():
						match = re.search(r'.0x([A-Fa-f0-9]+@plt)',line[i:].strip())
						if match:
							addr = match.group(1)
							m = re.search('@', addr)
							if m:
								#Replace multiple occurences of @ with single @(Example malloc@plt changes to malloc)
                                                        	addr = re.sub(r'@+','@',addr)
                                                        	addr = addr.split("@")[0]
							for element in symlist:	
								m = re.search(r'0*' + re.escape(addr) +r'\b',element)
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

									#Add the current address of instruction and function that is resolved to list
									if find_addr:
										addr_funclist.append(find_addr.group(1)+' '+func_name)
									break

					#Indirect calls of form - callq *offset(%rip)
					#After retreving information handle this case separately 
					elif re.search(r'\*?[a-zA-Z0-9]*\(%rip\)',line[i:].strip()):
						if sp in line[i:].strip():
							indirectaddr = line[line.find(sp)+1:].strip().split()[0] 
							#Store indirect address and name of function where this indirect branch exists in list
							item  = str(indirectaddr)+','+str(name)
							if item not in indirect_addr_list:
								indirect_addr_list.append(str(indirectaddr)+','+str(name))


							if find_addr:
								addr_funclist.append(find_addr.group(1)+' '+'SPECIALCASE__')

					else:
						#Indirect calls which are not handled yet
						if find_addr:
							addr_funclist.append(find_addr.group(1)+' '+'NOTHANDLEDYET__')

										

			if pattern2 in line:
				syscall = 'YES'
				sys_call_no = ''
				if register_values['%rax'] is not None:
					sys_call_no = register_values['%rax'].replace('$','')#Remove $ before hex value of system call no

				if sys_call_no not in sys_call_list:#Remove duplicate entries
					sys_call_list.append(sys_call_no)
					#Do we need to flush register-values dict here ??
			if re.search(r'\b'+re.escape(pattern5)+r'\b',line):
				#Gives the address of current call instruction
				find_addr = re.search(r'^0*([A-Fa-f0-9]+):',line.strip())
				if find_addr:
					addr_funclist.append(find_addr.group(1)+' '+'RETURN__')


		elif line.strip() == '':
			#may be end of function
			#store all values in class objects , reinitalize every thing
			if syscall != 'YES':
				syscall = 'NO'
			flag = 0
			for item in call_list:
				if item.func_name == name:
					#Merge two
					item.called_func = list(set(item.called_func)|set(func_list))
					item.calls_no = len(item.called_func)
					if syscall == 'YES':
						item.system_call = syscall
						item.syscall_no = list(set(item.syscall_no)|set(sys_call_list))
					flag = 1
					break
			if flag == 0:
				call_stat = CallStat(name,func_list,len(func_list),syscall,sys_call_list)		
				call_list.append(call_stat)
			#Reinitialize the variables again
			func_list = []
        		sys_call_list = []
			syscall = ''
			name = ''
			rax = ''	
			for i in registers:
                		register_values[i[0]] = None
					
		linenbr += 1
		


	#for last function parsed , below code is required
	if syscall != 'YES':
               	syscall = 'NO'			
	call_stat = CallStat(name,func_list,len(func_list),syscall,sys_call_list)
        call_list.append(call_stat)
	
       
	#Handling indirect calls of form form - callq *offset(%rip)
        #Read the contents of sections and get the actual address using indirect ref addr
	for item in indirect_addr_list:
		flag = 0
		for line in sectionlist:
			if re.search(r'\b' + re.escape(item.split(',')[0]) +r'\b',line):
				#address found in section header list
				flag = 1
				#fetch the 64 bit address and convert to actual address from little endian format
				#Example:3b5aa0 00ec1200 00000000 20f01200 00000000  --> actual address is 000000000012ec00
				s1 = line.split()[2]
				b = [s1[i:i+2] for i in range(0, len(s1), 2)]
				s1 = "".join(str(x) for x in reversed(b))
				
				s2 = line.split()[1]
				b = [s2[i:i+2] for i in range(0, len(s2), 2)]
                                s2 = "".join(str(x) for x in reversed(b))
				s1 = s1+s2
				match = re.search(r'0*([A-Fa-f0-9]+)',s1) 
				if match:
					addr = int(match.group(1),16)
					# search for the address in addr_funclist 
					for element in addr_funclist:
						if addr > int(element.split()[0],16):
							continue
						elif addr < int(element.split()[0],16):
							if element.split()[1] != 'RETURN__':
								#Extract and add the function name to caller function list
								for j in call_list:
									if j.func_name == item.split(',')[1]:
										if element.split()[1] not in j.called_func:
											j.called_func.append(element.split()[1])
											j.calls_no = len(j.called_func)
											break
							else:
								break		
				break			
			
		#if flag == 0:
			#Address not found in section header list , yet to be handled					
		#	print "callq *offset(%rip) form indirect call --run time initialization YET TO BE  handled"			
	
	#print the call graph
	#for item in call_list:
	#	item.displayCallStat()

 	#Insert into database
	insert_to_db(call_list,binaryname)

def insert_to_db(call_list,binaryname):

	con = getConnection()
        curr = con.cursor()
        for item in call_list:
                try:
                        if item.calls_no > 0:
                                for func in item.called_func:
                                        curr.execute('insert into CALLER_FUNC_INFO values (?,?,?)', (binaryname,item.func_name,func))
                        else:
                                curr.execute('insert into CALLER_FUNC_INFO values (?,?,?)', (binaryname,item.func_name,None))
                except Exception,err:
                        print("\nFailed to insert row into table CALLER_FUNC_INFO :\n" + "Binary Name:" + str(binaryname) + " Caller function:" + str(item.func_name) + "Callee Func:" + str(func))
                        print(Exception, err)

                try:
                        if len(item.syscall_no) > 0:
                                for no in item.syscall_no:
				

		
	
                                        curr.execute('insert into SYSCALL_INFO values (?,?,?,?)', (binaryname,item.func_name,no,sytemCallInfo[str(int(no,16))] if is_hex(no) and sytemCallInfo.has_key(str(int(no,16))) else None))
                        else:
                                curr.execute('insert into SYSCALL_INFO values (?,?,?,?)', (binaryname,item.func_name,None,None))
                except Exception,err:
                        print("\nFailed to insert row into table SYSCALL_INFO :\n" + "Binary Name:" + str(binaryname) + " Caller func:" + str(item.func_name) + "System call no:" + str(no))
                        print(Exception, err)
	
        con.commit()
        con.close()

def prepare():
    res = {}
    with open("systable.h","r") as text:
        for line in text:
            value, key = line.split()
            res[key] = value
    return res

def getConnection():
        return sqlite3.connect('syscall_popularity.db')


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
	

