"""
# Copyright (C) <2018-Present> labelVDOS
# Copyright (C) <2015-2018> Tzutalin
# Copyright (C) 2013  MIT, Computer Science and Artificial Intelligence Laboratory. Bryan Russell, Antonio Torralba, William T. Freeman

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import os
import csv
import sys
import codecs
from collections import defaultdict

FILE_EXT = '.csv'
ENCODE_METHOD = 'utf-8'
frameExtractor = lambda x: int(os.path.basename(x).\
                                split(".")[0])

class CsvWriter:

    def __init__(self, seqFolderPath, frameList):
        """
        The CsvWriter class saves the annotations in CSV format.
        Args:
            seqFolderPath: Directory containing all frames
            frameList: Path to all frames in the directory
        """
        self.seqFolderPath = seqFolderPath
        self.frameList = frameList
        self.boxDict = defaultdict(list)

    def addBndBox(self, xmin, ymin, xmax, ymax, name, idNo,
                isOccluded, isInterpolated, toInterpolate, frameNumber):
        """
        Adds a bounding box to the annotations.
        Args:
            xmin: Minimum x-coordinate
            ymin: Minimum y-coordinate
            xmax: Maximum x-coordinate
            ymax: Maximum y-coordinate
            name: Class of Object
            idNo: ID of Object
            toInterpolate: Whether to interpolate the shape
            isInterpolated: Whether the Box is
                derived from Interpolation
            frameNumber: Frame Number of Object
        """
        box = (name, idNo, xmin, ymax, xmax, ymin, int(isOccluded),
                int(toInterpolate), int(isInterpolated))
        self.boxDict[frameNumber].append(box)

    def save(self, targetFile=None):
        """
        Generates the annotations CSV file for the given video.
        Args:
            targetFile: File to save the annotations to
        """
        if targetFile is None:
            targetFile = os.path.abspath(seqFolderPath) + FILE_EXT
        with codecs.open(targetFile, 'wb',
                            encoding=ENCODE_METHOD) as out:
            csvWriter = csv.writer(out)
            csvWriter.writerow(["frameNumber", "label", "id", "x_TL", "y_TL",
                    "x_BR", "y_BR", "isOccluded",
                    "toInterpolate","isInterpolated"])
            for frameNumber in sorted(self.boxDict.keys()):
                for box in self.boxDict[frameNumber]:
                    csvWriter.writerow([frameNumber, *box])


class CsvReader:

    def __init__(self, filepath):
        """
        The CsvReader class reads the annotations and loads them in.
        Args:
            filepath: Path of the annotations file
        """
        self.filepath = filepath
        # Shapes Format
        # [label, [(x1,y1), (x2,y2), (x3,y3), (x4,y4)], line_color,
        # fill_color, idNo, isInterpolated, frameNo]
        self.shapes = []

    def addShape(self, frameNumber, label, idNo, x_TL, y_TL, x_BR, y_BR,
                    isOccluded, toInterpolate, isInterpolated):
        """
        Collects the necessary parameters to make a shape.
        Args:
            frameNumber: Number of the frame
            x_TL: x-coordinate of Top Left corner of BB
            y_TL: y-coordinate of Top Left corner of BB
            x_BR: x-coordinate of Bottom Right corner of BB
            y_BR: y-coordinate of Bottom Right corner of BB
            label: Label of BB
            idNo: ID of BB
            toInterpolate: Is the BB to be interpolated
            isInterpolated: Is the BB generated through interpolation
        """
        xmin = int(x_TL)
        ymin = int(y_BR)
        xmax = int(x_BR)
        ymax = int(y_TL)
        frameNumber = int(frameNumber)
        points = [(xmin, ymin), (xmax, ymin), (xmax, ymax), (xmin, ymax)]
        toInterpolate = bool(int(toInterpolate))
        isInterpolated = bool(int(isInterpolated))
        isOccluded = bool(int(isOccluded))
        self.shapes.append([label, points, None, None, idNo, isOccluded,
                        toInterpolate, isInterpolated, frameNumber])

    def parseCSV(self):
        """
        Parses the annotation CSV to accumulate the
        parameters of all shapes it contains.
        """
        if not self.filepath.endswith(FILE_EXT):
            print("Unsupported file extension")
            return

        with codecs.open(self.filepath, 'rb',
                            encoding=ENCODE_METHOD) as f:
            f.readline() # Skip Header
            csvReader = csv.reader(f)
            for row in csvReader:
                if len(row):
                    self.addShape(*row)

    def getShapes(self):
        """
        A function that returns all the shapes
        contained in the given annotation file.
        """
        self.parseCSV()
        return self.shapes
