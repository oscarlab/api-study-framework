import os
import shutil

in_dirname = "/filer/addressingmode/"
out_dirname = "/filer/aggregateam/"

for dir2name in os.listdir(in_dirname):
	packageDir = os.path.join(out_dirname,dir2name)
	if os.path.exists(packageDir):
		shutil.rmtree(packageDir)
	os.mkdir(packageDir)
	with open(os.path.join(packageDir, 'aggregate.csv'), 'w+') as csvFile:
		AMs = {}
		for fname in os.listdir(os.path.join(in_dirname, dir2name)):
			for line in open(os.path.join(in_dirname, dir2name, fname)):
				key, value = line.strip().split(': ')
				value = int(value)
				if key in AMs.keys():
					AMs[key] += value
				else:
					AMs[key] = value
		for key, value in AMs.items():
			csvFile.write(key+","+str(value)+"\n")