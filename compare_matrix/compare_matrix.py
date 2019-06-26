#!/usr/bin/env python2
from __future__ import print_function

import sys
import numpy as np

def field_striper(one_field):
    """Return the unique identifier (md5sum) from a label."""
    return one_field.split('_')[-1] # Unique identifier is after the last _


def sort_output(total_diff_list):
    """Take an output array made from join and return
    a view of the sorted one with descending difference.
    """
    # sorts with the fifth column
    # argsort() returns a list of index
    index_list = total_diff_list[:, 4].argsort()
    sorted_array = total_diff_list[index_list]
    return sorted_array[::-1]


def write_diff_file(diff_matrix, name_output):
    """Write the result of matrix join in the desired format."""
    np.savetxt(name_output, diff_matrix, fmt='%s') # Here spaces will separate elements


class Matrix(object):
    """From the format used in GeEC for matrices, seek out the header fields
    and index. Provides method to compute the difference between the two matrices.
    Only the union/join/compare method should be used by a user,
    everything else is done in the init.

    Format of GeEC matrix data file (example):
    1: \t a \t b \t c \n
    2: a \t num \t num \t num \n
    3: b \t num \t num \t num \n
    4: c \t num \t num \t num \n
    where the numbers to the left refer to the line number,
    (a,b,c) to field strings and num is a number from -1 to 1
    the matrix is symetric, diagonal of ones

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
        fields = header.strip().split('\t')
        # strip removes all white space on each side of the string (which strips off the first tab)
        # split creates a list of all strings separated by a tab
        for column_position, field in enumerate(fields):
            good_field = field_striper(field)
            self.header.append(good_field)
            self.dico[good_field] = column_position


    def parse_matrix(self, matrix_file):
        """Read the matrix numeric values into a numpy matrix
        (skipping the first column) and assign to the matrix attribute.
        """
        # First line already skipped with readline executed before
        self.matrix = np.genfromtxt(matrix_file, delimiter="\t",
                                    usecols=range(1, len(self.header)+1))


    def common_fields(self, matrix2):
        """Create a list of all common fields and returns it"""
        return [field for field in self.header if field in matrix2.dico]


    def join(self, matrix2):
        """Return a numpy array with the format [ [field1, field2, val1, val2, diff], [...], ...] which
        lists off the difference between data from the two entry matrix, for the common fields.
        """
        common_identifiers = self.common_fields(matrix2)

        total_diff_list = []  # all of the data to write the final diffence file

        # The matrix are symetric, we use counters to not go over the same elements
        for counter1, identifier1 in enumerate(common_identifiers):

            col1 = self.dico[identifier1]
            col2 = matrix2.dico[identifier1]
            # The respective column of the identifer in each matrix

            for counter2, identifier2 in enumerate(common_identifiers):

                if counter2 > counter1:
                # Don't calculate for the same identifier or the permutation of two identifiers

                    line1 = self.dico[identifier2]
                    line2 = matrix2.dico[identifier2]
                    # The respective line of the identifer in each matrix
                    # line and column coulb be inverted, the matrix are symetric

                    value1 = self.matrix[line1, col1]
                    value2 = matrix2.matrix[line2, col2]
                    diff = abs(value2 - value1)

                    total_diff_list.append([identifier1, identifier2, value1, value2, diff])

        return np.array(total_diff_list)


    def print_pairings(self):
        """Print non redundant correlation pairings."""
        sorted_md5s = sorted(self.header)
        for i, md5_1 in enumerate(sorted_md5s):
            line = self.dico[md5_1]
            for j, md5_2 in enumerate(sorted_md5s):
                if j > i:
                    col = self.dico[md5_2]
                    value = self.matrix[line, col]
                    s = "{}\t{}\t{}".format(md5_1, md5_2, value)
                    print(s)


def main():
    """We join our two data files from the expected format
    to find what data is different for the same combination of fields,
    sort them with the highest difference at the top
    and then we write a file containing all those differences
    """
    output_name = sys.argv[3]

    with open(sys.argv[1], 'r') as file1, open(sys.argv[2], 'r') as file2:
        matrix1, matrix2 = Matrix(file1), Matrix(file2)

    diff_list = matrix1.join(matrix2)
    sorted_diff_list = sort_output(diff_list)
    write_diff_file(sorted_diff_list, output_name)


if __name__ == "__main__":
    main()
