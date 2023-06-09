from PyQt6 import QtGui, QtWidgets, QtCore
from PyQt6.QtWidgets import QDialog, QPushButton, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QTableWidget, QLineEdit, QSizePolicy
import networkx as nx
import numpy as np
from ...utils.analytics_utils import get_correlations_att_edge
import pandas as pd
from collections import defaultdict
from textwrap import wrap
from .modularity import Modularity
from src.gui.social_graph.graph import GraphCanvas
from mycolorpy import colorlist as mcp
from ..colors import cmap1, cmap1_str

from collections import Counter
import matplotlib
import matplotlib.pyplot as plt
from matplotlib import patches
from ..mpl_chord_diagram_2 import chord_diagram
# shades = plt.get_cmap('Pastel2_r')
matplotlib.use("QtAgg")

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure

from ..custom_buttons import MediumGreenButton


class FullScreenWidget(QDialog):

    def __init__(self, content_fig, parent):
        super().__init__(parent)
        self.parent = parent

        self.setWindowTitle("Chord Diagram")
        self.setModal(True)
        self.setWindowFlag(QtCore.Qt.WindowType.WindowStaysOnTopHint)

        label = QLabel('Select number of edges displayed: ')
        font = QtGui.QFont()
        font.setPointSize(10)
        label.setFont(font)
        self.line_edit = QLineEdit()
        self.chord_button = QPushButton("Generate Chord Diagram")
        self.chord_button.setEnabled(False)
        self.line_edit.textChanged.connect(lambda text: self.chord_button.setEnabled(bool(text)))
        self.chord_button.clicked.connect(self.check_input)
        self.error_label = QLabel()
        self.error_label.setStyleSheet("color: red")

        horizontal_layout = QHBoxLayout()
        horizontal_layout.addWidget(label)
        horizontal_layout.addWidget(self.line_edit)
        horizontal_layout.addWidget(self.chord_button)

        input_widget = QWidget()
        input_layout = QVBoxLayout(input_widget)
        input_layout.addLayout(horizontal_layout)
        input_layout.addWidget(self.error_label, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)

        canvas_widget = QWidget()
        canvas_widget.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding,
                                    QtWidgets.QSizePolicy.Policy.Expanding)
        self.canvas_layout = QVBoxLayout(canvas_widget)
        self.canvas = FigureCanvasQTAgg(content_fig)
        self.canvas_layout.addWidget(self.canvas)

        close_button = MediumGreenButton("Close", parent=self)
        close_button.clicked.connect(self.exit_fullscreen)

        text = 'This chord diagram represents connections between different values of animal attributes. ' \
       'Each node corresponds to an attribute value. The thickness of the edges between them indicates the frequency of connections between animals with those attributes. ' \
       'Only the most recurring edges are displayed (default is top 20 if there are more than 20 edges; all edges otherwise).'

        description = QLabel(text)
        description.setFont(font)
        description.setWordWrap(True)
        description.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding,
                                  QtWidgets.QSizePolicy.Policy.Fixed)

        self.layout = QVBoxLayout()
        self.layout.addWidget(input_widget)
        self.layout.addWidget(canvas_widget)
        self.layout.addWidget(description)
        self.layout.addWidget(close_button)

        self.setLayout(self.layout)

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self.showMaximized()

    def exit_fullscreen(self):
        self.showNormal()
        self.close()

    def check_input(self):
        try:
            input_value = int(self.line_edit.text())
            self.chord_button.setEnabled(bool(input_value))
            max_edges = len(self.parent.sorted_df)
            if input_value >= 1 and input_value <= max_edges:
                self.error_label.setText('')
                self.update_chord_diagram(input_value, self.canvas_layout)
            else:
                self.error_label.setText('Value must be between 1 and ' + str(max_edges))
        except ValueError:
            self.error_label.setText("'" + self.line_edit.text() + "'" + ' is not a valid input')

    def update_chord_diagram(self, top_n, canvas_layout):
        canvas_layout.removeWidget(self.canvas)
        self.canvas.close()

        fig = Figure(figsize=(8, 5), dpi=100)
        ax, legend_ax = fig.subplots(1, 2, gridspec_kw={'width_ratios': [4, 1]})

        names = self.parent.chord_nodes['name'].tolist()
        matrix = np.zeros((len(names), len(names)))

        top_edges = self.parent.sorted_df.nlargest(top_n, 'value')

        for _, row in top_edges.iterrows():
            matrix[row['source']][row['target']] = row['value']
            matrix[row['target']][row['source']] = row['value']

        common = np.intersect1d(np.where(np.all(matrix == 0, axis=0)),
                                np.where(np.all(matrix == 0, axis=1)))
        matrix = np.delete(matrix, common, axis=0)
        matrix = np.delete(matrix, common, axis=1)

        common_indices_list = common.tolist()
        for index in sorted(common_indices_list, reverse=True):
            del names[index]

        row_sums = np.sum(matrix, axis=1)
        column_sums = np.sum(matrix, axis=0)
        index_sums = row_sums + column_sums
        max_index = np.argsort(index_sums)[-20:][::-1]

        chord_diagram(matrix,
                      ax=ax,
                      use_gradient=True,
                      sort='size',
                      directed=False,
                      cmap=cmap1,
                      chord_colors=None)

        num_nodes = matrix.shape[0]
        colors = cmap1(np.linspace(0, 1, num_nodes))
        handles = []
        labels = []
        if len(names) > 20:
            for i in max_index:
                handle = patches.Patch(color=colors[i], label=names[i], alpha=0.7)
                handles.append(handle)
                labels.append(names[i])

            title = 'Top 20 Nodes'
        else:
            for i, name in enumerate(names):
                handle = patches.Patch(color=colors[i], label=name, alpha=0.7)
                handles.append(handle)
                labels.append(name)

            title = 'Nodes'

        legend_ax.plot([], [], ' ', label='Legend')
        legend = legend_ax.legend(handles,
                                  labels,
                                  loc='upper center',
                                  bbox_to_anchor=(0.5, 1.15),
                                  title=title,
                                  fontsize=9,
                                  title_fontsize=10)
        legend_ax.axis('off')
        legend.set_frame_on(False)

        self.canvas = FigureCanvasQTAgg(fig)

        canvas_layout.addWidget(self.canvas)


class GraphAnalytics(QWidget):
    """
    Graph analytics page, contains metrics and visualizations
    """

    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent

        # background utilities
        self.graph = self.parent.graph_page.graph_page.graph
        self.node_features = self.parent.graph_page.graph_page.features
        self.N = self.graph.graph.number_of_nodes()
        nodes = list(self.graph.node_layout.keys())
        labels = [k for k, _ in list(self.node_features.values())[0].items()]
        for l in labels:
            features = [self.node_features[n][l] for n in nodes]
            if all(self.is_number(f) for f in features) and all(
                    isinstance(f, str) for f in features):
                for n in nodes:
                    self.node_features[n][l] = float(self.node_features[n][l])
            else:
                continue

        self.disc_attribute_labels = []
        index = defaultdict(list)
        for itemdict in list(self.node_features.values()):
            for k, v in itemdict.items():
                index[k].append(v)

        for k, v in index.items():
            if all(isinstance(x, str) or int(x) == x for x in v):
                self.disc_attribute_labels.append(k)

        self.cont_attribute_labels = list(set(labels) - set(self.disc_attribute_labels))

        self.attribute_distribution_plot = self.attribute_distribution_plot()
        self.attribute_distribution_cont = self.attribute_distribution_cont()
        self.modularity = Modularity(self.graph.graph)

        self.info_tab2 = QLabel(text=f"The optimal number of communities is {self.modularity.subcommunity_n}, " + \
                                     f"with Modularity = {self.modularity.max_modularity}.\n" + \
                                          "Nodes are color-coded by community.",
                                    alignment=QtCore.Qt.AlignmentFlag.AlignCenter)
        self.graph_gui_small = GraphCanvas(self.parent)
        self.graph_gui_small.node_colors = self.modularity.node_colors
        self.setup_ui()

    def is_number(self, s):
        try:
            float(s)
            return True
        except ValueError:
            return False

    def setup_ui(self):
        container_widget = QWidget()
        container_layout = QHBoxLayout(container_widget)

        # Create a vertical layout for the plots
        self.plots_layout = QVBoxLayout()
        plots_layout = self.plots_layout
        plots_layout.setSpacing(10)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOn)

        # graph = self.graph

        # Add discrete attribute distribution plot
        if len(self.disc_attribute_labels) > 0:
            self.attribute_distribution_plot.setFixedHeight(40 * len(self.disc_attribute_labels) +
                                                            200)
            plots_layout.addWidget(self.attribute_distribution_plot)

        # Add attribute distribution plot continuous variables
        if len(self.cont_attribute_labels) > 0:

            self.attribute_distribution_cont.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding,
                                                           QtWidgets.QSizePolicy.Policy.Expanding)
            self.attribute_distribution_cont.setFixedHeight(
                190 * int(np.ceil(len(self.cont_attribute_labels) / 2)) + 100)
            plots_layout.addWidget(self.attribute_distribution_cont)

        # # Add heatmap
        try:
            heatmap_plot = self.heatmap()
            heatmap_plot.setFixedHeight(500)
            plots_layout.addWidget(heatmap_plot)
        except:
            pass

        # add modularity plot
        self.modularity.bar.setMinimumHeight(400)
        plots_layout.addWidget(self.modularity.bar)

        self.graphlayout = QVBoxLayout()

        self.graphlayout.addWidget(
            QLabel(text="Optimal Community Distribtuion",
                   alignment=QtCore.Qt.AlignmentFlag.AlignCenter,
                   font=QtGui.QFont("Helvetica", 18, QtGui.QFont.Weight.Normal),
                   styleSheet="padding: 5px; background-color: 'white';"))

        self.info_tab2.setMinimumHeight(50)
        self.info_tab2.setStyleSheet("font-size: 12px; background-color: 'white';")
        self.graphlayout.addWidget(self.info_tab2)

        self.graph_gui_small.setMinimumHeight(400)
        self.graph_gui_small.node_colors = self.modularity.node_colors
        self.graph_gui_small.refresh()
        self.graphlayout.addWidget(self.graph_gui_small)
        self.graphlayout.setSpacing(0)

        plots_layout.addLayout(self.graphlayout)

        plots_layout.addStretch()
        plots_widget = QWidget()
        plots_widget.setLayout(plots_layout)
        scroll.setWidget(plots_widget)
        scroll.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOn)

        container_layout.addWidget(scroll)

        # add right column with table and button
        table_widget = QWidget()
        table_layout = QVBoxLayout(table_widget)
        graph_analytics_table = self.graph_analytics_table()
        table_layout.addWidget(graph_analytics_table)
        table_widget.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
        container_layout.addWidget(table_widget)

        # Add chord diagram
        chord_diagram_fig = self.chord_diagram(self.disc_attribute_labels,
                                               self.node_features,
                                               self.graph)
        self.chord_diagram_canvas = FigureCanvasQTAgg(chord_diagram_fig)
        fullscreen_widget = FullScreenWidget(chord_diagram_fig, self)
        button = MediumGreenButton("Chord Diagram", parent=self)
        button.clicked.connect(fullscreen_widget.show)
        table_layout.addWidget(button)

        main_layout = QVBoxLayout(self)
        main_layout.addWidget(container_widget)

    def adjacency_matrix(self):
        fig = Figure(figsize=(6, 5), dpi=100)
        graph = self.parent.graph_page.graph_page.graph.graph
        bi_adj_matrix = nx.adjacency_matrix(graph, weight=None)
        # adj_matrix = nx.adjacency_matrix(graph, weight='weight')

        ax = fig.add_subplot(111)
        fig.suptitle('Adjacency Matrix', x=0.55)
        fig.tight_layout(pad=3.0)
        im = ax.matshow(bi_adj_matrix.todense(), cmap='binary')
        nodes = list(graph.nodes)
        ax.set_xticks(np.arange(len(nodes)))
        ax.set_yticks(np.arange(len(nodes)))
        ax.set_xticklabels(nodes)
        ax.set_yticklabels(nodes)
        plt.setp(ax.get_xticklabels(), rotation=45, ha="left", rotation_mode="anchor")

        ax.legend()
        cbar = fig.colorbar(im, ax=ax, cmap='binary', ticks=[0, 1], shrink=0.5)
        cbar.set_ticklabels(['No Edge', 'Edge'])

        # canvas = FigureCanvasQTAgg(fig)
        return fig

    def heatmap(self):
        graph = self.parent.graph_page.graph_page.graph.graph
        node_features = self.parent.graph_page.graph_page.features
        correlations = get_correlations_att_edge(graph, node_features)
        fig = Figure(figsize=(7, 5), dpi=100)
        fig.suptitle('Correlation between attributes and edge existence')
        fig.text(
            0.5,
            0.8,
            "Pearson\'s two-tailed correlation coefficients between the existence of an edge between nodes, and similarity between the two nodes in various attributes. * indicates p<0.05 with Bonferroni correction.",
            ha='center',
            fontsize=8,
            wrap=True)
        ax = fig.add_subplot(111)
        attributes = list(correlations.keys())
        # delete nan values
        for i in reversed(range(len(attributes))):
            if np.isnan(correlations[attributes[i]][0]):
                del correlations[attributes[i]]
                del attributes[i]

        coefficients = [c[0] for c in list(correlations.values())]
        p_values = [c[1] for c in list(correlations.values())]
        array = np.array(coefficients).reshape(1, len(correlations))
        im = ax.imshow(array, cmap=cmap1, vmin=-0.5, vmax=0.5)
        fig.tight_layout(pad=3.0)

        #add legend
        fig.colorbar(im, ax=ax, label="Correlation", cmap=cmap1, ticks=[0.5, 0, -0.5], shrink=0.5)

        ax.set_xticks(np.arange(len(attributes)), labels=attributes)
        plt.setp(ax.get_xticklabels(), rotation=60, ha="right", rotation_mode="anchor", fontsize=6)

        # remove yticks
        ax.set_yticks([])
        for i in range(len(attributes)):
            # ax.text(i,
            #         -0.25,
            #         str(round(coefficients[i], 2)),
            #         ha='center',
            #         va='center',
            #         color='black',
            #         fontsize=8)
            if p_values[i] < 0.05 / len(attributes):  # bonferroni correction
                ax.text(i, 0.1, '*', ha='center', va='center', color='black', fontsize=10)

        return FigureCanvasQTAgg(fig)

    def graph_analytics_table(self):
        graph = self.parent.graph_page.graph_page.graph.graph
        n = graph.number_of_nodes()
        try:
            diam = nx.diameter(graph)
            avg_sp = round(nx.average_shortest_path_length(graph), 3)
        except:
            diam = 'N/A'  # graph disconnected
            avg_sp = 'N/A'

        try:
            ev_cent = round(sum([e for _, e in nx.eigenvector_centrality(graph).items()]) / n, 3)
        except:
            ev_cent = 'Did not converge'
        graph_metrics = {
            'Number of Nodes':
                graph.number_of_nodes(),
            'Number of Edges':
                graph.number_of_edges(),
            'Density':
                round(nx.density(graph), 3),
            'Diameter':
                diam,
            'Average Degree':
                round(sum([d for _, d in graph.degree()]) / n, 3),
            'Average Clustering':
                round(nx.average_clustering(graph), 3),
            'Average Shortest Path':
                avg_sp,
            'Average Betweenness Centrality':
                round(sum([b for _, b in nx.betweenness_centrality(graph).items()]) / n, 3),
            'Average Closeness Centrality':
                round(sum([c for _, c in nx.closeness_centrality(graph).items()]) / n, 3),
            'Average Eigenvector Centrality':
                ev_cent,
            'Average PageRank':
                round(sum([p for _, p in nx.pagerank(graph).items()]) / n, 3),
            'Average Degree Centrality':
                round(sum([d for _, d in nx.degree_centrality(graph).items()]) / n, 3)
        }
        table = QTableWidget()
        table.setRowCount(len(graph_metrics))
        table.setColumnCount(2)
        table.setHorizontalHeaderLabels(['Metric', 'Value'])
        table.verticalHeader().setVisible(False)
        # table.setVerticalHeaderLabels(graph_metrics.keys())
        for i, (metric, value) in enumerate(graph_metrics.items()):
            table.setItem(i, 0, QtWidgets.QTableWidgetItem(metric))
            table.setItem(i, 1, QtWidgets.QTableWidgetItem(str(value)))
        table.resizeColumnsToContents()
        table.resizeRowsToContents()

        return table

    def attribute_distribution_cont(self):
        fig = Figure(figsize=(7, 5), dpi=100)
        node_features = self.parent.graph_page.graph_page.features

        attribute_labels = self.cont_attribute_labels
        n = len(attribute_labels)
        fig.suptitle(f'Continuous Attribute Distribution for {self.N} Nodes')
        rescale = lambda y: (y - np.min(y)) / (np.max(y) - np.min(y))

        # fig.text(0.5,0.5, s="test")
        c = 2
        k = int(np.ceil(n / c))
        for i in range(n):
            ax = fig.add_subplot(k, c, i + 1)  # Need to make scrollable
            attribute = attribute_labels[i]
            attribute_values = [
                features[attribute]
                for features in node_features.values()
                if attribute in features.keys()
            ]
            attribute_values.sort(reverse=True)
            ax.bar(np.arange(len(attribute_values)), attribute_values, width=0.5, color=cmap1(0.1))
            ax.tick_params(axis='y', labelsize=5)
            ax.tick_params(axis='x', which='both', bottom=False, top=False, labelbottom=False)
            ax.set_title(attribute, fontsize=6)

        fig.tight_layout()

        return FigureCanvasQTAgg(fig)

    def attribute_distribution_plot(self):
        fig = Figure(figsize=(4, 5), dpi=100)
        node_features = self.parent.graph_page.graph_page.features
        attribute_labels = self.disc_attribute_labels
        # attribute_labels = sorted(set([key for _, value in node_features.items() for key, v in value.items() if type(v) == str or int(v) == v]), key=lambda x: x.lower())
        n = len(attribute_labels)
        fig.suptitle(f"Discrete Attribute Distribution for {self.N} Nodes")
        fig.tight_layout(pad=1.0)
        bars = []

        # sort by number of unique values
        attribute_labels = sorted(
            attribute_labels,
            key=lambda x: len(
                set([features[x] for features in node_features.values() if x in features.keys()])),
            reverse=True)

        for i in range(n):
            ax = fig.add_subplot(n, 1, i + 1)
            attribute = attribute_labels[i]
            attribute_values = [
                features[attribute]
                for features in node_features.values()
                if attribute in features.keys()
            ]

            attribute = attribute.replace('_', ' ').title()  # formatting
            attribute = '\n'.join(wrap(attribute, 11, break_long_words=False))

            element_counts = Counter(attribute_values)
            values = list(element_counts.keys())
            count = list(element_counts.values())
            shades = mcp.gen_color(cmap=cmap1_str, n=max(int(len(values) + 1), 25))

            for i in range(len(values)):
                bar = ax.barh(attribute,
                              count[i],
                              left=sum(count[:i]),
                              label=values[i],
                              color=shades[i])
                bars.extend(bar)
                ax.text(sum(count[:i]) + count[i] / 2,
                        attribute,
                        str(count[i]),
                        ha='center',
                        va='center',
                        color="white",
                        alpha=0.5,
                        fontsize=8,
                        fontweight='bold')
            ax.tick_params(axis='y', labelsize=7)
            ax.tick_params(axis='x', which='both', bottom=False, top=False, labelbottom=False)

            # for bar in bars:
            #     bar.set_picker(True)
        fig.subplots_adjust(left=0.2)

        def onclick(event):
            ax_save = None
            for bar in bars:
                if bar.contains(event)[0]:
                    ax = bar.axes
                    ax.set_zorder(200)
                    # amount of bars
                    n = len(ax.patches)
                    l = ax.legend(bbox_to_anchor=(0.5, 1.0),
                                  loc='upper center',
                                  ncol=min(4, np.ceil(n / 4)),
                                  fontsize=8)

                    ax_save = ax
                    break

            # This seems like a round-about way, but is necessary since mulitple bars are part of the same axes
            for bar in bars:
                ax = bar.axes
                if ax != ax_save:
                    ax.legend().remove()
                    ax.set_zorder(0)

            fig.canvas.draw_idle()

        fig.canvas.mpl_connect("button_press_event", onclick)

        return FigureCanvasQTAgg(fig)

    def chord_diagram(self, attribute_names, node_features, graph):
        fig = Figure(figsize=(8, 5), dpi=100)
        ax, legend_ax = fig.subplots(1, 2, gridspec_kw={'width_ratios': [4, 1]})

        features_df = pd.DataFrame(node_features).T
        features_df.index.name = 'node'
        edges_df = pd.DataFrame(graph.directed_edges, columns=['source', 'target'])

        att_dict = {}
        chord_nodes_list = []
        i = 0
        for att in attribute_names:
            unique_values = list(features_df[att].unique())
            unique_values = [value for value in unique_values if value != ' ']
            att_dict[att] = {
                att + ': ' + str(value): i + idx for idx, value in enumerate(unique_values)
            }
            i += len(unique_values)

        node_dict = {}
        for att, values in att_dict.items():
            node_dict.update(values)
            for val, idx in values.items():
                if val == 'nan':
                    continue
                chord_nodes_list.append({'index': idx, 'name': val, 'group': att})

        self.chord_nodes = pd.DataFrame(chord_nodes_list)
        self.chord_nodes = self.chord_nodes.sort_values(by='group')

        names = self.chord_nodes['name'].tolist()
        matrix = np.zeros((len(names), len(names)))

        combinations = []
        for _, row in edges_df.iterrows():
            sources = features_df.loc[row['source'], attribute_names].dropna()
            targets = features_df.loc[row['target'], attribute_names].dropna()
            sources_list = [att + ': ' + str(val) for att, val in sources.items() if val != ' ']
            targets_list = [att + ': ' + str(val) for att, val in targets.items() if val != ' ']
            combinations.extend({
                'source': node_dict[source], 'target': node_dict[target]
            } for source in sources_list for target in targets_list)

        chord_df = pd.DataFrame(combinations, columns=['source', 'target'])
        chord_df = chord_df.groupby(['source', 'target']).size().reset_index(name='value')
        chord_df = chord_df.nlargest(500, 'value')

        self.sorted_df = chord_df.sort_values('value', ascending=False)
        top_edges = self.sorted_df.nlargest(20, 'value')

        for _, row in top_edges.iterrows():
            matrix[row['source']][row['target']] = row['value']
            matrix[row['target']][row['source']] = row['value']

        common = np.intersect1d(np.where(np.all(matrix == 0, axis=0)),
                                np.where(np.all(matrix == 0, axis=1)))
        matrix = np.delete(matrix, common, axis=0)
        matrix = np.delete(matrix, common, axis=1)

        common_indices_list = common.tolist()
        for index in sorted(common_indices_list, reverse=True):
            del names[index]

        row_sums = np.sum(matrix, axis=1)
        column_sums = np.sum(matrix, axis=0)
        index_sums = row_sums + column_sums
        max_index = np.argsort(index_sums)[-20:][::-1]

        chord_diagram(matrix,
                      ax=ax,
                      use_gradient=True,
                      sort='size',
                      directed=False,
                      cmap=cmap1,
                      chord_colors=None)

        num_nodes = matrix.shape[0]
        colors = cmap1(np.linspace(0, 1, num_nodes))
        handles = []
        labels = []
        if len(names) > 20:
            for i in max_index:
                handle = patches.Patch(color=colors[i], label=names[i], alpha=0.7)
                handles.append(handle)
                labels.append(names[i])

            title = 'Top 20 Nodes'
        else:
            for i, name in enumerate(names):
                handle = patches.Patch(color=colors[i], label=name, alpha=0.7)
                handles.append(handle)
                labels.append(name)

            title = 'Nodes'

        legend_ax.plot([], [], ' ', label='Legend')
        legend = legend_ax.legend(handles,
                                  labels,
                                  loc='upper center',
                                  bbox_to_anchor=(0.5, 1.15),
                                  title=title,
                                  fontsize=9,
                                  title_fontsize=10)
        legend_ax.axis('off')
        legend.set_frame_on(False)

        return fig