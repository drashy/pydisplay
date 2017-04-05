#!/usr/bin/python
# -*- coding: utf-8 -*-

import json
import os
import re
import xml.etree.ElementTree as ET
import math
import random
import time
import threading
import datetime
import urllib2
import checkin

try:
    import pygame
    from pygame.locals import *
except ImportError:
    print '[!] Error [!] Please ensure you have pygame installed'
    exit()

#Version History
#  150112-1 - Added threaded update
#
#  141104-1 - Added config.py file for easier distribution
#             Added render_res to allow for under/oversized renderings
#             Added 'r' key to reload data/ads
#             Strip excess whitespace from price
#             Added feed-updating after 60 seconds and every hour after that


VERSION = "150112-1"
random.seed(time.time())


# Default Settings..
NAME = "None"
SCREEN_RES = (1280,720)
RENDER_RES = (1280,720)

DATADIR = "data"
PHOTODIR = "photos"
STARTUP_DELAY = 10 #secs
SHADOW_COLOR = (0,0,0,128)
ALLOWED_PROP_TYPES = ["RS", "RL"]
DELAY = 7000 #ms

OVERLAYS = {'logo1':{'x':10, 'y':10}, 'logo2':{'x':11, 'y':50}}#, 'htb':{'x':730, 'y':10}}

#Default Advert Settings
ADVERTDIR = "adverts"
ADVERTFREQ = 5 #every n properties
ADVERTDELAY = 10000 #ms

FEEDUPDATED = True

# Load config..
from config import *


class threadedUpdate(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)

    def run(self):
        print "\n\n=====Feed Update====================================================="
        try:
            import feedupdate
            feedupdate.feedupdate()
            FEEDUPDATED = True
        except KeyboardInterrupt:
            print "Keyboar Interrupt!"
            exit()
        except:
            print "ERROR: Could not update feed"
        print "=====End Feed Update=================================================\n\n"


class pydisplay(object):
    SOURCE = 'txt'
    XMLFILENAME = ""
    starttime = 0
    loadtime = 0
    loop = 1
    res = {}
    ads = {}
    DEBUG = False
    UPDATETIME = 0

    def __init__(self):
        print "pydisplay %s by Paul Ashton" % VERSION
        print "[Info] Branch name '%s'" % NAME
        print "[Info] Screen: %s, Render: %s" % (str(SCREEN_RES), str(RENDER_RES))
        print "[Info] Allowed property types: %s" % ALLOWED_PROP_TYPES

        if(not os.path.exists('propertylist.txt')):
            self.updatefeed()
        #  print "[Info] Using TXT as source"
        #  self.SOURCE = 'txt'
        #else:
        #  print "[Info] Using XML as source"
        #  self.SOURCE = 'xml'

        if(STARTUP_DELAY):
            print "[Info] Waiting for %s secs.." % STARTUP_DELAY
            time.sleep(STARTUP_DELAY)

        print "[Info] Setting up screen.."
        pygame.init()
        os.environ['SDL_VIDEO_WINDOW_POS'] = "0,0"
        self.screen = pygame.display.set_mode(SCREEN_RES,SRCALPHA|HWSURFACE|NOFRAME)
        #self.screen = pygame.display.set_mode(SCREEN_RES,SRCALPHA|HWSURFACE|FULLSCREEN)

        # Set up render buffer..
        self.rbuffer = pygame.Surface(RENDER_RES)

        print "[Info] Loading assets.."
        self.res["logo1"] = pygame.image.load(os.path.join(DATADIR,"logo1.png"))
        self.res["logo2"] = pygame.image.load(os.path.join(DATADIR,"logo2.png"))
        self.res["gilsans40"] = pygame.font.Font(os.path.join(DATADIR,"gilsansmt.ttf"), 40)
        self.res["gilsans30"] = pygame.font.Font(os.path.join(DATADIR,"gilsansmt.ttf"), 30)
        self.res["gilsans20"] = pygame.font.Font(os.path.join(DATADIR,"gilsansmt.ttf"), 20)
        self.res["gilsans10"] = pygame.font.Font(os.path.join(DATADIR,"gilsansmt.ttf"), 10)
        self.res["standby"] = pygame.image.load(os.path.join(DATADIR,"standby.jpg"))

        self.res["htb"] = pygame.image.load(os.path.join(DATADIR,"htb.png"))

        self.res["noimg"] = pygame.image.load(os.path.join(DATADIR,"noimg.jpg"))

        self.clock = pygame.time.Clock()
        self.UPDATETIME = time.time()+60 # 60 seconds in the future :D

        self.loadsource()
        self.main()


    def loadadverts(self):
        # Load adverts if needed
        if os.path.exists(ADVERTDIR):
            print "[Info] Loading adverts.."
            for f in os.listdir(ADVERTDIR):
                if ".jpg" in f.lower():
                    self.ads[f] = pygame.image.load(os.path.join(ADVERTDIR, f))
                    print "[Info] Advert loaded '%s'." % f
            print "[Info] %s adverts loaded." % len(self.ads)


    def loadsource(self):
        if self.SOURCE == 'xml':
            self.loadxml()
            sourcetime = "unknown (xml)"
        elif self.SOURCE == 'txt':
            self.loadtxt()
            sourcetime = os.path.getmtime('propertylist.txt')
        else:
            print "[Error] Unknown source '%s'" % self.SOURCE
            exit()

        # Lets have some randomness..
        random.shuffle(self.properties)

        #Update checkin server
        checkin.checkin(NAME, "ver:%s, props:%s" % (VERSION, len(self.properties)))
        checkin.checkin(NAME+"_feedtime", "%s" % sourcetime)
        checkin.checkin(NAME+"_time", "%s" % time.time())



    def loadtxt(self):
        print "[Debug] loadtxt()"
        f = open('propertylist.txt')
        self.properties = json.load(f)
        f.close()
        print "%s properties loaded." % len(self.properties)


    def loadxml(self):
        print "[Debug] loadxml()"
        # Find latest XML file
        files = os.listdir(PHOTODIR)
        valid = []
        for f in files:
            if f.lower()[-4:] == ".xml":
                valid.append(f)
        valid.sort()
        valid.reverse()
        if len(valid) < 1:
            print "[Error] No XML file found"
            exit()

        print "[Info] %s XML Files %s" % (len(valid), list(valid))
        done = False
        while not done:
            for filename in valid:
                filename = os.path.join(PHOTODIR, filename)
                print "[Info] XML = '%s'" % filename
                missing = 0
                try:
                    tree = ET.parse(filename)
                    root = tree.getroot()

                    self.properties = []
                    for child in root:
                        try:
                            aspid = child.find('id').text
                            proptype = child.find('type').text
                            if proptype not in ALLOWED_PROP_TYPES:
                                print "[Info] Not adding %s as '%s' is not allowed type" % (aspid, proptype)
                                continue
                            street = child.find('street').text.strip()
                            price = child.find('price').text.strip()
                            if u"£" not in price:
                                price = u"£%s pcm" % price #rental

                            #Images
                            img1 = child.find('image1').text
                            img2 = child.find('image2').text
                            img3 = child.find('image3').text
                            img4 = child.find('image4').text
                            #print "[debug] %s" % os.path.exists(os.path.join(PHOTODIR,img1))
                            if not os.path.exists(os.path.join(PHOTODIR,img1)) or not os.path.exists(os.path.join(PHOTODIR,img2)) or not os.path.exists(os.path.join(PHOTODIR,img3)) or not os.path.exists(os.path.join(PHOTODIR,img4)):
                                #print "[Info] Not adding %s as we don't have the images for it" % aspid
                                missing += 1
                                continue

                            #epc rating
                            try:
                                epc_rating = child.find('extras').find('extraitem1').text[-1:]
                            except:
                                epc_rating = "?"
                            #self.properties.append([street, price, aspid, img1, img2, img3, img4, epc_rating, proptype])
                            self.properties.append({'id':aspid,
                                                    'type':proptype,
                                                    'address':street,
                                                    'price':price,
                                                    'photos':[img1, img2, img3, img4],
                                                    'epc':epc_rating
                                                    })
                        except:
                            print "Failed to add %s to property list" % aspid
                            continue
                    if missing:
                        print "[Info] Ignored %s properties as they had missing images" % missing

                    if len(self.properties) < 1:
                        print "[Error] No displayable properties in feed"
                        raise

                except:
                    print "[ERROR] Could not parse xml file."
                    continue
                break

            if 'root' not in locals():
                print "[Error] No valid XML files, stand by.."
                self.screen.blit(self.res["standby"], (0,0))
                pygame.display.update()
                time.sleep(10)
            else:
                done = True

        #random.shuffle(self.properties)
        self.XMLFILENAME = filename
        self.loadtime = time.time()
        print "[Info] Loaded %s properties from '%s' at %s." % (len(self.properties), filename, self.loadtime)
        if len(self.properties) < 1:
            print "[Error] Nothing to display"
            exit()


    def draw_advert(self, ADVERT):
        self.rbuffer.fill((0,0,0))
        w,h = self.ads[ADVERT].get_size()
        self.rbuffer.blit(self.ads[ADVERT], ((RENDER_RES[0]-w)/2,(RENDER_RES[1]-h)/2))


    def draw_property(self, propnum):
        #Property Images
        imgs = [0,0,0,0]
        try:
            imgs[0] = pygame.image.load(os.path.join(PHOTODIR,self.properties[propnum]['photos'][0]))
        except:
            imgs[0] = self.res["noimg"]
            print "[Debug] Image could not load '%s'" % os.path.join(PHOTODIR,self.properties[propnum]['photos'][0])
        try:
            imgs[1] = pygame.image.load(os.path.join(PHOTODIR,self.properties[propnum]['photos'][1]))
        except:
            imgs[1] = self.res["noimg"]
            print "[Debug] Image could not load '%s'" % os.path.join(PHOTODIR,self.properties[propnum]['photos'][1])
        try:
            imgs[2] = pygame.image.load(os.path.join(PHOTODIR,self.properties[propnum]['photos'][2]))
        except:
            imgs[2] = self.res["noimg"]
            print "[Debug] Image could not load '%s'" % os.path.join(PHOTODIR,self.properties[propnum]['photos'][2])
        try:
            imgs[3] = pygame.image.load(os.path.join(PHOTODIR,self.properties[propnum]['photos'][3]))
        except:
            imgs[3] = self.res["noimg"]
            print "[Debug] Image could not load '%s'" % os.path.join(PHOTODIR,self.properties[propnum]['photos'][3])

        #Clear buffer and blit photos to it..
        self.rbuffer.fill((0,0,0))
        for b in BLITS:
            self.rbuffer.blit(pygame.transform.smoothscale(imgs[b[0]], (b[3], b[4])), (b[1],b[2]))

        #Overlays..
        for i in OVERLAYS:
            self.rbuffer.blit(self.res[i], (OVERLAYS[i]['x'], OVERLAYS[i]['y']))

        #Darkened bar
        s = pygame.Surface((960, 100))
        s.set_alpha(64)
        s.fill((0, 0, 0))
        self.rbuffer.blit(s, (0, RENDER_RES[1]-100))

        #Texts..
        def shadowtext(font, text, pos, color, shadow, depth=1):
            self.rbuffer.blit(font.render(text, True, shadow), (pos[0]-depth, pos[1]-depth))
            self.rbuffer.blit(font.render(text, True, shadow), (pos[0]+depth, pos[1]+depth))
            self.rbuffer.blit(font.render(text, True, color), pos)

        #Address
        shadowtext(self.res["gilsans40"], self.properties[propnum]['address'], (10,RENDER_RES[1]-100), (255,255,255), SHADOW_COLOR)
        #Price
        shadowtext(self.res["gilsans40"], self.properties[propnum]['price'], (10,RENDER_RES[1]-50), (255,255,255), SHADOW_COLOR)
        #ASP ID
        shadowtext(self.res["gilsans20"], "ID: "+self.properties[propnum]['id'], (865,RENDER_RES[1]-25), (255,255,255), SHADOW_COLOR)

        #EPC Rating
        if self.properties[propnum]['epc'][-1:] in ("A", "B", "C", "D", "E", "F", "G"):
            shadowtext(self.res["gilsans20"], "EPC Rating: %s" % self.properties[propnum]['epc'], (840,RENDER_RES[1]-100), (255,255,255), SHADOW_COLOR)
        else:
            print "[Debug] EPC rating missing for ID %s" % self.properties[propnum]['id']

    def updatefeed(self):
        threadedUpdate().start()

    def main(self):
        quit = 0
        frame = 0
        propnum = 0
        counter = 0
        ADVERT = False
        displayed = False

        self.starttime = pygame.time.get_ticks()

        self.loadadverts()

        #Hide the mouse
        pygame.mouse.set_visible(False)

        print "[%s][%s/%s] %s: (%s) %s" % (self.loop, propnum+1, len(self.properties), self.properties[propnum]['id'], self.properties[propnum]['type'], self.properties[propnum]['address'])

        while not quit:
            if not displayed:
                displayed = True

                if ADVERT:
                    self.draw_advert(ADVERT)
                else:
                    self.draw_property(propnum)

                if self.DEBUG:
                    s = pygame.Surface((500,200))
                    s.set_alpha(164)
                    s.fill((0,255,0))
                    self.rbuffer.blit(s, (100,100))
                    if ADVERT:
                        self.rbuffer.blit(self.res["gilsans20"].render("[Advert] %s" % ADVERT, True, (255,255,255)), (100,100))
                    else:
                        self.rbuffer.blit(self.res["gilsans20"].render("[%s/%s] %s: %s" % (propnum+1, len(self.properties), self.properties[propnum]['id'], self.properties[propnum]['address']), True, (255,255,255)), (100,100))
                        self.rbuffer.blit(self.res["gilsans20"].render(self.properties[propnum]['photos'][0], True, (0,0,0)), (100,120))
                        self.rbuffer.blit(self.res["gilsans20"].render(self.properties[propnum]['photos'][1], True, (0,0,0)), (100,140))
                        self.rbuffer.blit(self.res["gilsans20"].render(self.properties[propnum]['photos'][2], True, (0,0,0)), (100,160))
                        self.rbuffer.blit(self.res["gilsans20"].render(self.properties[propnum]['photos'][3], True, (0,0,0)), (100,180))
                        self.rbuffer.blit(self.res["gilsans20"].render("%s" % pygame.time.get_ticks(), True, (255,255,255)), (100,200))
                        self.rbuffer.blit(self.res["gilsans20"].render(self.SOURCE, True, (255,255,255)), (100,220))

                # Render to screen
                pygame.transform.smoothscale(self.rbuffer, SCREEN_RES, self.screen)

            # Process events
            for event in pygame.event.get():
                if event.type == KEYUP:
                    if event.key == K_ESCAPE:
                        quit = True
                    if event.key == K_d:
                        self.DEBUG = not self.DEBUG
                        displayed = False
                    if event.key == K_f:
                        self.toggle_fullscreen()
                    if event.key == K_SPACE:
                        self.starttime = -DELAY
                    if event.key == K_r:
                        propnum = len(self.properties)-1
                        self.starttime = -DELAY

            pygame.display.update()
            self.clock.tick(30)
            frame += 1


            # Update the feed?
            if time.time() >= self.UPDATETIME:
                self.UPDATETIME = time.time() + 60*60*4 # 4 hour in future
                self.updatefeed()
                print "[Info] Next feed update at %s." % datetime.datetime.fromtimestamp(self.UPDATETIME).strftime('%Y-%m-%d %H:%M:%S')


            # Delay..
            if ADVERT:
                checktime = self.starttime + ADVERTDELAY
            else:
                checktime = self.starttime + DELAY

            if pygame.time.get_ticks() > checktime:
                self.starttime = pygame.time.get_ticks()
                if ADVERT:
                    ADVERT = False
                    displayed = False
                else:
                    displayed = False
                    propnum += 1
                    counter += 1
                    if propnum >= len(self.properties):
                        self.loadsource()
                        self.loadadverts()
                        propnum = 0
                        self.loop += 1
                    if self.ads and counter % ADVERTFREQ == 0:
                        ADVERT = random.choice(self.ads.keys())
                        print "[Advert] '%s'" % ADVERT
                    print "[%s][%s/%s] %s: (%s) %s" % (self.loop, propnum+1, len(self.properties), self.properties[propnum]['id'], self.properties[propnum]['type'], self.properties[propnum]['address'])


pydisplay()
