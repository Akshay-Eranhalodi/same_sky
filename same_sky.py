#!/usr/bin/env python

import requests
import pandas as pd
from astropy.time import Time
from astropy import units as u
from ztfquery import skyvision
from ztfquery import fields
import os
import datetime
import argparse
import numpy as np

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


def result_df(
    logs_obs_frb, delta_frb_ztf, delta_t_min, df_one_frb, df_result, head_frb, head_log
):
    logs_obs_frb["delta_frb_ztf"] = delta_frb_ztf.to(u.minute).value
    mask = logs_obs_frb.delta_frb_ztf.between(-delta_t_min, delta_t_min)
    masked_logs = logs_obs_frb[mask]

    frb_details = [
        df_one_frb.event_id,
        df_one_frb.jd_det,
        df_one_frb.date,
        df_one_frb.time,
    ]
    for j in range(len(masked_logs)):
        log_details = [
            logs_obs_frb.iloc[j].datetime,
            logs_obs_frb.iloc[j].exptime,
            logs_obs_frb.iloc[j].obsjd,
            logs_obs_frb.iloc[j].delta_frb_ztf,
        ]
        row = {
            **dict(zip(head_frb, frb_details)),
            **dict(zip(head_log, log_details)),
        }
        df_result.loc[len(df_result)] = row
    return df_result


def same_sky(delta_t_min=None, from_iso=None, to_iso=None, op_file=None):
    df_voe = voe_DB()  # Collect the entire VOE FRB databse
    df_real = manipulate(df_voe)

    delta_t_min = delta_t_min * u.min

    from_iso = datetime.date.fromisoformat(from_iso)
    if to_iso is not None:
        to_iso = datetime.date.fromisoformat(to_iso)
    else:
        to_iso = datetime.date.today()

    df_real = df_real[df_real.date.between(from_iso, to_iso)]
    fmt_err = []
    head_frb = ["event_id", "FRB_jd", "FRB_date", "FRB_time"]
    head_log = ["ztf_datetime", "exposure", "ztf_jd", "delta_min"]

    df_result = pd.DataFrame(columns=head_frb + head_log)

    with open(op_file, "w") as f:
        f.write(f"{len(df_real)} FRB events found b/w {from_iso} : {to_iso}")
        f.write(f"\nList of ZTF obs of FRB fields within time range {delta_t_min}")

        for i in range(len(df_real)):
            try:
                frb_date = df_real.iloc[i].date.isoformat()
                frb_jd = df_real.iloc[i].jd_det
                ra_frb, dec_frb = df_real.iloc[i].RA, df_real.iloc[i].Dec

                logs = skyvision.CompletedLog.from_date(frb_date, update=True)

                logs_obs_frb = logs.get_filtered(
                    fields.get_fields_containing_target(ra_frb, dec_frb)
                )

                ztf_field_jd = logs_obs_frb.obsjd.to_numpy()

                delta_frb_ztf = (ztf_field_jd - frb_jd) * u.day

                if len(ztf_field_jd) > 0:
                    in_range = [one for one in delta_frb_ztf if abs(one) < delta_t_min]

                    if in_range:
                        f.write(
                            f"\n\nFound ZTF obs of FRB field within {delta_frb_ztf.to(u.minute)} \n"
                        )
                        f.write(f"FRB details:\n {df_real.iloc[i]}")
                        df_result = result_df(
                            logs_obs_frb,
                            delta_frb_ztf,
                            delta_t_min,
                            df_real.iloc[i],
                            df_result,
                            head_frb,
                            head_log,
                        )

            except Exception as e:
                if (
                    str(e) == "list indices must be integers or slices, not str"
                    or str(e) == "'CompletedLog' object has no attribute '_logs'"
                ):
                    pass  # To skip cases with wrong formattting (eg: 2022-12-08 ) or with days with no logs but are still loaded to CompletedLog object (eg: 2021-10-21)
                else:
                    raise
        f.write(
            f"\n\nFormat error of logs for the dates \n{np.unique(np.asarray(fmt_err))}"
        )
        df_result.to_csv("./frb_ztf_sky.csv", index=False)


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
        "--op_file",
        type=str,
        default=os.path.join(os.getcwd(), "frb.txt"),
        help="The output file (Defaults to CWD/frb.txt) ",
    )

    args = parser.parse_args()
    same_sky(**vars(args))
