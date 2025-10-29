import nltk, re, pprint
from nltk import word_tokenize
from urllib import request

url = "http://www.gutenberg.org/files/2554/2554-0.txt"
response = request.urlopen(url)
raw = response.read().decode('utf8')

tokens = word_tokenize(raw)
text = nltk.pos_tag(tokens[:10])

print(text)