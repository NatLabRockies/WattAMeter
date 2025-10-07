import marimo

__generated_with = "0.16.2"
app = marimo.App(auto_download=["ipynb"])


@app.cell
def _():
    import os
    from pathlib import Path
    from collections import deque
    from datetime import datetime
    import pandas as pd
    from matplotlib import pyplot as plt

    FILE_PATH = Path(os.path.realpath(__file__)).parent
    timestamp_fmt = "%Y-%m-%d_%H:%M:%S.%f"

    rapl_datafile = FILE_PATH / "rapl_wattameter.log"
    print("RAPL file: ", rapl_datafile)
    return datetime, deque, pd, plt, rapl_datafile, timestamp_fmt


@app.cell
def _(datetime, deque, pd, rapl_datafile, timestamp_fmt):
    _header = []
    _data = deque([])

    with open(rapl_datafile, "r") as f:
        # Skip 2 first lines
        print(f.readline(), end="")
        print(f.readline(), end="")

        # Read header
        _header = f.readline().split()[1:]
        _n_fields = len(_header)

        # Read data
        for _line in f:
            _fields = _line.split()
            _numeric_fields = [float("NAN")] * _n_fields
            _numeric_fields[0] = datetime.strptime(_fields[0], timestamp_fmt)
            _numeric_fields[1 : len(_fields)] = [float(val) for val in _fields[1:]]
            _data.append(_numeric_fields)

        # Compute elapsed time
        _t0 = _data[0][0].timestamp()
        elapsed_time = [0.0] * len(_data)
        for _i, _fields in enumerate(_data):
            elapsed_time[_i] = _fields[0].timestamp() - _t0  # in seconds

    df = pd.DataFrame(_data, columns=_header)
    df.set_index(_header[0], inplace=True)

    # Display the first few rows to verify
    print("First few rows of the data:")
    print(df.head())
    print(f"\nDataset shape: {df.shape}")
    print(f"Column names: {df.columns}")
    return (df,)


@app.cell
def _(df, plt):
    print(df["cpu-0[W]"].max())
    df.plot(y="cpu-0[W]")
    plt.show()
    return


@app.cell
def _(df, plt):
    print(df["cpu-1[W]"].max())
    df.plot(y="cpu-1[W]")
    plt.show()
    return


@app.cell
def _(df, plt):
    print(df["cpu-0-core[W]"].max())
    df.plot(y="cpu-0-core[W]")
    plt.show()
    return


@app.cell
def _(df, plt):
    print(df["cpu-1-core[W]"].max())
    df.plot(y="cpu-1-core[W]")
    plt.show()
    return


@app.cell
def _(df):
    # Compute sum of power columns and sum of temperature columns
    _power_columns = [col for col in df.columns if "W]" in col]
    df["total_power"] = df[_power_columns].sum(axis=1)
    return


@app.cell
def _(df, plt):
    # Plot
    df.plot(
        y="reading-time[ns]",
        title="reading-time[ns] over time[ns]",
    )
    plt.yscale("log")
    plt.show()
    return


@app.cell
def _(df, plt):
    # Plot an histogram of reading-time[ns] in log-log scale
    df["reading-time[ns]"].plot(
        kind="hist", logy=True, bins=100, title="Histogram of reading-time[ns]"
    )
    plt.show()
    return


@app.cell
def _(df, plt):
    # Plot an histogram of reading-time[ns] using boxplot
    df["reading-time[ns]"].plot(
        kind="box", title="Boxplot of reading-time[ns]", logy=True
    )
    plt.show()
    return


@app.cell
def _(df):
    # Compute correlation between columns
    correlation_matrix = df.corr()
    print("\nCorrelation matrix:")
    print(correlation_matrix)
    return


if __name__ == "__main__":
    app.run()
