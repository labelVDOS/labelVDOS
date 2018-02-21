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

from annotationComponents.csv_io import CsvWriter, FILE_EXT
import os.path
import sys

class LabelFileError(Exception):
    """
    An empty class to raise errors with the annotation files.
    """
    pass

class LabelFile(object):
    suffix = FILE_EXT
    def __init__(self, filename=None):
        """
        The LabelFile class is a wrapper around CsvWriter
        that interfaces between the "shapes" of the labelVid
        and the CSV writer.
        Args:
            filename: File to save the annotations into
        """
        self.shapes = []
        self.filename = filename

    def saveCsvFormat(self, shapes, seqFolderPath, frameList):
        """
        Converts the shapes into bounding boxes and adds
        other annotated information.
        Args:
            shape: List of dictionaries, one for each shape in the canvas
            seqFolderPath: Directory containing all frames
            frameList: Path to all frames in the directory
        """
        writer = CsvWriter(seqFolderPath, frameList)
        for shape in shapes:
            points = shape['points']
            label = shape['label']
            idNo = shape['idNo']
            isOccluded = shape['isOccluded']
            isInterpolated = shape['isInterpolated']
            toInterpolate = shape['toInterpolate']
            frameNumber = shape['frameNumber']
            bndbox = LabelFile.convertPoints2BndBox(points)
            writer.addBndBox(bndbox[0], bndbox[1], bndbox[2], bndbox[3], label,
                idNo, isOccluded, isInterpolated, toInterpolate, frameNumber)
        writer.save(targetFile=self.filename)
        return

    @staticmethod
    def isLabelFile(filename):
        """
        Checks if the label file is of the right extension
        Args:
            filename: CSV file to save annotations in
        """
        fileSuffix = os.path.splitext(filename)[1].lower()
        return fileSuffix == LabelFile.suffix

    @staticmethod
    def convertPoints2BndBox(points):
        """
        Converts the multiple possible points in a shape
        into a bounding box
        Args:
            points: Points present in the annotated shape.
        """
        xmin = float('inf')
        ymin = float('inf')
        xmax = float('-inf')
        ymax = float('-inf')
        for p in points:
            x = p[0]
            y = p[1]
            xmin = min(x, xmin)
            ymin = min(y, ymin)
            xmax = max(x, xmax)
            ymax = max(y, ymax)

        if xmin < 1:
            xmin = 1

        if ymin < 1:
            ymin = 1

        return (int(xmin), int(ymin), int(xmax), int(ymax))
