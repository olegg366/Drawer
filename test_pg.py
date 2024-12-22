import pyautogui as pg
from time import sleep

pg.FAILSAFE = False

for i in range(0, 500, 10):
    pg.mouseDown(_pause=False)
    pg.moveRel(i, 0, _pause=False)
    pg.mouseUp(_pause=False)