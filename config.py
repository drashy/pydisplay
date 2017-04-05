#!/usr/bin/python
# -*- coding: utf-8 -*-


#pydisplay settings..

NAME = "Display0"
SCREEN_RES = (1280,720)
RENDER_RES = (1280,720)

DATADIR = "data"
PHOTODIR = "photos"
#STARTUP_DELAY = 10 #secs
#SHADOW_COLOR = (0,0,0,128)
#ALLOWED_PROP_TYPES = ["RS", "RL"]
#DELAY = 7000 #ms

#OVERLAYS = {'logo1':{'x':10, 'y':10}, 'logo2':{'x':11, 'y':50}}#, 'htb':{'x':730, 'y':10}}

#Advert Settings
ADVERTDIR = "adverts"
ADVERTFREQ = 3 #every n properties
ADVERTDELAY = 7000 #ms

#    img num,   x,   y,   w,   h
#BLITS = [ [0, -64,   0,1024, 768],
#          [1, 960,   0, 320, 256],
#          [2, 960, 256, 320, 256],
#          [3, 960, 512, 320, 256]
#        ]
BLITS = [ [0,   0,   0, 960, 720],
          [1, 960,   0, 320, 240],
          [2, 960, 240, 320, 240],
          [3, 960, 480, 320, 240]
        ]






#pyupdate settings..
BRANCHES = ['BR1', 'BR2', 'BR3']
SKIPNOEPC = False
