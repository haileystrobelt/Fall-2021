import maya.cmds as cmds

def Renamer(input):
    sels = cmds.ls(sl=True) # selections
    c = input.count('#')
    part = input.partition("#" * c) # i.e. part = ["Leg_", "##", "_Jnt"]
    if part[1] == '':
        raise TypeError('Invalid input.')
    for i, sel in enumerate(sels):
        cmds.rename(part[0] + str(i+1).zfill(c) + part[2])

Renamer("Leg_##_Jnt")