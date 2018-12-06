import os
import shutil

in_dirname = "/filer/addressingmode/"
out_dirname = "/filer/aggregateam/"

for dir2name in os.listdir(in_dirname):
	packageDir = os.path.join(out_dirname,dir2name)
	if os.path.exists(packageDir):
		continue
		#shutil.rmtree(packageDir)
	os.mkdir(packageDir)
	with open(os.path.join(packageDir, 'aggregate.csv'), 'w+') as csvFile:
		AMs = {}
		for fname in os.listdir(os.path.join(in_dirname, dir2name)):
			for line in open(os.path.join(in_dirname, dir2name, fname)):
				try:
					key, value = line.strip().split(': ')
				except ValueError:
					continue
				value = int(value)
				if key in AMs.keys():
					AMs[key] += value
				else:
					AMs[key] = value
		for key, value in AMs.items():
			csvFile.write(key+","+str(value)+"\n")

aggregatedAMs = {}
with open('/filer/aggregate.csv', 'w+') as csvFile:
	for dir2name in os.listdir(out_dirname):
		packageDir = os.path.join(out_dirname,dir2name)
		for fname in os.listdir(packageDir):
			for line in open(os.path.join(out_dirname,dir2name,fname)):
					try:
						key, value = line.strip().split(',')
					except ValueError:
						continue
					value = int(value)
					if key in aggregatedAMs.keys():
						aggregatedAMs[key] += value
					else:
						aggregatedAMs[key] = value
	for key, value in aggregatedAMs.items():
		csvFile.write(key+","+str(value)+"\n")