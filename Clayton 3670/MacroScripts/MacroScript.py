import maya.cmds as cmds

# Sphere Bottom
cmds.polySphere(r=3, sx=20, sy=20, cuv=2, ch=1, n="bot_sphere")
cmds.move(0, 3, 0)

# Sphere Middle
cmds.polySphere(r=2, sx=20, sy=20, cuv=2, ch=1, n="mid_sphere")
cmds.move(0, 7, 0)

# Sphere Top
cmds.polySphere(r=1.5, sx=20, sy=20, cuv=2, ch=1, n="top_sphere")
cmds.move(0, 9.7, 0)

# Left Eye
cmds.polySphere(r=1, sx=20, sy=20, cuv=2, ch=1, n="left_eye")
cmds.scale(0.23, 0.23, 0.23)
cmds.move(1.4, 9.8, -0.5)

# Right Eye
cmds.duplicate('left_eye', n="right_eye")
cmds.select('right_eye')
cmds.move(1.4, 9.8, 0.5)

# Hat
cmds.polyCylinder(r=1.1, sx=20, sy=1, cuv=3, ch=1, n="hat")
cmds.move(0, 11.7, 0)


# Bottom Hat
cmds.duplicate('hat', n="bot_hat")
cmds.select('bot_hat')
cmds.move(0, 10.5, 0)
cmds.scale(1.72, 0.22, 1.72)

# Button Top
cmds.polyCylinder(r=1, sx=20, sy=1, cuv=3, ch=1, n="but_top")
cmds.rotate(0, 0, '110deg', 'but_top')
cmds.scale(0.2, 0.2, 0.2)
cmds.move(1.7, 7.9, 0)

# Button Bottom
cmds.duplicate('but_top', n="but_bot")
cmds.select('but_bot')
cmds.move(1.9, 7, 0)
cmds.rotate(0, 0, '90deg', 'but_bot')

# Button Middle
cmds.duplicate('but_bot', n="but_mid")
cmds.select('but_mid')
cmds.move(1.7, 6.1, 0)
cmds.rotate(0, 0, '70deg', 'but_mid')

# Nose
cmds.polyCone(r=1, sx=20, sy=1, cuv=3, ch=1, n="nose")
cmds.rotate(0, 0, '-90deg', 'nose')
cmds.scale(0.3, 0.5, 0.3, 'nose')
cmds.move(1.9, 9.4, 0)

# Left Arm
cmds.polyCylinder(r=1, sx=20, sy=1, cuv=3, ch=1, n="left_arm")
cmds.move(0, 7.3, -3)
cmds.rotate('-85deg', 0, 0, "left_arm")
cmds.scale(0.17, 1.4, 0.17)

# Left Bottom Finger
cmds.duplicate('left_arm', n="left_bot_fin")
cmds.select('left_bot_fin')
cmds.move(0, 7.21, -4.54)
cmds.scale(0.07, 0.58, 0.07)
cmds.rotate('-108deg', 0, 0, 'left_bot_fin')

# Left Top Finger
cmds.duplicate('left_bot_fin', n="left_top_fin")
cmds.select('left_top_fin')
cmds.move(0, 7.54, -4.58)
cmds.scale(0.07, 0.58, 0.07)
cmds.rotate('-70deg', 0, 0, 'left_top_fin')

# Mirror Left Arm
cmds.polyMirrorFace('left_arm', axis=2, axisDirection=0, n='right_arm')
cmds.polyMirrorFace('left_bot_fin', axis=2, axisDirection=0, n='right_bot_fin')
cmds.polyMirrorFace('left_top_fin', axis=2, axisDirection=0, n='right_top_fin')

# Ground Plane
cmds.polyCube(sx=10, sy=1, cuv=3, ch=1, n="ground")
cmds.scale(30, 1, 30)
