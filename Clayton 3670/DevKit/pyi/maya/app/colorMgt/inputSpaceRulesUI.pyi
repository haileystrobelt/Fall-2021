from typing import Any, Container, Dict, Generic, Iterable, Iterator, List, Optional, Set, Tuple, TypeVar, Union
from . import customTransformUI
import maya
import maya.mel as mel
import maya.cmds as cmds
import re
from . import reapplyRules


if False:
    from typing import Dict, List, Tuple, Union, Optional

class Rule(object):
    def __init__(self, name): ...
    def canDelete(self): ...
    __dict__ : dictproxy
    
    __weakref__ : getset_descriptor


class ChainRule(Rule):
    def __init__(self, name="''"): ...
    def appendRule(self, rule): ...
    def createHandlerRuleUI(self): ...
    def createUI(self): ...
    def indexToPosition(self, index): ...
    def isReadOnly(self): ...
    def onAddRule(self, *args): ...
    def onDeleteRule(self, *args): ...
    def onDown(self, *args): ...
    def onReapply(self, *args): ...
    def onSelect(self, *args): ...
    def onUp(self, *args): ...
    def positionToIndex(self, position): ...
    def selectRule(self, position): ...
    def updateHandlerRuleUI(self): ...
    def updateScrollList(self): ...


class OpaqueRule(Rule):
    def __init__(self, name): ...
    def createUI(self): ...


class ColorSpaceRule(Rule):
    def __init__(self, name): ...
    def createColorSpaceMenu(self): ...
    def fileRuleLayout(self, extWidget, patternWidget):
        """
        Shared layout for color space rules.
        """
        ...
    def getColorSpace(self): ...
    def onInputColorSpaceChange(self, *args): ...
    def onRemoveColorSpace(self, *args): ...
    def setColorSpace(self, colorSpace): ...
    def setMenuValidColorSpace(self, valid): ...
    def validateColorSpace(self, colorSpace): ...
    @property
    def colorSpace(self): ...
    @colorSpace.setter
    def colorSpace(self, value): ...


class FilePathRule(ColorSpaceRule):
    def __init__(self, name): ...
    def canDelete(self): ...
    def createUI(self): ...
    def getExtension(self): ...
    def getPattern(self): ...
    def onExtensionChange(self, *args): ...
    def onPatternChange(self, *args): ...
    def setExtension(self, extension): ...
    def setPattern(self, pattern): ...
    @property
    def extension(self): ...
    @extension.setter
    def extension(self, value): ...
    @property
    def pattern(self): ...
    @pattern.setter
    def pattern(self, value): ...


class DefaultRule(ColorSpaceRule):
    def __init__(self): ...
    def createUI(self): ...




def build(): ...
def nativeMode(): ...
def mayaImageFileExtensions():
    """
    Return the list of image file extensions read by Maya.
    """
    ...
def createUI(): ...


buttonWidth : int
hSpc : int
parentForm : str
red : list
black : list

