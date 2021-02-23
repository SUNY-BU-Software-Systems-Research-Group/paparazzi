from __future__ import absolute_import, print_function, division
import logging
import os
import argparse as ap
import time
import sys
import time
import threading
import socket
import struct
import signal
import cmath
import csv
import numpy as np
from os import getenv
# if PAPARAZZI_SRC not set, then assume the tree containing this
# file is a reasonable substitute
PPRZ_SRC = getenv("PAPARAZZI_SRC", os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../../')))
sys.path.append(PPRZ_SRC + "/sw/ext/pprzlink/lib/v1.0/python")

from pprzlink.ivy import IvyMessagesInterface
from pprzlink.message import PprzMessage

class KazeTimerThread(threading.Thread):
    def __init__(self, parent):
        threading.Thread.__init__(self)
        self.kaze = parent
    
    def run(self):
        self.play_idx = self.kaze.play_idx
        self.play_items = len(self.kaze.playback)
        logging.info('initial wind conditions ... ' + str(self.kaze.playback[self.play_idx]['wind_east'])
                                                    + str(self.kaze.playback[self.play_idx]['wind_north'])
                                                    + str(self.kaze.playback[self.play_idx]['wind_up']))
        while self.kaze.on:
            self.start_time = time.time()
            self.play_time = float(self.kaze.playback[self.play_idx]['play_time'])
            while((time.time() - self.start_time) < self.play_time):    
                if not self.kaze.on:
                    return
            with self.kaze.play_lock:
                self.kaze.play_idx = (self.play_idx + 1) % self.play_items
            self.play_idx = self.kaze.play_idx
            if self.kaze.on:
                logging.info('updated wind conditions ... ' + str(self.kaze.playback[self.play_idx]['wind_east'])
                                                     + str(self.kaze.playback[self.play_idx]['wind_north'])
                                                     + str(self.kaze.playback[self.play_idx]['wind_up']))

class Kaze():
    csv_fields = ['wind_east', 'wind_north', 'wind_up', 'play_time']
    def __init__(self, windpath, timescale=1.0, ircontrast=400, genrandwinds=False, maxspeed=None, mindt=None, maxdt=None, num_winds=0, port=2010): 
        #init ivy and register callback for WORLD_ENV_REG message
        print('Initing Kaze...')
        self.port = port
        self.playback = []
        self.gen = genrandwinds
        self.play_idx = 0
        self.play_lock = threading.Lock()
        self.msg = PprzMessage("ground", "WORLD_ENV")
        self.msg['time_scale'] = timescale
        # the next two fields are not used by kaze but are needed for sending WORLD_ENV message
        self.msg['gps_availability'] = 1 # the value is preset 
        self.msg['ir_contrast'] = ircontrast # the value is user defined 
        self.random_params = (maxspeed, mindt, maxdt)
        self.random_n = num_winds
        self.ivy = IvyMessagesInterface(start_ivy=False, ivy_bus="127.255.255.255:"+str(self.port))
        self.load(windpath)
        self.on = False
        self.cb_started = False # set to true after the first cb
        self.final_cb = False

    def __del__(self):
        print('Deleted Kaze.')

    def start(self):
        print('Kaze starting.')
        logging.debug('Starting Ivy...')
        if len(self.playback) is 0:
            raise KazeWindFileFmtError()
        logging.debug('Subscribing to IVY message...')
        self.ivy.subscribe(self.worldenv_cb, '(.* WORLD_ENV_REQ .*)')
        logging.debug('Subscribed.')
        #wait for ivy to start
        from ivy.std_api import IvyMainLoop
        self.ivy.start()
        self.on = True
        # start self.clock on the first cb after send
        self.clock = KazeTimerThread(self)

    def shutdown(self):
        logging.debug('Shutting down IVY...')
        self.on = False
        #join clock if self.first_cb == False
        if self.cb_started:
            self.final_cb = True
            self.clock.join()
            del self.clock
            self.cb_started = False
        # commented the below to allow kaze to shutdown even if ivy bus is terminated
        #while self.final_cb:
        #    continue 
        self.ivy.shutdown()
        logging.debug('IVY shutdown successful.')
    
    def load(self, windpath):
        if windpath is not "":
            try:
                with open(windpath) as csvfile:
                    reader = csv.DictReader(csvfile, fieldnames=self.csv_fields)
                    print("Loading wind file from existing file...")
                    for row in reader:
                        for k, v in row.items():
                            row[k] = float(v)
                        self.playback.append(row.copy()) 
            except IOError as e:
                # path does not exist so check if gen is True
                if not self.gen:
                    raise KazeGenFlagError()
                else:
                    # generate random wind file
                    random_params_map = map(lambda x: x is not None and float(x), self.random_params)
                    if all(random_params_map):
                        #params exist and non-zero
                        print("Generating wind file using random params...")
                        dir_file = os.path.split(windpath)
                        try:
                            if dir_file[0] is not '':
                                os.makedirs(dir_file[0], exist_ok = True)
                            with open(windpath, 'w') as random_winds:
                                for i in range (0, self.random_n):
                                    #write each wind into random_winds
                                    theta = 2*np.pi*np.random.rand()
                                    v = np.random.rand()
                                    phi = np.arccos((2*v)-1)
                                    (max_scale, min_dt, max_dt) = self.random_params
                                    r = max_scale * np.power(np.random.rand(), 1/3)
                                    x = r * np.cos(theta) * np.sin(phi)
                                    y = r * np.sin(theta) * np.sin(phi)
                                    z = r * np.cos(phi)
                                    dt = np.random.uniform(min_dt, max_dt)
                                    random_winds.write(str(x)+", "+str(y)+", "+str(z)+", "+str(dt)+"\n")
                            print("Loading random generated wind fiile...")
                            with open(windpath) as csvfile:
                                reader = csv.DictReader(csvfile, fieldnames=self.csv_fields)
                                for row in reader:
                                    for k, v in row.items():
                                        row[k] = float(v)
                                        self.playback.append(row.copy()) 
                        except:
                            raise KazeWindFilePathError()
                        # self.load(windpath) since now path should work and need to load into self.playback
                        # probably can be done more efficiently if needed
                        # self.load(windpath)
                    else:
                        raise KazeRandomGenError()
            except (ValueError, TypeError) as e:
                raise KazeWindFileFmtError()
            # I dont think the try will generate an exception other than IOError, ValueErorr, TypeError
            except Exception as e:
                logging.error('where did this exception come from...')
                exit()
    
    def worldenv_cb(self, ac_id, msg):
        # if cb_started is false then start the clock and set to true
        if self.final_cb:
            self.msg['wind_east'] = 0.0
            self.msg['wind_north'] = 0.0
            self.msg['wind_up'] = 0.0
            logging.info("wind_east: {}, wind_north: {}, wind_up: {}".format(self.msg['wind_east'], self.msg['wind_north'], self.msg['wind_up'])) 
            self.ivy.send(self.msg, None)
            self.final_cb = False
            print('cb done.')
            return
        if not self.cb_started:
            self.cb_started = True
            self.clock.start()
        wind = {}
        with self.play_lock:
            wind = self.playback[self.play_idx]
        for key, value in wind.items():
            if key is 'play_time':
                continue
            self.msg[key] = float(value)
        #self.msg['wind_east'] = 0.0
        #self.msg['wind_north'] = 0.0
        #self.msg['wind_up'] = 0.0
        logging.info("wind_east: {}, wind_north: {}, wind_up: {}".format(self.msg['wind_east'], self.msg['wind_north'], self.msg['wind_up'])) 
        self.ivy.send(self.msg, None)
        print('cb done.')

class KazeErrors(Exception):
    def __init__(self, message):
        self.args = "{0.__name__}: {1}".format(type(self), message)
        super().__init__(self.message)

class KazeWindFileNotFoundError(KazeErrors):
    def __init__(self, message="File could not be found."):
        self.message = message
        super().__init__(self.message)

class KazeGenFlagError(KazeErrors):
    def __init__(self, message="Please set the gen flag (i.e. -gen option) in order to random generate the input file."):
        self.message = message
        super().__init__(self.message)

class KazeWindFilePathError(KazeErrors):
    def __init__(self, message="Path to write file is not valid."):
        self.message = message
        super().__init__(self.message)

class KazeWindFileFmtError(KazeErrors):
    def __init__(self, message="File has the incorrect format; correct format per line:\n<float>, <float>, <float>, <float>"):
        self.message = message
        super().__init__(self.message)

class KazeRandomGenError(KazeErrors):
    def __init__(self, message="Random generation ran into an error, check random gen params."):
        self.message = message
        super().__init__(self.message)

def get_level(loglevel):
    num = getattr(logging, loglevel.upper(), None)
    if not isinstance(num, int):
        raise ValueError('Invalid log level: %s' % loglevel)
    return num

if __name__ == "__main__":
    PPRZLINK_PORT = 2010
    parser = ap.ArgumentParser(
        description="Create and Simulate Customizable Wind Condititons for Paparazzi UAV simulator"
    )
    parser.add_argument('windpath', help="Specifies relative or absolute file location of the wind playback file.")
    parser.add_argument('-ll', '--loglevel', type=get_level, default=logging.DEBUG, metavar='LL', help="Can input <debug|info|warning|error> (debug)")
    parser.add_argument('-ts','--timescale', type=float, default=1.0, metavar='TS', help="Set the timescale paparrazi uses to run nps (1.0)")
    parser.add_argument('-ir','--ircontrast', type=int, default=400, metavar='IR', help="Set the ircontrast at each wind message (400)")
    parser.add_argument('-gen', '--genrandwinds', action="store_true", help="If set and the file located at windpath does not exist, the following args will be used for random wind generation:")
    parser.add_argument('-s','--maxspeed', type=float, default=3.0, metavar='S', help="Set max speed for random wind file (3.0)")
    parser.add_argument('-min','--mindt', type=float, default=1.0, help="Set min delta t for random interval between winds (1.0)")
    parser.add_argument('-max','--maxdt', type=float, default=5.0, help="Set max delta t for random interval between winds (5.0)")
    parser.add_argument('-n', '--numwinds', type=int, default=5, metavar='N', help="Set number of wind vectors to generate (5)")
    parser.add_argument('-p', '--port', type=int, default=PPRZLINK_PORT, metavar='P', help="Set port for ivy_bus (2011)")
    args=parser.parse_args()
    os.makedirs("logs/", exist_ok = True)
    logging.basicConfig(format='%(asctime)s %(message)s', filename="logs/"+args.windpath+".log", filemode="w", level=args.loglevel)
    k = Kaze(args.windpath, args.timescale, args.ircontrast, args.genrandwinds, args.maxspeed, args.mindt, args.maxdt, args.numwinds, args.port)
    def sig_handler(signal, frame):
        k.shutdown()
        exit()
    signal.signal(signal.SIGINT, sig_handler)
    try:
        k.start()
    except Exception as e:
        k.shutdown()
        raise e
    signal.pause()
