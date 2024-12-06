# same_sky
Check chance coincidence of FRB obs with ZTF

# usage 
Check chance co-incidence of a FRB with ZTF observation of that same field withing a time range

optional arguments:
  -h, --help            show this help message and exit
  -t DELTA_T_MIN, --delta_t_min DELTA_T_MIN
                        The max time difference b/w FRB and ZTF observation of that field in minutes
  -from FROM_ISO, --from_iso FROM_ISO
                        Date in the format YYYY-MM-DD from which the search would be carried
  -to TO_ISO, --to_iso TO_ISO
                        Date in the format YYYY-MM-DD upto which the search would be carried (Defaults to Today)
  -op OP_DIR, --op_dir OP_DIR
                        The output directory to save frb.txt (Defaults to cwd)
