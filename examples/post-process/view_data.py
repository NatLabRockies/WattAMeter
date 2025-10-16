import marimo

__generated_with = "0.16.2"
app = marimo.App(width="medium", auto_download=["html"])


@app.cell
def _():
    from wattameter.utils import file_to_df, align_and_concat_df
    import matplotlib.pyplot as plt
    import re
    import marimo as mo

    return align_and_concat_df, file_to_df, mo, plt, re


@app.cell
def _(align_and_concat_df, file_to_df, re):
    _files = [
        "nvml_wattameter.log",
        "rapl_wattameter.log",
    ]
    df = align_and_concat_df([file_to_df(open(f)) for f in _files], start_at_0=True)

    # Add a few columns
    _cpu_power_columns = [col for col in df.columns if re.search(r"cpu-\d+\[W\]", col)]
    _gpu_power_columns = [col for col in df.columns if re.search(r"gpu-\d+\[mW\]", col)]
    _readt_columns = [col for col in df.columns if "reading-time" in col]
    if len(_cpu_power_columns) > 1:
        df["cpu_power[W]"] = df[_cpu_power_columns].sum(axis=1)
    if len(_gpu_power_columns) > 1:
        df["gpu_power[W]"] = df[_gpu_power_columns].sum(axis=1) * 1e-3
    if len(_cpu_power_columns) > 1 and len(_gpu_power_columns) > 1:
        df["total_power[W]"] = df["cpu_power[W]"] + df["gpu_power[W]"]
    if len(_readt_columns) > 1:
        df["total_readt[s]"] = df[_readt_columns].sum(axis=1) * 1e-9

    df
    return (df,)


@app.cell
def _(df, mo):
    array_ui = mo.ui.array(
        [
            mo.ui.multiselect(
                df.columns, value=["total_power[W]", "cpu_power[W]", "gpu_power[W]"]
            ),
            mo.ui.checkbox(label="Log scale", value=False),
        ]
    )
    array_ui
    return (array_ui,)


@app.cell
def _(array_ui, df, plt):
    _columns = array_ui[0].value
    _logy = array_ui[1].value

    if _columns:
        df[_columns].plot(style="-")
        plt.xlabel("time (s)")
        plt.legend()
        if _logy:
            plt.yscale("log")

        for _col in _columns:
            print(f"{_col}:")
            print(f"  Avg    = {df[_col].mean()}")
            print(f"  Std    = {df[_col].std()}")
            print(f"  Median = {df[_col].median()}")
            print(f"  Min    = {df[_col].min()}")
            print(f"  Max    = {df[_col].max()}")

    plt.gca()
    return


if __name__ == "__main__":
    app.run()
