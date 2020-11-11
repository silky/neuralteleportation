import os
import numpy as np
import seaborn as sns
import pandas as pd
from comet_ml.api import APIExperiment
from matplotlib import pyplot as plt
from io import StringIO
from tqdm import tqdm
from glob import glob
from pathlib import Path


def shim_metric_name(metric_name):
    # This is used to normalize the metrics names between Comet and CSV
    name_map = {
        "val_loss": "validate_loss",
        "val_accuracy": "validate_accuracy",
        "val_accuracy_top5": "validate_accuracy_top5",
    }
    return name_map[metric_name] if metric_name in name_map.keys() else metric_name


def get_metrics(exp, csv_file_path=None):
    # Fetches CSV file from comet and generates cometAPI style metrics list,
    # if no csv file is found on comet, fallsback on the comet metrics.
    if csv_file_path is None:
        asset_id = [asset["assetId"] for asset in exp.get_asset_list() if asset["fileName"] == "metrics.csv"]
        if len(asset_id) == 0:
            print("WARN: metrics.csv not found as a comet asset, falling back on comet metrics.")
            return exp.get_metrics()
        asset_content = exp.get_asset(asset_id, return_type="text")
        buff = StringIO(asset_content)
    else:
        buff = csv_file_path
    df = pd.read_csv(buff)
    metrics = []
    for _, row in df.iterrows():
        r_keys = [k for k in row.keys() if k != "step"]
        for k in r_keys:
            metric_obj = {
                "epoch": int(row["step"]),
                "metricName": shim_metric_name(k),
                "metricValue": row[k],
            }
            metrics.append(metric_obj)
    return metrics


def fetch_comet_data(exps_ids, metrics_filter, hparams_filter, group_by, experiments_csv_dict=None):
    all_metrics_grouped = {}
    for exp_id in tqdm(exps_ids, desc="Fetching data: "):
        exp = APIExperiment(previous_experiment=exp_id)
        hparams = exp.get_parameters_summary()
        hparams = [hparam for hparam in hparams if hparam["name"].lower() in hparams_filter]
        g_by_param = [hparam for hparam in hparams if hparam["name"].lower() == group_by]
        assert len(g_by_param) > 0, f"ERROR: Experiment {exp_id} does not have the hyperparameter {group_by}!"
        g_by_param = g_by_param[0]["valueCurrent"]
        if experiments_csv_dict is not None and exp_id in experiments_csv_dict.keys():
            metrics = get_metrics(exp, csv_file_path=experiments_csv_dict[exp_id])
        else:
            metrics = get_metrics(exp)
        metrics = [metric for metric in metrics if metric["metricName"].lower() in metrics_filter]
        metrics_dict = {}
        for metric in metrics:
            name = metric["metricName"]
            value = metric["metricValue"]
            epoch = metric["epoch"]
            if name not in metrics_dict.keys():
                metrics_dict[name] = {epoch: value}
            else:
                metrics_dict[name][epoch] = value
        if g_by_param not in all_metrics_grouped.keys():
            all_metrics_grouped[g_by_param] = [metrics_dict]
        else:
            all_metrics_grouped[g_by_param].append(metrics_dict)
    return all_metrics_grouped


def shim_param_name(g_name):
    name_map = {
        "random": "teleport",
    }
    return name_map[g_name] if g_name in name_map.keys() else g_name


def find_best_legend_pos(metric_name):
    metric_name = metric_name.lower()
    if "loss" in metric_name:
        return "upper right"
    if "accuracy" in metric_name:
        return "lower right"
    return "best"


def plot_mean_std_curve(metrics_grouped, metric_name, group_by, output_dir):
    # Upper bound on epochs, will be trimmed to max epochs
    n_epochs = 1000
    grouped_plots = {}
    for g_name in metrics_grouped.keys():
        g_metrics = metrics_grouped[g_name]
        nb_runs = len(g_metrics)
        g_data = np.zeros((n_epochs, nb_runs), dtype=np.float32)
        max_epochs = 0
        for i in range(nb_runs):
            run_metric = g_metrics[i][metric_name]
            for k in run_metric.keys():
                g_data[k, i] = float(run_metric[k])
                max_epochs = max(k, max_epochs)
        g_data = g_data[:max_epochs, :]
        grouped_plots[g_name] = {
            "data": g_data,
            "mean": np.mean(g_data, axis=1),
            "std": np.std(g_data, axis=1),
            "max_epochs": max_epochs
        }
    with sns.axes_style("darkgrid"):
        fig, ax = plt.subplots()
        fig.suptitle(f"{metric_name}")
        output_filename = os.path.join(output_dir, f"{metric_name}_{group_by}.png")
        clrs = sns.color_palette("husl", len(list(grouped_plots.keys())))
        for i, g_name in enumerate(list(grouped_plots.keys())):
            epochs = range(grouped_plots[g_name]["max_epochs"])
            g_mean = grouped_plots[g_name]["mean"]
            g_std = grouped_plots[g_name]["std"]
            ax.plot(epochs, g_mean, label=shim_param_name(g_name), c=clrs[i])
            ax.fill_between(epochs, g_mean - g_std, g_mean + g_std, alpha=0.3, facecolor=clrs[i])
            ax.set_ylabel(f"{metric_name}")
            ax.set_xlabel("epoch")
        ax.legend(loc=find_best_legend_pos(metric_name))
        plt.savefig(output_filename)
        print(f"Saved plot at : {output_filename}")


def parse_experiments_dir(experiment_dir):
    # Parser directory into experiment ids and their metrics.csv path
    all_dirs = glob(os.path.join(experiment_dir, "**/*.csv"), recursive=True)
    all_dirs = [p for p in all_dirs if "metrics.csv" in p.lower()]
    experiments_dict = {}
    for p in all_dirs:
        experiment_id = os.path.basename(os.path.dirname(p))
        experiments_dict[experiment_id] = p
    return experiments_dict, list(experiments_dict.keys())

if __name__ == '__main__':
    from argparse import ArgumentParser

    parser = ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--experiment_ids",
        type=str,
        nargs="+",
        help="IDs of the experiments to plot",
        default=None
    )
    group.add_argument(
        "--experiment_dir",
        type=str,
        help="Folder containing metrics.csv for each experiment",
        default=None
    )
    parser.add_argument(
        "--metrics",
        type=str,
        nargs="+",
        help="Metrics to plot curves for.",
        required=True
    )
    parser.add_argument(
        "--group_by",
        type=str,
        help="Hyperparameter to group experiments with.",
        required=True
    )
    parser.add_argument(
        "--out_dir",
        type=Path,
        help="Output directory to save figures in.",
        required=True
    )
    args = parser.parse_args()

    experiments_csv_dict = None
    experiments_ids = args.experiment_ids
    if args.experiment_ids:
        if len(args.experiment_ids) <= 1:
            print("ERROR: can't generate plots for one experiment!")
            exit(1)

    if args.experiment_dir:
        if not os.path.exists(args.experiment_dir):
            print(f"ERROR: {args.experiment_dir} does not exist!")
            exit(1)
        experiments_csv_dict, experiments_ids = parse_experiments_dir(args.experiment_dir)

    if not os.path.exists(args.out_dir):
        os.makedirs(args.out_dir, exist_ok=True)

    all_metrics_grouped = fetch_comet_data(experiments_ids, args.metrics, [args.group_by], args.group_by,
                                           experiments_csv_dict=experiments_csv_dict)
    for metric in args.metrics:
        plot_mean_std_curve(all_metrics_grouped, metric, args.group_by, args.out_dir)
