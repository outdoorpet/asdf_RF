import pyasdf
from os.path import join, exists
from os import remove as rm
import matplotlib.pyplot as plt
from rf import RFStream, rfstats
from rf.imaging import plot_profile_map
from rf.profile import get_profile_boxes
import numpy as np
import glob


from collections import defaultdict

import time


code_start_time = time.time()


# =========================== User Input Required =========================== #

#Path to the data
data_path = '/g/data/ha3/'

#IRIS Virtual Ntework name
virt_net = '_ANU'

# FDSN network identifier (2 Characters)
FDSNnetwork = 'AA'

# =========================================================================== #


# ASDF quakes file (High Performance Dataset) one file per network
ASDF_in = join(data_path, virt_net, FDSNnetwork, 'ASDF', FDSNnetwork + '_quakes' + '.h5')
ASDF_out = join(data_path, virt_net, FDSNnetwork, 'ASDF', FDSNnetwork + '_RF' + '.h5')


# remove the output if it exists
if exists(ASDF_out):
    rm(ASDF_out)

# Open the ASDF file
ds = pyasdf.ASDFDataSet(ASDF_in)

#get event catalogue
event_cat = ds.events

#for event in event_cat:
#    if '3329830' in str(event.resource_id):
#        print event.resource_id


def process_RF(st, inv):

    station_name = st[0].stats.station

    all_stn_RF = RFStream()

    # make dictionary of lists containing indexes of the traces with the same referred event
    event_dict = defaultdict(list)
    for _i, tr in enumerate(st):
        event_dict[tr.stats.asdf.event_ids[0]].append(_i)

    for event_key in event_dict.keys():
        if not len(event_dict[event_key]) == 3:
            print 'Not enough components'
            continue

        # Make sure the referred event matches for each stream
        ref_events = []
        ref_events.append(st[event_dict[event_key][0]].stats.asdf.event_ids[0])
        ref_events.append(st[event_dict[event_key][1]].stats.asdf.event_ids[0])
        ref_events.append(st[event_dict[event_key][2]].stats.asdf.event_ids[0])

        if not all(x == ref_events[0] for x in ref_events):
            print "Events are not the same"
            continue

        rf_stream = RFStream(traces=[st[event_dict[event_key][0]], st[event_dict[event_key][1]],
                                     st[event_dict[event_key][2]]])


        stats = None
        found_event = False
        for event in event_cat:
            if event.resource_id == ref_events[0]:
                found_event = True
                stats = rfstats(station=inv[0][0], event=event, phase='P', dist_range=(30, 90))

        if not found_event:
            print 'Event not in Catalogue'

        # Stats might be none if epicentral distance of earthquake is outside dist_range
        if not stats == None:

            for tr in rf_stream:
                tr.stats.update(stats)

            rf_stream.filter('bandpass', freqmin=0.05, freqmax=1.)
            rf_stream.rf(method='P', trim=(-10, 30), downsample=50, deconvolve='time')

            all_stn_RF.extend(rf_stream)

    #all_stn_RF.sort(keys=['distance'])
    all_stn_RF.select(station=station_name, component='Q').plot_rf(fillcolors=('k', 'gray'))


    return all_stn_RF



ds.process(process_function=process_RF, output_filename=ASDF_out, tag_map={'unproc_quake': 'receiver_function'})

del ds
print '\n'
print("--- Execution time: %s seconds ---" % (time.time() - code_start_time))