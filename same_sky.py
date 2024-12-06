#!/usr/bin/env python

import requests
import json
import pandas as pd
from astropy.time import Time
from astropy import units as u
from ztfquery import skyvision
from ztfquery import fields
import os
import datetime
import argparse

import warnings

warnings.filterwarnings("ignore")


def voe_DB():
    r = requests.get(
        "https://storage.googleapis.com/chimefrb-dev.appspot.com/voevents/chimefrb_voevent_data.json"
    )

    json_list = r.json()

    rows = []
    for entry in json_list:
        records = pd.json_normalize(entry["records"])
        records["event_id"] = entry["event_id"]
        rows.append(records)

    df = pd.concat(rows, ignore_index=True)
    return df


def manipulate(df_raw):
    # remove retracted alerts
    removed = df_raw.event_id[df_raw.Alert_Type == "Retraction"].tolist()
    df_real = df_raw[~df_raw["event_id"].isin(removed)]

    # convert detction time to jd
    df_real.Detected = df_real.Detected.apply(lambda x: x.split("+")[0])
    time_obj = Time(df_real.Detected.to_list())
    df_real["jd_det"] = time_obj.jd
    df_real["date"] = [x.datetime.date() for x in time_obj]
    df_real["time"] = [x.datetime.time() for x in time_obj]

    df_real.drop(columns=["Detected", "Published"], inplace=True)

    return df_real


def same_sky(delta_t_min=None, from_iso=None, to_iso=None, op_dir=None):
    df_voe = voe_DB()  # Collect the entire VOE FRB databse
    df_real = manipulate(df_voe)

    delta_t_min = delta_t_min * u.min

    from_iso = datetime.date.fromisoformat(from_iso)
    if to_iso is not None:
        to_iso = datetime.date.fromisoformat(to_iso)
    else:
        to_iso = datetime.date.today()

    df_real = df_real[df_real.date.between(from_iso, to_iso)]

    with open(os.path.join(op_dir, "frb.txt"), "w") as f:
        f.write(f"{len(df_real)} FRB events found b/w {from_iso} : {to_iso}")
        f.write(f" List of ZTF obs of FRB field within time range {delta_t_min}")

        for i in range(len(df_real)):
            try:
                frb_date = df_real.iloc[i].date.isoformat()
                frb_jd = df_real.iloc[i].jd_det
                ra_frb, dec_frb = df_real.iloc[i].RA, df_real.iloc[i].Dec

                logs = skyvision.CompletedLog.from_date(frb_date, update=True)

                ztf_field_jd = logs.get_filtered(
                    fields.get_fields_containing_target(ra_frb, dec_frb)
                ).obsjd.to_numpy()

                delta_frb_ztf = abs(frb_jd - ztf_field_jd) * u.day

                if len(ztf_field_jd) > 0:
                    in_range = [one for one in delta_frb_ztf if one < delta_t_min]

                    if in_range:
                        f.write(
                            f"\n\nFound ZTF obs of FRB field within {delta_frb_ztf.to(u.minute)} \n"
                        )
                        f.write(f"FRB details:\n {df_real.iloc[i]}")

            except AttributeError:
                pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Check chance co-incidence of a FRB with ZTF observation of that same field withing a time range "
    )

    parser.add_argument(
        "-t",
        "--delta_t_min",
        type=float,
        default=1440,
        help="The max time difference b/w FRB and ZTF observation of that field in minutes ",
    )
    parser.add_argument(
        "-from",
        "--from_iso",
        type=str,
        default="2021-10-09",
        help="Date in the format YYYY-MM-DD from which the search would be carried ",
    )
    parser.add_argument(
        "-to",
        "--to_iso",
        type=str,
        help="Date in the format YYYY-MM-DD upto which the search would be carried (Defaults to Today) ",
    )
    parser.add_argument(
        "-op",
        "--op_dir",
        type=str,
        default=os.getcwd(),
        help="The output directory to save frb.txt (Defaults to cwd) ",
    )

    args = parser.parse_args()
    same_sky(**vars(args))
