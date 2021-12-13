import maya.cmds as cmds

def ChangeColor(color):
    sels = cmds.ls(sl=True)
    for sel in sels:
        shapes = cmds.listRelatives(sel, children=True, shapes=True)
        for shape in shapes:
            cmds.setAttr('%s.overrideEnables' % (shape), True)
            cmds.setAttr('%s.overrideColor' % (shape), color)
    return


def SayHello(name):
    print('Hello %s! Have a nice day!' % name)
    return
