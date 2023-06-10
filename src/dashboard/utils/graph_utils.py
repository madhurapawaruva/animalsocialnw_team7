import networkx as nx
import numpy as np

from matplotlib import cm, colors
import matplotlib.pyplot as plt

shades = plt.get_cmap('Pastel1')


random_state = np.random.RandomState(42)

def read_graph(path, is_add_new_nodes=False):
    g = nx.read_graphml(path)

    edge_color, node_color = dict(), dict()
    if is_add_new_nodes:
         print("Implementation to Build")

    
    for _, edge in enumerate(g.edges):
        edge_color[edge] = 'tab:gray' 
    
    minval = min([degree for _, degree in g.degree()])
    maxval = max([degree for _, degree in g.degree()])
    norm = colors.Normalize(vmin=minval, vmax=maxval, clip=True)
    mapper = cm.ScalarMappable(norm=norm, cmap=shades)
    
    for node, degree in g.degree():
        node_color[node] =  mapper.to_rgba(degree)
    # node_color = np.asarray([degrees[n] for n in nodes])
    return g, edge_color, node_color