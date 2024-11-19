import os, sys, time, glob
import numpy as np
import matplotlib.pyplot as plt

from astropy.io import ascii

from alexmods.specutils import Spectrum1D

WTOL_DEFAULT = 0.02

def check_alignment(fnames, wtol = WTOL_DEFAULT):
    all_wave_mids = []
    all_N_orders = []

    for fname in fnames:
        specs = Spectrum1D.read(fname)
        wave1 = np.array([np.min(spec.dispersion) for spec in specs])
        wave2 = np.array([np.max(spec.dispersion) for spec in specs])
        wavemid = 0.5*(wave1+wave2)
        all_wave_mids.append(wavemid)
        all_N_orders.append(len(specs))
        
    all_N_orders = np.array(all_N_orders)
    if not np.all(all_N_orders == all_N_orders[0]):
        print(f"Not all spectra have the same number of orders")
        print(all_N_orders)
        print(all_wave_mids)
        return False
    else:
        print(f"{all_N_orders[0]} orders per spectrum")
    all_wave_mids = np.array(all_wave_mids)
    wavemids = np.all(np.max(all_wave_mids, axis=0) - np.min(all_wave_mids, axis=0) < wtol)
    ## All good
    if wavemids: return True
    print("Failure, misaligned wavelengths")
    for j in range(all_wave_mids.shape[1]):
        print(all_wave_mids[j])
    return False

def run_coadd(outfname, in_fnames, wtol = WTOL_DEFAULT):
    start = time.time()
    print(f"Coadding {in_fnames} to {outfname}")
    Nframe = len(in_fnames)
    specs = Spectrum1D.read(in_fnames[0])
    Nord = len(specs)
    Npix = len(specs[0].dispersion)
    outdir = os.path.dirname(outfname)
    print(f"Writing to {outdir} Nframe={Nframe} Nord={Nord} Npix={Npix}")
    fig1fname = outfname.replace(".fits","_spectra.png")
    fig2fname = outfname.replace(".fits","_snr.png")
    assert fig1fname != fig2fname, outfname
    
    all_waves = np.zeros((Nframe, Nord, Npix))
    all_fluxs = np.zeros((Nframe, Nord, Npix))
    all_errs = np.zeros((Nframe, Nord, Npix)) + np.inf
    
    for i, fname in enumerate(in_fnames):
        specs = Spectrum1D.read(fname)
        for j, spec in enumerate(specs):
            all_waves[i,j,:] = spec.dispersion
            all_fluxs[i,j,:] = spec.flux
            all_errs[i,j,:] = spec.ivar**-0.5
    
    # Check wavelength alignment before coadding
    for j in range(Nord):
        assert np.all(np.max(all_waves[:,j,:], axis=0) - np.min(all_waves[:,j,:], axis=0) < wtol), \
            (j, np.max(all_waves[:,j,:], axis=0) - np.min(all_waves[:,j,:], axis=0))
    
    # Total flux and variance just sum
    total_flux = np.sum(all_fluxs, axis=0)
    total_vars = np.sum(all_errs**2, axis=0)
    # total_errs = np.sqrt(total_vars)
    final_specs = []

    Ncol = 5
    Nrow = int(np.ceil(Nord/5))
    
    print(f"Plotting... ({time.time()-start:.1f}s)")
    fig1, axes1 = plt.subplots(Nrow, Ncol, figsize=(Ncol*5, Ncol*3))
    fig2, axes2 = plt.subplots(Nrow, Ncol, figsize=(Ncol*5, Ncol*3))
    for j in range(Nord):
        spec = Spectrum1D(all_waves[0,j,:], total_flux[j], 1/total_vars[j])
        final_specs.append(spec)
        
        ax1, ax2 = axes1.flat[j], axes2.flat[j]
        for i in range(Nframe):
            ax1.plot(all_waves[i,j], all_fluxs[i,j]/np.nanmedian(all_fluxs[i,j]), lw=1, rasterized=True)
            ax2.plot(all_waves[i,j], all_fluxs[i,j]/all_errs[i,j], lw=1, rasterized=True)
        ax1.plot(spec.dispersion, spec.flux/np.nanmedian(spec.flux), 'k-', lw=1, rasterized=True)
        ax2.plot(spec.dispersion, spec.flux*spec.ivar**0.5, 'k-', lw=1, rasterized=True)
        for ax in [ax1, ax2]:
            ax.set_xlim(spec.dispersion[0], spec.dispersion[-1])
            ax.text(.01,.99,f"{j:02}", ha='left', va='top', transform=ax.transAxes)
        ymin, ymax = np.nanpercentile(all_fluxs[i,j]/np.nanmedian(all_fluxs[i,j]), [1,99], axis=0)
        dy = ymax-ymin
        ax1.set_ylim(ymin-0.1*dy, ymax+0.1*dy)
    print(f"Saving... ({time.time()-start:.1f}s)")
    fig1.tight_layout()
    fig2.tight_layout()
    fig1.savefig(fig1fname, dpi=300)
    fig2.savefig(fig2fname, dpi=300)
    plt.close('all')
    print(f"Done! {time.time()-start:.1f}s")
    Spectrum1D.write_alex_spectrum_from_specs(outfname, final_specs, overwrite=True)
    
if __name__=="__main__":
    outfname = sys.argv[1]
    in_fnames = sys.argv[2:]

    if check_alignment(in_fnames):
        run_coadd(outfname, in_fnames)
    else:
        print(f"Failed wavelength/order alignment check for {outfname}")
        print(in_fnames)
        sys.exit(1)
