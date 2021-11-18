import maya.cmds as cmds

def colorChange(i, ctrl):
    colorList = ['pewter', 'black', 'iron', 'gray', 'red', 'navy blue', "indigo (crayola)", 'juniper', 'indigo',
                 'purple', 'tawny', 'hickory', 'cinnamon', 'scarlet', 'pear', 'sapphire', 'white', 'yellow',
                 'baby blue', 'sage', 'pink', 'tortilla', 'corn', 'hunter', 'peanut', 'sheen green', 'venom',
                 'dollar bill', 'turkish', 'maya blue', 'violet', 'magenta']
    # cmds.color('sphere1', ud=1)
    if isinstance(i, int):  # if it's an integer
        if 0 <= i <= 31:
            cmds.setAttr((ctrl[0] + '.overrideEnabled'), 1)
            cmds.setAttr((ctrl[0] + '.overrideColor'), i)  # use index, make sure it's converted though
        else:
            print("Incorrect input. Please provide a number 0-31. Or provide a name within the following list: \n")
            print(colorList)
    if i in colorList:
        i = colorList.index(i)  # if the index is in the list, find which index it's at
        cmds.setAttr((ctrl[0] + '.overrideEnabled'), 1)
        cmds.setAttr((ctrl[0] + '.overrideColor'), int(i))  # use that index to get the color in maya
    else:
        print("Please provide a number 0-31. Or provide a name within the following list: \n")
        print(colorList)



def createControl(color_ind):
    # matchtransformations can change both location and orientations to match transforms of selected objs
    # cmds.matchTransform('cylinder1', 'cone1')

    sels = cmds.ls(sl=True)  # grab selection
    len_sels = len(sels)  # store selection list length

    if len_sels == 0: # if no selections, set control to the center
        ctrl = cmds.circle(n='Default_Ctrl')  # create and name nurbs circle
        cmds.select(ctrl)  # select it
        cmds.rotate('90deg', 0, 0, r=True)  # fix incorrect rotation
        grp = cmds.group(ctrl, n='Grp_Crtl')

        colorChange(color_ind, ctrl) # change control's color

    elif len_sels == 1: # if there is only one selection, name it
        ctrl_name = sels[0] + "_Ctrl"
        ctrl = cmds.circle(n=ctrl_name)  # create and name nurbs circle
        cmds.select(ctrl)  # select it
        cmds.rotate('90deg', 0, 0, r=True)  # fix incorrect rotation
        grp = cmds.group(ctrl, n='Grp_Crtl')
        cmds.matchTransform(grp, sels[0]) # set control to match transforms of selection

        colorChange(color_ind, ctrl)  # change control's color

    else:
        for sel in sels:
            print(sels)
            print(sel)
            ctrl_name = sel + "_Ctrl"
            ctrl = cmds.circle(n=ctrl_name)  # create and name nurbs circle
            cmds.select(ctrl[0])  # select it
            cmds.rotate('90deg', 0, 0, r=True)  # fix incorrect rotation
            grp = cmds.group(ctrl[0], n='Grp_Crtl')
            cmds.matchTransform(ctrl[0], sel)  # set control to match transforms of selection

            colorChange(color_ind, ctrl)  # change control's color



