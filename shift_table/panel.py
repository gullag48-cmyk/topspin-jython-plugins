# -*- coding: utf-8 -*-
from __future__ import print_function
from javax.swing import (
    JScrollPane, JTable, JButton, JPanel, JOptionPane, JTabbedPane,
    JLabel, SwingConstants, BorderFactory, SwingUtilities,
    JFrame, JDialog, JList, JCheckBox, ListSelectionModel, JTextField,
    JFileChooser, JSplitPane, JDesktopPane, Timer
)
from javax.swing.table import DefaultTableModel, DefaultTableCellRenderer, TableRowSorter
from java.awt import (
    BorderLayout, FlowLayout, Toolkit, Dimension, Color, Font,
    Insets, Window, Frame, Container, Point
)
from java.awt.datatransfer import StringSelection
from java.awt.event import WindowAdapter, WindowEvent
from java.io import File
import xml.etree.ElementTree as ET
import os
import csv
from java.awt import Dimension as _Dimension

from constants import COLUMNS, get_pair_background
from layout import WrapLayout
from utils import _safe_str, smart_split_static, find_parent_container, detect_active_sample_path, _sample_path_from_title
from model import MergedTableModel
from renderers import ResidueRenderer, PairSplitRenderer
from xml_handler import ShiftXMLHandler


class ShiftTablePanel(JPanel):
    def __init__(self):
        super(ShiftTablePanel, self).__init__(BorderLayout())
        self.target_sample_path = None
        self.target_expno = None
        self.target_nucleus = None
        self.dirty = False
        self.loading = False
        self.pick_window = None
        self.parent_container = None
        self._active_dataset_path = None

        # --- Верхняя панель: Sample + Browse + Close ---
        top_panel = JPanel(BorderLayout(5, 5))
        top_panel.setBorder(BorderFactory.createEmptyBorder(5, 5, 5, 5))

        left_panel = JPanel(FlowLayout(FlowLayout.LEFT, 5, 0))
        left_panel.add(JLabel("Sample:"))
        self.sample_label = JTextField(12)
        self.sample_label.setEditable(False)
        self.sample_label.setFont(Font("SansSerif", Font.BOLD, 12))
        left_panel.add(self.sample_label)
        top_panel.add(left_panel, BorderLayout.WEST)

        right_panel = JPanel(FlowLayout(FlowLayout.RIGHT, 5, 0))
        refresh_btn = JButton("Refresh", actionPerformed=self.refresh_dataset)
        right_panel.add(refresh_btn)
        close_btn = JButton("Close Panel", actionPerformed=self.close_panel)
        right_panel.add(close_btn)
        top_panel.add(right_panel, BorderLayout.EAST)

        self.add(top_panel, BorderLayout.NORTH)

        # --- Таблица ---
        self.table_model = MergedTableModel(self, COLUMNS, 0)
        self.table = JTable(self.table_model)
        self.table.setRowHeight(25)
        self.table.setShowGrid(False)
        self.table.setIntercellSpacing(_Dimension(0, 0))
        self.table.getColumnModel().getColumn(0).setCellRenderer(ResidueRenderer())
        for col in range(1, len(COLUMNS)):
            self.table.getColumnModel().getColumn(col).setCellRenderer(PairSplitRenderer())
        header = self.table.getTableHeader()
        header.setPreferredSize(_Dimension(header.getPreferredSize().width, 30))
        scroll = JScrollPane(self.table)
        self.add(scroll, BorderLayout.CENTER)

        # --- Нижняя панель кнопок ---
        btn_panel = JPanel(WrapLayout(FlowLayout.LEFT, 5, 5))
        load_btn = JButton("Load Shifts", actionPerformed=self.load_shifts)
        save_btn = JButton("Save Shifts", actionPerformed=self.save_shifts)
        annot_btn = JButton("Annotate Peaks", actionPerformed=self.annotate_peaks)
        add_btn = JButton("Add Residue", actionPerformed=self.add_residue)
        copy_btn = JButton("Copy All", actionPerformed=self.copy_to_clipboard)
        clear_btn = JButton("Clear All", actionPerformed=self.clear_all)
        remove_btn = JButton("Remove Selected", actionPerformed=self.remove_selected_rows)
        move_up_btn = JButton("Move Up", actionPerformed=self.move_selected_up)
        move_down_btn = JButton("Move Down", actionPerformed=self.move_selected_down)
        csv_export_btn = JButton("Export CSV", actionPerformed=self.export_csv)

        btn_panel.add(load_btn)
        btn_panel.add(save_btn)
        btn_panel.add(annot_btn)
        btn_panel.add(add_btn)
        btn_panel.add(copy_btn)
        btn_panel.add(clear_btn)
        btn_panel.add(remove_btn)
        btn_panel.add(move_up_btn)
        btn_panel.add(move_down_btn)
        btn_panel.add(csv_export_btn)
        self.add(btn_panel, BorderLayout.SOUTH)

        # --- Таймер отслеживания активного датасета ---
        self._dataset_timer = Timer(3000, self._check_dataset_change)
        self._dataset_timer.setRepeats(True)
        self._dataset_timer.start()

    # ---------- Таймер ----------
    def _check_dataset_change(self, event):
        new_path = detect_active_sample_path()
        if new_path and new_path != self._active_dataset_path:
            self._active_dataset_path = new_path
            if self.dirty and self.target_sample_path:
                ans = JOptionPane.showConfirmDialog(self,
                    "Save changes before switching to {}?".format(os.path.basename(new_path)),
                    "Dataset Changed", JOptionPane.YES_NO_OPTION)
                if ans == JOptionPane.YES_OPTION:
                    ShiftXMLHandler.save(self.target_sample_path, self.table_model)
            self.set_sample_path(new_path)

    # ---------- Закрытие панели ----------
    def close_panel(self, event):
        self._dataset_timer.stop()
        if self.dirty:
            ans = JOptionPane.showConfirmDialog(self,
                "Save changes before closing the panel?",
                "Unsaved Changes", JOptionPane.YES_NO_CANCEL_OPTION)
            if ans == JOptionPane.CANCEL_OPTION:
                self._dataset_timer.start()
                return
            if ans == JOptionPane.YES_OPTION and self.target_sample_path:
                ShiftXMLHandler.save(self.target_sample_path, self.table_model)
        if self.parent_container:
            self.parent_container.remove(self)
            self.parent_container.revalidate()
            self.parent_container.repaint()
            self.parent_container = None

    # ---------- Выбор образца ----------
    def browse_sample(self, event):
        if self.dirty and self.target_sample_path:
            ans = JOptionPane.showConfirmDialog(self,
                "Save changes to {} before switching?".format(os.path.basename(self.target_sample_path)),
                "Unsaved Changes", JOptionPane.YES_NO_CANCEL_OPTION)
            if ans == JOptionPane.CANCEL_OPTION:
                return
            if ans == JOptionPane.YES_OPTION:
                ShiftXMLHandler.save(self.target_sample_path, self.table_model)
                self.dirty = False
        chooser = JFileChooser()
        chooser.setDialogTitle("Select Sample Directory")
        chooser.setFileSelectionMode(JFileChooser.DIRECTORIES_ONLY)
        if self.target_sample_path:
            chooser.setCurrentDirectory(File(self.target_sample_path))
        ret = chooser.showOpenDialog(self)
        if ret == JFileChooser.APPROVE_OPTION:
            new_path = chooser.getSelectedFile().getAbsolutePath()
            self.set_sample_path(new_path)

    def set_sample_path(self, path):
        self.target_sample_path = path
        self.sample_label.setText(os.path.basename(path) if path else "")
        if path:
            self.load_shifts_from_path(path)
        else:
            self.table_model.setRowCount(0)
            self.dirty = False

    def load_shifts_from_path(self, path):
        self.loading = True
        success = ShiftXMLHandler.load(path, self.table_model)
        self.loading = False
        if not success:
            self.table_model.setRowCount(0)
        self.dirty = False

    def load_shifts(self, event):
        if self.target_sample_path:
            if self.dirty:
                ans = JOptionPane.showConfirmDialog(self,
                    "Discard unsaved changes and reload from file?",
                    "Reload", JOptionPane.YES_NO_OPTION)
                if ans != JOptionPane.YES_OPTION:
                    return
            self.load_shifts_from_path(self.target_sample_path)
            JOptionPane.showMessageDialog(self, "Shifts reloaded.")
        else:
            JOptionPane.showMessageDialog(self, "No sample selected.", "Info", JOptionPane.INFORMATION_MESSAGE)

    def save_shifts(self, event):
        if self.target_sample_path:
            if ShiftXMLHandler.save(self.target_sample_path, self.table_model):
                self.dirty = False
                JOptionPane.showMessageDialog(self, "Saved.")
            else:
                JOptionPane.showMessageDialog(self, "Save failed!", "Error", JOptionPane.ERROR_MESSAGE)
        else:
            JOptionPane.showMessageDialog(self, "No sample selected.", "Info", JOptionPane.INFORMATION_MESSAGE)

    # ---------- Обновление из заголовка окна ----------
    def refresh_dataset(self, event):
        from java.awt import Window, Frame
        from javax.swing import JDesktopPane, JInternalFrame
        dataset_path = None
        for w in Window.getWindows():
            if isinstance(w, Frame) and w.getTitle() and 'topspin' in w.getTitle().lower():
                def _find_frame(comp):
                    if isinstance(comp, JDesktopPane):
                        for f in comp.getAllFrames():
                            if f.isVisible() and f.getTitle():
                                return f
                    if hasattr(comp, 'getComponents'):
                        for c in comp.getComponents():
                            res = _find_frame(c)
                            if res:
                                return res
                    return None
                frame = _find_frame(w)
                if frame:
                    title = frame.getTitle()
                    parts = title.split('"')
                    if len(parts) >= 3:
                        sample_name = parts[1]
                        rest = parts[2].strip().split(None, 2)
                        if len(rest) >= 3:
                            sample_path = os.path.join(rest[2], sample_name)
                            if os.path.isdir(sample_path):
                                dataset_path = os.path.abspath(sample_path)
                break
        if dataset_path and dataset_path != self.target_sample_path:
            if self.dirty:
                ans = JOptionPane.showConfirmDialog(self,
                    "Save changes before switching to {}?".format(os.path.basename(dataset_path)),
                    "Unsaved Changes", JOptionPane.YES_NO_OPTION)
                if ans == JOptionPane.YES_OPTION:
                    ShiftXMLHandler.save(self.target_sample_path, self.table_model)
            self._active_dataset_path = dataset_path
            self.set_sample_path(dataset_path)
        elif not dataset_path:
            JOptionPane.showMessageDialog(self,
                "Could not detect current dataset window title.",
                "Refresh", JOptionPane.WARNING_MESSAGE)

    # ---------- Удаление строк ----------
    def remove_selected_rows(self, event):
        rows = self.table.getSelectedRows()
        if not rows:
            JOptionPane.showMessageDialog(self, "Please select at least one row to remove.")
            return
        pair_indices = set()
        for r in rows:
            pair_start = r if r % 2 == 0 else r - 1
            if pair_start >= 0:
                pair_indices.add(pair_start // 2)
        for pair_idx in sorted(pair_indices, reverse=True):
            start_row = pair_idx * 2
            self.table_model.removeRow(start_row)
            self.table_model.removeRow(start_row)
        self.dirty = True
        self.table.clearSelection()

    # ---------- Аннотирование пиков ----------
    def annotate_peaks(self, event):
        if not self.target_sample_path:
            JOptionPane.showMessageDialog(self, "Please select a sample folder first.", "No sample", JOptionPane.ERROR_MESSAGE)
            return
        exp_info = self.select_experiment_dialog()
        if exp_info is None:
            return
        expno, nucleus = exp_info
        self.target_expno = expno
        self.target_nucleus = nucleus
        self.open_pick_window()

    def select_experiment_dialog(self):
        if not self.target_sample_path:
            return None
        experiments = []
        try:
            for entry in os.listdir(self.target_sample_path):
                full = os.path.join(self.target_sample_path, entry)
                if os.path.isdir(full) and entry.isdigit():
                    acqu_file = os.path.join(full, 'acqu')
                    if os.path.exists(acqu_file):
                        nuc = self._read_nucleus_from_acqu(acqu_file)
                        if nuc:
                            experiments.append((entry, nuc))
        except Exception as e:
            JOptionPane.showMessageDialog(self, "Error scanning experiments:\n{}".format(e), "Error", JOptionPane.ERROR_MESSAGE)
            return None
        if not experiments:
            JOptionPane.showMessageDialog(self, "No valid experiments found in sample folder.", "Info", JOptionPane.INFORMATION_MESSAGE)
            return None
        dialog = JDialog(SwingUtilities.getWindowAncestor(self), "Select Experiment", True)
        dialog.setSize(300, 200)
        dialog.setLocationRelativeTo(self)
        panel = JPanel(BorderLayout(10, 10))
        list_data = ["Exp {} ({})".format(exp, nuc) for exp, nuc in experiments]
        list_widget = JList(list_data)
        list_widget.setSelectionMode(ListSelectionModel.SINGLE_SELECTION)
        panel.add(JScrollPane(list_widget), BorderLayout.CENTER)
        btn_panel = JPanel(FlowLayout(FlowLayout.RIGHT))
        ok_btn = JButton("OK")
        cancel_btn = JButton("Cancel")
        btn_panel.add(ok_btn)
        btn_panel.add(cancel_btn)
        panel.add(btn_panel, BorderLayout.SOUTH)
        dialog.add(panel)
        result = []
        def on_ok(e):
            idx = list_widget.getSelectedIndex()
            if idx >= 0:
                result.append(experiments[idx])
                dialog.dispose()
            else:
                JOptionPane.showMessageDialog(dialog, "Please select an experiment.")
        ok_btn.addActionListener(on_ok)
        cancel_btn.addActionListener(lambda e: dialog.dispose())
        dialog.setVisible(True)
        if result:
            return result[0]
        return None

    def _read_nucleus_from_acqu(self, acqu_path):
        try:
            with open(acqu_path, 'r') as f:
                for line in f:
                    if line.startswith('##$NUC1='):
                        nuc = line.split('=')[1].strip().strip('<>')
                        return nuc
        except:
            pass
        return None

    # ---------- Окно выбора пиков ----------
    def open_pick_window(self):
        if self.pick_window is not None and self.pick_window.isDisplayable():
            self.pick_window.toFront()
            return
        title = "Pick Shifts - " + os.path.basename(self.target_sample_path)
        if self.target_expno:
            title += " (Exp {})".format(self.target_expno)
        frame = JFrame(title)
        frame.setSize(700, 400)
        frame.setDefaultCloseOperation(JFrame.DISPOSE_ON_CLOSE)

        nuc = self.target_nucleus
        is_proton = nuc.startswith("1H") if nuc else False
        print("DEBUG: nuc={} is_proton={}".format(nuc, is_proton))
        full_model = self.table_model
        pick_model = DefaultTableModel(COLUMNS, 0)

        total_rows = full_model.getRowCount()
        for r in range(total_rows):
            if (is_proton and r % 2 == 0) or (not is_proton and r % 2 == 1):
                if is_proton:
                    residue = _safe_str(full_model.getValueAt(r, 0))
                else:
                    residue = _safe_str(full_model.getValueAt(r - 1, 0)) if r - 1 >= 0 else ""
                shift_vals = [full_model.getValueAt(r, c) for c in range(1, len(COLUMNS))]
                row_data = [residue] + shift_vals
                pick_model.addRow(row_data)

        print("DEBUG: Main model rows:", full_model.getRowCount())
        for rm in range(full_model.getRowCount()):
            print("DEBUG: Main model row {}: {}".format(rm, [full_model.getValueAt(rm, c) for c in range(len(COLUMNS))]))
        print("DEBUG: Pick model rows:", pick_model.getRowCount())
        if pick_model.getRowCount() > 0:
            print("DEBUG: first row of pick model:", [pick_model.getValueAt(0, c) for c in range(len(COLUMNS))])

        pick_table = JTable(pick_model)
        pick_table.setRowHeight(25)
        pick_table.setShowGrid(False)
        pick_table.setIntercellSpacing(_Dimension(0, 0))
        pick_table.getColumnModel().getColumn(0).setCellRenderer(ResidueRenderer())
        for col in range(1, len(COLUMNS)):
            pick_table.getColumnModel().getColumn(col).setCellRenderer(PairSplitRenderer())
        header = pick_table.getTableHeader()
        header.setPreferredSize(_Dimension(header.getPreferredSize().width, 30))

        pick_table.setCellSelectionEnabled(True)
        pick_table.setRowSelectionAllowed(True)
        pick_table.setColumnSelectionAllowed(True)

        scroll = JScrollPane(pick_table)
        frame.add(scroll, BorderLayout.CENTER)

        btn_panel = JPanel(FlowLayout(FlowLayout.RIGHT))
        apply_btn = JButton("Apply Annotations", actionPerformed=lambda e: self.apply_annotations(pick_table))
        close_btn = JButton("Close", actionPerformed=lambda e: frame.dispose())
        btn_panel.add(apply_btn)
        btn_panel.add(close_btn)
        frame.add(btn_panel, BorderLayout.SOUTH)

        class PickWindowCloser(WindowAdapter):
            def windowClosed(self, e):
                self.panel._on_pick_window_closed()
        closer = PickWindowCloser()
        closer.panel = self
        frame.addWindowListener(closer)
        frame.setVisible(True)
        self.pick_window = frame

    def _on_pick_window_closed(self):
        self.pick_window = None

    def apply_annotations(self, pick_table):
        if not self.target_sample_path or not self.target_expno:
            JOptionPane.showMessageDialog(self.pick_window if self.pick_window else self,
                "No experiment selected. Use 'Annotate Peaks' first.")
            return
        nuc = self.target_nucleus
        is_proton = nuc.startswith("1H") if nuc else False
        pick_model = pick_table.getModel()

        sel_rows = pick_table.getSelectedRows()
        sel_cols = pick_table.getSelectedColumns()
        print("DEBUG: selected rows (view):", sel_rows)
        print("DEBUG: selected cols (view):", sel_cols)

        if not sel_rows or not sel_cols:
            JOptionPane.showMessageDialog(self.pick_window if self.pick_window else self,
                "Please select at least one cell in the Pick table.",
                "No selection", JOptionPane.INFORMATION_MESSAGE)
            return

        annotations = []
        for pick_row in sel_rows:
            residue = _safe_str(pick_model.getValueAt(pick_row, 0)).strip()
            if not residue:
                print("DEBUG:   residue empty, skipping row", pick_row)
                continue
            for pick_col in sel_cols:
                col = pick_col
                if col == 0:
                    print("DEBUG:   col=0 (Residue), skipping")
                    continue
                shift_str = _safe_str(pick_model.getValueAt(pick_row, col)).strip()
                print("DEBUG:   cell row={} col={} -> raw='{}' residue='{}'".format(
                    pick_row, col, shift_str, residue))
                if not shift_str:
                    continue
                try:
                    shift_val = float(shift_str)
                except ValueError:
                    print("DEBUG:   not a float, skipping")
                    continue
                atom = "H" if is_proton else "C"
                label = "{} {}{}".format(residue, atom, col)
                annotations.append((shift_val, label))

        print("DEBUG: annotations:", annotations)

        if not annotations:
            JOptionPane.showMessageDialog(self.pick_window if self.pick_window else self,
                "No valid shifts found in selected cells.",
                "Nothing to annotate", JOptionPane.INFORMATION_MESSAGE)
            return

        exp_dir = os.path.join(self.target_sample_path, self.target_expno)
        peaklist_path = os.path.join(exp_dir, "pdata", "1", "peaklist.xml")
        pdata_dir = os.path.dirname(peaklist_path)
        if not os.path.exists(pdata_dir):
            os.makedirs(pdata_dir)

        try:
            from datetime import datetime
            existing_peaks = {}
            if os.path.exists(peaklist_path):
                tree = ET.parse(peaklist_path)
                root = tree.getroot()
                for pl1d in root.findall("PeakList1D"):
                    for peak in pl1d.findall("Peak1D"):
                        f1 = peak.get("F1")
                        if f1:
                            try:
                                key = round(float(f1), 4)
                                existing_peaks[key] = (peak, pl1d)
                            except:
                                pass
            else:
                root = ET.Element("PeakList", modified=datetime.now().strftime('%Y-%m-%dT%H:%M:%S'))
                tree = ET.ElementTree(root)

            added = 0
            now_iso = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
            for shift, label in annotations:
                key = round(shift, 4)
                if key in existing_peaks:
                    peak_elem, _ = existing_peaks[key]
                    old_ann = peak_elem.get("annotation", "")
                    if not old_ann.strip():
                        peak_elem.set("annotation", label)
                        added += 1
                else:
                    single_pl1d = ET.SubElement(root, "PeakList1D")
                    header = ET.SubElement(single_pl1d, "PeakList1DHeader")
                    header.set("creator", "ShiftTable Annotator")
                    header.set("date", now_iso)
                    header.set("expNo", self.target_expno)
                    header.set("name", "annotated")
                    header.set("owner", "user")
                    header.set("procNo", "1")
                    header.set("source", "")
                    ET.SubElement(header, "PeakPickDetails").text = "Manually added via script"

                    peak_elem = ET.SubElement(single_pl1d, "Peak1D")
                    peak_elem.set("F1", "{:.6f}".format(shift))
                    peak_elem.set("annotation", label)
                    peak_elem.set("intensity", "0.0")
                    peak_elem.set("type", "1")
                    existing_peaks[key] = (peak_elem, single_pl1d)
                    added += 1

            if added == 0:
                JOptionPane.showMessageDialog(self.pick_window if self.pick_window else self,
                    "All selected peaks already exist and are annotated.", "Info", JOptionPane.INFORMATION_MESSAGE)
                return

            tree.write(peaklist_path, encoding="UTF-8", xml_declaration=True)
            JOptionPane.showMessageDialog(self.pick_window if self.pick_window else self,
                "{} peak(s) annotated successfully.".format(added), "Done", JOptionPane.INFORMATION_MESSAGE)
        except Exception as e:
            JOptionPane.showMessageDialog(self.pick_window if self.pick_window else self,
                "Failed to update peaklist.xml:\n{}".format(e), "Error", JOptionPane.ERROR_MESSAGE)

    # ---------- Редактирование таблицы ----------
    def add_residue(self, event):
        self.table_model.add_row_pair("", ['']*6, ['']*6)
        self.dirty = True

    def clear_all(self, event):
        self.table_model.setRowCount(0)
        self.dirty = True

    def copy_to_clipboard(self, event):
        sb = []
        for r in range(self.table_model.getRowCount()):
            row = [str(self.table_model.getValueAt(r, c) or "") for c in range(len(COLUMNS))]
            sb.append("\t".join(row))
        clipboard = Toolkit.getDefaultToolkit().getSystemClipboard()
        clipboard.setContents(StringSelection("\n".join(sb)), None)
        JOptionPane.showMessageDialog(self, "Copied to clipboard.")

    def move_selected_up(self, event):
        self._move_selected_rows(-1)

    def move_selected_down(self, event):
        self._move_selected_rows(+1)

    def _move_selected_rows(self, delta):
        rows = self.table.getSelectedRows()
        if not rows:
            return
        selected = rows[0]
        pair_start = selected if selected % 2 == 0 else selected - 1
        if pair_start < 0:
            return
        pair_idx = pair_start // 2
        new_pair_idx = pair_idx + delta
        max_pairs = self.table_model.getRowCount() // 2
        if new_pair_idx < 0 or new_pair_idx >= max_pairs:
            return
        model = self.table_model
        res_name = model.getValueAt(pair_idx * 2, 0)
        protons = [model.getValueAt(pair_idx * 2, c) for c in range(1, 7)]
        carbons = [model.getValueAt(pair_idx * 2 + 1, c) for c in range(1, 7)]
        for _ in range(2):
            model.removeRow(pair_idx * 2)
        insert_row = new_pair_idx * 2
        model.insertRow(insert_row, [res_name] + protons)
        model.insertRow(insert_row + 1, [''] + carbons)
        self.dirty = True
        self.table.setRowSelectionInterval(insert_row, insert_row + 1)

    def export_csv(self, event):
        if not self.target_sample_path:
            JOptionPane.showMessageDialog(self, "No sample directory to save to.", "Error", JOptionPane.ERROR_MESSAGE)
            return
        csv_file = os.path.join(self.target_sample_path, "shift_data.csv")
        try:
            with open(csv_file, 'wb') as f:
                writer = csv.writer(f)
                writer.writerow(COLUMNS)
                for r in range(0, self.table_model.getRowCount(), 2):
                    if r + 1 >= self.table_model.getRowCount():
                        break
                    res = str(self.table_model.getValueAt(r, 0) or "")
                    p_vals = [str(self.table_model.getValueAt(r, c) or "") for c in range(1, 7)]
                    c_vals = [str(self.table_model.getValueAt(r+1, c) or "") for c in range(1, 7)]
                    writer.writerow([res + " (H)"] + p_vals)
                    writer.writerow([res + " (C)"] + c_vals)
            JOptionPane.showMessageDialog(self, "Exported to {}".format(csv_file))
        except Exception as e:
            JOptionPane.showMessageDialog(self,
                "Failed to export CSV:\n{}".format(str(e)), "Export Error", JOptionPane.ERROR_MESSAGE)


# ============================================================
# Встраивание
# ============================================================
def embed_panel(initial_path=None):
    ts_frame = None
    for w in Window.getWindows():
        if isinstance(w, Frame) and w.getTitle() and 'topspin' in w.getTitle().lower():
            ts_frame = w
            break
    if not ts_frame:
        JOptionPane.showMessageDialog(None, "TopSpin frame not found.", "Error", JOptionPane.ERROR_MESSAGE)
        return

    parent = find_parent_container(ts_frame)
    if not parent:
        JOptionPane.showMessageDialog(None, "Could not locate parent container.", "Error", JOptionPane.ERROR_MESSAGE)
        return

    for comp in parent.getComponents():
        if isinstance(comp, ShiftTablePanel):
            new_path = initial_path or detect_active_sample_path()
            if new_path and new_path != comp._active_dataset_path:
                comp._active_dataset_path = new_path
                comp.set_sample_path(new_path)
            parent.revalidate()
            parent.repaint()
            return

    if not isinstance(parent.getLayout(), BorderLayout):
        parent.setLayout(BorderLayout())

    split_pane = None
    for comp in parent.getComponents():
        if isinstance(comp, JSplitPane):
            split_pane = comp
            break
    if split_pane:
        parent.remove(split_pane)
        parent.add(split_pane, BorderLayout.CENTER)

    panel = ShiftTablePanel()
    panel.parent_container = parent
    panel.setPreferredSize(_Dimension(420, 100))
    parent.add(panel, BorderLayout.EAST)
    parent.revalidate()
    parent.repaint()

    if initial_path is None:
        initial_path = detect_active_sample_path()
    if initial_path:
        panel._active_dataset_path = initial_path
        panel.set_sample_path(initial_path)

    print("Shift Table panel embedded on the right side.")
