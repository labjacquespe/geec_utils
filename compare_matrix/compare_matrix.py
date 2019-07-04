#!/usr/bin/env python2
from __future__ import print_function

import argparse
import itertools
import os.path
import sys

import numpy as np


def field_striper(one_field):
    """Return the unique identifier (md5sum) from a label."""
    return one_field.split('_')[-1] # when unique identifier is after the last _

def field_striper_alt(one_field):
    """Return the unique identifier (md5sum) from a label."""
    return one_field.split('_', 1)[0] # when unique identifier is before first _

def write_diff_list(diff_list, path, header):
    """Write the result of matrix join in descencing order of difference."""
    diff_list.sort(order="diff")
    np.savetxt(path, np.flipud(diff_list), fmt="%s\t%s\t%.4f\t%.4f\t%g", header=header)


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
        name : the name of the matrix
        header : A numpy list of the headers with unique identifiers
        matrix : The numbers (data other than first column and line) as a numpy matrix
        dico : A dictionary mapping each header field to its position index (row/column)"""

    def __init__(self, matrix_path, name):
        self.name = name
        self.header = []
        self.matrix = None
        self.dico = {}
        with open(matrix_path, 'r') as mat:
            self.parse_file(mat)

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

    def get_value(self, identifier1, identifier2):
        """Get a matrix value from labels."""
        i = self.dico[identifier1]
        j = self.dico[identifier2]
        return self.matrix[i, j]

    def join(self, matrix2):
        """Return a 1D structured numpy array with the format
        [(field1, field2, val1, val2, diff), ...]
        which lists off the difference between data from the two entry matrix,
        for the common fields. Also return the associated header.
        """
        header = "ID1\tID2\t{}\t{}\tdiff".format(self.name, matrix2.name)
        data_type = [("id1", 'U64'), ("id2", 'U64'), ("val1", 'f4'), ("val2", 'f4'), ("diff", 'f4')]
        total_diff_list = []  # all of the data to write the final difference file

        # We compute difference for each unique unordered pair of common identifiers,
        # ignoring same identifier pairs.
        common_identifiers = self.common_fields(matrix2)
        for identifier1, identifier2 in itertools.combinations(common_identifiers, 2):

            value1 = self.get_value(identifier1, identifier2)
            value2 = matrix2.get_value(identifier1, identifier2)
            diff = abs(value2 - value1)

            total_diff_list.append((identifier1, identifier2, value1, value2, diff))

        return np.array(total_diff_list, dtype=data_type), header

    def print_pairings(self):
        """Print non redundant correlation pairings."""
        for id_1, id_2 in itertools.combinations(sorted(self.header), 2):
            line = "{}\t{}\t{}".format(id_1, id_2, self.get_value(id_1, id_2))
            print(line)


def parse_args(args):
    """Define and return argument parser."""
    parser = argparse.ArgumentParser()
    parser.add_argument("matrix1", help="A GeEC matrix")
    parser.add_argument("matrix2", help="A GeEC matrix")
    parser.add_argument("output", help="Difference file")
    return parser.parse_args(args)


def matrix_name(path):
    """Return basename without last extension."""
    return os.path.splitext(os.path.basename(path))[0]


def main():
    """We join our two data files from the expected format
    to find what data is different for the same combination of fields,
    sort them with the highest difference at the top
    and then we write a file containing all those differences.
    """
    args = parse_args(sys.argv[1:])

    matrix_path1 = args.matrix1
    matrix_path2 = args.matrix2
    out_name = args.output

    matrix1 = Matrix(matrix_path1, name=matrix_name(matrix_path1))
    matrix2 = Matrix(matrix_path2, name=matrix_name(matrix_path2))

    diff_list, header = matrix1.join(matrix2)
    # print(len(diff_list))
    write_diff_list(diff_list, out_name, header)


if __name__ == "__main__":
    main()
