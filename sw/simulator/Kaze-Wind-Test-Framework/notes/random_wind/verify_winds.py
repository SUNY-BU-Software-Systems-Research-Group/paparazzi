import csv
import numpy as np

max_magnitude = 10
file_str = '/home/jsanch49/paparazzi/sw/simulator/Kaze-Wind-Simulator/notes/random_wind/random.input'
csv_fields = ['wind_east', 'wind_north', 'wind_up', 'play_time']

with open(file_str) as csvfile:
    reader = csv.DictReader(csvfile, fieldnames=csv_fields)
    for row in reader:
        east, north, up = (float(row['wind_east']), float(row['wind_north']), float(row['wind_up']))
        raw_mag = east*east + north*north + up*up
        mag = np.power(raw_mag ,1/3)
        if mag > max_magnitude:
            print('failed verification.')
            exit()
print('passed verification.')
