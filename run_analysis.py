#!/usr/bin/env python

"""
Runs MPAS-Analysis via a configuration file (e.g. `config.analysis`)
specifying analysis options.

Author: Xylar Asay-Davis, Phillip J. Wolfram
Last Modified: 01/29/2017
"""

import os
import matplotlib as mpl
import argparse

from mpas_analysis.configuration.MpasAnalysisConfigParser \
    import MpasAnalysisConfigParser

from mpas_analysis.ocean.variable_stream_map import oceanStreamMap, \
    oceanVariableMap

from mpas_analysis.sea_ice.variable_stream_map import seaIceStreamMap, \
    seaIceVariableMap


def path_existence(config, section, option, ignorestr=None):  # {{{
    inpath = config.get(section, option)
    if not (os.path.isdir(inpath) or os.path.isfile(inpath)):
        # assumes that path locations of ignorestr won't return an error, e.g.,
        # ignorestr="none" is a key word to indicate the path or file is
        # optional and is not needed
        if inpath == ignorestr:
            return False
        errmsg = "Path %s not found. Exiting..." % inpath
        raise SystemExit(errmsg)
    return inpath  # }}}


def makedirs(inpath):  # {{{
    if not os.path.exists(inpath):
        os.makedirs(inpath)
    return inpath  # }}}


def check_generate(config, analysisName, mpasCore, analysisCategory=None):
    # {{{
    """
    determine if a particular analysis of a particular core and (optionally)
    category should be generated.
    """
    generateList = config.getExpression('output', 'generate')
    generate = False
    for element in generateList:
        if '_' in element:
            (prefix, suffix) = element.split('_', 1)
        else:
            prefix = element
            suffix = None

        if prefix == 'all':
            if (suffix in [mpasCore, analysisCategory]) or (suffix is None):
                generate = True
        elif prefix == 'no':
            if suffix in [analysisName, mpasCore, analysisCategory]:
                generate = False
        elif element == analysisName:
            generate = True

    return generate  # }}}


def analysis(config):  # {{{
    # set default values of start and end dates for climotologies and
    # timeseries
    if config.has_option('time', 'climo_yr1') and \
            config.has_option('time', 'climo_yr2'):
        startDate = '{:04d}-01-01_00:00:00'.format(
            config.getint('time', 'climo_yr1'))
        endDate = '{:04d}-12-31_23:59:59'.format(
            config.getint('time', 'climo_yr2'))
        # use 'getWithDefaults' to set start and end dates without replacing
        # them if they already exist
        config.getWithDefault('time', 'climo_start_date', startDate)
        config.getWithDefault('time', 'climo_end_date', endDate)

    if config.has_option('time', 'timeseries_yr1') and \
            config.has_option('time', 'timeseries_yr2'):
        startDate = '{:04d}-01-01_00:00:00'.format(
            config.getint('time', 'timeseries_yr1'))
        endDate = '{:04d}-12-31_23:59:59'.format(
            config.getint('time', 'timeseries_yr2'))
        # use 'getWithDefaults' to set start and end dates without replacing
        # them if they already exist
        config.getWithDefault('time', 'timeseries_start_date', startDate)
        config.getWithDefault('time', 'timeseries_end_date', endDate)

    # Checks on directory/files existence:
    if config.get('case', 'ref_casename_v0') != 'None':
        path_existence(config, 'paths', 'ref_archive_v0_ocndir')
        path_existence(config, 'paths', 'ref_archive_v0_seaicedir')

    generate_seaice_timeseries = check_generate(
        config, analysisName='seaice_timeseries',  mpasCore='seaice',
        analysisCategory='timeseries')
    seaice_compare_obs = config.getboolean('seaice_timeseries',
                                           'compare_with_obs')
    generate_seaice_modelvsobs = check_generate(
        config, analysisName='seaice_modelvsobs',  mpasCore='seaice',
        analysisCategory='modelvsobs')

    if (generate_seaice_timeseries and seaice_compare_obs) or \
            generate_seaice_modelvsobs:
        # we will need sea-ice observations.  Make sure they're there
        for obsfile in ['obs_iceareaNH', 'obs_iceareaSH', 'obs_icevolNH',
                        'obs_icevolSH']:
            path_existence(config, 'seaIceData', obsfile, ignorestr='none')

    makedirs(config.get('paths', 'plots_dir'))

    # choose the right rendering backend, depending on whether we're displaying
    # to the screen
    if not config.getboolean('plot', 'displayToScreen'):
        mpl.use('Agg')
    import matplotlib.pyplot as plt

    # analysis can only be imported after the right MPL renderer is selected

    # GENERATE OCEAN DIAGNOSTICS
    if check_generate(config, analysisName='ohc_timeseries', mpasCore='ocean',
                      analysisCategory='timeseries'):
        print ""
        print "Plotting OHC time series..."
        from mpas_analysis.ocean.ohc_timeseries import ohc_timeseries
        ohc_timeseries(config, streamMap=oceanStreamMap,
                       variableMap=oceanVariableMap)

    if check_generate(config, analysisName='sst_timeseries', mpasCore='ocean',
                      analysisCategory='timeseries'):
        print ""
        print "Plotting SST time series..."
        from mpas_analysis.ocean.sst_timeseries import sst_timeseries
        sst_timeseries(config, streamMap=oceanStreamMap,
                       variableMap=oceanVariableMap)

    if check_generate(config, analysisName='nino34_timeseries',
                      mpasCore='ocean', analysisCategory='timeseries'):
        print ""
        print "Plotting Nino3.4 time series..."
        # from mpas_analysis.ocean.nino34_timeseries import nino34_timeseries
        # nino34_timeseries(config)

    if check_generate(config, analysisName='mht_timeseries', mpasCore='ocean',
                      analysisCategory='timeseries'):
        print ""
        print "Plotting Meridional Heat Transport (MHT)..."
        # from mpas_analysis.ocean.mht_timeseries import mht_timeseries
        # mht_timeseries(config)

    if check_generate(config, analysisName='moc_timeseries', mpasCore='ocean',
                      analysisCategory='timeseries'):
        print ""
        print "Plotting Meridional Overturning Circulation (MOC)..."
        # from mpas_analysis.ocean.moc_timeseries import moc_timeseries
        # moc_timeseries(config)

    if check_generate(config, analysisName='sst_modelvsobs', mpasCore='ocean',
                      analysisCategory='modelvsobs'):
        print ""
        print "Plotting 2-d maps of SST climatologies..."
        from mpas_analysis.ocean.ocean_modelvsobs import ocn_modelvsobs
        ocn_modelvsobs(config, 'sst', streamMap=oceanStreamMap,
                       variableMap=oceanVariableMap)

    if check_generate(config, analysisName='mld_modelvsobs', mpasCore='ocean',
                      analysisCategory='modelvsobs'):
        print ""
        print "Plotting 2-d maps of MLD climatologies..."
        from mpas_analysis.ocean.ocean_modelvsobs import ocn_modelvsobs
        ocn_modelvsobs(config, 'mld', streamMap=oceanStreamMap,
                       variableMap=oceanVariableMap)

    if check_generate(config, analysisName='sss_modelvsobs', mpasCore='ocean',
                      analysisCategory='modelvsobs'):
        print ""
        print "Plotting 2-d maps of SSS climatologies..."
        from mpas_analysis.ocean.ocean_modelvsobs import ocn_modelvsobs
        ocn_modelvsobs(config, 'sss', streamMap=oceanStreamMap,
                       variableMap=oceanVariableMap)

    # GENERATE SEA-ICE DIAGNOSTICS
    if check_generate(config, analysisName='seaice_timeseries',
                      mpasCore='seaice', analysisCategory='timeseries'):
        print ""
        print "Plotting sea-ice area and volume time series..."
        from mpas_analysis.sea_ice.timeseries import seaice_timeseries
        seaice_timeseries(config, streamMap=seaIceStreamMap,
                          variableMap=seaIceVariableMap)

    if check_generate(config, analysisName='seaice_modelvsobs',
                      mpasCore='seaice', analysisCategory='modelvsobs'):
        print ""
        print "Plotting 2-d maps of sea-ice concentration and thickness " \
            "climatologies..."
        from mpas_analysis.sea_ice.modelvsobs import seaice_modelvsobs
        seaice_modelvsobs(config, streamMap=seaIceStreamMap,
                          variableMap=seaIceVariableMap)

    # GENERATE LAND-ICE DIAGNOSTICS

    if config.getboolean('plot', 'displayToScreen'):
        plt.show()

    return  # }}}

if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("-g", "--generate", dest="generate",
                        help="A list of analysis modules to generate "
                        "(nearly identical generate option in config file).",
                        metavar="ANALYSIS1[,ANALYSIS2,ANALYSIS3,...]")
    parser.add_argument('configFiles', metavar='CONFIG',
                        type=str, nargs='+', help='config file')
    args = parser.parse_args()

    config = MpasAnalysisConfigParser()
    config.read(args.configFiles)

    if args.generate:
        # overwrite the 'generate' in config with a string that parses to
        # a list of string
        generateList = args.generate.split(',')
        generateString = ', '.join(["'{}'".format(element)
                                    for element in generateList])
        generateString = '[{}]'.format(generateString)
        config.set('output', 'generate', generateString)

    analysis(config)

# vim: foldmethod=marker ai ts=4 sts=4 et sw=4 ft=python
