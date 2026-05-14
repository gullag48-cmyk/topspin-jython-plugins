# -*- coding: utf-8 -*-
from __future__ import print_function
from javax.swing import JSplitPane, JDesktopPane, JTabbedPane, JOptionPane
from java.awt import Window, Frame
import os

def _safe_str(val):
    if val is None:
        return ""
    return str(val)

def smart_split_static(text):
    if not text:
        return [''] * 6
    semicolons = text.count(';')
    commas = text.count(',')
    if semicolons > 0:
        vals = text.split(';')
    elif commas > 0:
        vals = text.split(',')
    else:
        return [text] + [''] * 5
    result = [v.strip() for v in vals[:6]]
    result += [''] * (6 - len(result))
    return result

def find_parent_container(frame):
    def search(comp):
        if isinstance(comp, JSplitPane) and comp.getOrientation() == JSplitPane.HORIZONTAL_SPLIT:
            right = comp.getRightComponent()
            if right and (isinstance(right, JDesktopPane) or
                (isinstance(right, JTabbedPane) and any('SPECTRUM' in (comp.getTitleAt(i) or '') for i in range(comp.getTabCount())))):
                return comp.getParent()
        if hasattr(comp, 'getComponents'):
            for child in comp.getComponents():
                res = search(child)
                if res:
                    return res
        return None
    return search(frame)

def _sample_path_from_title(title):
    # ищем в заголовке сегмент с путём (содержит '\' или '/')
    words = title.split(' - ')
    for w in words:
        w = w.strip()
        if not os.path.isdir(w):
            continue
        # прямой путь — уже папка образца
        for entry in os.listdir(w):
            if entry.isdigit() and os.path.exists(os.path.join(w, entry, 'acqu')):
                return os.path.abspath(w)
        # возможно это путь до expno/pdata — поднимаемся на 3-4 уровня
        parent = os.path.dirname(os.path.dirname(os.path.dirname(w)))
        if os.path.isdir(parent):
            for entry in os.listdir(parent):
                if entry.isdigit() and os.path.exists(os.path.join(parent, entry, 'acqu')):
                    return os.path.abspath(parent)
        parent2 = os.path.dirname(parent)
        if os.path.isdir(parent2):
            for entry in os.listdir(parent2):
                if entry.isdigit() and os.path.exists(os.path.join(parent2, entry, 'acqu')):
                    return os.path.abspath(parent2)
    return None

def detect_active_sample_path():
    # Стратегия 1: CWD
    cwd = os.getcwd()
    parts = cwd.split(os.sep)
    for i in range(len(parts), 0, -1):
        candidate = os.sep.join(parts[:i])
        if not os.path.isdir(candidate):
            continue
        for entry in os.listdir(candidate):
            if entry.isdigit() and os.path.exists(os.path.join(candidate, entry, 'acqu')):
                return os.path.abspath(candidate)
    # Стратегия 3: заголовок окна TopSpin
    for w in Window.getWindows():
        if isinstance(w, Frame) and w.getTitle():
            title = w.getTitle()
            path = _sample_path_from_title(title)
            if path:
                return path
    return None
