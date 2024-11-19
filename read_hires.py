import numpy as np
from astropy.io import fits
from alexmods.specutils import Spectrum1D
import os, sys, time

def read_makee(num,outdir):
    fluxnames = ["{}/Flux-{:03}_{}.fits".format(outdir,num,i) for i in [1,2,3]]
    errnames  = ["{}/Err-{:03}_{}.fits".format(outdir,num,i) for i in [1,2,3]]
    # These are not used but here for reference
    arcnames  = ["{}/Arc-{:03}_{}.fits".format(outdir,num,i) for i in [1,2,3]]
    DNnames   = ["{}/DN-{:03}_{}.fits".format(outdir,num,i) for i in [1,2,3]]
    skynames  = ["{}/Sky-{:03}_{}.fits".format(outdir,num,i) for i in [1,2,3]]
    sumnames  = ["{}/Sum-{:03}_{}.fits".format(outdir,num,i) for i in [1,2,3]]
    varnames  = ["{}/Var-{:03}_{}.fits".format(outdir,num,i) for i in [1,2,3]]
    flatnames = ["{}/Flat-{:03}_{}.fits".format(outdir,num,i) for i in [1,2,3]]
    s2nnames  = ["{}/s2n-{:03}_{}.fits".format(outdir,num,i) for i in [1,2,3]]
    profnames = ["{}/profiles-{:03}_{}.fits".format(outdir,num,i) for i in [1,2,3]]
    
    orders = []
    for fluxname, errname in zip(fluxnames, errnames):
        wl = read_lambda(fluxname)
        with fits.open(fluxname) as fp:
            flux = fp[0].data
        with fits.open(errname) as fp:
            ivar = (fp[0].data)**-2.
        norder = wl.shape[0]
        for j in range(norder):
            spec = Spectrum1D(wl[j],flux[j],ivar[j])
            orders.append(spec)
    return orders

def read_lambda(fname):
    fp = fits.open(fname)
    hdr = fp[0].header
    npix = hdr["NAXIS1"]
    norders = hdr['NAXIS2']
    wl = np.zeros((npix,norders))
    for i in range(norders):
        lambdapoly = np.zeros(7)
        poly_string1 = hdr['WV_0_{:02}'.format(i+1)]
        poly_string2 = hdr['WV_4_{:02}'.format(i+1)]
        lambdapoly[0] = float(poly_string1[0:17])
        lambdapoly[1] = float(poly_string1[17:34])
        lambdapoly[2] = float(poly_string1[34:51])
        lambdapoly[3] = float(poly_string1[51:68])
        lambdapoly[4] = float(poly_string2[0:17])
        lambdapoly[5] = float(poly_string2[17:34])
        lambdapoly[6] = float(poly_string2[34:51])
        wl[:,i] = np.polyval(lambdapoly[::-1], np.arange(npix)+1.)
    return wl.T

if __name__=="__main__":
    num = int(sys.argv[1])
    path = sys.argv[2]
    print(f"Processing {num} {path}")
    t0 = time.time()
    orders = read_makee(num, path)
    outdir = f"{path}/orders_{num:04}"
    if not os.path.exists(outdir):
        os.mkdir(outdir)
    for i,order in enumerate(orders):
        order.write(outdir+"/{:02}.fits".format(i))
    Spectrum1D.write_alex_spectrum_from_specs(outdir+f"/{num:04}_multi.fits", orders, overwrite=True)
    print(f"Finished {len(orders)} orders in {time.time()-t0:.1f} seconds")
