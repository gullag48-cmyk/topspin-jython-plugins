# -*- coding: utf-8 -*-
import sys, os
try:
    script_dir = os.path.dirname(os.path.abspath(__file__))
except NameError:
    script_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
sys.path.insert(0, script_dir)

from java.awt import Window, Frame
from shift_table.panel import ShiftTablePanel, embed_panel
from shift_table.utils import find_parent_container

# Старт — CURDATA на CmdThread (работает)
sample_path = None
try:
    curdat = CURDATA()
    if curdat and len(curdat) >= 4:
        sp = os.path.join(curdat[3], curdat[0])
        if os.path.isdir(sp):
            sample_path = os.path.abspath(sp)
except:
    pass

# Встраиваем панель
try:
    embed_panel(initial_path=sample_path)
except TypeError:
    embed_panel()

# Устанавливаем начальный путь
if sample_path:
    for w in Window.getWindows():
        if isinstance(w, Frame) and w.getTitle() and 'topspin' in w.getTitle().lower():
            parent = find_parent_container(w)
            if parent:
                for comp in parent.getComponents():
                    if isinstance(comp, ShiftTablePanel) and comp.target_sample_path != sample_path:
                        comp._active_dataset_path = sample_path
                        comp.set_sample_path(sample_path)
                        break
            break
