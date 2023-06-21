from PyQt6.QtWidgets import QWidget, QHBoxLayout, QToolBar, QVBoxLayout
from PyQt6.QtGui import QAction
from PyQt6.QtCore import Qt
import matplotlib

matplotlib.use("Qt5Agg")

from .graph import GraphCanvas
from .side_bar import NodeInfoPage
from .info_page import InfoPage
from .color_bar import ColorBar
from .icons import AddNodeIcon, UndoIcon, PredEdgesIcon, AddEdgeIcon, RedoIcon, SaveIcon


class GraphPage(QWidget):
    """
    This is the page that belongs to the "graph" tab. It consists of three sub-pages:
     - Left page: shows information about the object which is hovered by the mouse
     - Graph page: shows the graph of animals
     - Right page: shows information about the selected object (the one last clicked on)
    """

    def __init__(self, parent):
        super().__init__()
        self.parent = parent

        # Toolbar
        self._create_tool_bar()

        # Page
        mainlayout = QVBoxLayout()
        hlayout = QHBoxLayout()
        # Sub-pages definition
        self.graph_page = GraphCanvas(parent, width=5, height=2, dpi=100)
        self.left_page = NodeInfoPage(self.graph_page.features, self.graph_page.metrics)
        self.right_page = NodeInfoPage(self.graph_page.features, self.graph_page.metrics)
        self.top_page = InfoPage(self.graph_page.graph.graph)
        self.color_bar = ColorBar(self.graph_page.graph.graph)
        # Sub-pages allocation on main page
        hlayout.addWidget(self.left_page)
        hlayout.addWidget(self.graph_page)
        hlayout.addWidget(self.right_page)
     
        mainlayout.addWidget(self.top_page)
        mainlayout.addWidget(self.color_bar)
        mainlayout.addLayout(hlayout)
        
        self.setLayout(mainlayout)

    def _create_tool_bar(self):

        # Define menu/toolbar
        self.toolbar = QToolBar(self.parent)
        self.parent.addToolBar(Qt.ToolBarArea.LeftToolBarArea, self.toolbar)

        # Icons listed from top to bottom
        self.icons = {
            "add_node": AddNodeIcon(self),
            "add_edge": AddEdgeIcon(self),
            "undo": UndoIcon(self),
            "redo": RedoIcon(self),
            "pred": PredEdgesIcon(self),
            "save": SaveIcon(self)
        }
        for action in list(self.icons.values()):
            self.toolbar.addAction(action)

    def refresh(self):
        self.graph_page.refresh()
        self.top_page.refresh(self.graph_page.graph.graph)
        self.icons["pred"].refresh(self.graph_page.graph.predictable)