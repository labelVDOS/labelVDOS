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

import pickle
import os
import sys

class Settings(object):
    def __init__(self, path = None):
        # Be default, the home will be in the same folder as labelImg
        self.data = {}
        if path:
            self.path = path
        else:
            home = os.path.expanduser("~")
            self.path = os.path.join(home, '.labelVidSettings.pkl')

    def __setitem__(self, key, value):
        self.data[key] = value

    def __getitem__(self, key):
        return self.data[key]

    def get(self, key, default=None):
        if key in self.data:
            return self.data[key]
        return default

    def save(self):
        if self.path:
            with open(self.path, 'wb') as f:
                pickle.dump(self.data, f, pickle.HIGHEST_PROTOCOL)
                return True
        return False

    def load(self):
        if os.path.exists(self.path):
            with open(self.path, 'rb') as f:
                self.data = pickle.load(f)
                return True
        return False

    def reset(self):
        if os.path.exists(self.path):
            os.remove(self.path)
            print ('Remove setting pkl file ${0}'.format(self.path))
        self.data = {}
        self.path = None
