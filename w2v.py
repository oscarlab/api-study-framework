import logging
import importlib
import os
import sys
import matplotlib.pyplot as plt
import numpy as np
from sklearn.manifold import TSNE

reload(logging)
logging.basicConfig(format='%(asctime)s %(levelname)s:%(message)s', level=logging.INFO, datefmt='%I:%M:%S')

import gensim

class GetSentences(object):
	def __init__(self, dirname):
			self.dirname = dirname
	def __iter__(self):
		for dir2name in os.listdir(self.dirname):
			for fname in os.listdir(os.path.join(self.dirname, dir2name)):
				for line in open(os.path.join(self.dirname, dir2name, fname)):
					yield line.split()

sentences = GetSentences('/filer/corpus')

model = gensim.models.Word2Vec(sentences, min_count=5, sg=1, iter=5, size=100, window=5, workers=3)
