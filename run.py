from time import time

import numpy as np
import pandas as pd
import tensorflow as tf
import torch

from data.dataset import split_without_cold_start
from data.impl.movielens import MovielensDataset
from evaluation.evaluation import eval_pointwise, eval_top
from models.ensembling.ensemble_model import EnsembleModel
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

ensemble = EnsembleModel(models)

results = []

for model in models:
    model.on_start()

for model in models + [ensemble]:
    print(model.get_name())
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

for model in models:
    model.on_stop()

results_df = pd.DataFrame.from_records(results)
results_df['ensemble_weight'] = np.zeros(len(results_df))
for i in range(len(ensemble.models)):
    results_df[results_df.name == ensemble.models[i].get_name()].ensemble_weight = ensemble.ensemble_model.coef_[i]
results_df.ensemble_weight = results_df.ensemble_weight / results_df.ensemble_weight.sum()
results_df[results_df.name == ensemble.get_name()].ensemble_weight = 1
results_df.to_csv('results.tsv', sep='\t', index=False)
print(results_df)
print("Models selected: ", [x.get_name() for x in ensemble.models])