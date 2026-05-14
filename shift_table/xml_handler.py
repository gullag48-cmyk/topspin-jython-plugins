from __future__ import print_function
from javax.swing import JOptionPane
import xml.etree.ElementTree as ET
import os
from constants import XML_FILENAME
from utils import smart_split_static

class ShiftXMLHandler:
    @staticmethod
    def load(path, model):
        xml_file = os.path.join(path, XML_FILENAME)
        if not os.path.exists(xml_file):
            return False
        try:
            tree = ET.parse(xml_file)
            root = tree.getroot()
            rows = []
            for residue in root.findall('residue'):
                name = residue.get('name', '')
                p_node = residue.find('proton')
                c_node = residue.find('carbon')
                p_text = p_node.text if p_node is not None else ""
                c_text = c_node.text if c_node is not None else ""
                protons = smart_split_static(p_text)
                carbons = smart_split_static(c_text)
                rows.append((name, protons, carbons))
            model.replace_all_data(rows)
            return True
        except Exception as e:
            JOptionPane.showMessageDialog(None,
                "Failed to load {}:\n{}".format(xml_file, str(e)),
                "Load Error", JOptionPane.ERROR_MESSAGE)
            return False

    @staticmethod
    def save(path, model):
        if path is None:
            return False
        root = ET.Element("shifts")
        for r in range(0, model.getRowCount(), 2):
            if r + 1 >= model.getRowCount():
                break
            name = str(model.getValueAt(r, 0) or '')
            p_vals = [str(model.getValueAt(r, c) or '') for c in range(1, 7)]
            c_vals = [str(model.getValueAt(r + 1, c) or '') for c in range(1, 7)]
            res = ET.SubElement(root, "residue", name=name)
            ET.SubElement(res, "proton").text = ';'.join(p_vals)
            ET.SubElement(res, "carbon").text = ';'.join(c_vals)
        xml_file = os.path.join(path, XML_FILENAME)
        try:
            tree = ET.ElementTree(root)
            tree.write(xml_file, encoding="UTF-8", xml_declaration=True)
            return True
        except Exception as e:
            JOptionPane.showMessageDialog(None,
                "Failed to save {}:\n{}".format(xml_file, str(e)),
                "Save Error", JOptionPane.ERROR_MESSAGE)
            return False
