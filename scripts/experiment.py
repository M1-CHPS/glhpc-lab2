#!/usr/bin/env python3
"""_summary_
This script will execute the mytransform application with a predefine pipeline
To benchmark the execution time of the student's implementation.
"""

from pathlib import Path
import pandas as pd
import numpy as np
import subprocess
import matplotlib as mpl

mpl.use("Agg")  # Use a non-interactive backend for matplotlib
import matplotlib.pyplot as plt
import seaborn as sns
import logging

from rich.console import Console
from rich.logging import RichHandler
from rich.progress import Progress
import time

from PIL import Image
from PIL import ImageChops

console = Console()

PIPELINE = (
    "0 -1 load images/image1.bmp\n"
    "1 0 quantize 16\n"
    "2 0 quantize 16\n"
    "3 0 quantize 16\n"
    "4 0 quantize 16\n"
    "5 0 quantize 16\n"
    "6 0 quantize 16\n"
    "7 0 quantize 16\n"
    "8 0 quantize 16\n"
    "9 0 quantize 16\n"
    "10 9 invert\n"
    "11 10 grayscale\n"
    "12 11 save {output}/output.bmp\n"
)

NWARMUP = 5
NMETA = 20
IMAGE_TOLERANCE = 2  # allowed max per-channel difference (0..255)


def run_kernel(kernel, pipeline_file, output_path):
    begin = time.perf_counter()
    subprocess.check_output([str(kernel.resolve()), str(pipeline_file)])
    end = time.perf_counter()
    # Check if the output is valid

    if not output_path.exists():
        raise FileNotFoundError(
            f"Could not find {output_path} ! Your program most likely crashed or did not produce the expected output."
        )

    reference = Path(__file__).parent / "reference.bmp"
    # always compute the pixel-wise difference (work in a fixed mode)
    out_img = Image.open(output_path).convert("RGBA")
    ref_img = Image.open(reference).convert("RGBA")
    diff = ImageChops.difference(out_img, ref_img)

    # diff.getextrema() returns (min,max) tuples per band; take the max channel delta
    extrema = diff.getextrema()
    max_delta = max(band[1] for band in extrema)

    if max_delta > IMAGE_TOLERANCE:
        diff.save(output_path.with_suffix(".diff.bmp"))
        logger.error(f"Generated diff image, saved as {output_path.with_suffix('.diff.bmp')}, max pixel delta = {max_delta}")
        raise ValueError(
            f"Output image {output_path} differs from reference {reference}: max per-channel delta = {max_delta} (tolerance={IMAGE_TOLERANCE})"
        )
    return end - begin


def run_experiment(kernel, pipeline_file, output):
    output_path = output / f"output.bmp"
    with Progress(
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task("Running warmup...", total=NWARMUP)

        for _ in range(NWARMUP):
            subprocess.check_output([str(kernel.resolve()), str(pipeline_file)])
            progress.update(task, advance=1)

        task = progress.add_task("Running experiment...", total=NMETA)
        timings = []
        for i in range(NMETA):
            elapsed_time = run_kernel(kernel, pipeline_file, output_path)
            timings.append((i, elapsed_time))
            progress.update(task, advance=1)
    return pd.DataFrame(timings, columns=["Iteration", "Time"])


def plot(data, output_path):
    logger.info(f"Plotting execution time distribution...")
    fig, ax = plt.subplots(figsize=(10, 6), layout="constrained")
    sns.histplot(
        data=data,
        x="Time",
        kde=True,
        ax=ax,
        color="blue",
    )
    ax.set_title("Pipeline Execution Time Distribution")
    ax.set_xlabel("Time (seconds)")

    fig.savefig(output_path / "timings.png")
    logger.info(f"Plot saved to {output_path / 'timings.png'}")


def update_comparison():
    merged = []
    for file in Path("./results").iterdir():
        if not file.is_dir():
            continue
        df = pd.read_csv(file / "timings.csv")
        df["run"] = file.name
        merged.append(df)

    if not merged or len(merged) < 2:
        logger.warning("Skipping comparison update, not enough runs found.")
        return

    merged_df = pd.concat(merged, ignore_index=True)

    logger.info("Updating comparison...")
    fig, ax = plt.subplots(figsize=(10, 6), layout="constrained")
    sns.barplot(
        data=merged_df,
        x="run",
        y="Time",
        ax=ax,
        hue="run",
        palette="magma",
        lw=2,
        edgecolor="black",
    )

    for container in ax.containers:
        ax.bar_label(container, fmt="%.2fs", padding=8)

    ax.set_title("Average Execution Time Comparison")
    ax.set_xlabel("Versions")
    ax.set_ylabel("Average Time (seconds)")
    fig.savefig(Path("./results/comparison.png"), bbox_inches="tight", dpi=200, pad_inches=0.1)


def main(args):
    global PIPELINE
    PIPELINE = PIPELINE.format(output=args.output)
    pipeline_file = args.output / "pipeline.pipeline"
    with open(pipeline_file, "w") as f:
        f.write(PIPELINE)

    timings = run_experiment(args.kernel, pipeline_file, args.output)

    output_path = args.output / "timings.csv"
    timings.to_csv(output_path, index=False)

    plot(timings, args.output)
    update_comparison()

    logger.info(f"Experiment completed. Results saved to {output_path}")


def setup_logging():
    """Setup logging configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(console=console)],
    )
    logging.getLogger("matplotlib").setLevel(logging.WARNING)
    global logger
    logger = logging.getLogger("rich")
    logger.info("Logging setup complete.")

    return logger


def parse_args():
    import argparse

    parser = argparse.ArgumentParser(description="Analyse data.")
    parser.add_argument(
        "--kernel",
        type=Path,
        help="Path to the mytransform binary",
        default="./mytransform",
    )
    parser.add_argument("output", type=Path, help="Output directory")

    args = parser.parse_args()

    if not args.kernel.exists():
        raise FileNotFoundError(f"Kernel file {args.kernel} does not exist ! Are you sure you ran make ?")
    if not args.output.exists():
        args.output.mkdir(parents=True, exist_ok=True)

    return args


if __name__ == "__main__":
    args = parse_args()
    setup_logging()
    try:
        main(args)
    except Exception as e:
        logger.exception(e, exc_info=True)
