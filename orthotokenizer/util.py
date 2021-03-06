from __future__ import print_function
import codecs
import unicodedata


def normalized_rows(path, separator, skip_comments=True):
    for line in codecs.open(path, 'r', 'utf8'):
        line = unicodedata.normalize('NFD', line.strip())
        if line and (not skip_comments or not line.startswith('#')):
            if separator:
                yield [col.strip() for col in line.split(separator)]
            else:
                yield line


def normalized_string(string, add_boundaries=True):
    if add_boundaries:
        string = string.replace(" ", "#")
    return unicodedata.normalize("NFD", string)
