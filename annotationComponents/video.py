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
import PIL.ImageDraw as ImageDraw
import PIL.ImageFont as ImageFont

from PIL import Image

def visualiseAnnotations(srcPath, destPath, boxes, classes):
    image = Image.open(srcPath)
    for box, clss in zip(boxes, classes):
        xmin, ymin, xmax, ymax = box
        drawBBox(image, clss, ymin, xmin, ymax, xmax)
    image.save(destPath)

def drawBBox(image, label, ymin, xmin, ymax, xmax,
                                color='red', thickness=4):
    draw = ImageDraw.Draw(image)

    left, right, top, bottom = (xmin, xmax, ymin, ymax)

    draw.line([(left, top), (left, bottom), (right, bottom),
            (right, top), (left, top)], width=thickness, fill=color)

    try:
        font = ImageFont.truetype('arial.ttf', 12)
    except IOError:
        font = ImageFont.load_default()

    text_bottom = bottom

    text_width, text_height = font.getsize(label)
    margin = np.ceil(0.05 * text_height)
    draw.rectangle([(left, text_bottom - text_height - 2 * margin),
                        (left + text_width, text_bottom)], fill=color)
    draw.text((left + margin, text_bottom - text_height + margin),
                label, fill='black', font=font)
