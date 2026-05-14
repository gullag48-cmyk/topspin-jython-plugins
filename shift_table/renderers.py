from __future__ import print_function
from javax.swing import BorderFactory, SwingConstants
from javax.swing.table import DefaultTableCellRenderer
from constants import GRID_COLOR, get_pair_background

class ResidueRenderer(DefaultTableCellRenderer):
    def getTableCellRendererComponent(self, table, value, isSelected, hasFocus, row, column):
        if row % 2 == 0:
            comp = super(ResidueRenderer, self).getTableCellRendererComponent(
                table, value, isSelected, hasFocus, row, column)
        else:
            comp = DefaultTableCellRenderer()
            comp = comp.getTableCellRendererComponent(table, "", isSelected, hasFocus, row, column)
            comp.setBorder(BorderFactory.createMatteBorder(0, 0, 1, 0, GRID_COLOR))
        comp.setVerticalAlignment(SwingConstants.CENTER)
        comp.setHorizontalAlignment(SwingConstants.CENTER)
        if not isSelected:
            comp.setBackground(get_pair_background(row))
        return comp

class PairSplitRenderer(DefaultTableCellRenderer):
    def getTableCellRendererComponent(self, table, value, isSelected, hasFocus, row, column):
        comp = super(PairSplitRenderer, self).getTableCellRendererComponent(
            table, value, isSelected, hasFocus, row, column)
        comp.setHorizontalAlignment(SwingConstants.CENTER)
        bottom = 1 if row % 2 == 1 else 0
        comp.setBorder(BorderFactory.createCompoundBorder(
            BorderFactory.createMatteBorder(0, 0, bottom, 0, GRID_COLOR),
            BorderFactory.createEmptyBorder(4, 8, 4, 8)))
        if not isSelected:
            comp.setBackground(get_pair_background(row))
        return comp
