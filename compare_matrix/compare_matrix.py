#!/usr/bin/env python2
from __future__ import print_function

import argparse
import itertools
import sys

import numpy as np

def field_striper(one_field):
    """Return the unique identifier (md5sum) from a label."""
    return one_field.split('_')[-1] # when unique identifier is after the last _

def field_striper_alt(one_field):
    """Return the unique identifier (md5sum) from a label."""
    return one_field.split('_', 1)[0] # when unique identifier is before first _

def write_diff_list(diff_list, path):
    """Write the result of matrix join in descencing order of difference."""
    diff_list.sort(order="diff") # sort on the differen
    np.savetxt(path, np.flipud(diff_list), fmt="%s %s %.4f %.4f %g", delimiter='\t')


class Matrix(object):
    """From the format used in GeEC for matrices, seek out the header fields
    and index. Provides method to compute the difference between the two matrices.
    Only the union/join/compare method should be used by a user,
    everything else is done in the init.

    Format of GeEC matrix data file (example):
    1: X \t a \t b \t c \n
    2: a \t num \t num \t num \n
    3: b \t num \t num \t num \n
    4: c \t num \t num \t num \n
    where the numbers to the left refer to the line number,
    (a,b,c) to field strings and num is a number from -1 to 1
    the matrix is symetric, diagonal of ones.
    X is either empty or information that is not a column label.

    Args:
        matrix_file : already opened GeEC matrix data file

    Attributes:
        header : A numpy list of the headers with unique identifiers
        matrix : The numbers (data other than first column and line) as a numpy matrix
        dico : A dictionary mapping each header field to its position index (row/column)"""

    def __init__(self, matrix_file):
        self.header = []
        self.matrix = None
        self.dico = {}
        self.parse_file(matrix_file)


    def parse_file(self, matrix_file):
        """Call parse_header and parse_matrix method
        to fill the header and matrix attributes.
        """
        self.parse_header(matrix_file.readline())
        # Readline is used to read the first line of matrix_file as a string
        # which changes how matrix_file is read (goes to next line).
        # This means parse_matrix gets a different file than parse_header (without first line)
        self.parse_matrix(matrix_file)


    def parse_header(self, header):
        """Create a list of header fields with their unique identifier using
        the header string and a dictionary mapping each key identifier to
        its column index.
        """
        # we ignore the first column (empty or other info than label)
        fields = header.rstrip('\n').split('\t')[1:]
        for column_position, field in enumerate(fields):
            good_field = field_striper_alt(field)
            self.header.append(good_field)
            self.dico[good_field] = column_position


    def parse_matrix(self, matrix_file):
        """Read the matrix numeric values into a numpy matrix
        (skipping the first column) and assign to the matrix attribute.
        """
        # First line already skipped with readline executed before
        used_cols = range(1, len(self.header) + 1)
        self.matrix = np.genfromtxt(matrix_file, delimiter="\t", usecols=used_cols)


    def common_fields(self, matrix2):
        """Create a list of all common fields and returns it"""
        return [field for field in self.header if field in matrix2.dico]


    def join(self, matrix2):
        """Return a structured numpy array with the format [ (field1, field2, val1, val2, diff), ...] which
        lists off the difference between data from the two entry matrix, for the common fields.
        """
        data_type = [("id1", 'U64'), ("id2", 'U64'), ("val1", 'f4'), ("val2", 'f4'), ("diff", 'f4')]
        total_diff_list = []  # all of the data to write the final difference file

        # We compute difference for each unique unordered pair of common identifiers,
        # ignoring same identifier pairs.
        common_identifiers = self.common_fields(matrix2)
        for identifier1, identifier2 in itertools.combinations(common_identifiers, 2):

            col1 = self.dico[identifier1]
            col2 = matrix2.dico[identifier1]

            line1 = self.dico[identifier2]
            line2 = matrix2.dico[identifier2]

            value1 = self.matrix[line1, col1]
            value2 = matrix2.matrix[line2, col2]
            diff = abs(value2 - value1)

            total_diff_list.append((identifier1, identifier2, value1, value2, diff))

        return np.array(total_diff_list, dtype=data_type)

    def print_pairings(self):
        """Print non redundant correlation pairings."""
        for md5_1, md5_2 in itertools.combinations(sorted(self.header), 2):
            line = self.dico[md5_1]
            col = self.dico[md5_2]
            value = self.matrix[line, col]
            s = "{}\t{}\t{}".format(md5_1, md5_2, value)
            print(s)


def parse_args(args):
    """Define and return argument parser."""
    parser = argparse.ArgumentParser()
    parser.add_argument("matrix1", help="A GeEC matrix")
    parser.add_argument("matrix2", help="A GeEC matrix")
    parser.add_argument("output", help="Difference file")
    return parser.parse_args(args)


def main():
    """We join our two data files from the expected format
    to find what data is different for the same combination of fields,
    sort them with the highest difference at the top
    and then we write a file containing all those differences.
    """
    args = parse_args(sys.argv[1:])

    with open(args.matrix1, 'r') as file1, open(args.matrix2, 'r') as file2:
        matrix1, matrix2 = Matrix(file1), Matrix(file2)

    diff_list = matrix1.join(matrix2)
    print(len(diff_list))
    write_diff_list(diff_list, args.output)


if __name__ == "__main__":
    main()
