#!/usr/bin/python
# -*- coding: utf-8 -*-

import json
import os
import urllib2
import urlparse
import xml.etree.ElementTree as ET
import sys
import time


#Default config..
BRANCHES = ['']
PHOTODIR = 'photos'

# Load config..
from config import *

def feedupdate():
    PHOTOURL = 'http://test.aspasia.net/pls/test/docs/%s'

    proplist = []

    # Make sure we have somewhere to save the photos to..
    if not os.path.exists(PHOTODIR):
        os.mkdir(PHOTODIR)
        print "Created '%s'." % PHOTODIR

    # And go..
    noepccount = 0
    nophotocount = 0
    badrecordcount = 0
    deadurlcount = 0

    start_time = time.time()

    for branch in BRANCHES:
        for proptype in ['RS', 'RL']:
            print "Branch '%s' proptype '%s'.." % (branch, proptype)
            xml = urllib2.urlopen('http://test.aspasia.net/pls/test/aspasia_search.xml?upw=testpassword&de=%s&pp=1000&br=%s' % (proptype, branch)).read()
            root = ET.fromstring(xml)
            houses = root.find('houses')

            idlist = []
            print "  %s properties found, grabbing details.." % len(houses)
            for house in houses:
                idlist.append(house.attrib['id'])

            for i in idlist:
                print "    Retrieving ID %s:" % i
                try:
                    url = 'http://test.aspasia.net/pls/test/xml_export.xml?prn=N&preg=N&pid=%s' % i
                    print "      [Debug] Opening %s" % url
                    xml = urllib2.urlopen(url, timeout = 5).read()
                except:
                    print "      [Debug] COULDN@T OPEN URL??!! (%s)" % sys.exc_info()[1]
                    deadurlcount += 1
                    continue
                print "      [Debug] Opened url successfully"
                root = ET.fromstring(xml)

                #find EPC rating
                epc = ''
                try:
                    for t in root[0].find('ACCOMMODATION').find('FLOOR').findall('ROOM'):
                        if t.find('PARA') is not None:
                            #print t.find('PARA').text
                            if t.find('PARA').text and 'EPC' in t.find('PARA').text:
                                epc = t.find('PARA').text[-1:].upper()
                                break
                except:
                    print "      Skipped: Error processing record (EPC)"
                    badrecordcount += 1
                    continue

                if not epc[-1:].upper() in ("A", "B", "C", "D", "E", "F", "G"):
                    if SKIPNOEPC:
                        print "      Skipped: No EPC found!"
                        noepccount += 1
                        continue
                    else:
                        print "      WARNING! No EPC found!"

                numphotos = len(root[0].find('PHOTOS').findall('PRINTQUALITYIMAGE')[:4])
                # Skip this prop if not enough photos
                if numphotos < 4:
                    print "      Skipped: not enough photos (%d)" % numphotos
                    nophotocount += 1
                    continue

                try:
                    p = {'id':i,
                         'type':proptype,
                         'address':root[0].find('ADDRESS').find('DISPLAY_ADDRESS').text,
                         'price':root[0].find('PROPERTYPRICETEXT').text.strip(),
                         'photos':[t.text.split('/')[-1:][0] for t in root[0].find('PHOTOS').findall('PRINTQUALITYIMAGE')[:4]],
                         'epc':epc
                         }
                except:
                    print "      Skipped: Error processing record (makeup)"
                    badrecordcount += 1
                    continue

                for t in p['photos']:
                    if not os.path.exists(os.path.join(PHOTODIR, t)):
                        print "      Grabbing photo '%s'..." % t
                        data = urllib2.urlopen(PHOTOURL % t).read()

                        # Write image to file
                        f = open(os.path.join(PHOTODIR, t), 'wb')
                        f.write(data)
                        f.close()
                    else:
                        print "      NOT grabbing '%s' as it exists already." % t

                proplist.append(p)


    # Write out to file..
    fname = "propertylist.txt"
    f = open(fname, "wb")
    json.dump(proplist, f)
    f.close()
    print "\n\nWrote %d properties to '%s'" % (len(proplist), fname)
    print "\nSkipped a total of %d properties:" % (noepccount+nophotocount+badrecordcount+deadurlcount)
    if noepccount > 0: print "   %d records had no-epc" % noepccount
    if nophotocount > 0: print "   %d records had <4 photos" % nophotocount
    if badrecordcount > 0: print "   %d records could not be processed" % badrecordcount
    if deadurlcount > 0: print "   %d URL's did not open" % deadurlcount

    time_taken = time.time()-start_time
    print "\n\nTime taken: %s secs" % time_taken

    print "\n\nDone!"

if __name__ == "__main__":
    feedupdate()

