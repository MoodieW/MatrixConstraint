'''
    File name: customParentConstraint.py
    Author: Wayne Moodie
    Date created: 7/30/2018
    Date last modified: 4/22/20
    Python Version: 2.7
    Todo List : Figure out adding in new drivers
                Ui Build
'''

from pymel.core import *


def lockNull(object):
    '''Clears Null to be used for settings'''

    setAttr(object + '.v', k=False, l=True)

    lockAttr = 'xyz'
    for axis in lockAttr:
        setAttr(object + '.t' + axis, k=False, l=True)
        setAttr(object + '.s' + axis, k=False, l=True)
        setAttr(object + '.r' + axis, k=False, l=True)


def matrixConstarint(parent=False, point=False, orient=False, scale=False,
                     all=False, x=False, y=False, z=False):
    my_list = ls(sl=True)
    select(d=True)

    if len(my_list) == 0:
        raise ValueError("No object given to constrain. Please give driver(s) and driven objects in that order.")

    weight = 1.0 / len(my_list[:-1])

    tempStr = 'parent', 'point', 'orient', 'scale'
    tempBool = parent, point, orient, scale
    list = zip(tempBool, tempStr)

    for attr in list:
        if attr[0]:

            if objExists(my_list[-1] + '_' + attr[-1] + '_ConstraintSettings'):
                delete(my_list[-1] + '_' + attr[-1] + '_ConstraintSettings')

            constraintCtrl = group(n=my_list[-1] + '_' + attr[-1] + '_ConstraintSettings')
            constraintCtrl.setParent(my_list[-1])
            lockNull(constraintCtrl)
            select(d=True)

            decomp = createNode('decomposeMatrix', n=my_list[-1] + '_' + attr[-1] + '_decompMatrix')
            mult = createNode('multMatrix', n=my_list[-1] + '_' + attr[-1] + '_multMatrix')
            wt = createNode('wtAddMatrix', n=my_list[-1] + '_' + attr[-1] + '_wtMatrix')

    for iter, transformNode in enumerate(my_list[:-1]):
        transformNode.worldMatrix >> wt.wtMatrix[iter].matrixIn
        constraintCtrl.addAttr(transformNode + '_Weight', type='double', k=True, dv=weight)
        connectAttr(constraintCtrl + '.' + transformNode + '_Weight', wt.wtMatrix[iter].weightIn)

    wt.matrixSum >> mult.matrixIn[0]
    mult.matrixSum >> decomp.inputMatrix
    my_list[-1].parentInverseMatrix >> mult.matrixIn[1]

    if point:
        decomp.outputTranslate >> my_list[-1].translate
    if orient:
        decomp.outputTranslate >> my_list[-1].rotate
    if orient:
        decomp.outputTranslate >> my_list[-1].scale
    if parent:
        decomp.outputTranslate >> my_list[-1].translate
        decomp.outputTranslate >> my_list[-1].rotate


# Translate picker
point = False
tx, ty, tz = False, False, False
transList = tx, ty, tz

# Scale section      
axisSel = 0
for axis in scaleList:
    if axis == True:
        connectAttr(decompose + '.outputScale' + axisList[axisSel], driven + '.scale' + axisList[axisSel])
        axisSel += 1
