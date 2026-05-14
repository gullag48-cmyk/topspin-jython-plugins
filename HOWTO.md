# TopSpin Jython Plugin Development Guide

## Building a side-panel plugin with Swing and Jython for Bruker TopSpin

This guide walks through developing a Jython plugin embedded into the TopSpin interface as a side panel. The reference implementation is the **Shift Table & Peak Annotator** in this repository.

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Project Structure](#2-project-structure)
3. [Entry Point and the CURDATA Problem](#3-entry-point-and-the-curdata-problem)
4. [Swing Components](#4-swing-components)
5. [Embedding the Panel](#5-embedding-the-panel)
6. [Detecting the Active Dataset](#6-detecting-the-active-dataset)
7. [Working with XML](#7-working-with-xml)
8. [Jython Pitfalls](#8-jython-pitfalls)
9. [Checklist for New Plugins](#9-checklist-for-new-plugins)

---

## 1. Introduction

TopSpin ships with **Jython 2.7** — a Java-based implementation of Python 2.7. This allows you to use Python syntax while accessing the full Java Swing/AWT API and TopSpin internals.

### Running a script

```bash
xpy C:/path/to/script.py
```

Or from the TopSpin command line:

```
xpy script_name   # if placed in a scanned directory
```

### What you can do

- Build Swing UI panels (JTable, JButton, JPanel, etc.)
- Read/write TopSpin data files (acqu, proc, peaklist.xml, etc.)
- Execute TopSpin commands via `XCMD()`
- Query the active dataset via `CURDATA()` (CmdThread only!)
- Embed custom panels directly into the TopSpin window layout

### Limitations at a glance

| Limitation | Workaround |
|-----------|-----------|
| `CURDATA()` only works in `__main__` (CmdThread) | Compute in entry point, pass as argument |
| Jython caches compiled `.class` files between runs | Clear module from `sys.modules` or restart TopSpin |
| `getName()` conflicts with Java `Component.getName()` | Use `str(comp.getClass())` |
| Swing listeners run on EDT, not CmdThread | Never call `CURDATA()` from listeners — read window title instead |

---

## 2. Project Structure

A modular plugin avoids a monolithic "god file". Organize your code into a package:

```
plugin_name.py              # Entry point (4-10 lines)
plugin_package/
    __init__.py             # Empty
    constants.py            # Colors, column names, shared literals
    utils.py                # Helpers: path detection, container search
    layout.py               # Custom Swing LayoutManager
    model.py                # Custom TableModel
    renderers.py            # Custom TableCellRenderers
    xml_handler.py          # XML read/write
    panel.py                # Main JPanel + embed function
```

### Dependency graph

```
entry_point.py
    -> panel.py
        -> constants.py
        -> utils.py
        -> layout.py
        -> model.py
        -> renderers.py
        -> xml_handler.py
            -> utils.py
            -> constants.py
```

No circular imports.

### Entry point

```python
# -*- coding: utf-8 -*-
import sys, os
try:
    script_dir = os.path.dirname(os.path.abspath(__file__))
except NameError:
    script_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
sys.path.insert(0, script_dir)

from plugin_package.panel import embed_panel

if __name__ == "__main__":
    embed_panel()
```

> **Note:** `__file__` is not defined when running under TopSpin's `xpy`. Use `sys.argv[0]` as fallback.

---

## 3. Entry Point and the CURDATA Problem

### The CmdThread constraint

When you run `xpy script.py`, the script executes on TopSpin's **CmdThread**. Key TopSpin functions like `CURDATA()` require CmdThread context and **fail with "NOT_A_CMDTHREAD"** when called from the Event Dispatch Thread (EDT).

### Where CURDATA works / fails

| Context | Works? | Reason |
|---------|--------|--------|
| Top-level code in `xpy` script | Yes | Runs on CmdThread |
| `javax.swing.Timer` callback | **No** | EDT |
| `JButton` ActionListener | **No** | EDT |
| `WindowFocusListener` | **No** | EDT |
| `threading.Thread` | **No** | Not CmdThread |

### Solution: pass from `__main__`, don't import

Jython 2.7 does not make TopSpin builtins (CURDATA, XCMD, etc.) available in imported modules. Compute the path in your entry point and pass it:

```python
# entry_point.py (runs on CmdThread)
if __name__ == "__main__":
    sample_path = None
    try:
        curdat = CURDATA()
        if curdat and len(curdat) >= 4:
            sp = os.path.join(curdat[3], curdat[0])
            if os.path.isdir(sp):
                sample_path = os.path.abspath(sp)
    except:
        pass
    embed_panel(initial_path=sample_path)
```

```python
# panel.py
def embed_panel(initial_path=None):
    if initial_path is None:
        initial_path = detect_active_sample_path()  # fallback via CWD/window title
    if initial_path:
        panel.set_sample_path(initial_path)
```

### Detecting dataset changes from EDT

Since `CURDATA()` is unavailable from the EDT, detect dataset changes via the **TopSpin window title**:

1. Navigate the component tree to find `TopspinInFrame` (a `JInternalFrame` inside `BDesktop`)
2. Read its title — format: `"SampleName" ExpNo ProcNo DataPath`
3. Parse: `sample_path = os.path.join(data_path, sample_name)`

```python
def refresh_dataset(self, event):
    for w in Window.getWindows():
        if isinstance(w, Frame) and 'topspin' in w.getTitle().lower():
            def find_frame(comp):
                if isinstance(comp, JDesktopPane):
                    for f in comp.getAllFrames():
                        if f.isVisible() and f.getTitle():
                            return f
                if hasattr(comp, 'getComponents'):
                    for c in comp.getComponents():
                        res = find_frame(c)
                        if res:
                            return res
                return None
            frame = find_frame(w)
            if frame:
                title = frame.getTitle()
                parts = title.split('"')
                if len(parts) >= 3:
                    sample_name = parts[1]
                    rest = parts[2].strip().split(None, 2)
                    if len(rest) >= 3:
                        sample_path = os.path.join(rest[2], sample_name)
                        if os.path.isdir(sample_path):
                            self.set_sample_path(os.path.abspath(sample_path))
            break
```

---

## 4. Swing Components

### JTable with custom model

```python
from javax.swing.table import DefaultTableModel

class MyTableModel(DefaultTableModel):
    def __init__(self, columns, rows):
        super(MyTableModel, self).__init__(columns, rows)

    def setValueAt(self, value, row, col):
        if col > 0 and value is not None:
            if not self._is_valid(str(value)):
                JOptionPane.showMessageDialog(None, "Invalid value")
                return
        super(MyTableModel, self).setValueAt(value, row, col)
```

### Custom cell renderer

```python
from javax.swing.table import DefaultTableCellRenderer
from java.awt import Color

class MyRenderer(DefaultTableCellRenderer):
    def getTableCellRendererComponent(self, table, value, isSelected, hasFocus, row, column):
        comp = super(MyRenderer, self).getTableCellRendererComponent(
            table, value, isSelected, hasFocus, row, column)
        if not isSelected:
            comp.setBackground(Color(245, 248, 252))
        return comp
```

### WrapLayout for toolbar buttons

Swing's `FlowLayout` does not wrap buttons when the panel is resized. Implement `WrapLayout`:

```python
class WrapLayout(FlowLayout):
    def preferredLayoutSize(self, target):
        # compute wrapping based on parent width
        # see layout.py in this project for full implementation
        ...
```

---

## 5. Embedding the Panel

### Finding the TopSpin frame

```python
def embed_panel():
    ts_frame = None
    for w in Window.getWindows():
        if isinstance(w, Frame) and w.getTitle() and 'topspin' in w.getTitle().lower():
            ts_frame = w
            break
```

### Finding the container for your panel

TopSpin's window layout uses `JSplitPane(HORIZONTAL)` inside a container. Your panel goes into `BorderLayout.EAST` of that container:

```python
def find_main_container(frame):
    def search(comp):
        if isinstance(comp, JSplitPane) and comp.getOrientation() == JSplitPane.HORIZONTAL_SPLIT:
            right = comp.getRightComponent()
            if right and (isinstance(right, JDesktopPane) or
                isinstance(right, JTabbedPane)):
                return comp.getParent()
        if hasattr(comp, 'getComponents'):
            for child in comp.getComponents():
                res = search(child)
                if res:
                    return res
        return None
    return search(frame)
```

### Adding your panel

```python
if not isinstance(parent.getLayout(), BorderLayout):
    parent.setLayout(BorderLayout())

panel = MyPanel()
parent.add(panel, BorderLayout.EAST)
parent.revalidate()
parent.repaint()
```

> Check if your panel already exists before adding a duplicate:

```python
for comp in parent.getComponents():
    if isinstance(comp, MyPanel):
        return  # already embedded
```

---

## 6. Detecting the Active Dataset

### Method 1: CURDATA (startup only, CmdThread)

```python
try:
    curdat = CURDATA()  # returns [name, expno, procno, directory, user]
    sample_path = os.path.join(curdat[3], curdat[0])
except:
    pass
```

### Method 2: CWD traversal (fallback)

```python
cwd = os.getcwd()
parts = cwd.split(os.sep)
for i in range(len(parts), 0, -1):
    candidate = os.sep.join(parts[:i])
    if os.path.isdir(candidate):
        for entry in os.listdir(candidate):
            if entry.isdigit() and os.path.exists(os.path.join(candidate, entry, 'acqu')):
                return os.path.abspath(candidate)
```

### Method 3: Window title parsing (from EDT)

Parse the `TopspinInFrame` title (see [Section 3](#detecting-dataset-changes-from-edt)).

### Method 4: Timer polling (from EDT, reads window title)

```python
from javax.swing import Timer

def check_dataset(event):
    # parse window title here...
    pass

Timer(3000, check_dataset).start()
```

---

## 7. Working with XML

TopSpin stores peak lists, parameters, and metadata in XML files. Use `xml.etree.ElementTree`:

```python
import xml.etree.ElementTree as ET

# Read
tree = ET.parse("peaklist.xml")
root = tree.getroot()
for peak in root.findall(".//Peak1D"):
    f1 = peak.get("F1")
    annotation = peak.get("annotation")

# Write
root = ET.Element("PeakList")
pl1d = ET.SubElement(root, "PeakList1D")
peak = ET.SubElement(pl1d, "Peak1D")
peak.set("F1", "120.5")
peak.set("annotation", "MyLabel")
tree = ET.ElementTree(root)
tree.write("output.xml", encoding="UTF-8", xml_declaration=True)
```

### Schema compliance

TopSpin validates peaklist.xml against a schema. A `<PeakList1DHeader>` must contain `<PeakPickDetails>`:

```python
header = ET.SubElement(pl1d, "PeakList1DHeader")
header.set("creator", "MyScript")
ET.SubElement(header, "PeakPickDetails").text = "Generated by MyScript"
```

---

## 8. Jython Pitfalls

### 8.1 Method name conflicts

Java methods like `Component.getName()` conflict with Python's `__name__` / naming conventions.  
**Workaround:** call via Java reflection or use alternatives:

```python
# Avoid:
comp.getClass().getName()       # ERROR: expected 1 arg

# Use:
str(comp.getClass())            # "class javax.swing.JPanel"
```

### 8.2 Bytecode caching

Jython compiles `.py` to `.class` files and caches them. If you edit your module and rerun `xpy`, the old code may still be used.

**Fix:** delete from `sys.modules` before importing:

```python
for _m in list(sys.modules):
    if _m.startswith('my_package'):
        del sys.modules[_m]
```

Or restart TopSpin.

### 8.3 `set` vs `Set`

In Jython, `set()` is Python's builtin, but Java also has a `Set` interface. To avoid ambiguity, import from `java.util` explicitly:

```python
from java.util import Set as JavaSet
```

### 8.4 Encoding

All files with non-ASCII characters (comments, strings) must declare encoding:

```python
# -*- coding: utf-8 -*-
```

### 8.5 String types

Jython converts Java `String` to Python `unicode` when passing through `str()`. Use `str()` consistently.

---

## 9. Checklist for New Plugins

- [ ] Entry point uses `try/except` for `__file__` + fallback to `sys.argv[0]`
- [ ] Entry point adds script directory to `sys.path`
- [ ] All `.py` files with non-ASCII declare `# -*- coding: utf-8 -*-`
- [ ] `CURDATA()` is only called in `__main__`, never in EDT listeners
- [ ] Dataset changes detected via window title parsing, not CURDATA
- [ ] Panel embedding checks for duplicate instances
- [ ] XML output includes required schema elements (PeakPickDetails)
- [ ] `.gitignore` tracks only essential files
- [ ] Java method name conflicts avoided (no bare `getName()`)
