# -*- coding: utf-8 -*-
"""
Module for graphemeic and orthographic tokenization with orthography profiles.

"""

__author__ = "Steven Moran"
__date__ = "2010-12-01"

import os
import codecs
import unicodedata

import regex as re

import orthotokenizer
from orthotokenizer.tree import Tree


class Tokenizer(object):
    """
    Class for orthographic parsing using orthography profiles as designed for the QLC project.

    Parameters
    ----------

    orthography_profile : string (default = None)
        Filename (without extension) of the a document source-specific orthography profile and rules file.

    Notes
    -----

    The Tokenizer reads in an orthography profile and calls a helper
    class to build a trie data structure, which stores the possible Unicode
    character combinations that are specified in the orthography profile
    and appear in the data source.

    For example, an orthography profile might specify that in source X
    <uu> is a single grapheme (Unicode parlance: tailored grapheme) and
    thererfore it should be chunked as so. Given an orthography profile and
    some data to parse, the process would look like this:

    input string example: uubo uubo
    output string example: uu b o # uu b o

    See also the test_orthography script in lingpy/scripts/orthography/

    Additionally, the Tokenizer provides functionality to transform graphemes
    into associated character(s) specified in additional columns in the orthography
    profile. A dictionary is created that keeps a mapping between source-specific
    graphemes and their counterparts (e.g. an IPA column in the orthography profile).

    The tokenizer can also be used for pure Unicode character and grapheme
    tokenization, i.e. it uses the Unicode standard grapheme parsing rules, as
    implemented in the Python regex package by Matthew Barnett, to do basic tokenization
    with the "\X" grapheme regular expression match. This grapheme match
    combines one or more Combining Diacritical Marks to their base character.
    These are called "Grapheme clusters" in Unicode parlance. With these functions
    the Tokenizer is meant to do basic rudimentary parsing for things like getting
    an additional unigram model (segments and their counts) in an input data source.

    An additional method (in its infancy) called combine_modifiers handles the
    case where there are Unicode Spacing Modifier Letters, which are not explicitly
    combined to their base character in the Unicode Standard. These graphemes
    are called "Tailored grapheme clusters" in Unicode. For more information
    see the Unicode Standard Annex #29: Unicode Text Segmentation:

    http://www.unicode.org/reports/tr29/

    Lastly, the Tokenizer can be used to transformation as specified in an
    orthography rules file. These transformations are specified in a separate
    file from the orthography profile (that specifics the document specific graphemes,
    and possibly their IPA counterparts) and the orthography rules should
    be applied to the output of an OrthographyParser.

    In an orthography rules file, rules are given in order in regular
    expressions, e.g. this rule replaces a vowel followed by an <n>
    followed by <space> followed by a second vowel with first vowel
    <space> <n> <space> second vowel, e.g.:

    ([a|á|e|é|i|í|o|ó|u|ú])(n)(\s)([a|á|e|é|i|í|o|ó|u|ú]), \1 \2 \4

    """

    def __init__(self, orthography_profile=None):
        # check various places for orthography profiles
        ortho_path = ""
        if orthography_profile:
            # strip possible file extension
            if orthography_profile.endswith('.prf'):
                orthography_profile = orthography_profile[:-4]

            # get path and filename of orthography profile
            if os.path.exists(orthography_profile+".prf"):
                ortho_path = orthography_profile
            else:
                ortho_path = os.path.join(
                    os.path.dirname(orthotokenizer.__file__),
                    'profiles',
                    orthography_profile
                )

        # orthography profile processing
        if os.path.isfile(ortho_path+".prf"):
            self.orthography_profile = ortho_path+".prf"

            # read in orthography profile and create a trie structure for tokenization
            self.tree = Tree(self.orthography_profile)

            # store column labels from the orthography profile
            self.column_labels = []

            # look up table of graphemes to other column transforms
            self.mappings = {}

            # double check that there are no duplicate graphemes in the orthography profile
            self.op_graphemes = {}

            # process the orthography profiles and rules
            self._init_profile(self.orthography_profile)

        else:
            self.orthography_profile = None

        # orthography profile rules and replacements
        if os.path.isfile(ortho_path+".rules"):
            self.orthography_profile_rules = ortho_path+".rules"
            self.op_rules = []
            self.op_replacements = []
            self._init_rules(self.orthography_profile_rules)
        else:
            self.orthography_profile_rules = None

    def _init_profile(self, f):
        """
        Process and initialize data structures given an orthography profile.
        """
        f = codecs.open(f, "r", "utf-8")
        line_count = 0
        for line in f:
            line_count += 1
            line = line.strip()

            # skip any comments in the orthography profile
            if line.startswith("#") or line == "":
                continue

            # deal with the columns header -- should always start with "graphemes" as per the orthography profiles specification
            if line.lower().startswith("graphemes"):
                column_tokens = line.split("\t")

                # clean the header
                for column_token in column_tokens:
                    self.column_labels.append(column_token.lower().strip())
                continue

            # Unicode NFD the line
            line = unicodedata.normalize("NFD", line)

            # split the orthography profile into columns
            tokens = line.split("\t")
            grapheme = tokens[0].strip()

            # check for duplicates in the orthography profile (fail if dups)
            if not grapheme in self.op_graphemes:
                self.op_graphemes[grapheme] = 1
            else:
                raise Exception("You have a duplicate in your orthography profile at: {0}".format(line_count))

            if len(tokens) == 1:
                continue

            for i in range(0, len(tokens)):
                token = tokens[i].strip()
                self.mappings[grapheme, self.column_labels[i].lower()] = token

        f.close()


    def _init_rules(self, f):
        """
        Process the orthography rules file.
        """
        rules_file = codecs.open(f, "r", 'utf-8')

        # compile the orthography rules
        for line in rules_file:
            line = line.strip()

            # skip any comments
            if line.startswith("#") or line == "":
                continue

            line = unicodedata.normalize("NFD", line)
            rule, replacement = line.split(",")
            rule = rule.strip() # just in case there's trailing whitespace
            replacement = replacement.strip() # because there's probably trailing whitespace!
            self.op_rules.append(re.compile(rule))
            self.op_replacements.append(replacement)
        rules_file.close()

        # check that num rules == num replacements; if not fail
        if len(self.op_rules) != len(self.op_replacements):
            raise ValueError("[i] Number of inputs does not match number of outputs in the rules file.")

    def characters(self, string):
        """
        Given a string as input, return a space-delimited string of Unicode characters (code points rendered as glyphs).

        Parameters
        ----------
        string : str
            A Unicode string to be parsed into graphemes.

        Returns
        -------
        result : str
            String returned is space-delimited on Unicode characters and contains "#" to mark word boundaries.
            The string is in NFD.

        Notes
        -----
        Input is first normalized according to Normalization Ford D(ecomposition).
        String returned contains "#" to mark word boundaries.
        """

        string = string.replace(" ", "#") # add boundaries between words
        string = unicodedata.normalize("NFD", string)
        result = ""
        for character in string:
            result += character+" "
        return result.strip()

    def grapheme_clusters(self, string):
        """
        See: Unicode Standard Annex #29: UNICODE TEXT SEGMENTATION
        http://www.unicode.org/reports/tr29/

        Given a string as input, return a space-delimited string of Unicode graphemes using the "\X" regular expression.

        Parameters
        ----------
        string : str
            A Unicode string to be parsed into graphemes.

        Returns
        -------
        result : str
            String returned is space-delimited on Unicode graphemes and contains "#" to mark word boundaries.
            The string is in NFD.

        Notes
        -----
        Input is first normalized according to Normalization Ford D(ecomposition).
        """

        # init the regex Unicode grapheme cluster match
        grapheme_pattern = re.compile("\X", re.UNICODE)

        # add boundaries between words
        string = string.replace(" ", "#")

        # Unicode NDF the string
        string = unicodedata.normalize("NFD", string)

        result = ""
        graphemes = grapheme_pattern.findall(string)
        for grapheme in graphemes:
            result += grapheme+" "
        result = result.strip()
        return result

    def graphemes(self, string):
        """
        Tokenizes strings given an orthograhy profile that specifies graphemes in a source doculect.

        Parameters
        ----------
        string : str
            The str to be parsed and formatted.

        Returns
        -------
        result : str
            The result of the parsed and QLC formatted str.

        """
        string = unicodedata.normalize("NFD", string)

        # if no orthography profile is specified, simply return
        # Unicode grapheme clusters, regex pattern "\X"
        if self.orthography_profile == None:
            return self.grapheme_clusters(string)

        parses = []
        for word in string.split():
            parse = self.tree.parse(word)

            # case where the parsing fails
            if len(parse) == 0:
                # replace characters in string but not in orthography profile with <?>
                parse = " "+self.find_missing_characters(self.characters(word))

            parses.append(parse)

        # remove the outter word boundaries
        result = "".join(parses).replace("##", "#")
        result = result.rstrip("#")
        result = result.lstrip("#")
        return result.strip()


    def transform(self, string, column="graphemes"):
        """
        Transform a string's graphemes into the mappings given in a different column
        in the orthography profile. By default this function returns an orthography
        profile grapheme tokenized string.

        Parameters
        ----------
        string : str
            The input string to be parsed.

        conversion : str (default = "graphemes")
            The label of the column to transform to. Default it to tokenize with orthography profile.

        Returns
        -------
        result : str
            Result of the transformation.

        """
        # This method can't be called unless an orthography profile was specified.
        if self.orthography_profile is None:
            raise Exception("This method only works when an orthography profile is specified.")

        if column == "graphemes":
            return self.graphemes(string)

        # if the column label for conversion doesn't exist, return grapheme tokenization
        if not column in self.column_labels:
            return self.graphemes(string)

        # first tokenize the input string into orthography profile graphemes
        tokenized_string = self.graphemes(string)
        tokens = tokenized_string.split()

        result = []
        for token in tokens:
            # special cases: word breaks and unparsables
            if token == "#":
                result.append("#")
                continue
            if token == "?":
                result.append("?")
                continue

            # transform given the grapheme and column label; skip NULL
            target = self.mappings[token, column]
            if not target == "NULL":
                # result.append(self.mappings[token, column])
                result.append(target)

        return " ".join(result).strip()

    def tokenize(self, string, column="graphemes"):
        """
        This function determines what to do given any combination
        of orthography profiles and rules or not orthography profiles
        or rules.

        Parameters
        ----------
        string : str
            The input string to be tokenized.

        column : str (default = "graphemes")
            The column label for the transformation, if specified.

        Returns
        -------
        result : str
            Result of the tokenization.

        """

        if self.orthography_profile and self.orthography_profile_rules:
            return self.rules(self.transform(string, column))

        if not self.orthography_profile and not self.orthography_profile_rules:
            return self.grapheme_clusters(string)

        if self.orthography_profile and not self.orthography_profile_rules:
            return self.transform(string, column)

        # it's not yet clear what the order for this procedure should be
        if not self.orthography_profile and self.orthography_profile_rules:
            return self.rules(self.grapheme_clusters(string))

    def transform_rules(self, string):
        """
        Convenience function that first tokenizes a string into orthographic profile-
        specified graphemes and then applies the orthography profile rules.
        """
        return self.rules(self.transform(string))

    def rules(self, string):
        """
        Function to parse input string and return output of str with ortho rules applied.

        Parameters
        ----------
        string : str
            The input string to be parsed.

        Returns
        -------
        result : str
            Result of the orthography rules applied to the input str.

        """
        # if no orthography profile rules file has been specified, simply return the string
        if self.orthography_profile_rules is None:
            return string

        result = unicodedata.normalize("NFD", string)
        for i in range(0, len(self.op_rules)):
            match = self.op_rules[i].search(result)
            if match:
                result = re.sub(self.op_rules[i], self.op_replacements[i], result)

        # this is in case someone introduces a non-NFD ordered sequence of characters
        # in the orthography profile
        return unicodedata.normalize("NFD", result)

    def find_missing_characters(self, char_tokenized_string):
        """
        Given a string tokenized into characters, return a characters
        tokenized string where each character missing from the orthography
        profile is replaced with a question mark <?>.
        """
        return " ".join(
            [c if c in self.op_graphemes else "?" for c in char_tokenized_string.split()])

    def tokenize_ipa(self, string):
        """
        Experimental method for tokenizing IPA.
        """
        string = unicodedata.normalize("NFD", string)
        grapheme_clusters = self.grapheme_clusters(string)
        return self.combine_modifiers(grapheme_clusters)

    def combine_modifiers(self, string):
        """
        Given a string that is space-delimited on Unicode grapheme clusters,
        group Unicode modifier letters with their preceding base characters.

        Parameters
        ----------
        string : str
            A Unicode string tokenized into grapheme clusters to be tokenized into simple IPA.

        .. todo:: check if we need to apply NDF after string is parsed

        """
        result = []
        graphemes = string.split()
        temp = ""
        count = len(graphemes)

        for grapheme in reversed(graphemes):
            count -= 1
            if len(grapheme) == 1 and unicodedata.category(grapheme) == "Lm":
                temp = grapheme+temp
                # hack for the cases where a space modifier is the first character in the str
                if count == 0:
                    result[-1] = temp+result[-1]
                continue

            result.append(grapheme+temp)
            temp = ""

        # check for tie bars
        segments = result[::-1]

        i = 0
        r = []
        while i < len(segments):
            if ord(segments[i][-1]) in [865, 860]:
                r.append(segments[i]+segments[i+1])
                i = i+2
            else:
                r.append(segments[i])
                i += 1

        return " ".join(r)


        """
        # list of points (decimal) of Unicode Mns that require a closing grapheme
        # 865 COMBINING DOUBLE INVERTED BREVE
        # 860 COMBINING DOUBLE BREVE BELOW

        bimodifiers = [860, 865]

        graphemes = string.split()
        print(graphemes)

        result = []
        temp = ""

        i = 0
        while i < len(graphemes)-1:
            # TODO: catch if the first thing is a modifer
            print(graphemes[i])
            for char in graphemes[i]:
                if unicodedata.category(char) == "Mn":
                    result.append
            i += 1
            continue

            # result.append(graphemes[i])

            if i+1 <= len(graphemes):
                for char in graphemes[i]:
                    print(graphemes[i])
                    if unicodedata.category(graphemes[i]) == "Mn":
                        # temp = graphemes[i]+graphemes[i+1]+graphemes[i+2]
                        i = i+2
                        graphemes.append(temp)
                        continue
                result.append(graphemes[i])
                i += 1

            # unicodedata.category() == "Mn" # Mark, non-spacing characters
            # if i < len(graphemes) - 1:
                # check for i+1
                # if it's combiner, grab it
                # i++
                # if char is in bimodifiers

        return " ".join(result)

        """

