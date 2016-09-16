# Script to build the ASDF SQL data base using sqlalchemy (seperate database for each station in a network)
# This will be done automatically on ASDF creation in the future

import pyasdf
from os.path import join, exists, basename
import glob
import sys
from obspy.core import UTCDateTime, read
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import sessionmaker
import time

code_start_time = time.time()

# =========================== User Input Required =========================== #

#Path to the data
data_path = '/media/obsuser/seismic_data_1/'

#IRIS Virtual Ntework name
virt_net = '_GA_OBS'

# FDSN network identifier (2 Characters)
FDSNnetwork = '8B'

# =========================================================================== #

path_XML = join(data_path, virt_net, FDSNnetwork, 'network_metadata/stnXML', FDSNnetwork+ '.xml')
path_miniSEED = join(data_path, virt_net, FDSNnetwork, 'raw_SEED/')
path_quakeML = join(data_path, virt_net, FDSNnetwork, 'event_metadata/quakeML/')

# Output ASDF file (High Performance Dataset) one file per network
ASDF_out = join(data_path, virt_net, FDSNnetwork, 'ASDF', FDSNnetwork + '.h5')

# Create the ASDF file
ds = pyasdf.ASDFDataSet(ASDF_out, compression="gzip-3")

# Add the station XML data to the ASDF file
ds.add_stationxml(path_XML)

# Set up the sql waveform databases
Base = declarative_base()
Session = sessionmaker()

class Waveforms(Base):
    __tablename__ = 'waveforms'
    # Here we define columns for the table
    # Notice that each column is also a normal Python instance attribute.
    starttime = Column(Integer)
    endtime = Column(Integer)
    station_id = Column(String(250), nullable=False)
    tag = Column(String(250), nullable=False)
    full_id = Column(String(250), nullable=False, primary_key=True)


# Function to seperate the waveform string into seperate fields
def waveform_sep(ws):
    a = ws.split('__')
    starttime = int(UTCDateTime(a[1].encode('ascii')).timestamp)
    endtime = int(UTCDateTime(a[2].encode('ascii')).timestamp)

    # Returns: (station_id, starttime, endtime, waveform_tag)
    return (ws.encode('ascii'), a[0].encode('ascii'), starttime, endtime, a[3].encode('ascii'))


# Get a list of miniseed files in raw_SEED directory
seed_files = glob.glob(path_miniSEED + '*.msd')[0:100]
seed_files.sort()

# Iterate through the miniseed files, fix the header values and add waveforms
for _i, filename in enumerate(seed_files):

    print "\r Adding file ", _i + 1, ' of ', len(seed_files), ' ....',
    sys.stdout.flush()

    station_name = basename(filename).split('_')[0]

    #print station_name

    # read the miniseed file
    st = read(filename)

    # there will only be one trace in stream because the data is by channels
    tr = st[0]

    # Makes sure header is correct
    tr.stats.network = FDSNnetwork
    tr.stats.station = station_name
    tr.stats.channel = 'B' + tr.stats.channel[1:]

    ds.add_waveforms(tr, tag="raw_recording")

    # Make the data name for the waveform so that we can add it to the SQL database
    data_name = "{net}.{sta}.{loc}.{cha}__{start}__{end}__{tag}".format(
        net=tr.stats.network,
        sta=tr.stats.station,
        loc=tr.stats.location,
        cha=tr.stats.channel,
        start=tr.stats.starttime.strftime("%Y-%m-%dT%H:%M:%S"),
        end=tr.stats.endtime.strftime("%Y-%m-%dT%H:%M:%S"),
        tag="raw_recording")

    #SQL filename for station
    SQL_out = join(data_path, virt_net, FDSNnetwork, 'ASDF', station_name + '.db')

    #check if SQL file exists:
    if not exists(SQL_out):
        # Open and create the SQL file
        # Create an engine that stores data
        engine = create_engine('sqlite:////' + SQL_out)

        # Create all tables in the engine
        Base.metadata.create_all(engine)

    # The ASDF formatted waveform name [full_id, station_id, starttime, endtime, tag]

    waveform_info = waveform_sep(data_name)
    #print waveform_info

    new_waveform = Waveforms(full_id=waveform_info[0], station_id=waveform_info[1], starttime=waveform_info[2], endtime=waveform_info[3], tag=waveform_info[4])

    # Initiate a session with the SQL database so that we can add data to it
    Session.configure(bind=engine)
    session = Session()

    # Add the waveform info to the session
    session.add(new_waveform)
    session.commit()



del ds
print '\n'
print("--- Execution time: %s seconds ---" % (time.time() - code_start_time))



