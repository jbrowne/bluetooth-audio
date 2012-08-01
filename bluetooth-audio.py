#!/usr/bin/env python
"""
Usage: bluetooth-audio.py [setup]
Description: System script to pipe audio received from a bluetooth
    device into the system speakers.
    Call with "setup" parameter to set some initial parameters
Author: Jeff Browne (jbrowne@cs.ucsb.edu)

From http://ubuntuforums.org/showthread.php?t=1464189&page=4

It works! Thanks everyone! jackflap's link worked perfectly!
http://jprvita.wordpress.com/2009/12/15/1-2-3-4-a2dp-stream/ I've upgraded to
Ubuntu 10.04 by now; I have bluez 4.60 and pulseaudio 0.9.21.  Here's how I did
it for my iPod touch (3.1.3) on my Dell Inspiron 1720:
    1. I skipped step one, it was already loaded.
    2. Add "Enable=Source" right under "#Disable=Control,Source" in the
       "[General]" section.
    3. Restart the computer (to restart all the bluetooth 'stuff')
    4. Pair the iPod touch and the computer by clicking the bluetooth icon ->
       Set up new device -> Forward. Click PIN options and select '1234',
       Close. Enable bluetooth on the iPod; on the computer select it in the
       list, Forward. Type the PIN (1234) on the iPod, Connect.
    5. Install d-feet (from Synaptic) and run it (Applications -> Programming
       -> D-Feet). Then File -> Connect to System Bus. Under Bus Name select
       org.bluez and a tree will appear on the right. Under Object Paths,
       expand the /org/bluez/1464/hci0/dev's until you find the one with
       Interfaces that have org.bluez.AudioSource. Expand the AudioSource and
       double-click on Methods -> Connect(). A dialog will appear; just click
       Execute. It should say 'This method did not return anything' (I had to
       do it twice the first time.)
    6. Open a terminal (Accessories -> Terminal) and type pacmd and press
       enter.  6a. Then type list-sources and press enter. Find the one with
       device.description = "Name of your iPod" then scroll up to where it says
       'name: ' (under 'index: ') and copy the name somewhere without the < and
       >(mine was bluez_source.00_...) 6b. Then type list-sinks and press
       >enter. I only had one (ALSA) and copy the name just as before (mine was
       >alsa.output.pci-000_00...) 6c. Type exit and press enter.
    7. Now type 'pactl load-module module-loopback source=YOURSOURCE
       sink=YOURSINK' (for me, it was pactl load-module module-loopback
       source=bluez_source.00_... sink=alsa.output.pci-000_00...) and press
       enter! Viola! Now the iPod should play through the computer as if it
       were a headset!

Note: Save the number that returns after pactl. When you disconnect your iPod,
type pactl unload-module YOURNUMBER and press enter (it changes everytime; for
example: pactl unload-module 25) 
"""
import sys
import os
import re
import pdb
import time
import commands

bt_config_file = '/etc/bluetooth/audio.conf'

def CheckEnableSource():
    "Step 2. Returns True if the file is changed and needs to be reloaded"
    print "Enable Source"
    try:
        fp = open(bt_config_file, "r")
        strings = re.findall(r'Enable[\s]*=[\s]*Source', fp.read())
        fp.close()
        if len(strings) == 0:
            fp = open(bt_config_file, 'a')
            fp.write("Enable=Source")
            fp.close()
            return True
        else:
            return False
    except Exception as e:
        raise
    finally:
        fp.close()

def ReloadBlueTooth():
    "Step 3: Reload bluetooth"
    cmd = "service bluetooth restart"
    print "Reloading Bluetooth"
    print cmd
    print "~~~~~~~~~~~~~~~~~~~"
    try:
        (status, output) = commands.getstatusoutput(cmd)
        #print_output
        if status != 0:
            raise Exception("Error restarting bluetooth: \n%s" % output)
    except Exception as e:
        raise

def PromptForPairing():
    raw_input("\nPair the device with your computer and press <Enter>")

def DBus_GetDevices(service):
    cmd_query = "qdbus --system %s" % (service)

    print "Querying bluetooth devices"
    print cmd_query
    print "~~~~~~~~~~~~~~~~~~~"
    (status, output) = commands.getstatusoutput(cmd_query)
    #print_output
    paths = re.findall(r'(/org/bluez/[\d]+/hci\d+/dev[^/]*)\s+', output)
    return paths
    """
    if len(paths) > 1:
        idx = -1
        paths.insert(0, "<< Cancel >>")
        while idx not in range(len(paths)):
            print "Select device to connect to."
            for i, path in enumerate(paths):
                print "%s:\t%s" %(i, path)
            idx = int(raw_input("--> "))
        if idx == 0:
            raise Exception ("User ended selection")
        else:
            path = paths[idx]
    elif len(paths) == 1:
        path = paths[0]
        print "Choosing default device %s" % (path)
    else:
        raise Exception ("Could not connect on dbus: no matching path")

    return path
    """
    
def DBus_isConnected(service, path):
    is_connected = "org.bluez.Control.IsConnected"
    cmd_check = "qdbus --system %s %s %s" % (service, path, is_connected)
    print "Checkng if already connected to device %s" % (path)
    print cmd_check
    print "~~~~~~~~~~~~~~~~~~~"
    try:
        (status, output) = commands.getstatusoutput(cmd_check)
        if output == "true":
            return True
        elif output == "false":
            return False
        else:
            raise Exception("Cannot determine connected status of %s\n%s" %
                            (path, output))
    except Exception as e:
        raise
    
def DBusConnectToDevice(service, path):
    connect = "org.bluez.AudioSource.Connect"
    cmd_connect = "qdbus --system %s %s %s" % (service, path, connect)
    print "Connecting to device %s" % (path)
    print cmd_connect
    print "~~~~~~~~~~~~~~~~~~~"
    try:
        (status, output) = commands.getstatusoutput(cmd_connect)
        print "Status %s" % (status)
        print output
    except Exception as e:
        raise

def DBusConnect():
    service = "org.bluez"
    paths = DBus_GetDevices(service)
    for path in paths:
        if DBus_isConnected(service, path):
            print "Connected to %s" % (path)
        else:
            DBusConnectToDevice(service, path)




def ParseSinkSourceList(sourcelist):
    retList = []
    curName = None
    curDesc = None
    for line in sourcelist.split("\n"):
        line = line.strip()
        if line.startswith("index"):
            curName = None
            curDesc = None

        if line.startswith("name"):
            curName = re.findall(r'name:\s<(.*)>', line)[0]
        if line.startswith("device.description"):
            curDesc = re.findall(r'device.description = "(.*)"', line)[0]
            retList.append( (curName, curDesc,) )
    return retList

def ChooseAudioSource():
    cmd_list_sources = "pacmd list-sources"
    print "Populating Audio Sources"
    print cmd_list_sources
    print "~~~~~~~~~~~~~~~~~~~"
    (status, output) = commands.getstatusoutput(cmd_list_sources)
    #print_output
    #device.description = "HD Webcam C910 Digital Stereo (IEC958)"
    sources = ParseSinkSourceList(output)

    if len(sources) > 1:
        sources.insert(0,("<< Cancel >>", "<< Cancel >>"))
        idx = -1
        while idx not in range(len(sources)):
            print "Which source would you like to use?"
            for i, name in enumerate(sources):
                print "%s:\t%s" % (i, name[1])
            idx = int(raw_input("--> "))

        if idx == 0:
            raise Exception ("Exit by user")
        else:
            source = sources[idx][0]
    elif len(sources) == 1:
        print "Using default source:\n%s" % (sources[0][1])
        source = sources[0][0]
    else:
        raise Exception ("No sources available")

    return source

def ChooseAudioSink():
    cmd_list_sinks = "pacmd list-sinks"
    print "Populating Audio Sources"
    print cmd_list_sinks
    print "~~~~~~~~~~~~~~~~~~~"
    (status, output) = commands.getstatusoutput(cmd_list_sinks)
    #print_output
    sinks = ParseSinkSourceList(output)

    if len(sinks) > 1:
        sinks.insert(0,("<< Cancel >>", "<<cancel>>"))
        if len(sinks) > 1:
            idx = -1
            while idx not in range(len(sinks)):
                print "Which sink would you like to use?"
                for i, name in enumerate(sinks):
                    print "%s:\t%s" % (i, name[1])
                idx = int(raw_input("--> "))
            if idx == 0:
                raise Exception ("Exit by user")
            else:
                sink = sinks[idx][0]
    elif len(sinks) == 1:
        print "Using default sink\n%s" % (sinks[0][1])
        sink = sinks[0][0]
    else:
        raise Exception ("No sinks available")

    return sink

    
    
def LinkSourceAndSink(source, sink):
    cmd_link = "pactl load-module module-loopback source=%s sink=%s" % \
        (source, sink)
    print "Linking Source and Sink"
    print cmd_link
    print "~~~~~~~~~~~~~~~~~~~"
    (status, output) = commands.getstatusoutput(cmd_link)
    try:
        #print_output
        return int(output)
    except Exception as e:
        print "Unexpected output: \n%s" % (output)
        raise
    
def UnlinkSourceAndSink(module):
    cmd_link = "pactl unload-module %s" % (module)
    print "UN-Linking Source and Sink"
    print cmd_link
    print "~~~~~~~~~~~~~~~~~~~"
    (status, output) = commands.getstatusoutput(cmd_link)
    #print_output
    

    

def Setup():
    if CheckEnableSource():
        ReloadBlueTooth()

def main(args):
    if len(args) > 1 and args[1].lower() == "setup":
        Setup()
    #PromptForPairing()
    DBusConnect()
    source = ChooseAudioSource()
    sink = ChooseAudioSink()
    try:
        moduleNumber = LinkSourceAndSink(source, sink)
        while True:
            time.sleep(100)
    finally:
        UnlinkSourceAndSink(moduleNumber)


if __name__ == "__main__":
    main(sys.argv)
    exit(0)
