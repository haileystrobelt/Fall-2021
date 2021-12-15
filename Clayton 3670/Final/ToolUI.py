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

        cmds.button(parent=m_column, label='Ball', command='cmds.polySphere()')
        cmds.button(parent=m_column, label='Red Color', command=lambda *x: self.color_button_cmd(13))
        cmds.button(parent=m_column, label='Green Color', command=lambda x: self.color_button_cmd(16))
        cmds.button(parent=m_column, label='Blue Color', command=lambda x: self.color_button_cmd(5))

        # Text Field Components
        self.name_txtfield = cmds.textField(parent=m_column)
        cmds.button(parent=m_column, command=lambda *x: self.say_hello_cmds())

        self.name_txtfieldbtn_grp = cmds.textFieldButtonGrp(parent=m_column,
                                                            label='Name',
                                                            buttonLabel='Say Hello!',
                                                            buttonCommand=lambda *x: self.txtfieldbtn_cmd())

        m_grid = cmds.gridLayout(parent=self.m_window,
                                 columnsResizable=True)
        for i in range(0, 32):
            cmds.button(parent=m_grid, label=str(i), command=lambda *x: self.color_button_cmd(i))


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

myUI = ToolUI()
myUI.create()





