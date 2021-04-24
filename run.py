from time import time

import numpy as np
import pandas as pd
import tensorflow as tf
import torch

from data.dataset import split_without_cold_start
from data.impl.amazon import AmazonReviewsDataset
from data.impl.movielens import MovielensDataset
from evaluation.evaluation import eval_pointwise, eval_top
from models.impl.als import AlsModel
from models.impl.cornac.bivae import BiVAEModel
from models.impl.cornac.bpr import BPRModel
from models.impl.deeprec.lightgcn import LightGCNModel
from models.impl.fastai import FastaiModel
from models.impl.ncf import NCFModel
from models.impl.sar import SarModel
from models.impl.svd import SvdModel

TOP_K = 10
SEED = 42

np.random.seed(SEED)
torch.manual_seed(SEED)
torch.cuda.manual_seed(SEED)

tf.get_logger().setLevel('ERROR')

dataset = AmazonReviewsDataset()
dataset.load()
exit(0)

dataset = MovielensDataset()
dataset.load()
train_hot, valid_hot = split_without_cold_start(dataset, ratio=0.75)

models = [
    AlsModel(),
    BiVAEModel(),
    BPRModel(),
    FastaiModel(),
    LightGCNModel(TOP_K),
    NCFModel(),
    SarModel(),
    SvdModel(),
]

results = []

for model in models:
    print(model.get_name())
    model.on_start()
    t0 = time()
    model.train(train_hot)
    t1 = time()
    pred_top = model.predict_k(train_hot, TOP_K)
    t2 = time()
    pred_scores = model.predict_scores(valid_hot)
    t3 = time()
    results.append({
        **{
            'name': model.get_name(),
            'train_time': t1 - t0,
            'predict_top_time': t2 - t1,
            'predict_all_time': t3 - t2
        },
        **eval_pointwise(valid_hot, pred_scores),
        **eval_top(valid_hot, pred_top, TOP_K),
    })
    model.on_stop()

print(pd.DataFrame.from_records(results))