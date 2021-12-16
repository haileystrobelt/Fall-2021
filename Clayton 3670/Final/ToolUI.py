import importlib
import maya.cmds as cmds

class ToolUI():
    def __init__(self):
        self.m_window = 'changeColorUIWin'
        self.name_txtfield = ''
        self.name_txtfieldbtn_grp = ''


    def create(self): # Creates our window
        self.delete()

        self.m_window = cmds.window(self.m_window,
                                    title="My Tools",
                                    widthHeight=(200, 55))

        m_column = cmds.columnLayout(parent=self.m_window,
                                     adjustableColumn=True)

        cmds.button(parent=m_column, label='Create Control', command=lambda *x: self.create_ctrl_btn())

        cmds.button(parent=m_column, label='Create Ball', command='cmds.polySphere()')

        # Text Field Components

        self.name_txtfieldbtn_grp = cmds.textFieldButtonGrp(parent=m_column,
                                                            placeholderText="Leg_##_Jnt",
                                                            label='Name',
                                                            buttonLabel='Rename',
                                                            buttonCommand=lambda *x: self.renamer_btn())


        self.create_color_btns() # Creates color buttons

        cmds.showWindow(self.m_window)


    def delete(self):
        if cmds.window(self.m_window, exists=True):
            cmds.deleteUI(self.m_window)

    def txtfieldbtn_cmd(self):
        import tools
        importlib.reload(tools)
        txt_data = cmds.textFieldButtonGrp(self.name_txtfieldbtn_grp, q=True, text=True)
        tools.SayHello(txt_data)
        return

    def say_hello_cmds(self):
        import tools
        importlib.reload(tools)
        tools.SayHello('George')
        return []

    def color_button_cmd(self, color):
        import tools
        importlib.reload(tools)
        print(color)
        tools.ChangeColor(color)
        return

    def renamer_btn(self):
        import tools
        importlib.reload(tools)
        txt_data = cmds.textFieldButtonGrp(self.name_txtfieldbtn_grp, q=True, text=True)
        tools.Renamer(txt_data)
        return

    def create_ctrl_btn(self):
        import tools
        importlib.reload(tools)
        tools.createControl()

    def create_color_btns(self):
        m_grid = cmds.gridLayout(parent=self.m_window,
                                 columnsResizable=True)

        cmds.button(parent=m_grid, label=str(0), command=lambda *x: self.color_button_cmd(0))
        cmds.button(parent=m_grid, backgroundColor=[0, 0, 0], label=str(1), command=lambda *x: self.color_button_cmd(1))
        cmds.button(parent=m_grid, backgroundColor=[0.25098,  0.25098,  0.25098], label=str(2), command=lambda *x: self.color_button_cmd(2))
        cmds.button(parent=m_grid, backgroundColor=[0.60000,  0.60000,  0.60000], label=str(3), command=lambda *x: self.color_button_cmd(3))
        cmds.button(parent=m_grid, backgroundColor=[0.60784,  0.00000,  0.15686], label=str(4), command=lambda *x: self.color_button_cmd(4))
        cmds.button(parent=m_grid, backgroundColor=[0.00000,  0.01569,  0.37647], label=str(5), command=lambda *x: self.color_button_cmd(5))
        cmds.button(parent=m_grid, backgroundColor=[0, 0, 1], label=str(6), command=lambda *x: self.color_button_cmd(6))
        cmds.button(parent=m_grid, backgroundColor=[0.00000,  0.27451,  0.09804], label=str(7), command=lambda *x: self.color_button_cmd(7))
        cmds.button(parent=m_grid, backgroundColor=[0.14902,  0.00000,  0.26275], label=str(8), command=lambda *x: self.color_button_cmd(8))
        cmds.button(parent=m_grid, backgroundColor=[0.78431,  0.00000,  0.78431], label=str(9), command=lambda *x: self.color_button_cmd(9))
        cmds.button(parent=m_grid, backgroundColor=[0.54118,  0.28235,  0.20000], label=str(10), command=lambda *x: self.color_button_cmd(10))
        cmds.button(parent=m_grid, backgroundColor=[0.24706,  0.13725,  0.12157], label=str(11), command=lambda *x: self.color_button_cmd(11))
        cmds.button(parent=m_grid, backgroundColor=[0.60000,  0.14902,  0], label=str(12), command=lambda *x: self.color_button_cmd(12))
        cmds.button(parent=m_grid, backgroundColor=[1, 0, 0], label=str(13), command=lambda *x: self.color_button_cmd(13))
        cmds.button(parent=m_grid, backgroundColor=[0, 1, 0], label=str(14), command=lambda *x: self.color_button_cmd(14))
        cmds.button(parent=m_grid, backgroundColor=[0.00000,  0.25490,  0.60000], label=str(15), command=lambda *x: self.color_button_cmd(15))
        cmds.button(parent=m_grid, backgroundColor=[1, 1, 1], label=str(16), command=lambda *x: self.color_button_cmd(16))
        cmds.button(parent=m_grid, backgroundColor=[1, 1, 0], label=str(17), command=lambda *x: self.color_button_cmd(17))
        cmds.button(parent=m_grid, backgroundColor=[0.39216,  0.86275,  1.00000], label=str(18), command=lambda *x: self.color_button_cmd(18))
        cmds.button(parent=m_grid, backgroundColor=[0.26275,  1.00000,  0.63922], label=str(19), command=lambda *x: self.color_button_cmd(19))
        cmds.button(parent=m_grid, backgroundColor=[1.00000,  0.69020,  0.69020], label=str(20), command=lambda *x: self.color_button_cmd(20))
        cmds.button(parent=m_grid, backgroundColor=[0.89412,  0.67451,  0.47451], label=str(21), command=lambda *x: self.color_button_cmd(21))
        cmds.button(parent=m_grid, backgroundColor=[1, 1, 0.38824], label=str(22), command=lambda *x: self.color_button_cmd(22))
        cmds.button(parent=m_grid, backgroundColor=[0,  0.60000,  0.32941], label=str(23), command=lambda *x: self.color_button_cmd(23))
        cmds.button(parent=m_grid, backgroundColor=[0.63137,  0.41569,  0.18824], label=str(24), command=lambda *x: self.color_button_cmd(24))
        cmds.button(parent=m_grid, backgroundColor=[0.61961,  0.63137,  0.18824], label=str(25), command=lambda *x: self.color_button_cmd(25))
        cmds.button(parent=m_grid, backgroundColor=[0.40784,  0.63137,  0.18824], label=str(26), command=lambda *x: self.color_button_cmd(26))
        cmds.button(parent=m_grid, backgroundColor=[0.18824,  0.63137,  0.36471], label=str(27), command=lambda *x: self.color_button_cmd(27))
        cmds.button(parent=m_grid, backgroundColor=[0.18824,  0.63137,  0.63137], label=str(28), command=lambda *x: self.color_button_cmd(28))
        cmds.button(parent=m_grid, backgroundColor=[0.18824,  0.40392,  0.63137], label=str(29), command=lambda *x: self.color_button_cmd(29))
        cmds.button(parent=m_grid, backgroundColor=[0.43529,  0.18824,  0.63137], label=str(30), command=lambda *x: self.color_button_cmd(30))
        cmds.button(parent=m_grid, backgroundColor=[0.63137,  0.18824,  0.41569], label=str(31), command=lambda *x: self.color_button_cmd(31))

        return


myUI = ToolUI()
myUI.create()





