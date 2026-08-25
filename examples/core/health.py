import sys
from pprint import pprint

from shepherd_sdk import Shepherd


robot = Shepherd(sys.argv[1]) if len(sys.argv) > 1 else Shepherd()
pprint(robot.health())
pprint(robot.capabilities())

