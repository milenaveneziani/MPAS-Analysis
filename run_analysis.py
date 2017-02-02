#!/usr/bin/env python

"""
Runs MPAS-Analysis via a configuration file (e.g. `config.analysis`)
specifying analysis options.

Author: Xylar Asay-Davis, Phillip J. Wolfram
Last Modified: 02/02/2017
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

from mpas_analysis.shared.io.utility import buildConfigFullPath


def checkPathExists(path):  # {{{
    """
    Raise an exception if the given path does not exist.

    Author: Xylar Asay-Davis
    Last Modified: 02/02/2017
    """
    if not (os.path.isdir(path) or os.path.isfile(path)):
        raise OSError('Path {} not found'.format(path))
# }}}


def makeDirectories(path):  # {{{
    """
    Make the given path if it does not already exist.

    Returns the path unchanged.

    Author: Xylar Asay-Davis
    Last Modified: 02/02/2017
    """

    try:
        os.makedirs(path)
    except OSError:
        pass
    return path  # }}}


def checkGenerate(config, analysisName, mpasCore, analysisCategory=None):
    # {{{
    """
    determine if a particular analysis of a particular core and (optionally)
    category should be generated.

    Author: Xylar Asay-Davis
    Last Modified: 02/02/2017
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
    if config.has_option('climatology', 'startYear') and \
            config.has_option('climatology', 'endYear'):
        startDate = '{:04d}-01-01_00:00:00'.format(
            config.getint('climatology', 'startYear'))
        endDate = '{:04d}-12-31_23:59:59'.format(
            config.getint('climatology', 'endYear'))
        # use 'getWithDefaults' to set start and end dates without replacing
        # them if they already exist
        config.getWithDefault('climatology', 'startDate', startDate)
        config.getWithDefault('climatology', 'endDate', endDate)

    if config.has_option('timeSeries', 'startYear') and \
            config.has_option('timeSeries', 'endYear'):
        startDate = '{:04d}-01-01_00:00:00'.format(
            config.getint('timeSeries', 'startYear'))
        endDate = '{:04d}-12-31_23:59:59'.format(
            config.getint('timeSeries', 'endYear'))
        # use 'getWithDefaults' to set start and end dates without replacing
        # them if they already timeseries
        config.getWithDefault('timeSeries', 'startDate', startDate)
        config.getWithDefault('timeSeries', 'endDate', endDate)

    # Checks on directory/files existence:
    if config.get('runs', 'preprocessedReferenceRunName') != 'None':
        checkPathExists(config.get('oceanPreprocessedReference',
                                   'baseDirectory'))
        checkPathExists(config.get('seaIcePreprocessedReference',
                                   'baseDirectory'))

    generateTimeSeriesSeaIce = checkGenerate(
        config, analysisName='timeSeriesSeaIceAreaVol',  mpasCore='seaIce',
        analysisCategory='timeSeries')
    compareTimeSeriesSeaIceWithObservations = config.getboolean(
            'timeSeriesSeaIceAreaVol', 'compareWithObservations')
    generateRegriddedSeaIce = checkGenerate(
        config, analysisName='regriddedSeaIceConcThick',  mpasCore='seaIce',
        analysisCategory='regriddedHorizontal')

    if ((generateTimeSeriesSeaIce and
         compareTimeSeriesSeaIceWithObservations) or generateRegriddedSeaIce):
        # we will need sea-ice observations.  Make sure they're there
        baseDirectory = config.get('seaIceObservations', 'baseDirectory')
        for observationName in ['areaNH', 'areaSH', 'volNH', 'volSH']:
            fileName = config.get('seaIceObservations', observationName)
            if fileName.lower() == 'none':
                continue
            checkPathExists('{}/{}'.format(baseDirectory, fileName))

    makeDirectories(buildConfigFullPath(config, 'output', 'plotsSubdirectory'))

    # choose the right rendering backend, depending on whether we're displaying
    # to the screen
    if not config.getboolean('plot', 'displayToScreen'):
        mpl.use('Agg')
    import matplotlib.pyplot as plt

    # analysis can only be imported after the right MPL renderer is selected

    # GENERATE OCEAN DIAGNOSTICS
    if checkGenerate(config, analysisName='timeSeriesOHC', mpasCore='ocean',
                     analysisCategory='timeSeries'):
        print ""
        print "Plotting OHC time series..."
        from mpas_analysis.ocean.ohc_timeseries import ohc_timeseries
        ohc_timeseries(config, streamMap=oceanStreamMap,
                       variableMap=oceanVariableMap)

    if checkGenerate(config, analysisName='timeSeriesSST', mpasCore='ocean',
                     analysisCategory='timeSeries'):
        print ""
        print "Plotting SST time series..."
        from mpas_analysis.ocean.sst_timeseries import sst_timeseries
        sst_timeseries(config, streamMap=oceanStreamMap,
                       variableMap=oceanVariableMap)

    if checkGenerate(config, analysisName='timeSeriesNino34',
                     mpasCore='ocean', analysisCategory='timeSeries'):
        print ""
        print "Plotting Nino3.4 time series..."
        # from mpas_analysis.ocean.nino34_timeseries import nino34_timeseries
        # nino34_timeseries(config)

    if checkGenerate(config, analysisName='timeSeriesMHT', mpasCore='ocean',
                     analysisCategory='timeSeries'):
        print ""
        print "Plotting Meridional Heat Transport (MHT)..."
        # from mpas_analysis.ocean.mht_timeseries import mht_timeseries
        # mht_timeseries(config)

    if checkGenerate(config, analysisName='timeSeriesMOC', mpasCore='ocean',
                     analysisCategory='timeSeries'):
        print ""
        print "Plotting Meridional Overturning Circulation (MOC)..."
        # from mpas_analysis.ocean.moc_timeseries import moc_timeseries
        # moc_timeseries(config)

    if checkGenerate(config, analysisName='regriddedSST', mpasCore='ocean',
                     analysisCategory='regriddedHorizontal'):
        print ""
        print "Plotting 2-d maps of SST climatologies..."
        from mpas_analysis.ocean.ocean_modelvsobs import ocn_modelvsobs
        ocn_modelvsobs(config, 'sst', streamMap=oceanStreamMap,
                       variableMap=oceanVariableMap)

    if checkGenerate(config, analysisName='regriddedMLD', mpasCore='ocean',
                     analysisCategory='regriddedHorizontal'):
        print ""
        print "Plotting 2-d maps of MLD climatologies..."
        from mpas_analysis.ocean.ocean_modelvsobs import ocn_modelvsobs
        ocn_modelvsobs(config, 'mld', streamMap=oceanStreamMap,
                       variableMap=oceanVariableMap)

    if checkGenerate(config, analysisName='regriddedSSS', mpasCore='ocean',
                     analysisCategory='regriddedHorizontal'):
        print ""
        print "Plotting 2-d maps of SSS climatologies..."
        from mpas_analysis.ocean.ocean_modelvsobs import ocn_modelvsobs
        ocn_modelvsobs(config, 'sss', streamMap=oceanStreamMap,
                       variableMap=oceanVariableMap)

    # GENERATE SEA-ICE DIAGNOSTICS
    if checkGenerate(config, analysisName='timeSeriesSeaIceAreaVol',
                     mpasCore='seaIce', analysisCategory='timeSeries'):
        print ""
        print "Plotting sea-ice area and volume time series..."
        from mpas_analysis.sea_ice.timeseries import seaice_timeseries
        seaice_timeseries(config, streamMap=seaIceStreamMap,
                          variableMap=seaIceVariableMap)

    if checkGenerate(config, analysisName='regriddedSeaIceConcThick',
                     mpasCore='seaIce',
                     analysisCategory='regriddedHorizontal'):
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
