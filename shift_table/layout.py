from java.awt import FlowLayout
from java.awt import Dimension as _Dimension

class WrapLayout(FlowLayout):
    def minimumLayoutSize(self, target):
        return self.preferredLayoutSize(target)

    def preferredLayoutSize(self, target):
        parent = target.getParent()
        if parent is None:
            return super(WrapLayout, self).preferredLayoutSize(target)
        width = parent.getWidth()
        if width == 0:
            width = Integer.MAX_VALUE
        hgap = self.getHgap()
        vgap = self.getVgap()
        insets = parent.getInsets()
        maxWidth = width - insets.left - insets.right
        x = 0
        y = insets.top + vgap
        rowHeight = 0
        for comp in target.getComponents():
            if not comp.isVisible():
                continue
            d = comp.getPreferredSize()
            if x + d.width > maxWidth:
                x = insets.left + hgap
                y += rowHeight + vgap
                rowHeight = 0
            x += d.width + hgap
            rowHeight = max(rowHeight, d.height)
        y += rowHeight + vgap
        return _Dimension(maxWidth, y + insets.bottom)
