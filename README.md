# TopSpin Jython Plugins

A collection of Jython plugins embedded into the Bruker TopSpin interface. Each plugin comes with full source code and serves as a working example for building your own TopSpin plugins.

## Plugins

### Shift Table & Peak Annotator

Editable shift table panel embedded on the right side of the TopSpin workspace. Manage chemical shift data per sample, annotate peak lists directly from the table.

**Features:**
- Residue-based shift table (proton/carbon pairs)
- Save/load shifts to `shift_data.xml` per sample
- Automatic dataset detection via CURDATA at startup
- Manual Refresh button to re-detect the active dataset
- Annotate 1D peak lists from selected table cells
- Export to CSV

## Quick Start

```bash
xpy C:/path/to/jtable.py
```

A panel appears on the right side of the TopSpin window. Click **Refresh** to load the current dataset, or run `xpy` again to re-detect.

## Structure

```
jtable.py                    # Entry point (CURDATA + embed)
shift_table/
    panel.py                 # Main panel class + embed logic
    model.py                 # JTable model with validation
    renderers.py             # Custom table cell renderers
    xml_handler.py           # XML read/write for shift data
    utils.py                 # Helpers: path detection, window parsing
    constants.py             # Colors, column definitions
    layout.py                # WrapLayout for toolbar buttons
HOWTO.md                     # Full development guide (English)
jtable_Inst.md               # Documentation (Russian)
```

## Requirements

- Bruker TopSpin 5.0+
- Jython (bundled with TopSpin)

## Development Guide

See **[HOWTO.md](HOWTO.md)** for a complete walkthrough on building your own TopSpin Jython plugins, including:

- Project structure and module dependencies
- The CURDATA / CmdThread problem and how to work around it
- Detecting the active dataset from EDT (window title parsing)
- Swing components: JTable, renderers, layout
- Embedding panels into the TopSpin window
- Jython pitfalls: method name conflicts, bytecode caching, encoding

## License

MIT
