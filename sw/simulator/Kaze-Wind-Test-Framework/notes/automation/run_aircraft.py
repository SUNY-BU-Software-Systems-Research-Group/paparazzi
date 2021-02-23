import os
import sys
import argparse
import time
import subprocess
import re

parser=argparse.ArgumentParser()
parser.add_argument("-a", "--aircraft", dest="AIRCRAFT", default="ardrone2_1")
parser.add_argument("-t", "--type", dest="SIM_TYPE", default="nps")
parser.add_argument("-i", "--acid", help="aircraft ID", dest='acid', default=1, type=int)
parser.add_argument("-n", "--numaircrafts", dest="num_aircrafts", default=1, type=int)
parser.add_argument("-p", "--port", dest="port", default="2010", type=str)
args=parser.parse_args()
PPRZ_HOME = os.getenv("PAPARAZZI_HOME", os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), './')))
PPRZ_SRC = os.getenv("PAPARAZZI_SRC", os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), './')))
sys.path.append(PPRZ_SRC + "/sw/ext/pprzlink/lib/v1.0/python")

from pprzlink.ivy import IvyMessagesInterface
from pprzlink.message import PprzMessage

TIMEOUT_S = 100

SIM_SITL = None
SIM_SERVER = None
SIM_LINK = None
ivy_interface = None
FLIGHT_STARTED = False
ABOVE_GROUND_LEVEL_M = 0.0
TELEM_PORT_DOWN = 4242
PPRZLINK_PORT = 2010
TELEM_PORT_UP = 4243
SIM_PROCS = []

def cb(ac_id: str, msg: PprzMessage):
	global ABOVE_GROUND_LEVEL_M
	if msg is not None and "agl : " in str(msg):
		ABOVE_GROUND_LEVEL_M=float(re.findall("agl : \d+\.\d+", str(msg))[0][6:])


def build_aircraft():
	os.system("make -C "+PPRZ_HOME+" -f Makefile.ac AIRCRAFT="+args.AIRCRAFT+" "+args.SIM_TYPE+".compile")

def kill_simulation():
	global SIM_SITL, SIM_SERVER, SIM_LINK
	if (SIM_SITL != None):
		SIM_SITL.terminate()
	if (SIM_SERVER != None):
		SIM_SERVER.terminate()
	if (SIM_LINK != None):
		SIM_LINK.terminate()

def run_simulation1():
	global SIM_SITL, SIM_SERVER, SIM_LINK
	sim_cmd = PPRZ_HOME+"/sw/simulator/pprzsim-launch -a "+args.AIRCRAFT +" -t nps -b 127.255.255.255:"+args.port
	SIM_SITL = subprocess.Popen(sim_cmd.split(' '), start_new_session=True)
	server_cmd = PPRZ_HOME+"/sw/ground_segment/tmtc/server -b 127.255.255.255:"+args.port
	SIM_SERVER = subprocess.Popen(server_cmd.split(' '), start_new_session=True)
	link_cmd = PPRZ_HOME+"/sw/ground_segment/tmtc/link -udp  -b 127.255.255.255:" + args.port + " -udp_port "+ str(int(args.port)+2232) + " -udp_uplink_port " + str(int(args.port)+2233)
	SIM_LINK = subprocess.Popen(link_cmd.split(' '), start_new_session=True)
	SIM_PROCS.append([SIM_SITL, SIM_SERVER, SIM_LINK])


def main():
	global ABOVE_GROUND_LEVEL_M, FLIGHT_STARTED
	#build_aircraft()
	run_simulation1()
	ivy_interface = IvyMessagesInterface("AutoSim", start_ivy=False, ivy_bus="127.255.255.255:"  + args.port)
	ivy_interface.subscribe(cb, PprzMessage("telemetry", "NPS_POS_LLH"))
	ivy_interface.start()
	start_time = time.time()
	while(1):
	    time.sleep(1)
	    print("FLIGHT_STARTED: "+str(FLIGHT_STARTED)+" | AGL: " + str(ABOVE_GROUND_LEVEL_M))
	    if (ABOVE_GROUND_LEVEL_M > 1.0 and not FLIGHT_STARTED):
	        FLIGHT_STARTED = True
	    elif (ABOVE_GROUND_LEVEL_M < 1.0 and FLIGHT_STARTED):
                print("drone has landed...\nexiting...")
                time.sleep(5) # allow landing to finish
                kill_simulation()
                ivy_interface.shutdown()
                break
	    if (time.time()-start_time > TIMEOUT_S):
                print("timeout reached...\nexiting...")
                kill_simulation()
                ivy_interface.shutdown()
                break
main()
