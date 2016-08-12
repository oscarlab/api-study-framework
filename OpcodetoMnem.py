import elementtree.ElementTree as ET

tree = ET.parse('x86reference.xml')
root = tree.getroot()

onebyte = root.getchildren()[0]
mnem_dict_one_byte = {}

for opcd in onebyte.getchildren():
	for mnem in opcd.findall('.//mnem'):
		if opcd.get('value') in mnem_dict_one_byte:
			mnem_dict_one_byte[opcd.get('value')].append(mnem.text)
		else:
			mnem_dict_one_byte[opcd.get('value')] = [mnem.text]

twobyte = root.getchildren()[1]
mnem_dict_two_byte = {}

for opcd in twobyte.getchildren():
	for entry in opcd.findall('.//entry'):
		mnem = entry.find('.//mnem')
		value = '0F' + opcd.get('value')
		text = mnem.text
		#prefix = entry.find('pref')
		#if prefix is not None:
		#	text = prefix.text + text
		if value in mnem_dict_two_byte:
			mnem_dict_two_byte[value].append(text)
		else:
			mnem_dict_two_byte[value] = [text]


for dec, opc, count in opcs:
	try:
		if len(opc) == 2:
			mnem = mnem_dict_one_byte[opc]
		elif len(opc) == 4:
			mnem = mnem_dict_two_byte[opc]
		else:
			mnem = ""
		print dec, "|", opc, "|", mnem, "|", count
	except KeyError:
		print dec, "|", opc, "|", "|", count