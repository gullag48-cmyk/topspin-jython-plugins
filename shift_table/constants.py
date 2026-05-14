from java.awt import Color

COLUMNS = ["Residue", "H1/C1", "H2/C2", "H3/C3", "H4/C4", "H5/C5", "H6/C6"]
XML_FILENAME = "shift_data.xml"
PAIR_BACKGROUND_0 = Color(245, 248, 252)
PAIR_BACKGROUND_1 = Color.WHITE
GRID_COLOR = Color(200, 200, 200)

def get_pair_background(row):
    pair_index = row // 2
    return PAIR_BACKGROUND_0 if pair_index % 2 == 0 else PAIR_BACKGROUND_1
