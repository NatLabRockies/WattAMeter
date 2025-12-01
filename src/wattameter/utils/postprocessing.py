# SPDX-License-Identifier: BSD-3-Clause
# SPDX-FileCopyrightText: 2025, Alliance for Sustainable Energy, LLC

from datetime import datetime
from collections import deque


def _get_pandas():
    try:
        import pandas as pd
    except Exception as exc:  # pragma: no cover - error path
        raise ImportError(
            "WattAMeter optional dependency 'pandas' is required for postprocessing. "
            "Install it with `pip install wattameter[postprocessing]` or `pip install pandas`. "
            f"Original error: {exc}"
        )
    return pd


def file_to_df(f, timestamp_fmt="%Y-%m-%d_%H:%M:%S.%f", header=None, skip_lines=1):
    """Convert an output file from Wattameter Tracker to a pandas DataFrame.

    :param f: Open file object to read from.
    :param timestamp_fmt: Format string for parsing timestamps.
    :param header: List of column names. If None, the header is read from the
        file.
    :param skip_lines: Number of lines to skip at the beginning of the file.
    """

    pd = _get_pandas()

    # Skip header lines
    for _ in range(skip_lines):
        f.readline()

    # Read header
    if header is None:
        _header = f.readline().split()[1:]
    else:
        _header = header
    _n_fields = len(_header)

    # Read data
    _data = deque([])
    for _line in f:
        _fields = _line.split()
        _numeric_fields = [float("NAN")] * _n_fields
        _numeric_fields[0] = datetime.strptime(_fields[0], timestamp_fmt)
        _numeric_fields[1 : len(_fields)] = [
            pd.to_numeric(val, errors="raise") for val in _fields[1:]
        ]
        _data.append(_numeric_fields)

    # Create dataframe
    df = pd.DataFrame(_data, columns=_header)
    df.set_index(_header[0], inplace=True)

    return df


def align_and_concat_df(_list_df, dt=None, start_at_0=False):
    """Create a single dataframe from multiple dataframes, aligning them in time.

    The column labels of the input dataframes are prefixed with their index in the
    input list to avoid collisions.

    :param _list_df: List of pandas DataFrames to combine. Each DataFrame must have a DateTimeIndex.
    :param dt: Time step in seconds for the new index. If None, the average time step
        across all dataframes is used.
    :param start_at_0: If True, reset the index to start at 0 seconds. If False,
        use time stamps that start at a common start time among the dataframes.
    :return: A single pandas DataFrame with aligned time index and combined data.
    """

    pd = _get_pandas()

    # Compute average dt
    if dt is None:
        _mean_dt = [
            (_df.index[-1] - _df.index[0]).total_seconds() / (len(_df) - 1)
            for _df in _list_df
        ]
        print(f"Average dt per node: {_mean_dt}")
        dt = sum(_mean_dt) / len(_mean_dt)
        print(f"Using dt = {dt} seconds")
    else:
        print(f"Using user-provided dt = {dt} seconds")

    # Find common start time
    max_start_time = max([_df.index[0] for _df in _list_df])
    print(f"Common start time = {max_start_time}")

    # Find common end time
    min_end_time = min([_df.index[-1] for _df in _list_df])
    print(f"Common end time = {min_end_time}")

    # Create new index
    n = int((min_end_time - max_start_time).total_seconds() / dt) + 1
    new_idx = pd.Index(
        [max_start_time + pd.to_timedelta(i * dt, unit="s") for i in range(n)]
    )

    # Use new index
    _copy_of_list_df = []
    for _df in _list_df:
        _idx = _df.index  # old index
        _new_idx = new_idx.difference(_idx)  # new index, removing duplicates

        # add new index to dataframe and interpolate values
        _df = pd.concat([_df, pd.DataFrame(index=_new_idx)]).sort_index()
        _df = _df.interpolate(method="polynomial", order=1)

        # remove old index
        _df = _df.drop(_idx.difference(new_idx))

        # store
        _copy_of_list_df.append(_df)

    # Create single dataframe
    df = pd.DataFrame(index=new_idx)
    for _i, _df in enumerate(_copy_of_list_df):
        _df_prefix = _df.add_prefix(f"{_i}_")
        df = df.add(_df_prefix, fill_value=0)

    # Reset index to start at 0 if requested
    if start_at_0:
        new_idx = pd.Index([i * dt for i in range(n)])
        df.index = new_idx

    return df
