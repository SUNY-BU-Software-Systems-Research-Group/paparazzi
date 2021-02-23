import logging
import argparse as ap
import signal
import sys
from kaze import Kaze

def get_level(loglevel):
    num = getattr(logging, loglevel.upper(), None)
    if not isinstance(num, int):
        raise ValueError('Invalid log level: %s' % loglevel)
    return num

parser = ap.ArgumentParser(
    description="Create and Simulate Customizable Wind Condititons for Paparazzi UAV simulator"
)

parser.add_argument('windpath', help="Specifies relative or absolute file location of the wind playback file.")
parser.add_argument('--loglevel', type=get_level, default=logging.DEBUG, metavar='LL', help="Can input <debug|info|warning|error> (debug)")
parser.add_argument('--timescale', type=float, default=1.0, metavar='TS', help="Set the timescale paparrazi uses to run nps (1.0)")
parser.add_argument('--ircontrast', type=int, default=400, metavar='IR', help="Set the ircontrast at each wind message (400)")
parser.add_argument('-gen', '--genrandwinds', action="store_true", help="If set and the file located at windpath does not exist, the following args will be used for random wind generation:")
parser.add_argument('--maxspeed', type=float, default=3.0, metavar='S', help="Set max speed for random wind file (3.0)")
parser.add_argument('--mindt', type=float, default=1.0, help="Set min delta t for random interval between winds (1.0)")
parser.add_argument('--maxdt', type=float, default=5.0, help="Set max delta t for random interval between winds (5.0)")
parser.add_argument('--numwinds', type=int, default=5, metavar='N', help="Set number of wind vectors to generate (5)")
args = parser.parse_args()
logging.basicConfig(format='%(asctime)s %(message)s', filename="kaze.log", filemode="w", level=args.loglevel)
#logging.basicConfig(filename="kaze.log", filemode="w", level=args.loglevel)
kaze = Kaze(args.windpath, args.timescale, args.ircontrast, args.genrandwinds, args.maxspeed, args.mindt, args.maxdt, args.numwinds)

def signal_handler(signal, frame):
    kaze.shutdown()
    exit()

signal.signal(signal.SIGINT, signal_handler)
kaze.start()
signal.pause()    

