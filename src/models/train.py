"""
Usage :  python train.py --animal bat

"""
import numpy as np
import torch

from argparse import ArgumentParser

import sys
import os
import random

myDir = os.getcwd()
sys.path.append(myDir)
from pathlib import Path

path = Path(myDir)
a = str(path.parent.absolute())
sys.path.append(a)

import scipy.sparse as sp


from src.utils.gae_utils import mask_test_edges, preprocess_graph
from src.models.gae import Encoder, Decoder, GraphAutoEncoder

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
n_epochs = 100


def get_preprocessed_adj(adj, features):
    # # Preprocess the data
    n_nodes, feat_dim = features.shape
    # Store original adjacency matrix (without diagonal entries) for later
    adj_orig = adj
    adj_orig = adj_orig - sp.dia_matrix(
        (adj_orig.diagonal()[np.newaxis, :], [0]), shape=adj_orig.shape
    )
    adj_orig.eliminate_zeros()
    (
        adj_train,
        train_edges,
        val_edges,
        val_edges_false,
        test_edges,
        test_edges_false,
    ) = mask_test_edges(adj)
    adj = adj_train

    # Some preprocessing
    adj_norm = preprocess_graph(adj)
    adj_label = adj_train + sp.eye(adj_train.shape[0])
    adj_label = torch.FloatTensor(adj_label.toarray())
    pos_weight = torch.Tensor([(adj.shape[0] * adj.shape[0] - adj.sum()) / adj.sum()])
    norm = (
        adj.shape[0]
        * adj.shape[0]
        / float((adj.shape[0] * adj.shape[0] - adj.sum()) * 2)
    )

    return (
        adj_norm,
        adj_label,
        norm,
        pos_weight,
        adj_orig,
        val_edges,
        val_edges_false,
        test_edges,
        test_edges_false,
    )


def train_model(animal, version, features, edgelist, adj):
    (
        adj_norm,
        adj_label,
        norm,
        pos_weight,
        adj_orig,
        val_edges,
        val_edges_false,
        test_edges,
        test_edges_false,
    ) = get_preprocessed_adj(adj, features)
    n_nodes, feat_dim = features.shape
    encoder = Encoder(input_feat_dim=feat_dim, hidden_dim1=32, hidden_dim2=16)
    decoder = Decoder()
    autoencoder = GraphAutoEncoder(encoder, decoder)
    encoder.to(device)
    decoder.to(device)

    # Train the Graph vae
    save_dir = os.getcwd().split("src")[0] + "/results/models/"

    autoencoder.fit(
        device,
        features,
        adj_norm,
        adj_label,
        n_nodes,
        norm,
        pos_weight,
        adj_orig,
        val_edges,
        val_edges_false,
        test_edges,
        test_edges_false,
        animal,
        version,
        save_dir,
        n_epochs,
    )


if __name__ == "__main__":
    from glob import glob
    from src.loaders.asnr_dataloader import ASNRGraph

    argp = ArgumentParser()
    argp.add_argument("--seed", default=42, type=int)
    args = argp.parse_args()

    if args.seed:
        np.random.seed(args.seed)
        torch.manual_seed(args.seed)
    
    with open('./datasets/final_datasets.txt') as f:
          lines = f.readlines()
    for path in lines:
        path = path.replace("\n", "")       
        features, edgelist, adj, _, _ = ASNRGraph(path=path).preprocess()
        animal = path.split("/")[-2] #.split(".")[0]
        train_model(animal, "default", features, edgelist, adj)
        print("Animal trained for: ", animal)
   
