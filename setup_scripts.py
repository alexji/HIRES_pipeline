"""
Steps:
- Specify Flat Frame Numbers
- Specify Arcs Frame Number
"""
import numpy as np
import os, sys, time, glob

from astropy.table import Table
from astropy.io import fits
from alexmods.specutils import Spectrum1D

DATA_DIR = "./raw_data"
ABS_DATA_DIR = os.path.abspath(DATA_DIR)
FLAT1NUMS = list(range(142,151+1))
FLAT1PREFIX = "flat1master"
FLAT2NUMS = list(range(158,167+1))
FLAT2PREFIX = "flat2master"
ARCNUM = 101
MANUAL_TRACE_DICT = { # manually specify the trace file for some objects
    "SDV6416":"hires0114",
}

def main():
    if not os.path.exists("reduction_outputs"):
        print("Creating reduction_outputs/")
        os.mkdir("reduction_outputs")
    if not os.path.exists("reduction_outputs/raw_data"):
        print("Creating reduction_outputs/raw_data symlink")
        os.system(f"cd reduction_outputs; ln -s {ABS_DATA_DIR} raw_data; cd ..")
    if not os.path.exists("Final-Products"):
        print("Creating Final-Products/")
        os.mkdir("Final-Products")
    write_master_flat_script()
    write_reduction_table()
    write_reduction_scripts()
    write_postprocessing_scripts()
    write_coadd_scripts()

def write_master_flat_script():
    flat1fnames = [f"{DATA_DIR}/hires{num:04d}.fits" for num in FLAT1NUMS]
    flat2fnames = [f"{DATA_DIR}/hires{num:04d}.fits" for num in FLAT2NUMS]
    with open("master_flat_script.sh", "w") as fp:
        def write(x): fp.write(x + "\n")
        write("#!/bin/bash")
        for fname in flat1fnames+flat2fnames:
            print(fname)
            write(f"HIRES2_readwrite {fname} mode=5")

        for ccd in [1,2,3]:
            fnames = " ".join([f"{fn.replace('.fits','')}_{ccd}.fits" for fn in flat1fnames])
            write(f"flatave "+fnames)
            write(f"mv flat001.fits {DATA_DIR}/{FLAT1PREFIX}_{ccd}.fits")

            fnames = " ".join([f"{fn.replace('.fits','')}_{ccd}.fits" for fn in flat2fnames])
            write(f"flatave "+fnames)
            write(f"mv flat001.fits {DATA_DIR}/{FLAT2PREFIX}_{ccd}.fits")
        
    os.system("chmod +x master_flat_script.sh")
    print("master_flat_script.sh created")
    print(f"will create {DATA_DIR}/{FLAT1PREFIX}_*.fits and {DATA_DIR}/{FLAT2PREFIX}_*.fits")

def write_reduction_table(unique_obj_as_trace=True):
    # Columns are FILE, OBJECT
    tab = Table.read("obslog.txt", format="ascii")
    tab.rename_column("OBJECT", "OBJNAME")
    tab["NUM"] = [int(os.path.basename(row["FILE"]).replace("hires","").replace(".fits","")) for row in tab]
    # Add TRACE, ARC, FLAT1, FLAT2
    tab["FLAT1PREFIX"] = FLAT1PREFIX
    tab["FLAT2PREFIX"] = FLAT2PREFIX
    tab["ARC"] = f"hires{ARCNUM:04d}.fits"

    tab["TRACE"] = tab["FILE"]
    if unique_obj_as_trace:
        objects = np.unique(tab["OBJNAME"])
        for obj in objects:
            if obj in MANUAL_TRACE_DICT:
                file_to_use = MANUAL_TRACE_DICT[obj]+".fits"
                tab["TRACE"][tab["OBJNAME"]==obj] = file_to_use
                print("Using {} as trace for {} (MANUAL)".format(file_to_use, obj))
            else:
                obj_rows = tab[tab["OBJNAME"]==obj]
                snrs = [fits.getheader(DATA_DIR+"/"+row["FILE"])["SIG2NOIS"] for row in obj_rows]
                ix = np.argmax(snrs)
                file_to_use = obj_rows[ix]["FILE"]
                tab["TRACE"][tab["OBJNAME"]==obj] = file_to_use
                print("Using {} as trace for {}".format(file_to_use, obj))
            
    tab.write("reduction_table.txt", format="ascii.fixed_width_two_line", overwrite=True)

run_script_template = """#!/bin/bash
MAKEE="makee -noskyshift -novac"
OBJNAME={0:}
OBJ={1:}
TRACE={2:}
FLAT1={3:}_1.fits
FLAT2={3:}_2.fits
FLAT3={4:}_3.fits
ARC={5:}

cd reduction_outputs
mkdir -p out_{0:}
cd out_{0:}
$MAKEE ../$OBJ ../$TRACE ../$FLAT1 ../$ARC ccdloc=1 >& $OBJNAME.log_1
$MAKEE ../$OBJ ../$TRACE ../$FLAT2 ../$ARC ccdloc=2 >& $OBJNAME.log_2
$MAKEE ../$OBJ ../$TRACE ../$FLAT3 ../$ARC ccdloc=3 >& $OBJNAME.log_3
cd ../..
"""
def write_reduction_scripts():
    all_run_script_fnames = []
    tab = Table.read("reduction_table.txt", format="ascii.fixed_width_two_line")
    for row in tab:
        filename = os.path.basename(row["FILE"]).replace(".fits","")
        objfile = DATA_DIR+"/"+row["FILE"]
        tracefile = DATA_DIR+"/"+row["TRACE"]
        flat1file = DATA_DIR+"/"+row["FLAT1PREFIX"]
        flat2file = DATA_DIR+"/"+row["FLAT2PREFIX"]
        arcfile = DATA_DIR+"/"+row["ARC"]
        run_script_fname = f"reduction_outputs/run_{filename}.sh"
        with open(run_script_fname, "w") as fp:
            fp.write(run_script_template.format(filename, objfile, tracefile, 
                                                flat1file, flat2file, arcfile))
        all_run_script_fnames.append(run_script_fname)
        os.system(f"chmod +x {run_script_fname}")
        print(f"wrote {run_script_fname}")
    with open("run_all_reduction.sh", "w") as fp:
        for fname in all_run_script_fnames:
            fp.write(f"./{fname}\n")
    os.system("chmod +x run_all_reduction.sh")

def write_postprocessing_scripts():
    tab = Table.read("reduction_table.txt", format="ascii.fixed_width_two_line")
    with open("postprocess.sh", "w") as fp:
        def write(x): fp.write(x + "\n")
        write("#!/bin/bash")
        for row in tab:
            num = f'{row["NUM"]:04d}'
            path = "reduction_outputs/out_"+os.path.basename(row["FILE"]).replace(".fits","")
            write(f"python read_hires.py {num} {path}")
    os.system("chmod +x postprocess.sh")
    print("postprocess.sh created")

def write_coadd_scripts():
    tab = Table.read("reduction_table.txt", format="ascii.fixed_width_two_line")
    objects = np.unique(tab["OBJNAME"])

    with open("run_coadd.sh", "w") as fp:
        def write(x): fp.write(x + "\n")
        write("#!/bin/bash")

        for obj in objects:
            obj_rows = tab[tab["OBJNAME"]==obj]
            out_dirs = [f"reduction_outputs/out_{os.path.basename(row['FILE']).replace('.fits','')}" for row in obj_rows]
            files_to_coadd = [f"{outdir}/orders_{num:04d}/{num:04d}_multi.fits" for outdir,num in zip(out_dirs, obj_rows["NUM"])]
            outfname = f"Final-Products/{obj}.fits"
            write(f"python coadd.py {outfname} {' '.join(files_to_coadd)}")

    os.system("chmod +x run_coadd.sh")
    print("run_coadd.sh created")

if __name__ == "__main__":
    main()
