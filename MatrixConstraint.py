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
from functools import wraps
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
def matrixConstraint(parent=False, point=False, orient=False, scale=False,
                     all=False, x=False, y=False, z=False , maintainOffset = False):
    """
    Creates a matrix based constraint network instead of Maya's default constraint system. Since we are using matrices
    it runs a bit more efficient yielding .0375 fps increase per setup over Maya's constraint setup. results may vary
    This was based on  Vasil Shotarov over at https://bindpose.com/maya-matrix-nodes-blending-matrices/.
    Special thanks to him for sharing the information.

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
    my_list = ls(sl=True)
    select(d=True)
    # Error handling checks for selection and checks for a axes to constrain
    if len(my_list) == 0 or len(my_list) == 1:
        raise ValueError("Not enough object given to constrain. Please give driver(s) and driven objects in that order.")

    bool = all, x, y, z

    if True not in bool:
        raise ValueError("No axes given to constrain. Please assign axes to constrain.")

    drivers = my_list[:-1]
    driven  = my_list[-1]
    weight = 1.0 / len(drivers)

    tempStr = ['parent', 'point', 'orient', 'scale']
    tempBool =[ parent, point, orient, scale]
    list = zip(tempBool, tempStr)
    # starts passing our drivers matrices through the wtAddMatrix, MultMatrix, finally to the Decompose Matrix
    for attr in list:
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

#from PyQt5 import QtWidgets, QtCore, QtGui
class MatrixConstraintUI(QtWidgets.QDialog):

    def __init__(self):
        super(MatrixConstraintUI, self).__init__()

        self.setWindowTitle('Matrix Constraints')

        self.buildUI()
        self.populateUI()

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


        pointLabel     = QtWidgets.QLabel('Point Constraint:')
        pointLabel.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        pointConBtn    = QtWidgets.QCheckBox('All')
        gridAx.addWidget(pointLabel, 2, 0)
        gridAx.addWidget(pointConBtn, 2, 1)

        pointX,pointY,pointZ = QtWidgets.QCheckBox('X'),QtWidgets.QCheckBox('Y'),QtWidgets.QCheckBox('Z')
        gridAx.addWidget(pointX, 3, 1)
        gridAx.addWidget(pointY, 3, 2)
        gridAx.addWidget(pointZ, 3, 3)



        parentLabel    = QtWidgets.QLabel('Parent Constraint:')
        parentLabel.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        parentConBtn   = QtWidgets.QCheckBox('All')
        gridAx.addWidget(parentLabel, 4, 0)
        gridAx.addWidget(parentConBtn, 4, 1)

        parentX, parentY, parentZ = QtWidgets.QCheckBox('X'), QtWidgets.QCheckBox('Y'), QtWidgets.QCheckBox('Z')
        gridAx.addWidget(parentX, 5, 1)
        gridAx.addWidget(parentY, 5, 2)
        gridAx.addWidget(parentZ, 5, 3)

        orientLabel    = QtWidgets.QLabel('Orient Constraint:')
        orientLabel.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        orientConBtn   = QtWidgets.QCheckBox('All')
        gridAx.addWidget(orientLabel, 6, 0)
        gridAx.addWidget(orientConBtn, 6, 1)

        orientX, orientY, orientZ = QtWidgets.QCheckBox('X'), QtWidgets.QCheckBox('Y'), QtWidgets.QCheckBox('Z')
        gridAx.addWidget(orientX, 7, 1)
        gridAx.addWidget(orientY, 7, 2)
        gridAx.addWidget(orientZ, 7, 3)

        scaleLabel     = QtWidgets.QLabel('Scale Constraint:')
        scaleLabel.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        scaleConBtn    = QtWidgets.QCheckBox('All')
        gridAx.addWidget(scaleLabel, 8, 0)
        gridAx.addWidget(scaleConBtn, 8, 1)

        scaleX, scaleY, scaleZ = QtWidgets.QCheckBox('X'), QtWidgets.QCheckBox('Y'), QtWidgets.QCheckBox('Z')
        gridAx.addWidget(scaleX, 9, 1)
        gridAx.addWidget(scaleY, 9, 2)
        gridAx.addWidget(scaleZ, 9, 3)



    def populateUI(self):
        print
        'populating it '


def showUI():
    ui = MatrixConstraintUI()
    ui.show()
    return ui





if __name__ == "__main__":
    ui = showUI()
    #matrixConstraint(parent=True, all=True)
