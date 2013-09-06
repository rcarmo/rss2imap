#!/usr/bin/env python
"""Naive text summarizer"""

from collections import defaultdict
import re

def sentences(text):
    start = 0
    for match in re.finditer('(\s*[.!?]\s*)|(\n{2,})', text):
        yield text[start:match.end()].strip()
        start = match.end()

    if start < len(text):
        yield text[start:].strip()
        

def frequency(text):
    counts = defaultdict(int)
    for token in text.split(): # simplest tokenizer ever
        counts[token] += 1
    return counts


def score(sentence, frequencies):
    return sum((frequencies[token] for token in sentence.split()))


def reorder(sentences, text):
    sentences.sort(lambda a, b: text.find(a) - text.find(b))
    return sentences

    
def summarize(text, limit=3):
    items = [s for s in sentences(text)]
    items.sort(key=lambda s: score(s, frequency(text)), reverse=1)
    return '\n'.join(["<p><i>%s</i></p>" % s for s in reorder(items[:limit], text)])
