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

from numpy import array
from copy import deepcopy
from collections import defaultdict
from PyQt5.QtCore import QPointF
from annotationComponents.labelFile import LabelFile

NearestLowInit  = -1
NearestHighInit = 1e8

def findNearestFrames(frameList, frame):
	nearestLow  = NearestLowInit
	nearestHigh = NearestHighInit
	mid = None
	for f in frameList:
		if f > nearestLow and f < frame:
			nearestLow = f
		elif f < nearestHigh and f > frame:
			nearestHigh = f
		elif f == frame:
			mid = f
	if mid is not None:
		if nearestLow == NearestLowInit and nearestHigh != NearestHighInit:
			return [(mid, nearestHigh)]
		elif nearestLow != NearestLowInit and nearestHigh == NearestHighInit:
			return [(nearestLow, mid)]
		elif nearestLow != NearestLowInit and nearestHigh != NearestHighInit:
			return [(nearestLow, mid), (mid, nearestHigh)]
		else:
			return []
	else:
		return [(nearestLow, nearestHigh)]

def propagateShadows(shape, frame):
	nearestShape = deepcopy(shape)
	nearestShape.frame = frame
	return nearestShape

def propagateFrameLabel(frameClassDict, frame):
	nearestLow, _ = findNearestFrames(frameClassDict.keys(), frame)[0]
	return frameClassDict[nearestLow]

def interpolateShadows(startShape, endShape):
	def interpPointsToCoordinates(points):
		xmin = int(points[0])
		ymin = int(points[1])
		xmax = int(points[2])
		ymax = int(points[3])
		return [(xmin, ymin), (xmax, ymin), (xmax, ymax), (xmin, ymax)]

	startPoints = [(p.x(), p.y()) for p in startShape.points]
	startPoints = array(LabelFile.convertPoints2BndBox(startPoints))

	endPoints = [(p.x(), p.y()) for p in endShape.points]
	endPoints = array(LabelFile.convertPoints2BndBox(endPoints))

	frameDiff = int(endShape.frame - startShape.frame)
	diffVector = (endPoints - startPoints) / float(frameDiff)
	interpPoints = [startPoints + diffVector * i for i in range(1, frameDiff)]

	interpShadows = []
	for idx, interpPoint in enumerate(interpPoints):
		shape = deepcopy(startShape)
		shape.points = []
		shape.isInterpolated = True
		shape.frame = startShape.frame + idx + 1
		for x, y in interpPointsToCoordinates(interpPoint):
			shape.addPoint(QPointF(x, y))
		interpShadows.append((shape.frame, shape))

	return interpShadows

def createInterpolations(gtIdToFrameToShape, frame, idChanges):
	interpFramesToShapes = defaultdict(list)
	for idNo in idChanges:
		framesToShapes = gtIdToFrameToShape[idNo]
		for nearestLow, nearestHigh in findNearestFrames(framesToShapes.keys(), frame):
			if nearestLow != NearestLowInit and nearestHigh != NearestHighInit:
				startShape = framesToShapes[nearestLow]
				endShape = framesToShapes[nearestHigh]
				if startShape.toInterpolate:
					for frame, shape in interpolateShadows(startShape, endShape):
						interpFramesToShapes[frame].append(shape)
	return interpFramesToShapes

def createShadows(gtIdToFrameToShape, frame):
	propShadows = []
	for idNo, framesToShapes in gtIdToFrameToShape.items():
		for nearestLow, nearestHigh in findNearestFrames(framesToShapes.keys(), frame):
			if nearestLow != NearestLowInit and nearestHigh == NearestHighInit and frame not in framesToShapes:
				shape = framesToShapes[nearestLow]
				if shape.toInterpolate:
					propShadows.append(propagateShadows(shape, frame))
	return propShadows

# def createProposals(detections, frame, existingShapes):
# return detections.show(frame, existingShapes)
