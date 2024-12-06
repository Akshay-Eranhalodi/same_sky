# same_sky
Check chance coincidence of FRB obs with ZTF

# usage 
Check chance co-incidence of a FRB with ZTF observation of that same field withing a time range

usage: same_sky.py [-h] [-t ] [-from ] [-to ] [-op ]

optional arguments:

  -h, --help            show this help message and exit
  
  -t , --delta_t_min 
  
                        The max time difference b/w FRB and ZTF observation of that field in minutes
                        
  -from , --from_iso
  
                        Date in the format YYYY-MM-DD from which the search would be carried
                        
  -to , --to_iso
  
                        Date in the format YYYY-MM-DD upto which the search would be carried (Defaults to Today)
                        
  -op , --op_dir
  
                        The output directory to save frb.txt (Defaults to cwd)
