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
__author__ = ["aroraadit83704@gmail.com", "ishani.janveja@gmail.com"]
__appname__ = "labelVideo"

import os
import sys

if __name__ == "__main__" and __package__ is None:
    sys.path.insert(0, os.path.dirname(__file__))
    __package__ = "labelVideo"

from main.misc import *

import os.path
import sys

from json import load
from csv import reader, writer

from ffmpy import FFmpeg
from shutil import rmtree
from copy import deepcopy
from functools import partial
from collections import defaultdict

from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *

from displayComponents import *
from helperComponents import *
from statefulComponents import *
from annotationComponents import *
from interpolationComponents import *

class MainWindow(QMainWindow, WindowMixin):
    FIT_WINDOW, FIT_WIDTH, MANUAL_ZOOM = list(range(3))

    def __init__(self, defaultSettingsFile, defaultLabelsFile,
                        defaultFrameLabelsFile):

        # Initialisation of the Main Window Super Class
        super(MainWindow, self).__init__()

        # Setting the Main Window Title
        self.setWindowTitle(__appname__)

        # Initialisation and Loading the Settings Pickle File
        self.settings = Settings(defaultSettingsFile)
        self.settings.load()

        # Initialising the Directory Variables
        self.dirname = None
        self.defaultSaveDir = None
        self.lastOpenDir = None
        self.labelFile = None

        # Initialising the Variable Holding the Paths of all Frame Images
        self.framePathList = []

        # Whether Some Changes Have Been Made
        self.dirty = False

        # TODO: What does this do?
        self._noSelectionSlot = False

        # Separating Drawing a Single B.Box vs Drawing Multiple B.Boxes
        self.drawUsingCreate = False


        # The Text Options for the Dialog Boxes
        self.labelChoices = load(open(defaultLabelsFile, "r"))
        self.prevLabelText = ''

        # The Text and Options in the ID Dialog
        self.prevIDText = '000'
        self.prevFrameIds = []
        self.currFrameIds = []

        # The Number of Previous Frames whose IDs are in the ID Dialog Box
        self.poolOver = 5

        # The Current Frame Number
        self.frameNumber = 0
        self.prevFrameNumber = 0

        # The Frame Class Data Structures
        self.frameClass = "None"
        # TODO: The Following Must Have None
        self.frameClassChoices = load(open(defaultFrameLabelsFile, "r"))
        self.gtFrameClassDict = {}
        self.frameClassDict = {}

        # Base Data Structures for Annotation
        self.framesToShapes = defaultdict(list)
        self.itemsToShapes = {}
        self.shapesToItems = {}

        # Additional Data Structures for Propagation
        self.shadowShapesToItems = {}
        self.shadowItemsToShapes = {}
        self.shadowToReal = []

        # Additional Data Structures for Interpolation
        self.idToFrameToShape = defaultdict(dict)
        self.gtIdToFrameToShape = defaultdict(dict)
        self.idChanged = []

        # Other Application State Variables
        self.image = QImage()
        self.filePath = None
        self.recentDirs = []
        self.maxRecent = 5
        self.lineColor = None
        self.fillColor = None
        self.zoom_level = 100
        self.fit_window = False
        self.autoSaveTime = 15000


        # The Layout
        self.initialiseLayout()

        # The Actions
        self.initialiseActions()

        # The Settings
        self.initialiseSettings()

        # The AutoSave Timer
        self.initialiseAutosaver()


        # The Status Bar
        self.statusBar().showMessage('%s started.' % __appname__)
        self.statusBar().show()

    ## Frame Changer Functions ##
    def initSliderFrameNumberClass(self):
        """
        Initialises the slider and frame label when a new video is loaded in.
        """
        # Sets the slider range
        self.fileSlider.setMinimum(0)
        self.fileSlider.setMaximum(max(len(self.framePathList) - 1, 1))
        self.fileSlider.setTickPosition(QSlider.TicksBelow)
        self.fileSlider.setTickInterval(1)

        # Initialises the slider
        self.fileSlider.setValue(0)

        # Initialises the frame label
        self.frameLabel.setText("{}".format(0))

        # Initialises the frame number
        self.frameNumber = self.fileSlider.value()

        # Intialises the frame class dict
        self.frameClass = "None"
        self.gtFrameClassDict[self.fileSlider.value()] = self.frameClass
        self.setFrameHolderText()

    def frameLabelChange(self):
        value = int(self.frameLabel.text())
        max_value = max(len(self.framePathList) - 1, 1)
        self.prevFrameNumber = self.frameNumber
        self.frameNumber = max(min(value, max_value), 0)
        self.frameLabel.setText("{}".format(self.frameNumber))
        self.fileSlider.setValue(self.frameNumber)
        self.frameNumberChanged()

    def sliderMoved(self):
        self.openImg(self.fileSlider.value())
        self.frameLabel.setText("{}".format(self.fileSlider.value()))

    def sliderValueChange(self):
        self.prevFrameNumber = self.frameNumber
        self.frameNumber = self.fileSlider.value()
        self.frameLabel.setText("{}".format(self.frameNumber))
        self.frameNumberChanged()

    def forwardFrame(self):
        self.prevFrameNumber = self.frameNumber
        self.frameNumber = min(self.frameNumber+1, len(self.framePathList)-1)
        self.fileSlider.setValue(self.frameNumber)
        self.frameLabel.setText("{}".format(self.frameNumber))
        self.frameNumberChanged()

    def backwardFrame(self):
        self.prevFrameNumber = self.frameNumber
        self.frameNumber = max(self.frameNumber-1, 0)
        self.fileSlider.setValue(self.frameNumber)
        self.frameLabel.setText("{}".format(self.frameNumber))
        self.frameNumberChanged()

    def refreshFrameIds(self):
        self.prevFrameIds = []
        self.currFrameIds = []
        for i in range(max(self.frameNumber - self.poolOver, 0),
                        self.frameNumber + 1):
            self.prevFrameIds += [s.idNo for s in self.framesToShapes[i]]
        self.prevFrameIds = list(set(self.prevFrameIds))

    def setUpShadows(self, shadowShapes, interpFramesToShapes):

        self.shadowItemsToShapes.clear()
        self.shadowShapesToItems.clear()
        for shape in shadowShapes:
            item = self.createItem(shape)
            self.shadowItemsToShapes[item] = shape
            self.shadowShapesToItems[shape] = item

        for frame, shapes in interpFramesToShapes.items():
            self.framesToShapes[frame] += shapes
            for shape in shapes:
                existingShape = None
                try:
                    existingShape = self.idToFrameToShape[shape.idNo][frame]
                    self.framesToShapes[frame].remove(existingShape)
                except:
                    pass
                if existingShape:
                    item = self.shapesToItems[existingShape]
                    del self.shapesToItems[existingShape]
                else:
                    item = self.createItem(shape)
                self.itemsToShapes[item] = shape
                self.shapesToItems[shape] = item
                self.idToFrameToShape[shape.idNo][frame] = shape

        for action in self.actions.onShapesPresent:
            action.setEnabled(True)

    def convertShadowToReal(self):
        for shape in self.shadowToReal:
            self.addLabel(deepcopy(shape))
        self.shadowToReal = []

    def frameNumberChanged(self):

        # self.canvas.selectedShape = None
        # self.canvas.update()
        self.openImg()

        self.convertShadowToReal()
        interpFramesToShapes = createInterpolations(self.gtIdToFrameToShape,
                self.prevFrameNumber, self.idChanged)
        self.idChanged = []

        shadowShapes = createShadows(self.gtIdToFrameToShape, self.frameNumber)
        self.setUpShadows(shadowShapes, interpFramesToShapes)

        shapes = shadowShapes + self.framesToShapes[self.frameNumber]
        self.canvas.loadShapes(shapes)
        self.updateLabelList(shapes)
        self.refreshFrameIds()

        self.propagateClassLabel()
        self.setFrameHolderText()


    ## Frame Class Label Functions ##
    def navigateChoices(self, selectionDict):
        def makeChoice(choices):
            dialog = LabelDialog(parent=self,
                                listItem=choices)
            text = dialog.popUp()
            return text

        path = []
        while True:
            if type(selectionDict) == dict:
                choice = makeChoice(selectionDict.keys())
                if choice is None:
                    classes = None
                    break
                selectionDict = selectionDict[choice]
                path.append(choice)
            elif type(selectionDict) == list:
                classes = selectionDict
                break
            else:
                print("CODE BUG: {}".format("selectLabel"))
                classes = None
                break
        return path, classes

    def setFrameHolderText(self):
        self.frameHolder.setText("Class: {:20s} | Frame".format(self.frameClass))

    def assignClassLabel(self):
        path, choices = self.navigateChoices(self.frameClassChoices)
        if choices is None or path is None:
            return
        if len(path) > 0:
            text = " - ".join(path)
        else:
            text = ""
        if len(choices) > 0:
            labelDialog = LabelDialog(parent=self,
                                        listItem = choices,
                                        title = "Frame Class")
            choice = labelDialog.popUp(text=self.frameClass)
            if choice is not None:
                text = text + " - " + choice
            else:
                text = ""
        if len(text) > 0:
            self.frameClass = text
            self.gtFrameClassDict[self.frameNumber] = text
            self.setFrameHolderText()
            self.setDirty()

    def propagateClassLabel(self):
        if self.frameNumber not in self.gtFrameClassDict:
            self.frameClass = propagateFrameLabel(self.gtFrameClassDict,
                                                    self.frameNumber)
        else:
            self.frameClass = self.gtFrameClassDict[self.frameNumber]

    def saveClassLabel(self):
        csvPath = os.path.basename(self.dirname) + "_Class" + FILE_EXT
        csvPath = os.path.join(self.defaultSaveDir, csvPath)
        listWriter = writer(open(csvPath, 'w'))
        listWriter.writerow(["Frame", "Class"])
        for k,v in self.gtFrameClassDict.items():
                listWriter.writerow([k, v])

    def loadClassLabel(self, csvPath):
        listReader = reader(open(csvPath, "r"))
        next(listReader)
        for row in listReader:
            if row:
                k, v = row
                self.gtFrameClassDict[int(k)] = v
        self.propagateClassLabel()
        self.setFrameHolderText()


    ## Canvas Related Functions ##
    def connectCanvasSignals(self):
        self.canvas.zoomRequest.connect(self.zoomRequest)
        self.canvas.scrollRequest.connect(self.scrollRequest)
        self.canvas.newShape.connect(self.shapeTypeSelector)
        self.canvas.shapeMoved.connect(self.setDirty)
        self.canvas.clickedShape.connect(self.shapeClick)
        self.canvas.selectionChanged.connect(self.shapeSelectionChanged)
        self.canvas.drawingPolygon.connect(self.toggleDrawingSensitive)
        self.canvas.deleteShape.connect(self.deleteSelectedShape)

    def shapeClick(self):
        shape = self.canvas.selectedShape
        if shape:
            self.idChanged.append(shape.idNo)
            self.idChanged = list(set(self.idChanged))
            if shape in self.shapesToItems:
                    self.shapesToItems[shape].setSelected(True)
                    if shape.isInterpolated:
                        shape.isInterpolated = False
                        self.gtIdToFrameToShape[shape.idNo][self.frameNumber] = shape
            elif shape in self.shadowShapesToItems:
                self.shadowShapesToItems[shape].setSelected(True)
                if shape not in self.shadowToReal:
                    shape.isInterpolated = False
                    self.shadowToReal.append(shape)
            else:
                print("CODE BUG {}".format("shapeClick"))

    def selectLabel(self, prevText = None, prevIdNo = None):
        selectionDict = self.labelChoices

        _, classes = self.navigateChoices(selectionDict)
        if classes is None:
            return None, None

        labelDialog = LabelDialog(parent=self,
                                    listItem = classes,
                                    title = "Label")
        idDialog = IdDialog(parent=self,
                                    listItem=self.prevFrameIds,
                                    title = "ID")

        if prevText is None:
            prevText = self.prevLabelText
        if prevIdNo is None:
            prevIdNo = self.prevIDText
        text = labelDialog.popUp(text=prevText)
        idNo = idDialog.popUp(text=prevIdNo)
        return text, idNo

    def shapeTypeSelector(self):
        self.timer.stop()
        text, idNo = self.selectLabel()
        self.newShape(text, idNo)
        self.timer.start(self.autoSaveTime)

    def newShape(self, text, idNo):
        if text != None and idNo != None:
            if self.frameNumber in self.idToFrameToShape[idNo]:
                self.canvas.resetAllLines()
                self.errorMessage(u'This ID already exists',
                                    u'<b>%s</b>' % idNo)
                return

            self.prevLabelText = text
            self.prevIDText = "{:03d}".format(max(int(idNo),
                                    int(self.prevIDText)) + 1)

            generate_color = generateColorByText(text)
            shape = self.canvas.setLastLabel(text, generate_color, generate_color)
            shape.idNo = "{:03d}".format(int(idNo))
            shape.toInterpolate = True
            shape.isInterpolated = False
            shape.isOccluded = False

            self.currFrameIds.append(shape.idNo)
            self.addLabel(shape)

            if self.drawUsingCreate:
                self.canvas.setEditing(True)
                self.actions.create.setEnabled(True)
                self.actions.createMode.setEnabled(True)
            else:
                self.actions.create.setEnabled(True)
            self.actions.editMode.setEnabled(True)

            self.setDirty()
        else:
            self.canvas.resetAllLines()

    def deleteSelectedShape(self):
        self.remLabel(self.canvas.deleteSelected())
        self.setDirty()
        if self.noShapes():
            for action in self.actions.onShapesPresent:
                action.setEnabled(False)

    def copyShape(self):
        self.canvas.endMove(copy=True)
        self.addLabel(self.canvas.selectedShape)
        self.setDirty()

    def moveShape(self):
        self.canvas.endMove(copy=False)
        self.setDirty()

    def shapeSelectionChanged(self, selected=False):
        if self._noSelectionSlot:
            self._noSelectionSlot = False
        else:
            shape = self.canvas.selectedShape
            if not shape:
                self.labelList.clearSelection()
        self.actions.delete.setEnabled(selected)
        self.actions.edit.setEnabled(selected)
        self.actions.hideBBox.setEnabled(selected)
        self.actions.toggleInterpolation.setEnabled(selected)

    def toggleInterpolation(self):
        self.canvas.selectedShape.toInterpolate = \
            not self.canvas.selectedShape.toInterpolate

    def togglePolygons(self, value):
        for shape in self.framesToShapes[self.frameNumber]:
            self.canvas.setShapeVisible(shape, value)

    def hideBBox(self):
        self.canvas.setShapeVisible(self.canvas.selectedShape, False)


    ## Label List Related Functions ##
    def connectLabelListSignals(self):
        """
        Connect the Label List Signals to their Relevant Functions
        """
        self.labelList.itemActivated.connect(self.labelSelectionChanged)
        self.labelList.itemSelectionChanged.connect(self.labelSelectionChanged)
        self.labelList.itemDoubleClicked.connect(self.editLabel)
        self.labelList.itemChanged.connect(self.labelItemChanged)

    def createItem(self, shape):
        text = shape.idNo + " - " + shape.label
        item = HashableQListWidgetItem(text)
        item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
        if shape.isOccluded:
            item.setCheckState(Qt.Checked)
        else:
            item.setCheckState(Qt.Unchecked)
        item.setBackground(QColor(255, 255, 255))
        return item

    def currentItem(self):
        items = self.labelList.selectedItems()
        if items:
            return items[0]
        return None

    def addLabel(self, shape, loadFromFile = False):
        item = self.createItem(shape)

        if shape.frame == None:
            shape.frame = self.frameNumber
            self.framesToShapes[self.frameNumber].append(shape)
            self.labelList.addItem(item)
        else:
            frame = shape.frame
            self.framesToShapes[frame].append(shape)
            if frame == self.frameNumber:
                self.labelList.addItem(item)

        self.itemsToShapes[item] = shape
        self.shapesToItems[shape] = item

        if not shape.isInterpolated:
            self.gtIdToFrameToShape[shape.idNo][shape.frame] = shape
        self.idToFrameToShape[shape.idNo][shape.frame] = shape

        for action in self.actions.onShapesPresent:
            action.setEnabled(True)

    def editLabel(self):
        """
        Edits label for a given item
        """
        if not self.canvas.editing():
            return
        self.timer.stop()
        item = self.currentItem()
        text, idNo = self.selectLabel(item.text().split(" - ")[1],
                                        item.text().split(" - ")[0])
        if text is not None and idNo is not None:
            item.setBackground(generateColorByText(text))
            text = "{:03d}".format(int(idNo)) + " - " + text
            item.setText(text)
            self.setDirty()
        self.timer.start(self.autoSaveTime)

    def labelItemChanged(self, item):
        if item in self.itemsToShapes:
            shape = self.itemsToShapes[item]
        elif item in self.shadowItemsToShapes:
            shape = self.shadowItemsToShapes[item]
        else:
            print("CODE BUG {}".format("labelItemChanged"))
            return
        idNo, label = item.text().split(" - ")
        if label != shape.label or idNo != shape.idNo:
            shape.label = label
            shape.idNo = idNo
            shape.line_color = generateColorByText(shape.label)
            for s in self.idToFrameToShape[idNo].values():
                if s == shape:
                    continue
                color = generateColorByText(label)
                s.label = label
                s.line_color = color
                self.shapesToItems[s].setBackground(color)
                self.shapesToItems[s].setText(idNo + " - " + label)
            self.setDirty()
        else:
            if item.checkState() == Qt.Checked:
                shape.isOccluded = True
            else:
                shape.isOccluded = False
            self.canvas.update()

    def remLabel(self, shape):
        if shape is None:
            return
        if shape in self.shapesToItems:
            if int(shape.idNo) == int(self.prevIDText) - 1:
                self.prevIDText = "{:03d}".format(int(self.prevIDText) - 1)
            item = self.shapesToItems[shape]
            del self.shapesToItems[shape]
            del self.itemsToShapes[item]
            del self.idToFrameToShape[shape.idNo][shape.frame]
            del self.gtIdToFrameToShape[shape.idNo][shape.frame]
            self.framesToShapes[shape.frame].remove(shape)
            self.labelList.takeItem(self.labelList.row(item))
            del shape
            del item
        elif shape in self.shadowShapesToItems:
            item = self.shadowShapesToItems[shape]
            self.labelList.takeItem(self.labelList.row(item))
            del self.shadowShapesToItems[shape]
            del self.shadowItemsToShapes[item]
            del shape
            del item
        else:
            print("CODE BUG {}".format("remLabel"))

    def updateLabelList(self, shapes):
        for _ in range(self.labelList.count()):
            self.labelList.takeItem(0)
        for shape in shapes:
            if shape in self.shapesToItems:
                item = self.shapesToItems[shape]
            elif shape in self.shadowShapesToItems:
                item = self.shadowShapesToItems[shape]
            else:
                print("CODE BUG {}".format("updateLabelList"))
            self.labelList.addItem(item)

    def popLabelListMenu(self, point):
        """
        """
        self.menus.labelList.exec_(self.labelList.mapToGlobal(point))

    def labelSelectionChanged(self):
        item = self.currentItem()
        if item and self.canvas.editing():
            item.setBackground(QColor(255, 255, 255))
            self._noSelectionSlot = True
            if item in self.itemsToShapes:
                shape = self.itemsToShapes[item]
            elif item in self.shadowItemsToShapes:
                shape = self.shadowItemsToShapes[item]
            else:
                print("CODE BUG {}".format("labelSelectionChanged"))
                return
            self.canvas.selectShape(shape)
            self.canvas.setShapeVisible(shape, True)

    def loadLabels(self, shapes):
        s = []
        for label, points, line_color, fill_color, idNo, isOccluded,\
                toInterpolate, isInterpolated, frame in shapes:
            shape = Shape(label=label, frame=frame, idNo=idNo,
                                isOccluded = isOccluded,
                                toInterpolate=toInterpolate,
                                isInterpolated=isInterpolated)
            for x, y in points:
                shape.addPoint(QPointF(x, y))
            shape.close()

            if line_color:
                shape.line_color = QColor(*line_color)
            else:
                shape.line_color = generateColorByText(label)

            if fill_color:
                shape.fill_color = QColor(*fill_color)
            else:
                shape.fill_color = generateColorByText(label)

            if frame == self.frameNumber:
                s.append(shape)

            self.addLabel(shape, loadFromFile = True)

        self.canvas.loadShapes(s)

    def saveLabels(self, annotationFilePath):
        annotationFilePath = annotationFilePath
        if self.labelFile is None:
            self.labelFile = LabelFile(annotationFilePath)

        def format_shape(s):
            return dict(label=s.label,
                        points=[(p.x(), p.y()) for p in s.points],
                        idNo=s.idNo, frameNumber = s.frame,
                        isOccluded = s.isOccluded,
                        toInterpolate = s.toInterpolate,
                        isInterpolated = s.isInterpolated)

        shapes = [format_shape(shape) for shape in self.shapesToItems.keys()]
        try:
            self.labelFile.saveCsvFormat(shapes, self.dirname,
                                            self.framePathList)
            return True
        except LabelFileError as e:
            self.errorMessage(u'Error saving label data', u'<b>%s</b>' % e)
            return False


    ## Drawing / Editing Modes ##
    def toggleDrawingSensitive(self, drawing=True):
        """
        Disables toggling between modes in the middle of a drawing.
        """
        self.actions.create.setEnabled(not drawing)
        self.actions.createMode.setEnabled(not drawing)
        self.actions.editMode.setEnabled(not drawing)
        if not drawing:
            self.status('Cancel creation.')
            self.canvas.setEditing(True)
            self.canvas.restoreCursor()

    def createShape(self):
        """
        Facilitates the creation of a single bounding box.
        """
        self.drawUsingCreate = True
        self.canvas.setEditing(False)
        self.actions.create.setEnabled(False)
        self.actions.createMode.setEnabled(True)
        self.actions.editMode.setEnabled(True)

    def setCreateMode(self):
        """
        Facilitates creation of multiple bounding boxes.
        """
        self.drawUsingCreate = False
        self.canvas.setEditing(False)
        self.actions.create.setEnabled(True)
        self.actions.createMode.setEnabled(False)
        self.actions.editMode.setEnabled(True)

    def setEditMode(self):
        """
        Facilitates editing of bounding boxes.
        """
        self.canvas.setEditing(True)
        self.actions.create.setEnabled(True)
        self.actions.createMode.setEnabled(True)
        self.actions.editMode.setEnabled(False)
        self.labelSelectionChanged()


    ## Loader Functions ##
    def openAnnotations(self):
        def openAnnotationDialog():
            csvPath = os.path.basename(self.dirname) + FILE_EXT
            csvPath = os.path.join(self.defaultSaveDir, csvPath)

            filters = "Open CSV file (%s)" % ' '.join(['*.csv'])
            filename = QFileDialog.getOpenFileName(self,
                            '%s - Choose a CSV file' % __appname__,
                            csvPath, filters)
            return filename

        if self.filePath is None:
            self.status('Please select image first')
            return
        filename = openAnnotationDialog()
        if filename:
            if isinstance(filename, (tuple, list)):
                filename = filename[0]
            self.resetAnnotations()
            self.loadAnnotations(filename)

    def openSequence(self, targetDirPath = None):
        def resetState():
            self.resetAnnotations()
            self.filePath = None
            self.dirname = None
            self.imageData = None
            self.canvas.resetState()
            self.labelCoordinates.clear()

        def openSequenceDialog():
            if self.lastOpenDir and os.path.exists(self.lastOpenDir):
                defaultOpenDirPath = self.lastOpenDir
            else:
                defaultOpenDirPath = self.currentPath()

            targetDirPath = QFileDialog.getExistingDirectory(self,
                                '%s - Open Directory' % __appname__,
                                defaultOpenDirPath,
                                QFileDialog.ShowDirsOnly | \
                                        QFileDialog.DontResolveSymlinks)
            targetDirPath = os.path.abspath(targetDirPath)

            return targetDirPath

        def parseTargetDir(dirpath):
            if dirpath:
                dirpath = os.path.abspath(dirpath)
            else:
                dirpath = openSequenceDialog()

            if not os.path.isdir(dirpath):
                print("CODE BUG: {}".format("openSequence"))
                print("Incorrect Targets are Falling Into Load Recent")
                return
            else:
                return dirpath

        def updateSaveStateVariables(dirpath):
            self.defaultSaveDir = os.path.dirname(dirpath)
            self.lastOpenDir = dirpath
            self.dirname = dirpath

        def updateFramePathList(dirpath):
            extensions = ['.jpeg', '.jpg', '.png', '.bmp']
            images = []

            for root, dirs, files in os.walk(dirpath):
                for file in files:
                    if file.lower().endswith(tuple(extensions)):
                        relativePath = os.path.join(root, file)
                        path = os.path.abspath(relativePath)
                        images.append(path)

            images.sort(key=lambda x: x.lower())
            self.framePathList = images

        def addRecentFile(dirpath):
            if dirpath in self.recentDirs:
                self.recentDirs.remove(dirpath)
            elif len(self.recentDirs) >= self.maxRecent:
                self.recentDirs.pop()
            self.recentDirs.insert(0, dirpath)

        def loadAnnotationsIfExist(dirpath):
            csvPath = os.path.basename(dirpath) + FILE_EXT
            csvPath = os.path.join(self.defaultSaveDir, csvPath)
            if os.path.isfile(csvPath):
                self.loadAnnotations(csvPath)
            csvPath = os.path.basename(dirpath) + "_Class" + FILE_EXT
            csvPath = os.path.join(self.defaultSaveDir, csvPath)
            if os.path.isfile(csvPath):
                self.loadClassLabel(csvPath)

        def selectItemLabelList():
            if self.labelList.count():
                count = self.labelList.count()
                self.labelList.setCurrentItem(self.labelList.item(count-1))
                self.labelList.item(count-1).setSelected(True)

        self.autoSave()
        resetState()

        targetDirPath = parseTargetDir(targetDirPath)
        if targetDirPath is None:
            return
        self.filePath = None

        updateSaveStateVariables(targetDirPath)
        updateFramePathList(targetDirPath)
        addRecentFile(targetDirPath)

        windowTitle = __appname__ + ' ' + os.path.basename(targetDirPath)
        self.initSliderFrameNumberClass()
        self.openImg()
        self.setWindowTitle(windowTitle)
        self.setFitWindow()

        loadAnnotationsIfExist(targetDirPath)
        selectItemLabelList()

        self.setClean()

    def openVideo(self):
        def openVideoDialog():
            filters = "%s" % ' '.join(['*.avi', '*.mp4', '*.mpeg', '*.webm'])
            filename = QFileDialog.getOpenFileName(self,
                            '%s - Choose a Video file' % __appname__,
                            self.defaultSaveDir, filters)
            return filename

        def convertToFrameSequence(srcPath):
            destDir = os.path.join(os.path.dirname(__file__), "..")
            destDir = os.path.join(destDir, os.path.basename(srcPath).split(".")[0])
            destPath = os.path.join(destDir, "%06d.png")
            if not os.path.exists(destDir):
                os.makedirs(destDir)
                ff = FFmpeg(inputs={srcPath: None}, outputs={destPath: None})
                ff.run()
            return destDir

        extensions = ['.avi', '.mp4', '.mpeg', '.webm']

        filename = openVideoDialog()[0]
        if filename.lower().endswith(tuple(extensions)):
            destDir = os.path.abspath(convertToFrameSequence(filename))
            self.openSequence(destDir)

    def openImg(self, frameNumber = None):
        if len(self.framePathList) <= 0:
            return
        if frameNumber is None:
            frameNumber = self.frameNumber
        filename = self.framePathList[frameNumber]
        self.canvas.setEnabled(False)
        filePath = str(filename)
        unicodeFilePath = filePath

        if unicodeFilePath and os.path.exists(unicodeFilePath):
            self.imageData = read(unicodeFilePath, None)
            image = QImage.fromData(self.imageData)
            if image.isNull():
                self.errorMessage(u'Error opening file <p>Make sure <i>%s</i> is a valid image file.</p>' % unicodeFilePath)
                self.status(u'Error reading %s' % unicodeFilePath)
                return
            self.status('Loaded %s' % os.path.basename(unicodeFilePath))
            self.image = image
            self.filePath = unicodeFilePath
            self.canvas.loadPixmap(QPixmap.fromImage(image))
            self.canvas.setEnabled(True)
            self.toggleActions(True)
            self.canvas.setFocus(True)

    def loadAnnotations(self, csvPath):
        def setPrevIdText(shapeLists):
            if len(shapeLists):
                self.prevIDText = max([int(s.idNo) for shapeList in shapeLists
                                            for s in shapeList]) + 1
            else:
                self.prevIDText = 0
            self.prevIDText = "{:03d}".format(self.prevIDText)

        if self.dirname is None:
            return
        if not os.path.isfile(csvPath):
            return
        reader = CsvReader(csvPath)
        shapes = reader.getShapes()
        self.loadLabels(shapes)
        setPrevIdText(self.framesToShapes.values())
        self.refreshFrameIds()

    def resetAnnotations(self):
        self.shadowShapesToItems.clear()
        self.shadowItemsToShapes.clear()
        self.itemsToShapes.clear()
        self.shapesToItems.clear()
        self.framesToShapes.clear()
        self.idToFrameToShape.clear()
        self.gtIdToFrameToShape.clear()
        self.shadowToReal = []
        self.idChanged = []
        self.labelList.clear()
        self.labelFile = None


    ## Saver Functions ##
    def autoSave(self):
        if not self.dirty:
            return True
        self.frameNumberChanged()
        if self.dirname:
            self.saveFile()
            self.saveClassLabel()
            self.setClean()
            return True
        return False

    def setDirty(self):
        self.dirty = True

    def setClean(self):
        self.dirty = False
        self.actions.create.setEnabled(True)
        self.actions.createMode.setEnabled(True)
        self.actions.editMode.setEnabled(True)

    def saveFile(self, _value=False):
        csvPath = os.path.basename(self.dirname) + FILE_EXT
        csvPath = os.path.join(self.defaultSaveDir, csvPath)
        self._saveFile(csvPath)

    def _saveFile(self, annotationFilePath):
        if annotationFilePath and self.saveLabels(annotationFilePath):
            self.setClean()
            self.statusBar().showMessage('Saved to  %s' % annotationFilePath)
            self.statusBar().show()

    def saveVideo(self):
        def format_shape(s):
            points = [(p.x(), p.y()) for p in s.points]
            points = LabelFile.convertPoints2BndBox(points)
            text = s.idNo + " - " + s.label
            if s.isOccluded:
                text += "_Occ"
            return points, text

        def drawBBoxes(saveDir):
            for frame in self.framesToShapes.keys():
                srcPath = self.framePathList[frame]
                destPath = os.path.join(saveDir, "{:06d}.png".format(frame))
                boxes = []
                classes = []
                for shape in self.framesToShapes[frame]:
                    if shape in self.shadowShapesToItems:
                        continue
                    box, clss = format_shape(shape)
                    boxes.append(box)
                    classes.append(clss)
                visualiseAnnotations(srcPath, destPath, boxes, classes)

        def convertVideo(saveDir):
            srcPath = os.path.join(saveDir, "%06d.png")
            destPath = self.dirname + "_Annotations.mp4"
            ff = FFmpeg(inputs={srcPath: "-r 10 -f image2 -s 1080x300 -pix_fmt yuv420p"},
                        outputs={destPath: None})
            ff.run()


        saveDir = os.path.join(self.dirname, "Temp")
        if not os.path.exists(saveDir):
            os.makedirs(saveDir)

        drawBBoxes(saveDir)
        convertVideo(saveDir)
        rmtree(saveDir)


    ## Backbone Functions ##

    def initialiseLayout(self):
        """
        Initialises the Layout of the Window
        """

        # The Bounding Box Annotation Display Pane #

        # The Label List Widget
        self.labelList = QListWidget()
        self.connectLabelListSignals()

        # Wrapping the Wdiget in a Dock
        self.dock = QDockWidget(u'Bounding Box Labels', self)
        self.dock.setObjectName(u'Labels')
        self.dock.setWidget(self.labelList)


        # The Frame Switching Pane #

        # The Frame Switcher Layout
        frameSwitcherLayout = QHBoxLayout()
        frameSwitcherLayout.setContentsMargins(0, 0, 0, 0)

        # Displays the String "Frame" and its Class
        self.frameHolder = QLabel()
        self.frameHolder.setText("Frame")
        frameSwitcherLayout.addWidget(self.frameHolder)

        # Adds in a Text Box to Edit the Frame Number
        self.frameLabel = QLineEdit()
        self.frameLabel.returnPressed.connect(self.frameLabelChange)
        self.frameLabel.setFont(QFont("Arial",10))
        frameSwitcherLayout.addWidget(self.frameLabel)

        # Combine them into one Layout
        frameSwitcherContainer = QWidget()
        frameSwitcherContainer.setLayout(frameSwitcherLayout)

        # Initialise the Complete Frame Switching Pane
        sliderLayout = QVBoxLayout()
        sliderLayout.setContentsMargins(0, 0, 0, 0)

        # Add in a File Slider
        sliderLayout.addWidget(frameSwitcherContainer)
        self.fileSlider = QSlider(Qt.Horizontal)
        self.fileSlider.sliderMoved.connect(self.sliderMoved)
        self.fileSlider.sliderReleased.connect(self.sliderValueChange)
        self.initSliderFrameNumberClass()
        sliderLayout.addWidget(self.fileSlider)

        # Wrap the Slider in a Layout Container
        fileSliderContainer = QWidget()
        fileSliderContainer.setLayout(sliderLayout)

        # Wrap the Container in a Dock
        self.sliderDock = QDockWidget(u'Frame Slider', self)
        self.sliderDock.setWidget(fileSliderContainer)


        # The Central Pane #

        # The Canvas on which to Draw Bounding Boxes
        self.canvas = Canvas(parent=self)

        # To Zoom and Scroll Bounding Boxes
        self.zoomWidget = ZoomWidget()
        scroll = QScrollArea()
        scroll.setWidget(self.canvas)
        scroll.setWidgetResizable(True)
        self.scrollBars = {
            Qt.Vertical: scroll.verticalScrollBar(),
            Qt.Horizontal: scroll.horizontalScrollBar()
        }
        self.scrollArea = scroll

        # The Canvas Coordinates Display
        self.labelCoordinates = QLabel('')
        self.statusBar().addPermanentWidget(self.labelCoordinates)

        # The Canvas Signals
        self.connectCanvasSignals()
        self.canvas.forward.connect(self.forwardFrame)
        self.canvas.backward.connect(self.backwardFrame)

        # The Overall Layout #
        self.setCentralWidget(scroll)
        self.addDockWidget(Qt.RightDockWidgetArea, self.dock)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.sliderDock)

    def initialiseActions(self):
        """
        Initialises the actions that can be performed.
        """
        action = partial(newAction, self)
        def initialiseZoomActions():
            ## ZOOM ##

            zoom = QWidgetAction(self)
            zoom.setDefaultWidget(self.zoomWidget)
            self.zoomWidget.setEnabled(False)
            self.zoomWidget.valueChanged.connect(self.paintCanvas)

            zoomIn = action('Zoom &In', partial(self.addZoom, 10),
                            'Ctrl++', enabled=False)
            zoomOut = action('&Zoom Out', partial(self.addZoom, -10),
                            'Ctrl+-', enabled=False)
            zoomOrg = action('&Original size', partial(self.setZoom, 100),
                            'Ctrl+=', enabled=False)
            fitWindow = action('&Fit Window', self.setFitWindow,
                            'Ctrl+F', checkable=True, enabled=False)
            fitWidth = action('Fit &Width', self.setFitWidth,
                            'Ctrl+Shift+F', checkable=True, enabled=False)

            # Group zoom controls into a list for easier toggling.
            zoomActions = (self.zoomWidget, zoomIn, zoomOut,
                           zoomOrg, fitWindow, fitWidth)

            self.zoomMode = self.MANUAL_ZOOM

            self.scalers = {
                self.FIT_WINDOW: self.scaleFitWindow,
                self.FIT_WIDTH: self.scaleFitWidth,
                # Set to one to scale to 100% when loading files.
                self.MANUAL_ZOOM: lambda: 1,
            }

            zoomDict = dict(zoom=zoom, zoomIn=zoomIn, zoomOut=zoomOut,
                            zoomOrg=zoomOrg, fitWindow=fitWindow,
                            fitWidth=fitWidth, zoomActions=zoomActions)
            return zoomDict



        openSeq        = action("&Open Sequence", self.openSequence,
                                "Ctrl+O")
        openAnnotation = action('&Open Annotation', self.openAnnotations,
                                "Ctrl+Shift+O")
        openVideo      = action('&Open Video', self.openVideo,
                                "Ctrl+Shift+V")
        saveVideo      = action('&Save Video', self.saveVideo,
                                "Ctrl+Shift+S")

        createMode     = action('Create\nMultiple\nRectBoxes', self.setCreateMode,
                                "Ctrl+M", enabled = False)
        editMode       = action('&Edit\nRectBox', self.setEditMode,
                                "Ctrl+J", enabled = False)
        create         = action('Create\nRectBox', self.createShape,
                                "Ctrl+R", enabled = False)

        assign         = action('Assign\nClassLabel', self.assignClassLabel,
                                "Ctrl+L")

        edit           = action('&Edit Label', self.editLabel,
                                "Ctrl+E", enabled=False)
        delete         = action('Delete\nRectBox', self.deleteSelectedShape,
                                "Delete", enabled=False)

        hideAll        = action('&Hide All\nRectBoxes',
                                partial(self.togglePolygons, False),
                                'Ctrl+H', enabled=False)
        showAll        = action('&Show All\nRectBoxes',
                                partial(self.togglePolygons, True),
                                "Ctrl+A", enabled=False)

        hideBBox       =  action('&Hide BBox', self.hideBBox,
                                "Ctrl+I", enabled=False)

        toggleInterpolation = action('&Toggle\nInterpolation',
                                self.toggleInterpolation, enabled=False)

        self.actions = struct(open=openSeq, create=create,
                            createMode=createMode, editMode=editMode,
                            edit=edit, delete = delete,
                            hideBBox = hideBBox,
                            toggleInterpolation=toggleInterpolation,
                            onLoadActive = (create, createMode, editMode),
                            onShapesPresent=(hideAll, showAll),
                            **initialiseZoomActions())

        # Label list context menu.
        labelMenu = QMenu()
        addActions(labelMenu, (edit, delete))
        self.labelList.setContextMenuPolicy(Qt.CustomContextMenu)
        self.labelList.customContextMenuRequested.connect(
            self.popLabelListMenu)

        labels = self.dock.toggleViewAction()
        labels.setText('Show/Hide Label Panel')

        sliders = self.sliderDock.toggleViewAction()
        sliders.setText('Show Slider Panel')


        self.menus = struct(
            file=self.menu('&File'),
            view=self.menu('&View'),
            recentDirs=QMenu('Open &Recent'),
            labelList=labelMenu)

        addActions(self.menus.file, [openSeq, openAnnotation, openVideo, None,
                                        saveVideo, None,
                                        self.menus.recentDirs])
        self.menus.file.aboutToShow.connect(self.updateFileMenu)

        addActions(self.menus.view, [labels, sliders, None,
                                    self.actions.zoomOrg,
                                    self.actions.fitWindow,
                                    self.actions.fitWidth])

        self.tools = self.toolbar('Tools')
        addActions(self.tools, [create, None, createMode, None, editMode, None,
                                hideAll, None, showAll, None,
                                self.actions.zoomIn, None,
                                self.actions.zoomOut, None,
                                assign])

        addActions(self.canvas.menus[0], [self.actions.hideBBox, None,
                                        self.actions.toggleInterpolation, None,
                                        assign, None,
                                        create, createMode, editMode, None,
                                        edit, delete])

        addActions(self.canvas.menus[1], (
            action('&Copy here', self.copyShape),
            action('&Move here', self.moveShape)))

    def updateFileMenu(self):
        currFilePath = self.dirname

        def exists(filename):
            return os.path.exists(filename)
        menu = self.menus.recentDirs
        menu.clear()
        files = [f for f in self.recentDirs if f !=
                 currFilePath and exists(f)]
        for i, f in enumerate(files):
            icon = QIcon('labels')
            action = QAction(
                icon, '&%d %s' % (i + 1, QFileInfo(f).fileName()), self)
            action.triggered.connect(partial(self.openSequence, f))
            menu.addAction(action)

    def toggleActions(self, value=True):
        """
        Enable/Disable widgets which depend on an opened video.
        """
        for z in self.actions.zoomActions:
            z.setEnabled(value)
        for action in self.actions.onLoadActive:
            action.setEnabled(value)

    def initialiseSettings(self):
        settings = self.settings
        if settings.get(SETTING_RECENT_FILES):
            if have_qstring():
                recentFileQStringList = settings.get(SETTING_RECENT_FILES)
                self.recentDirs = [i for i in recentFileQStringList]
            else:
                self.recentDirs = recentFileQStringList = settings.get(SETTING_RECENT_FILES)

        size = settings.get(SETTING_WIN_SIZE, QSize(600, 500))
        position = settings.get(SETTING_WIN_POSE, QPoint(0, 0))
        self.resize(size)
        self.move(position)
        saveDir = settings.get(SETTING_SAVE_DIR, None)
        self.lastOpenDir = settings.get(SETTING_LAST_OPEN_DIR, None)
        if saveDir is not None and os.path.exists(saveDir):
            self.defaultSaveDir = saveDir
            self.statusBar().showMessage('%s started. Annotation will be saved to %s' % (__appname__, self.defaultSaveDir))
            self.statusBar().show()

        self.restoreState(settings.get(SETTING_WIN_STATE, QByteArray()))
        Shape.line_color = self.lineColor = QColor(settings.get(SETTING_LINE_COLOR, DEFAULT_LINE_COLOR))
        Shape.fill_color = self.fillColor = QColor(settings.get(SETTING_FILL_COLOR, DEFAULT_FILL_COLOR))
        self.canvas.setDrawingColor(self.lineColor)

        # Populate the File menu dynamically.
        # self.updateFileMenu()

    def initialiseAutosaver(self):
        # Time Driven Auto-Saver
        self.timer = QTimer()
        self.timer.timeout.connect(self.autoSave)
        self.timer.start(self.autoSaveTime)


    ## Auxillary Functions ##
    def currentPath(self):
        """
        Returns the path of the current sequence directory
        """
        return self.dirname if self.dirname else '.'

    def errorMessage(self, title, message):
        return QMessageBox.critical(self, title,
                                    '<p><b>%s</b></p>%s' % (title, message))

    def queueEvent(self, function):
        """
        Allows time intensive functions to run in the background.
        """
        QTimer.singleShot(0, function)

    def status(self, message, delay=5000):
        """
        Facilitates highlighting of key events.
        """
        self.statusBar().showMessage(message, delay)

    def noShapes(self):
        """
        Checks whether there are any shapes defined for the current video.
        """
        return not self.itemsToShapes


    ## Main Window Events ##
    def resizeEvent(self, event):
        """
        Resizes the canvas.
        """
        if self.canvas and not self.image.isNull() \
                and self.zoomMode != self.MANUAL_ZOOM:
            self.adjustScale()
        super(MainWindow, self).resizeEvent(event)

    def closeEvent(self, event):
        if not self.autoSave():
            event.ignore()
        settings = self.settings
        # If it loads images from dir, don't load it at the begining
        if self.dirname is None:
            settings[SETTING_FILENAME] = self.currentPath()
        else:
            settings[SETTING_FILENAME] = ''

        settings[SETTING_WIN_SIZE] = self.size()
        settings[SETTING_WIN_POSE] = self.pos()
        settings[SETTING_WIN_STATE] = self.saveState()
        settings[SETTING_LINE_COLOR] = self.lineColor
        settings[SETTING_FILL_COLOR] = self.fillColor
        settings[SETTING_RECENT_FILES] = self.recentDirs
        if self.defaultSaveDir and os.path.exists(self.defaultSaveDir):
            settings[SETTING_SAVE_DIR] = self.defaultSaveDir
        else:
            settings[SETTING_SAVE_DIR] = ""

        if self.lastOpenDir and os.path.exists(self.lastOpenDir):
            settings[SETTING_LAST_OPEN_DIR] = self.lastOpenDir
        else:
            settings[SETTING_LAST_OPEN_DIR] = ""

        settings.save()


    ## Zoom and Scroll ##
    def scrollRequest(self, delta, orientation):
        """
        Facilitates scrolling across the canvas.
        """
        units = - delta / (8 * 15)
        bar = self.scrollBars[orientation]
        bar.setValue(bar.value() + bar.singleStep() * units)

    def setZoom(self, value):
        """
        Sets the zoom to a given value.
        """
        self.actions.fitWidth.setChecked(False)
        self.actions.fitWindow.setChecked(False)
        self.zoomMode = self.MANUAL_ZOOM
        self.zoomWidget.setValue(value)

    def addZoom(self, increment=10):
        """
        Increments the zoom by a particular value.
        """
        self.setZoom(self.zoomWidget.value() + increment)

    def zoomRequest(self, delta):
        """
        Carries out the actual zooming in of the canvas.
        """
        # get the current scrollbar positions
        # calculate the percentages ~ coordinates
        h_bar = self.scrollBars[Qt.Horizontal]
        v_bar = self.scrollBars[Qt.Vertical]

        # get the current maximum, to know the difference after zooming
        h_bar_max = h_bar.maximum()
        v_bar_max = v_bar.maximum()

        # get the cursor position and canvas size
        # calculate the desired movement from 0 to 1
        # where 0 = move left
        #       1 = move right
        # up and down analogous
        cursor = QCursor()
        pos = cursor.pos()
        relative_pos = QWidget.mapFromGlobal(self, pos)

        cursor_x = relative_pos.x()
        cursor_y = relative_pos.y()

        w = self.scrollArea.width()
        h = self.scrollArea.height()

        # the scaling from 0 to 1 has some padding
        # you don't have to hit the very leftmost pixel for a maximum-left movement
        margin = 0.1
        move_x = (cursor_x - margin * w) / (w - 2 * margin * w)
        move_y = (cursor_y - margin * h) / (h - 2 * margin * h)

        # clamp the values from 0 to 1
        move_x = min(max(move_x, 0), 1)
        move_y = min(max(move_y, 0), 1)

        # zoom in
        units = delta / (8 * 15)
        scale = 10
        self.addZoom(scale * units)

        # get the difference in scrollbar values
        # this is how far we can move
        d_h_bar_max = h_bar.maximum() - h_bar_max
        d_v_bar_max = v_bar.maximum() - v_bar_max

        # get the new scrollbar values
        new_h_bar_value = h_bar.value() + move_x * d_h_bar_max
        new_v_bar_value = v_bar.value() + move_y * d_v_bar_max

        h_bar.setValue(new_h_bar_value)
        v_bar.setValue(new_v_bar_value)

    def setFitWindow(self, value=True):
        """
        Zooms to fit the image in the window.
        """
        if value:
            self.actions.fitWidth.setChecked(False)
        self.zoomMode = self.FIT_WINDOW if value else self.MANUAL_ZOOM
        self.adjustScale()

    def setFitWidth(self, value=True):
        """
        Zooms to fit the image to the width of the window.
        """
        if value:
            self.actions.fitWindow.setChecked(False)
        self.zoomMode = self.FIT_WIDTH if value else self.MANUAL_ZOOM
        self.adjustScale()

    def adjustScale(self, initial=False):
        """
        Adjusts the scale of the image to fit the window.
        """
        value = self.scalers[self.FIT_WINDOW if initial else self.zoomMode]()
        self.zoomWidget.setValue(int(100 * value))

    def scaleFitWindow(self):
        """
        Figures out the size of the pixmap in order to fit the main widget.
        """
        e = 2.0  # So that no scrollbars are generated.
        w1 = self.centralWidget().width() - e
        h1 = self.centralWidget().height() - e
        a1 = w1 / h1
        # Calculate a new scale value based on the pixmap's aspect ratio.
        w2 = self.canvas.pixmap.width() - 0.0
        h2 = self.canvas.pixmap.height() - 0.0
        a2 = w2 / h2
        return w1 / w2 if a2 >= a1 else h1 / h2

    def scaleFitWidth(self):
        """
        Figures out the size of the pixmap in order to fit the main widget.
        """
        w = self.centralWidget().width() - 2.0
        return w / self.canvas.pixmap.width()

    def paintCanvas(self):
        """
        Scales and updates the image in the canvas.
        """
        assert not self.image.isNull(), "cannot paint null image"
        self.canvas.scale = 0.01 * self.zoomWidget.value()
        self.canvas.adjustSize()
        self.canvas.update()


def get_main_app():
    """
    Executing the Main Application Code
    """
    app = QApplication([])
    app.setApplicationName(__appname__)
    appData = os.path.join(os.path.dirname(__file__), 'appData')
    predefLabelsPath = os.path.join(appData, "labels.json")
    predefFrameLabelsPath = os.path.join(appData, "classes.json")
    settingsPath = os.path.join(appData, '.settings.pkl')
    win = MainWindow(settingsPath, predefLabelsPath, predefFrameLabelsPath)
    win.show()
    return app, win

def main():
    """
    A Wrapper to Help in Easy Execution
    """
    app, _win = get_main_app()
    return app.exec_()

if __name__ == '__main__':
    sys.exit(main())
