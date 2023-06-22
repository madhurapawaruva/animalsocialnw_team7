import logging
import os
import logging
import pickle
from src.loaders.asnr_dataloader import ASNRGraph
from src.models.train import train_model

from ..action import GlobalAction
from ...static import PageState, GRAPH_VERSION_FOLDER, versions
from ..stack import ActionStack

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('retrain.action')


class Retrain(GlobalAction):

    def __init__(self, graph_gui, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.graph_gui = graph_gui

    def do(self):
        # Retraining graph
        features, edgelist, adj, _, _ = ASNRGraph(graph_obj=self.graph_gui.graph.graph).preprocess()
        train_model(PageState.id, features, edgelist, adj)
        logger.info("Graph retrained")

        # Increasing current version number
        graph_folder = os.path.join(GRAPH_VERSION_FOLDER, str(PageState.id))
        os.makedirs(graph_folder, exist_ok=True)
        version_id = f"v{len(os.listdir(graph_folder))}"
        versions[PageState.id].append(version_id)
        PageState.select_version(version_id, is_next_version=True)
        print("previous version: ", PageState.curr_version)

        # Refresh on page
        self.graph_gui.graph.reset()
        ActionStack.reset()
        logger.info("Graph set as default, starting position.")
        self.graph_gui.refresh()