"""
A module for showing Luxembourgish braille dots
as a progress bar or spinner.
"""

__author__ = "Kenan Masri"
__version__ = "0.1.0"
__license__ = "MIT"

import itertools
import argparse
import time
import sys

def animate(message, speed=0.033):
    for c in itertools.cycle([ 
        '⡀','⠄','⠂','⠁','⠈','⠐','⠠','⢀', # Luxembourgish braille dots :D
    ]):
        sys.stdout.write('\r' + c + ' ' + message)
        sys.stdout.flush()
        time.sleep(0.033)

if __name__ == "__main__":
    args = sys.argv
    message = ""
    speed = args[2] if len(args) >= 3 else 0.033

    sys.stdout.flush()
    while True:
        animate(message, speed=speed)
        time.sleep(0.001)
