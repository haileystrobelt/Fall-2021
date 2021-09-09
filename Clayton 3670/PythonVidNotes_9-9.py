import maya.cmds as cmds


#Delete cubes in the scene w/o having to do it manually.
cubeList = cmds.ls('myCube*') #aterick symbol will allow any text
#after myCube is acceptable. I.e. ['myCube1', 'myCube1Shape', 'myCube2', ... etc.]
if len(cubeList) > 0;
    cmds.delete(cubeList)


result = cmds.polyCube(w=9, h=9, d=9, name='myCube#')

print('result: ' + str(result))