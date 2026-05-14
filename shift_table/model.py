from __future__ import print_function
from javax.swing import JOptionPane
from javax.swing.table import DefaultTableModel

class MergedTableModel(DefaultTableModel):
    def __init__(self, panel, columns, rows):
        super(MergedTableModel, self).__init__(columns, rows)
        self.panel = panel
        self._loading = False

    def set_loading(self, flag):
        self._loading = flag

    def setValueAt(self, value, row, col):
        if row < 0 or row >= self.getRowCount():
            return
        if col > 0 and value is not None and str(value).strip():
            if not self._is_valid_shift(str(value).strip()):
                JOptionPane.showMessageDialog(self.panel,
                    "Invalid shift value: '{}'. Please enter a number.".format(value),
                    "Validation Error", JOptionPane.WARNING_MESSAGE)
                return
        super(MergedTableModel, self).setValueAt(value, row, col)
        if col == 0 and row % 2 == 0 and row + 1 < self.getRowCount():
            super(MergedTableModel, self).setValueAt(value, row + 1, col)
        if not self._loading and not self.panel.loading:
            self.panel.dirty = True

    def _is_valid_shift(self, s):
        try:
            float(s)
            return True
        except ValueError:
            return False

    def add_row_pair(self, res_name, p_vals, c_vals):
        self.addRow([res_name] + list(p_vals))
        self.addRow([''] + list(c_vals))

    def replace_all_data(self, rows_list):
        self.setRowCount(0)
        for res, protons, carbons in rows_list:
            self.addRow([res] + protons)
            self.addRow([''] + carbons)
        if not self._loading:
            self.panel.dirty = False
