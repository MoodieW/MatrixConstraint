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
if __name__ == "__main__":

    matrixConstraint(orient=True, all=True, maintainOffset = True)
