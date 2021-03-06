# -*- coding: utf-8 -*
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import os
import time
import math
from random import shuffle
import numpy as np
import collections
import pickle
import pdb

class Vocab(object):
	def __init__(self, vocab_size):
		self.EOS = "<eos>"
		self.UNK = "<unk>"
		self.vocab_size = vocab_size
	
	def read_words(self, file_path):  # return 1-D list
		f = open(file_path)
		data = []
		for line in f:
			data.extend(line.replace("\n"," %s " % self.EOS).split())
		f.close()
		return data

	def build_vocab(self, data_path, dataset):
		train_path = os.path.join(data_path, dataset, "%s.train.txt" % dataset)
		test_path = os.path.join(data_path, dataset, "%s.test.txt" % dataset)
		self.vocab_path = os.path.join(data_path, dataset, "vocabulary.pkl")
		
		if os.path.isfile(self.vocab_path):
			vocab_file = open(self.vocab_path, 'rb')
			self.words = pickle.load(vocab_file)
		else:
			data = []
			for f in train_path, test_path:
				data.extend(self.read_words(f))
			counter = collections.Counter(data)  # sort words '.': 5, ',': 4......
			#counter_items = [i for i in counter.items() if i[1] >= 3]
			#count_pairs = sorted(counter_items, key=lambda x: (-x[1], x[0]))[:FLAGS.vocab_size-1]	# make it pair list, ('.', 5)
			count_pairs = sorted(counter.items(), key=lambda x: (-x[1], x[0]))
			words = list(zip(*count_pairs)[0])
			if self.UNK not in words:
				words.insert(0, "<unk>")
			self.words = words[:self.vocab_size]
			assert len(self.words) == self.vocab_size
			# Shuffle the vocabulary
			shuffle(self.words)

			# Save the vocabulary with pickle for future use
			vocab_file = open(self.vocab_path, 'wb')
			pickle.dump(self.words, vocab_file)
		vocab_file.close()

		self.word2id = dict(zip(self.words, range(self.vocab_size)))	 #�'gone': 17, 'bert': 9, 'bris': 10, 
	
class Reader(object):
	def __init__(self, data_path, dataset, vocab_size, batch_size=None, num_steps=None):
		
		self.batch_size = batch_size
		self.num_steps = num_steps
		self.vocab_size = vocab_size
		self.lightrnn_size = int(math.sqrt(self.vocab_size))
		# Make sure that vocab_size is lightrnn_size * lightrnn_size
		assert self.lightrnn_size*self.lightrnn_size == self.vocab_size
		
		self.vocab = Vocab(vocab_size)
		self.vocab.build_vocab(data_path, dataset)
		self.word2id = self.vocab.word2id
		lightrnn_seq = np.arange(self.lightrnn_size)
		self.wordid2r = np.repeat(lightrnn_seq, self.lightrnn_size)
		self.wordid2c = np.tile(lightrnn_seq, self.lightrnn_size)
		self.id2wordid = np.arange(self.vocab_size)

	def read_file(self, file_path):
		raw_data = self.vocab.read_words(file_path)
		step_num = (len(raw_data)-1) // (self.batch_size * self.num_steps)
		data = []
		for i in range(step_num):
			batch_data = raw_data[i*self.batch_size*self.num_steps: (i+1)*self.batch_size*self.num_steps+1]
			batch_id = [self.word2id[word] if self.word2id.has_key(word) else self.word2id[self.vocab.UNK] for word in batch_data]
			data.append(np.asarray(batch_id))
		return data, step_num

	def get_next_batch(self, data):
		for d in data:
			d_r = [self.wordid2r[k] for k in d]
			d_c = [self.wordid2c[k] for k in d]
			# data is time-majored here for efficiency
			x_r = np.transpose(np.array(d_r[:-1], dtype=np.int32).reshape([self.batch_size, self.num_steps]))
			x_c = np.transpose(np.array(d_c[:-1], dtype=np.int32).reshape([self.batch_size, self.num_steps]))
			y_r = np.transpose(np.array(d_r[1:], dtype=np.int32).reshape([self.batch_size, self.num_steps]))
			y_c = np.transpose(np.array(d_c[1:], dtype=np.int32).reshape([self.batch_size, self.num_steps]))
			y = y_r * self.lightrnn_size + y_c
			yield x_r, x_c, y_r, y_c, y
