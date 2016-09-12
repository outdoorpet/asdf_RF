# Script to ASDF file and use the quakeML (included) metdata to extract earthquake waveforms then store
# them in the ASDF file.

import pyasdf
from os.path import expanduser
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String
from sqlalchemy import or_, and_


#### =========================== User Input Required =========================== ####

# FDSN network identifier (2 Characters)
network = '8B'

#### =========================================================================== ####

Base = declarative_base()

class Waveforms(Base):
    __tablename__ = 'waveforms'
    # Here we define columns for the table
    # Notice that each column is also a normal Python instance attribute.
    starttime = Column(Integer)
    endtime = Column(Integer)
    station_id = Column(String(250), nullable=False)
    tag = Column(String(250), nullable=False)
    full_id = Column(String(250), nullable=False, primary_key=True)

# ASDF file (High Performance Dataset) one file per network
ASDF_in = expanduser('~') + '/Desktop/DATA/' + network + '/ASDF/' + network + '.h5'

# Open the ASDF file
ds = pyasdf.ASDFDataSet(ASDF_in)

# Access the event metadata
event_cat = ds.events

# Get list of stations in ASDF file
sta_list = ds.waveforms.list()

# Iterate through all stations in ASDF file
for _i, station_name in enumerate(sta_list):
    print 'Working on Station: {0}'.format(sta_list[_i])

    # SQL file for station
    SQL_in = expanduser('~') + '/Desktop/DATA/' + network + '/ASDF/' + station_name + '.db'

    # Initialize the sqlalchemy sqlite engine
    engine = create_engine('sqlite:////' + SQL_in)

    Session = sessionmaker(bind=engine)
    session = Session()


    for _j, event in enumerate(event_cat):
        #print '\r  Extracting {0} of {1} Earthquakes....'.format(_j + 1, event_cat.count()),
        #sys.stdout.flush()

        # Get quake origin info
        origin_info = event.preferred_origin() or event.origins[0]

        qtime = origin_info.time.timestamp

        print 'qtime = ', origin_info.time, qtime

        for matched_waveform in session.query(Waveforms).\
                filter(or_(and_(Waveforms.starttime <= qtime, qtime < Waveforms.endtime), and_(qtime <= Waveforms.starttime, Waveforms.starttime < qtime + 3600))):
            # Now write extract all matched waveforms, concatenate using Obspy and write to ASDF with associated event tag
            pass

    break








