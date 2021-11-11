import maya.cmds as cmds

cmds.polySphere(r=1) # ['pSphere1', 'polySphere']

cmds.polySphere(obj[1], e=True, r=5)

cmds.xform(obj[1], q=True, rotatePivot=True, worldSpace=True)

cmds.listRelatives(obj[0], children=True, shapes=True)

sels = cmds.ls(sl=True)
for sel in sels:
    shapes = cmds.listRelatives(sel, children=True, shapes=True)
    print(sel + ": ")