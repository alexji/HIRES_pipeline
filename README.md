# HIRES_pipeline
Pipeline for running MAKEE for HIRES

Requires `alexmods` for spectrum processing.

When you download from KOA, make sure you download using the `hiresXXXX` filename format, as I have assumed that throughout for simplicity.

Note that this pipeline will likely not work out of the box. You'll need to pay attention and understand what's going on in order for it to go smoothly.
I would strongly recommend trying to reduce just one star all the way before you run the whole pipeline.

## Step 0
* Install alexmods https://github.com/alexji/alexmods
* Install MAKEE https://www2.keck.hawaii.edu/inst/common/makeewww/. 

MAKEE is kind of annoying to install. To get pgplot and X11 to work on a Mac, I install XQuartz CarPy and edit `*/Makefile` in MAKEE to link to the right X11 and pgplot libraries. You'll also need to make sure you have gcc and gfortran installed (I usually use homebrew, but you'll need to add flags due to legacy fortran issues, and make sure you are running the homebrew gcc and gfortran together).

## Step 1
Create `obslog.txt` a text file that can be read by `astropy.ascii.read` with columns `FILE` and `OBJECT`.
You want to only have science files in here, not calibration.

To create `obslog.txt` I usually use something like:
```
cd <my_raw_data_dir>
dfits *fits | fitsort object exptime > ../obslog.txt
```
`dfits` and `fitsort` are part of ESO Eclipse: https://www.eso.org/sci/software/eclipse/

Then you can manually edit the file to have what you want.
The pipeline will attempt to coadd anything where `OBJECT` is the same so if you want separate spectra for each frame then give them different names manually.

## Step 2
Put all the science and calibration files into the `raw_data` directory, and specify that path.
Decide on which flats and arc numbers you want to do.
Manually edit the start of `setup_scripts.py` to have these.
FLAT1 is used for the blue/green chips, FLAT2 is used for the red chip, in case you care.

TODO check how the data directory symlink works in less good situations.

Then:
```
python setup_scripts.py
```

This creates all the scripts that will be run.
You can look at `reduction_table.txt` to see all the choices that have been made for what arc, flat, and trace files are being used to reduce each science file.

The most common failure mode I have encountered is problems with the trace star.
By default, I grab all the spectra with the same `OBJECT` and pick the one with the highest S/N (in the HIRES header) for tracing all frames of that star. You can change the setup script to use each frame individually, but I have found this is bad because it tends to result in different orders for different frames.

If you have a good trace star, you can use that instead for everything (TODO make this easy)

## Step 3
```
./master_flat_script.sh
```
Uses MAKEE to create a master flat. Should be a few seconds.

## Step 4
```
./run_all_reduction.sh
```
The main reduction step.
This goes through each file and runs MAKEE (using the flags `-noskyshift` and `-novac` as appropriate for stars).
If you want to see exactly what is being run, check `reduction_outputs/run_hiresXXXX.sh`.
Make sure to run it from the top level directory as the script 
The work is done in `reduction_outputs/out_hiresXXXX/`
MAKEE is quite fast, but this will still take many minutes if you have a lot of data.

## Step 5
Assuming everything went well with MAKEE, you can run:
```
./postprocess.sh
```
Which will take the MAKEE outputs and put them in my echelle spectrum format.
This ends up being in `reduction_outputs/out_hiresXXXX/orders_XXXX/XXXX_multi.fits`, with the individual orders saved there as separate files as well.
This will print out errors if things did not go well in the reduction step, and you need to go back and fix/rerun anything that broke (e.g. bad traces)

## Step 6
Once you have it all, you can do
```
./run_coadd.sh
```
Which will coadd everything and put it into a new directory `Final-Products/`
This includes creating quick plots of the individual spectra + coadded spectrum
(TODO make it possible to disable plot making since this actually dominates the runtime)
