import os

dirname = "/filer/aggregateam/"

AMs = {}
with open('/filer/aggregateam.csv', 'w+') as csvFile:
	for dir2name in os.listdir(dirname):
		packageDir = os.path.join(dirname,dir2name)
		for fname in os.listdir(packageDir):
			for line in open(os.path.join(dirname,dir2name,fname)):
					try:
						key, value = line.strip().split(',')
					except ValueError:
						continue
					value = int(value)
					if key in AMs.keys():
						AMs[key] += value
					else:
						AMs[key] = value
	for key, value in AMs.items():
		csvFile.write(key+","+str(value)+"\n")
