from pprint import pprint

from shepherd_sdk import Shepherd


robot = Shepherd()
pprint(robot.health())
pprint(robot.capabilities())

