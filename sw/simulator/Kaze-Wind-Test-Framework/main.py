import logging
import argparse as ap
import os
import sys
import time
import subprocess
import signal
import re
import xml.etree.ElementTree as ET
import kaze
def get_level(loglevel):
    num = getattr(logging, loglevel.upper(), None)
    if not isinstance(num, int):
        raise ValueError('Invalid log level: %s' % loglevel)
    return num

parser = ap.ArgumentParser(
    description="Create and Simulate Customizable Wind Condititons for Paparazzi UAV simulator"
)
parser.add_argument("-n", "--name", dest="AC_NAME", default="ardrone2")
parser.add_argument("-i", "--id", dest="AC_ID", default="1")
parser.add_argument("-f", "--frame", dest="AC_FRAME",default="conf/airframes/examples/ardrone2.xml")
parser.add_argument("-r", "--radio", dest="AC_RADIO", default="conf/radios/dummy.xml")
parser.add_argument("-t", "--telemetry", dest="AC_TELEM", default="telemetry/default_rotorcraft.xml")
parser.add_argument("-p", "--flightplan", dest="AC_FP", default="conf/flight_plans/rotorcraft_basic.xml")
parser.add_argument("-s", "--settings", dest="AC_SETTINGS", default="settings/rotorcraft_basic.xml settings/nps.xml")
parser.add_argument("-m", "--modules", dest="AC_MODULES", default="modules/video_rtp_stream.xml modules/geo_mag.xml [modules/air_data.xml] modules/gps_ubx_ucenter.xml modules/ins_extended.xml modules/ahrs_int_cmpl_quat.xml modules/stabilization_int_quat.xml modules/nav_basic_rotorcraft.xml modules/guidance_rotorcraft.xml modules/gps.xml modules/imu_common.xml")
parser.add_argument("-l", "--link", dest="AC_LINK", default="conf/modules/telemetry_transparent_udp.xml")
parser.add_argument("-c", "--color", dest="AC_COLOR", default="white")
#parser.add_argument("-q","--size", dest="NUMBER_ACS", default=1);
parser.add_argument('windpath', nargs='+', help="Specifies relative or absolute file location of the wind playback file.")
parser.add_argument('--loglevel', type=get_level, default=logging.DEBUG, metavar='LL', help="Can input <debug|info|warning|error> (debug)")
parser.add_argument('--timescale', type=float, default=1.0, metavar='TS', help="Set the timescale paparrazi uses to run nps (1.0)")
parser.add_argument('--ircontrast', type=int, default=400, metavar='IR', help="Set the ircontrast at each wind message (400)")
parser.add_argument('-gen', '--genrandwinds', action="store_true", help="If set and the file located at windpath does not exist, the following args will be used for random wind generation:")
parser.add_argument('--maxspeed', type=float, default=3.0, metavar='S', help="Set max speed for random wind file (3.0)")
parser.add_argument('--mindt', type=float, default=1.0, help="Set min delta t for random interval between winds (1.0)")
parser.add_argument('--maxdt', type=float, default=5.0, help="Set max delta t for random interval between winds (5.0)")
parser.add_argument('--numwinds', type=int, default=5, metavar='N', help="Set number of wind vectors to generate (5)")
args=parser.parse_args()
NUMBER_ACS = len(args.windpath) + 1
PPRZ_HOME = os.getenv("PAPARAZZI_HOME", os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), './')))
PPRZ_SRC = os.getenv("PAPARAZZI_SRC", os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), './')))
sys.path.append(PPRZ_SRC + "/sw/ext/pprzlink/lib/v1.0/python")

PPRZLINK_PORT=2010

def create_telemetry(index):
	os.system("cp "+PPRZ_HOME+"/"+args.AC_LINK+" "+PPRZ_HOME+"/"+args.AC_LINK[:-4]+"_"+str(index)+".xml")
	tree = ET.parse(PPRZ_HOME+"/"+args.AC_LINK[:-4]+"_"+str(index)+".xml")
	root = tree.getroot()
	for child in root.getchildren():
		if child.tag == "makefile":
			for child2 in child.getchildren():
				if child2.tag == "configure":
					if "name" in child2.attrib and child2.attrib["name"] == "MODEM_PORT_OUT":
						child2.attrib["default"] = str(int(child2.attrib["default"])+2*index)
					elif "name" in child2.attrib and child2.attrib["name"] == "MODEM_PORT_IN":
						child2.attrib["default"] = str(int(child2.attrib["default"])+2*index)
	tree.write(PPRZ_HOME+"/"+args.AC_LINK[:-4]+"_"+str(index)+".xml")
	
def create_aircraft(index):
	os.system("cp "+PPRZ_HOME+"/"+args.AC_FRAME+" "+PPRZ_HOME+"/"+args.AC_FRAME[:-4]+"_"+str(index)+".xml")
	tree = ET.parse(PPRZ_HOME+"/"+args.AC_FRAME[:-4]+"_"+str(index)+".xml")
	root = tree.getroot()
	for child in root.getchildren():
		if child.tag == "firmware":
			for child2 in child.getchildren():
				if child2.tag == "module" and child2.attrib["name"] == "telemetry":
					child2.attrib["type"] = child2.attrib["type"]+"_"+str(index) 
	tree.write(PPRZ_HOME+"/"+args.AC_FRAME[:-4]+"_"+str(index)+".xml")

def add_aircraft(AC_NAME, AC_ID, AC_FRAME, AC_RADIO, AC_TELEM, AC_FP, AC_SETTINGS, AC_MODULES, AC_COLOR):
    tree = ET.parse(PPRZ_HOME+'/conf/conf.xml')
    root = tree.getroot()
    #child = ET.Element("aircraft\n  name=\""+AC_NAME+"\"\n  ac_id=\""+AC_ID+"\"\n  airframe=\""+AC_FRAME[5:]+"\"\n  radios=\""+AC_RADIO[5:]+"\"\n  telemetry=\""+AC_TELEM+"\"\n  flight_plan=\""+AC_FP[5:]+"\"\n  settings=\""+AC_SETTINGS+"\"\n  settings_modules=\""+AC_MODULES+"\"\n  gui_color=\""+AC_COLOR+"\"\n")
    child = ET.Element('aircraft ac_id="'+AC_ID+'" airframe="'+AC_FRAME[5:]+'" flight_plan="'+AC_FP[5:]+'" gui_color="'+AC_COLOR+'" name="'+AC_NAME+'" radio="'+AC_RADIO[5:]+'" settings="'+AC_SETTINGS+'" settings_modules="'+AC_MODULES+'" telemetry="'+AC_TELEM+'"')
    root.append(child)
    tree.write(PPRZ_HOME+'/conf/conf.xml')

def create_and_add_aircrafts():
    #exit the program/print error when in conf.xml there is an aircraft id in range [AC_ID, AC_ID+NUMBER_ACS)
    tree = ET.parse(PPRZ_HOME+'/conf/conf.xml')
    root = tree.getroot()
    for aircraft in root:
        ac_id = int(aircraft.attrib['ac_id'])
        if ac_id >= int(args.AC_ID) and ac_id < (int(args.AC_ID) + NUMBER_ACS):
            print("check conf.xml for conflicting ac_id")
            exit()
    for i in range(1, NUMBER_ACS+1):
        create_telemetry(i)
        create_aircraft(i)
        add_aircraft(args.AC_NAME+"_"+str(i), str((int(args.AC_ID)+i-1)%255), args.AC_FRAME[:-4]+"_"+str(i)+".xml", args.AC_RADIO, args.AC_TELEM, args.AC_FP, args.AC_SETTINGS, args.AC_MODULES, args.AC_COLOR)
		
def compile_all_aircrafts():
	for i in range(1, NUMBER_ACS+1):
		os.system("make -C "+PPRZ_HOME+" -f Makefile.ac AIRCRAFT="+args.AC_NAME+"_"+str(i)+" nps.compile")


def run_all_aircrafts():
    SIM_PROCS = []
    KAZE_PROCS = []
    for i in range(0, NUMBER_ACS):
        #KAZE_PROCS.append(kaze.Kaze(args.windpath[i-1], args.timescale, args.ircontrast, args.genrandwinds, args.maxspeed, args.mindt, args.maxdt, args.numwinds, PPRZLINK_PORT+i))
        #KAZE_PROCS[i-1].start()
        if i is not 0:
            gen_option = " -gen " if args.genrandwinds else "" 
            kaze_cmd = "python3 kaze.py "+str(args.windpath[i-1])+" -ts "+str(args.timescale)+" -ir "+str(args.ircontrast)+gen_option+"-p "+str(PPRZLINK_PORT+i)+" -s "+str(args.maxspeed)+" -max "+str(args.maxdt)+" -min "+str(args.mindt)+" -n "+str(args.numwinds)
            KAZE_THREAD = subprocess.Popen(kaze_cmd.split(' '), start_new_session=True)
            KAZE_PROCS.append(KAZE_THREAD)
        sim_cmd = "python3 run_aircraft.py -a " + args.AC_NAME +"_" + str(i+1) + " -p " + str(PPRZLINK_PORT+i) + " -i " + str(int(args.AC_ID) + i)
        print(sim_cmd) 
        SIM_THREAD = subprocess.Popen(sim_cmd.split(' '), start_new_session=True)
        SIM_PROCS.append(SIM_THREAD)    
    for i in range(0, NUMBER_ACS):
        SIM_PROCS[i].wait()
    for i in range(0, len(KAZE_PROCS)):
        os.killpg(os.getpgid(KAZE_PROCS[i].pid), signal.SIGTERM)

create_and_add_aircrafts()
compile_all_aircrafts()
run_all_aircrafts()
# clean up
tree = ET.parse(PPRZ_HOME+'/conf/conf.xml')
root = tree.getroot()
for ac in root.findall('aircraft'):
    ac_id = int(ac.attrib['ac_id'])
    if ac_id >= int(args.AC_ID) and ac_id < (int(args.AC_ID)+NUMBER_ACS):
        root.remove(ac)
tree.write(PPRZ_HOME+'/conf/conf.xml')
