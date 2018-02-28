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
import numpy as np

from pandas import read_csv
from collections import defaultdict
from PyQt5.QtCore import QPointF
from helperComponents.drawingHelpers import Shape

def iou(bb_test,bb_gt):
	"""
	Computes IUO between two bboxes in the form [x1,y1,x2,y2]
	"""
	xx1 = np.maximum(bb_test[0], bb_gt[0])
	yy1 = np.maximum(bb_test[1], bb_gt[1])
	xx2 = np.minimum(bb_test[2], bb_gt[2])
	yy2 = np.minimum(bb_test[3], bb_gt[3])
	w = np.maximum(0., xx2 - xx1)
	h = np.maximum(0., yy2 - yy1)
	wh = w * h
	o = wh / ((bb_test[2]-bb_test[0])*(bb_test[3]-bb_test[1]) \
			  + (bb_gt[2]-bb_gt[0])*(bb_gt[3]-bb_gt[1]) - wh)
	return(o)

def convertShapeToBBox(shape):
	xmin = float('inf')
	ymin = float('inf')
	xmax = float('-inf')
	ymax = float('-inf')
	for p in shape.points:
		x = p.x()
		y = p.y()
		xmin = min(x, xmin)
		ymin = min(y, ymin)
		xmax = max(x, xmax)
		ymax = max(y, ymax)

	if xmin < 1:
		xmin = 1

	if ymin < 1:
		ymin = 1

	return np.array([int(xmin), int(ymin), int(xmax), int(ymax)])

class objectDetection:
	count = 0

	def __init__(self, objectDetectionFile, iouThreshold = 0.3,
					iouCompetitorThresh = 0.7):
		self.objectDetections = self.load(objectDetectionFile)
		self.iouThreshold = iouThreshold
		self.iouCompetitorThresh = iouCompetitorThresh

	def load(self, objectDetectionFile):
		kitti_annotation_mapping = {0:"Frame", 1:"ID", 2:"Type", 3:"Truncated",
									4:"Occluded", 6:"x_L", 7:"y_T",
									8:"x_R", 9:"y_B"}
		kitti_annotation_columns = ["Sequence Number","Src", "Dest", "x_L",
									"y_B", "x_R", "y_T"]

		def parse_annotations(annotations):
			annotations = annotations[[0, 1, 2, 3, 4, 6, 7, 8, 9]]
			annotations = annotations.rename(kitti_annotation_mapping, axis = 1)
			annotations["w"] = annotations["x_R"] - annotations["x_L"]
			annotations["h"] = annotations["y_T"] - annotations["y_B"]
			annotations["c_x"] = 0.5 * ( annotations["x_R"] + annotations["x_L"] )
			annotations["c_y"] = 0.5 * ( annotations["y_T"] + annotations["y_B"] )
			annotations = annotations[annotations["Type"] != "DontCare"]
			annotations = annotations[annotations["Truncated"] == 0]
			annotations = annotations.reset_index(drop = True)
			annotations = annotations[["Frame", "Type","x_L", "y_T", "x_R", "y_B"]]
			return annotations

		def convertBndBoxToShape(annotation):

			def pointsToCoords(points):
				xmin = int(points[0])
				ymin = int(points[1])
				xmax = int(points[2])
				ymax = int(points[3])
				return [(xmin, ymin), (xmax, ymin), (xmax, ymax), (xmin, ymax)]

			shape = Shape(label = annotation["Type"], frame = annotation["Frame"])
			shape.isDetection = True
			shape.isOccluded = False
			shape.idNo = "{:03d}".format(-1 * (objectDetection.count + 1))
			objectDetection.count = (objectDetection.count + 1) % 900
			points = pointsToCoords(np.array(annotation[["x_L", "y_T", "x_R", "y_B"]]))
			for x,y in points:
				shape.addPoint(QPointF(x, y))

			return shape

		def convertAnnotationsToShapes():
			annotationDict = defaultdict(list)
			annotations = read_csv(objectDetectionFile, sep = " ", header = None)
			annotations = parse_annotations(annotations)
			for idx in range(len(annotations)):
				row = annotations.iloc[idx]
				shape = convertBndBoxToShape(row)
				annotationDict[shape.frame].append(shape)
			return annotationDict

		return convertAnnotationsToShapes()

	def show(self, frame, existingShapes):

		def convertToArrays(frame, existingShapes):
			detections = self.objectDetections[frame]
			detectionArray = [convertShapeToBBox(s) for s in
								detections]
			presentArray = [convertShapeToBBox(s) for s in
								existingShapes]
			return detections, detectionArray, presentArray

		def computeProposals(frame, existingShapes):
			detections, detectionArray, existingArray = \
                                    convertToArrays(frame, existingShapes)
			proposals = []
			for detection, bbox in zip(detections, detectionArray):
				flag = True
				for shape in existingArray:
					if iou(shape, bbox) > self.iouThreshold:
						flag = False
						break
				if flag:
					proposals.append(detection)
			return proposals

		return computeProposals(frame, existingShapes)

	def getNearest(self, frame, shape):
		bbox = convertShapeToBBox(shape)
		competitorShapes = self.objectDetections[frame]
		competitorIoUs = [convertShapeToBBox(s) for s in competitorShapes]
		competitorIoUs = np.array([iou(bbox, comp) for comp in competitorIoUs])
		bestCompetitor = np.argmax(competitorIoUs)
		if competitorIoUs[bestCompetitor] > self.iouCompetitorThresh:
			return competitorShapes[bestCompetitor]
		return None
