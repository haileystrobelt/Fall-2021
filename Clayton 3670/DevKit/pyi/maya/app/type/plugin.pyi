from typing import Any, Container, Dict, Generic, Iterable, Iterator, List, Optional, Set, Tuple, TypeVar, Union
import maya.OpenMayaAnim as oma
import maya.OpenMaya as om
import maya.cmds as cmds


if False:
    from typing import Dict, List, Tuple, Union, Optional

def removeAnimCallback(): ...
def animCurveEdited(objs, clientData): ...
def register(): ...
def registerAnimCallback(): ...
def deregister(): ...
def getAnimCallbackOption(): ...
def setAnimCallbackOption(enabled): ...


animCallback : NoneType

