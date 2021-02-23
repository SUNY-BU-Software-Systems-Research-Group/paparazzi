# Kaze-Paparazzi-Test-Framework

HOW TO START PAPARAZZI WIN 10:

Open XLaunch application and hit next until there is an additional arguments field. Here input "-ac" and click finish.
Then make sure the DISPLAY variable is configured properly, as WSL is on another IP.
Open Ubuntu 18.04 and type "./paparazzi/paparazzi &".


HOW TO INSTALL KAZE WIND SIMULATOR:

"cd paparazzi/sw/simulator/"

"git clone <this repo's url>"

"cd Kaze-Wind-Simulator"

"python3 -m venv venv"

"source venv/bin/activate"

"python -m pip install -r requirements.txt"

"python main.py <sample.input>"


DEPENDENCIES:

python >= 3.6.9

look at contents of requirements.txt for python dependencies


USAGE:

usage: main.py [-h] [--loglevel LOGLEVEL] [--ircontrast IRCONTRAST] windpath

Create and Simulate Customizable Wind Condititons for Paparazzi UAV simulator

positional arguments:

  windpath              Specifies relative or absolute file location of the
                        wind playback file.

optional arguments:

  -h, --help            show this help message and exit
  
  --loglevel LOGLEVEL   Can input <debug|info|warning|error> (debug)
  
  --ircontrast IRCONTRAST
                        Set the ircontrast at each wind message (400)


IMPORTANT NOTES:

This program works as expected in 'nps' targets and not in 'sim' targets. 

At exit, kaze disconnects to the ivy bus and there no longer will be wind data sent to the GCS. 

Exit Kaze before stopping all processes in Paparazzi. Future work could include Kaze as a process that paparazzi can exit with the button press. If the user attempts to exit Kaze after exiting the GCS an easy workaround to exit Kaze is starting the GCS. This allows Kaze to send the final cb it was waiting to do before exiting.

Kaze will playback wind data in a loop (from top to bottom). A file with one entry means playback the same data until the program ends.
