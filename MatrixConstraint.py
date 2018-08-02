'''
    File name: customParentConstraint.py
    Author: Wayne Moodie
    Date created: 7/30/2018
    Date last modified: 7/30/2018
    Python Version: 2.7
    Todo List : Ui Build
                add solo axis
'''

from pymel.core import *
from functools import wraps, partial
from MatrixConstraint.Qt import QtWidgets, QtCore, QtGui

def undoFunc(func):
    @wraps(func)
    def funcWrapper(*args, **kwargs):
        undoInfo(openChunk=True, chunkName=func.__name__)
        try:
            result = func(*args, **kwargs)
            undoInfo(closeChunk=True)
            return result
        except:
            undoInfo(closeChunk=True)
            if undoInfo(query=True, undoName=True) == func.__name__:
                undo()
            raise  # this doesn't raise the exception
    return funcWrapper



def lockNull(object):
    '''Clears Null to be used for settings'''

    setAttr(object + '.v', k=False, l=True)

    lockAttr = 'xyz'
    for axis in lockAttr:
        setAttr(object + '.t' + axis, k=False, l=True)
        setAttr(object + '.s' + axis, k=False, l=True)
        setAttr(object + '.r' + axis, k=False, l=True)



@undoFunc
def matrixConstraint(objects = None,  parent=False, point=False, orient=False, scale=False,
                     all=False, x=False, y=False, z=False , maintainOffset = False):
    """
    Creates a matrix based constraint network instead of Maya's default constraint system. Since we are using matrices
    it runs a bit more efficient yielding .0375 fps increase per setup over Maya's constraint setup. results may vary
    This was based on  Vasil Shotarov over at https://bindpose.com/maya-matrix-nodes-blending-matrices/.
    Special thanks to him for sharing the information.

    :param objects: Give a list of objects to constrain. The final object in the list will be constrained to the formers
    :param parent: Mark True for parent style constraint
    :param point: Mark True for point style constraint
    :param orient: Mark True for Orient style constraint
    :param scale: Mark True for scale style constraint
    :param all: Mark True all axes to be constrained
    :param x: Mark True x axis to be constrained
    :param y: Mark True y axis to be constrained
    :param z: Mark True z axis to be constrained
    :param maintainOffset: Mark True to MaintainOffeset
    :param args: Provide selection of only transform nodes. They can be strings or PyNodes
          I.E. matrixConstraint( 'cone1','cube1' parent=False, all =True)
    :return: Constraint settings node
    """
    # uses ls selection ,but will default to objects parameter if the parameter is not none
    myList = ls(sl=True)

    if objects is not None:
        if isinstance(objects, list):
            myList = [PyNode(i) for i in objects]
        else:
            raise ValueError("object parameter needs a LIST of transform nodes.")

    select(d=True)
    # Error handling checks for selection and checks for a axes to constrain
    if len(myList) == 0 or len(myList) == 1:
        raise ValueError("Not enough object given to constrain. Please give driver(s) and driven objects in that order.")

    bool = all, x, y, z

    if True not in bool:
        raise ValueError("No axes given to constrain. Please assign axes to constrain.")

    drivers = myList[:-1]
    driven  = myList[-1]
    weight = 1.0 / len(drivers)

    tempStr = ['parent', 'point', 'orient', 'scale']
    tempBool =[ parent, point, orient, scale]
    attrList = zip(tempBool, tempStr)
    # starts passing our drivers matrices through the wtAddMatrix, MultMatrix, finally to the Decompose Matrix
    for attr in attrList:
        if attr[0]:

            if objExists(driven + '_' + attr[-1] + '_ConstraintSettings'):
                delete(driven + '_' + attr[-1] + '_ConstraintSettings')

            constraintCtrl = group(n=driven + '_' + attr[-1] + '_ConstraintSettings')
            constraintCtrl.setParent(driven)
            lockNull(constraintCtrl)
            select(d=True)

            decomp = createNode('decomposeMatrix', n=driven + '_' + attr[-1] + '_decompMatrix')
            mult = createNode('multMatrix', n=driven + '_' + attr[-1] + '_multMatrix')
            wt = createNode('wtAddMatrix', n=driven + '_' + attr[-1] + '_wtMatrix')

    # Sets up our constraint control under the driven object. It will always share equal influence between all drivers
    # by default.
    for iter, transformNode in enumerate(drivers):

        if maintainOffset:
            offset = driven.getMatrix() *transformNode.getMatrix().inverse()
            offsetMult = createNode('multMatrix', n=transformNode + '_' + driven + '_offsetMultMatrix')
            transformNode.worldMatrix >> offsetMult.matrixIn[0]
            offsetMult.matrixIn[1].set(offset)
            offsetMult.matrixSum >> wt.wtMatrix[iter].matrixIn

        else:
            transformNode.worldMatrix >> wt.wtMatrix[iter].matrixIn

        constraintCtrl.addAttr(transformNode + '_Weight', type='double', k=True, dv=weight)
        connectAttr(constraintCtrl + '.' + transformNode + '_Weight', wt.wtMatrix[iter].weightIn)

    wt.matrixSum >> mult.matrixIn[0]
    mult.matrixSum >> decomp.inputMatrix
    driven.parentInverseMatrix >> mult.matrixIn[1]

    axes      = 'XYZ'
    axesBool  = [x,y,z]
    axesCheck = zip(axesBool, axes)
    # Plugs the constraint into the driven object based on Keyword arguments
    if point:
        if all:
            decomp.outputTranslate >> driven.translate
        else:
            for axis in axesCheck:
                if axis[0]:
                    connectAttr(decomp + '.outputTranslate' + axis[-1], driven+'.translate'+axis[-1])

    if orient:
        if all:
            decomp.outputRotate >> driven.rotate
        else:
            for axis in axesCheck:
                if axis[0]:
                    connectAttr(decomp + '.outputRotate' + axis[-1], driven+'.rotate'+axis[-1])

    if scale:
        if all:
            decomp.outputScale >> driven.scale
        else:
            for axis in axesCheck:
                if axis[0]:
                    connectAttr(decomp + '.outputScale' + axis[-1], driven+'.scale'+axis[-1])

    if parent:
        if all:
            decomp.outputTranslate >> driven.translate
            decomp.outputRotate >> driven.rotate
        else:
            for axis in axesCheck:
                if axis[0]:
                    connectAttr(decomp + '.outputTranslate' + axis[-1], driven+'.translate'+axis[-1])
                    connectAttr(decomp + '.outputRotate' + axis[-1], driven + '.rotate' + axis[-1])

class MatrixConstraintUI(QtWidgets.QDialog):

    parent,point,orient,scale,mo, = False,False,False,False,False
    tx,ty,tz,rx,ry,rz,sx,sy,sz = False,False,False,False,False,False,False,False,False

    def __init__(self):
        super(MatrixConstraintUI, self).__init__()

        self.setWindowTitle('Matrix Constraints')

        self.buildUI()


    def buildUI(self):
        gridAx = QtWidgets.QGridLayout(self)


        maintainOffsetLabel = QtWidgets.QLabel('Maintain Offset:')
        maintainOffsetLabel.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        maintainOffsetBtn = QtWidgets.QCheckBox()
        gridAx.addWidget(maintainOffsetLabel, 0, 0)
        gridAx.addWidget(maintainOffsetBtn, 0, 1)




        matrixLabel = QtWidgets.QLabel('Constraint Axes:')
        matrixLabel.setAlignment(QtCore.Qt.AlignRight| QtCore.Qt.AlignVCenter)
        gridAx.addWidget(matrixLabel, 1, 0)


        parentLabel    = QtWidgets.QLabel('Parent Constraint:')
        parentLabel.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.parentCheck   = QtWidgets.QCheckBox('All')
        gridAx.addWidget(parentLabel, 2, 0)
        gridAx.addWidget(self.parentCheck, 2, 1)

        self.parentCheckX,self.parentCheckY, self.parentCheckZ = QtWidgets.QCheckBox('X'),\
                                                                 QtWidgets.QCheckBox('Y'), QtWidgets.QCheckBox('Z')
        gridAx.addWidget(self.parentCheckX, 3, 1)
        gridAx.addWidget(self.parentCheckY, 3, 2)
        gridAx.addWidget(self.parentCheckZ, 3, 3)
        self.parentCheck.stateChanged.connect(self.parentAll)
        self.parentCheckX.stateChanged.connect(self.parentX)
        self.parentCheckX.stateChanged.connect(self.parentY)
        self.parentCheckX.stateChanged.connect(self.parentZ)


        pointLabel = QtWidgets.QLabel('Point Constraint:')
        pointLabel.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.pointCheck = QtWidgets.QCheckBox('All')
        gridAx.addWidget(pointLabel, 4, 0)
        gridAx.addWidget(self.pointCheck, 4, 1)

        self.pointCheckX, self.pointCheckY, self.pointCheckZ = QtWidgets.QCheckBox('X'), \
                                                               QtWidgets.QCheckBox('Y'), QtWidgets.QCheckBox('Z')
        gridAx.addWidget(self.pointCheckX, 5, 1)
        gridAx.addWidget(self.pointCheckY, 5, 2)
        gridAx.addWidget(self.pointCheckZ, 5, 3)
        self.pointCheck.stateChanged.connect(self.translateAll)
        self.pointCheckX.stateChanged.connect(self.translateX)
        self.pointCheckX.stateChanged.connect(self.translateY)
        self.pointCheckX.stateChanged.connect(self.translateZ)


        orientLabel    = QtWidgets.QLabel('Orient Constraint:')
        orientLabel.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.orientCheck   = QtWidgets.QCheckBox('All')
        gridAx.addWidget(orientLabel, 6, 0)
        gridAx.addWidget(self.orientCheck, 6, 1)

        self.orientCheckX, self.orientCheckY, self.orientCheckZ = QtWidgets.QCheckBox('X'),\
                                                                  QtWidgets.QCheckBox('Y'), QtWidgets.QCheckBox('Z')
        gridAx.addWidget(self.orientCheckX, 7, 1)
        gridAx.addWidget(self.orientCheckY, 7, 2)
        gridAx.addWidget(self.orientCheckZ, 7, 3)
        self.orientCheck.stateChanged.connect(self.rotateAll)
        self.orientCheckX.stateChanged.connect(self.rotateX)
        self.orientCheckX.stateChanged.connect(self.rotateY)
        self.orientCheckX.stateChanged.connect(self.rotateZ)

        scaleLabel     = QtWidgets.QLabel('Scale Constraint:')
        scaleLabel.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.scaleCheck  = QtWidgets.QCheckBox('All')
        gridAx.addWidget(scaleLabel, 8, 0)
        gridAx.addWidget(self.scaleCheck, 8, 1)

        self.scaleCheckX, self.scaleCheckY, self.scaleCheckZ = QtWidgets.QCheckBox('X'),\
                                                               QtWidgets.QCheckBox('Y'), QtWidgets.QCheckBox('Z')

        gridAx.addWidget(self.scaleCheckX, 9, 1)
        gridAx.addWidget(self.scaleCheckY, 9, 2)
        gridAx.addWidget(self.scaleCheckZ, 9, 3)
        self.scaleCheck.stateChanged.connect(self.scaleAll)
        self.scaleCheckX.stateChanged.connect(self.scaleX)
        self.scaleCheckX.stateChanged.connect(self.scaleY)
        self.scaleCheckX.stateChanged.connect(self.scaleZ)

        pointBtn = QtWidgets.QPushButton('Point Matrix')
        parentBtn = QtWidgets.QPushButton('Parent Matrix')
        orientBtn = QtWidgets.QPushButton('Orient Matrix')
        scaleBtn = QtWidgets.QPushButton('Scale Matrix')
        close= QtWidgets.QPushButton("Close")
        gridAx.addWidget(parentBtn, 10, 0)
        gridAx.addWidget(pointBtn, 10, 1)
        gridAx.addWidget(orientBtn, 10, 2)
        gridAx.addWidget(scaleBtn, 10, 3)
        gridAx.addWidget(close, 11, 0,11,4)
        pointBtn.clicked.connect(partial(matrixConstraint,
                                         point=True,
                                         x=MatrixConstraintUI.tx,
                                         y=MatrixConstraintUI.ty,
                                         z=MatrixConstraintUI.tz,
                                         maintainOffset=MatrixConstraintUI.mo))
        parentBtn.clicked.connect(partial(matrixConstraint,
                                         parent=True,
                                         x=MatrixConstraintUI.tx,
                                         y=MatrixConstraintUI.ty,
                                         z=MatrixConstraintUI.tz,
                                         maintainOffset=MatrixConstraintUI.mo))
        orientBtn.clicked.connect(partial(matrixConstraint,
                                          parent=True,
                                          x=MatrixConstraintUI.rx,
                                          y=MatrixConstraintUI.ry,
                                          z=MatrixConstraintUI.rz,
                                          maintainOffset=MatrixConstraintUI.mo))
        scaleBtn.clicked.connect(partial(matrixConstraint,
                                         parent=True,
                                         x=MatrixConstraintUI.sx,
                                         y=MatrixConstraintUI.sy,
                                         z=MatrixConstraintUI.sz,
                                         maintainOffset=MatrixConstraintUI.mo))
        close.clicked.connect(self.close)




    def maintainOffset(self, toggle):
        MatrixConstraintUI.mo = bool(toggle)


    def translateAll(self, toggle):
        self.translateX(toggle)
        self.translateY(toggle)
        self.translateZ(toggle)
        self.pointCheckY.setChecked(False)
        self.pointCheckX.setChecked(False)
        self.pointCheckZ.setChecked(False)

    def translateX(self, toggle):
        MatrixConstraintUI.tx = bool(toggle)
    def translateY(self, toggle):
        MatrixConstraintUI.ty = bool(toggle)
    def translateZ(self, toggle):
        MatrixConstraintUI.tz = bool(toggle)


    def rotateAll(self, toggle):
        self.rotateX(toggle)
        self.rotateY(toggle)
        self.rotateZ(toggle)
        self.orientCheckX.setChecked(False)
        self.orientCheckY.setChecked(False)
        self.orientCheckZ.setChecked(False)

    def rotateX(self, toggle):
        MatrixConstraintUI.rx = bool(toggle)
    def rotateY(self, toggle):
        MatrixConstraintUI.ry = bool(toggle)
    def rotateZ(self, toggle):
        MatrixConstraintUI.rz = bool(toggle)

    def scaleAll(self, toggle):
        self.scaleX(toggle)
        self.scaleY(toggle)
        self.scaleZ(toggle)
        self.scaleCheckX.setChecked(False)
        self.scaleCheckY.setChecked(False)
        self.scaleCheckZ.setChecked(False)

    def scaleX(self, toggle):
        MatrixConstraintUI.sx = bool(toggle)
    def scaleY(self, toggle):
        MatrixConstraintUI.sy = bool(toggle)
    def scaleZ(self, toggle):
        MatrixConstraintUI.sz = bool(toggle)
        

    def parentAll(self, toggle):
        self.parentX(toggle)
        self.parentY(toggle)
        self.parentZ(toggle)
        self.parentCheckX.setChecked(False)
        self.parentCheckY.setChecked(False)
        self.parentCheckZ.setChecked(False)

    def parentX(self, toggle):
        self.translateX(toggle)
        self.rotateX(toggle)
    def parentY(self, toggle):
        self.translateY(toggle)
        self.rotateY(toggle)
    def parentZ(self, toggle):
        self.translateZ(toggle)
        self.rotateZ(toggle)




def showUI():
    ui = MatrixConstraintUI()
    if ui:
        ui.close()
        ui.show()
    else:
        ui.show()
    return ui





if __name__ == "__main__":
    ui = showUI()
    #matrixConstraint(parent=True, all=True, maintainOffset=True)
