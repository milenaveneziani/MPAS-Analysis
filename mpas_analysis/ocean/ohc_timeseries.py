import numpy as np
import netCDF4
from netCDF4 import Dataset as netcdf_dataset
import xarray as xr
import pandas as pd
import datetime

from ..shared.mpas_xarray.mpas_xarray import preprocess_mpas, \
    remove_repeated_time_index

from ..shared.plot.plotting import timeseries_analysis_plot

from ..shared.io import NameList, StreamsFile

from ..shared.timekeeping.Date import Date


def ohc_timeseries(config, streamMap=None, variableMap=None):
    """
    Performs analysis of ocean heat content (OHC) from time-series output.
    config is an instance of an MpasAnalysisConfigParser containing
    configuration options.

    config is an instance of MpasAnalysisConfigParser containing configuration
    options.

    If present, streamMap is a dictionary of MPAS-O stream names that map to
    their mpas_analysis counterparts.

    If present, variableMap is a dictionary of MPAS-O variable names that map
    to their mpas_analysis counterparts.

    Author: Xylar Asay-Davis, Milena Veneziani
    Last Modified: 01/07/2017
    """

    # read parameters from config file
    casename = config.get('case', 'casename')
    ref_casename_v0 = config.get('case', 'ref_casename_v0')
    indir_v0data = config.get('ocean_reference', 'basedir')

    compare_with_obs = config.getboolean('ohc_timeseries', 'compare_with_obs')

    output_basedir = config.get('output', 'basedir')
    plots_dir = '{}/{}'.format(output_basedir,
                               config.get('output', 'plots_subdir'))

    yr_offset = config.getint('time', 'yr_offset')

    N_movavg = config.getint('ohc_timeseries', 'N_movavg')

    regions = config.getExpression('regions', 'regions')
    plot_titles = config.getExpression('regions', 'plot_titles')
    iregions = config.getExpression('ohc_timeseries', 'regionIndicesToPlot')

    indir = config.get('input', 'basedir')

    namelist_filename = config.get('input', 'ocean_namelist_filename')
    namelist = NameList(namelist_filename, path=indir)

    streams_filename = config.get('input', 'ocean_streams_filename')
    streams = StreamsFile(streams_filename, streamsdir=indir)

    # Note: input file, not a mesh file because we need dycore specific fields
    # such as refBottomDepth and namelist fields such as config_density0, as
    # well as simulationStartTime, that are not guaranteed to be in the mesh
    # file.
    try:
        inputfile = streams.readpath('restart')[0]
    except ValueError:
        raise IOError('No MPAS-O restart file found: need at least one '
                      'restart file for OHC calculation')

    # get a list of timeSeriesStats output files from the streams file,
    # reading only those that are between the start and end dates
    startDate = config.get('time_series', 'start_date')
    endDate = config.get('time_series', 'end_date')
    streamName = streams.find_stream(streamMap['timeSeriesStats'])
    infiles = streams.readpath(streamName, startDate=startDate,
                               endDate=endDate)
    print 'Reading files {} through {}'.format(infiles[0], infiles[-1])

    # Define/read in general variables
    print '  Read in depth and compute specific depth indexes...'
    f = netcdf_dataset(inputfile, mode='r')
    # reference depth [m]
    depth = f.variables['refBottomDepth'][:]
    # simulation start time
    simStartTime = netCDF4.chartostring(f.variables['simulationStartTime'][:])
    simStartTime = str(simStartTime)
    f.close()
    # specific heat [J/(kg*degC)]
    cp = namelist.getfloat('config_specific_heat_sea_water')
    # [kg/m3]
    rho = namelist.getfloat('config_density0')
    fac = 1e-22*rho*cp

    k700m = np.where(depth > 700.)[0][0] - 1
    k2000m = np.where(depth > 2000.)[0][0] - 1

    kbtm = len(depth)-1

    # Load data
    print '  Load ocean data...'
    varList = ['avgLayerTemperature',
               'sumLayerMaskValue',
               'avgLayerArea',
               'avgLayerThickness']
    ds = xr.open_mfdataset(
        infiles,
        preprocess=lambda x: preprocess_mpas(x,
                                             yearoffset=yr_offset,
                                             timestr='Time',
                                             onlyvars=varList,
                                             varmap=variableMap))

    ds = remove_repeated_time_index(ds)

    # convert the start and end dates to datetime objects using
    # the Date class, which ensures the results are within the
    # supported range
    time_start = Date(startDate).to_datetime(yr_offset)
    time_end = Date(endDate).to_datetime(yr_offset)
    # select only the data in the specified range of years
    ds = ds.sel(Time=slice(time_start, time_end))

    # Select year-1 data and average it (for later computing anomalies)
    time_start_yr1 = Date(simStartTime).to_datetime(yr_offset)
    if time_start_yr1 < time_start:
        startDate_yr1 = simStartTime
        endDate_yr1 = startDate_yr1[0:5]+'12-31'+startDate_yr1[10:]
        infiles_yr1 = streams.readpath(streamName, startDate=startDate_yr1,
                                       endDate=endDate_yr1)
        ds_yr1 = xr.open_mfdataset(
                infiles_yr1,
                preprocess=lambda x: preprocess_mpas(x,
                                                     yearoffset=yr_offset,
                                                     timestr='Time',
                                                     onlyvars=varList,
                                                     varmap=variableMap))

        ds_yr1 = remove_repeated_time_index(ds_yr1)
    else:
        time_start = datetime.datetime(time_start.year, 1, 1)
        time_end = datetime.datetime(time_start.year, 12, 31)
        ds_yr1 = ds.sel(Time=slice(time_start, time_end))
    mean_yr1 = ds_yr1.mean('Time')

    print '  Compute temperature anomalies...'
    avgLayerTemperature = ds.avgLayerTemperature
    avgLayerTemperature_yr1 = mean_yr1.avgLayerTemperature

    avgLayTemp_anomaly = avgLayerTemperature - avgLayerTemperature_yr1

    year_start = (pd.to_datetime(ds.Time.min().values)).year
    year_end = (pd.to_datetime(ds.Time.max().values)).year
    time_start = datetime.datetime(year_start, 1, 1)
    time_end = datetime.datetime(year_end, 12, 31)

    if ref_casename_v0 != 'None':
        print '  Load in OHC for ACMEv0 case...'
        infiles_v0data = '{}/OHC.{}.year*.nc'.format(
            indir_v0data, ref_casename_v0)
        ds_v0 = xr.open_mfdataset(
            infiles_v0data,
            preprocess=lambda x: preprocess_mpas(x, yearoffset=yr_offset))
        ds_v0 = remove_repeated_time_index(ds_v0)
        year_end_v0 = (pd.to_datetime(ds_v0.Time.max().values)).year
        if year_start <= year_end_v0:
            ds_v0_tslice = ds_v0.sel(Time=slice(time_start, time_end))
        else:
            print '   Warning: v0 time series lies outside current bounds ' \
                'of v1 time series. Skipping it.'
            ref_casename_v0 = 'None'

    sumLayerMaskValue = ds.sumLayerMaskValue
    avgLayerArea = ds.avgLayerArea
    avgLayerThickness = ds.avgLayerThickness

    print '  Compute OHC and make plots...'
    for index in range(len(iregions)):
        iregion = iregions[index]

        # Compute volume of each layer in the region:
        layerArea = sumLayerMaskValue[:, iregion, :] * \
            avgLayerArea[:, iregion, :]
        layerVolume = layerArea * avgLayerThickness[:, iregion, :]

        # Compute OHC:
        ohc = layerVolume * avgLayTemp_anomaly[:, iregion, :]
        # OHC over 0-bottom depth range:
        ohc_tot = ohc.sum('nVertLevels')
        ohc_tot = fac*ohc_tot

        # OHC over 0-700m depth range:
        ohc_700m = fac*ohc[:, 0:k700m].sum('nVertLevels')

        # OHC over 700m-2000m depth range:
        ohc_2000m = fac*ohc[:, k700m+1:k2000m].sum('nVertLevels')

        # OHC over 2000m-bottom depth range:
        ohc_btm = ohc[:, k2000m+1:kbtm].sum('nVertLevels')
        ohc_btm = fac*ohc_btm

        title = 'OHC, {}, 0-bottom (thick-), 0-700m (thin-), 700-2000m (--),' \
                ' 2000m-bottom (-.) \n {}'.format(plot_titles[iregion],
                                                  casename)

        xlabel = 'Time [years]'
        ylabel = '[x$10^{22}$ J]'

        if ref_casename_v0 != 'None':
            figname = '{}/ohc_{}_{}_{}.png'.format(plots_dir,
                                                   regions[iregion],
                                                   casename,
                                                   ref_casename_v0)
            ohc_v0_tot = ds_v0_tslice.ohc_tot
            ohc_v0_700m = ds_v0_tslice.ohc_700m
            ohc_v0_2000m = ds_v0_tslice.ohc_2000m
            ohc_v0_btm = ds_v0_tslice.ohc_btm
            title = '{} (r), {} (b)'.format(title, ref_casename_v0)
            timeseries_analysis_plot(config, [ohc_tot, ohc_700m, ohc_2000m,
                                              ohc_btm, ohc_v0_tot, ohc_v0_700m,
                                              ohc_v0_2000m, ohc_v0_btm],
                                     N_movavg, title, xlabel, ylabel, figname,
                                     lineStyles=['r-', 'r-', 'r--', 'r-.',
                                                 'b-', 'b-', 'b--', 'b-.'],
                                     lineWidths=[2, 1, 1.5, 1.5, 2, 1, 1.5,
                                                 1.5])

        if not compare_with_obs and ref_casename_v0 == 'None':
            figname = '{}/ohc_{}_{}.png'.format(plots_dir, regions[iregion],
                                                casename)
            timeseries_analysis_plot(config, [ohc_tot, ohc_700m, ohc_2000m,
                                              ohc_btm],
                                     N_movavg, title, xlabel, ylabel, figname,
                                     lineStyles=['r-', 'r-', 'r--', 'r-.'],
                                     lineWidths=[2, 1, 1.5, 1.5])
