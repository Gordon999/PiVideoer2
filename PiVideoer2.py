#!/usr/bin/env python3

"""Copyright (c) 2025
Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:
The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE."""

# Version
version = "1.10"

import time
import cv2
import numpy as np
import pygame
from pygame.locals import *
from PIL import Image
import os,glob
import signal
import datetime
import shutil
import glob
from gpiozero import Button
from gpiozero import LED
from gpiozero import CPUTemperature
from gpiozero import PWMLED
import sys
import random
from picamera2 import Picamera2, Preview, MappedArray
from picamera2.encoders import H264Encoder
from picamera2.outputs import CircularOutput
from libcamera import controls
import threading
from queue import Queue
import ephem
import datetime

# Your Location
somewhere = ephem.Observer()
somewhere.lat = '51.49340' # set your location latitude
somewhere.lon = '00.00980' # set your location longtitude
somewhere.elevation = 100  # set your location height
UTC_offset = 0             # set your local time offset to UTC

# set screen size
scr_width  = 800
scr_height = 480

# set preview size
pre_width  = 640
pre_height = 480

# use GPIO for external camera triggers, IR switch and/or optional FAN (NOT Pi5 Active Cooler / Case Fan).
# DISABLE Pi FAN CONTROL in Preferences > Performance to GPIO 14 !!
use_gpio   = 1

# ext camera trigger output gpios (if use_gpio = 1)
s_focus    = 20
s_trig     = 21

# ext trigger input gpios (if use_gpio = 1)
e_trig1    = 12
e_trig2    = 16

# Waveshare IR filter switch output (if use_gpio = 1)
sw_ir      = 26
sw_ir1     = 19

# IR light
ir_light   = 13

# fan ctrl gpio (if use_gpio = 1) This is not the Pi5 active cooler !!
# DISABLE Pi FAN CONTROL in Preferences > Performance to GPIO 14 !!
fan        = 14
fan_ctrl   = 1  # 0 for OFF.

# enable watchdog
watch = False

# set default config parameters
v_crop        = 150     # size of vertical detection window *
h_crop        = 110     # size of horizontal detection window *
threshold     = 15      # minm change in pixel luminance *
threshold2    = 255     # maxm change in pixel luminance *
detection     = 10      # % of pixels detected to trigger, in % *
det_high      = 100     # max % of pixels detected to trigger, in %  *
col_filter    = 3       # 3 = FULL, SEE COL_FILTERS *
nr            = 2       # Noise reduction, 0 off, 1 low, 2 high *
pre_frames    = 2       # seconds *
dspeed        = 100     # detection speed 1-100, 1 = slowest *
mp4_fps       = 25      # set MP4 fps *
mp4_anno      = 1       # mp4_annotate MP4s with date and time , 1 = yes, 0 = no *
SD_F_Act      = 0       # Action on SD FULL, 0 = STOP, 1 = DELETE OLDEST VIDEO, 2 = COPY TO USB (if fitted) *
interval      = 0       # seconds of wait between capturing Pictures / TIMELAPSE (set threshold to 0)*
v_length      = 15000   # video length in mS *
# setup for 1st camera
mode          = 1       # set camera mode *
speed         = 18      # set manual shutter , in shutters list *
gain          = 0       # set gain , 0 = AUTO *
brightness    = 0       # set camera brightness *
contrast      = 7       # set camera contrast *
awb           = 0       # auto white balance, 0 = AUTO *
red           = 1.5     # red balance *
blue          = 1.5     # blue balance *
meter         = 0       # metering *
ev            = -4      # eV *
denoise       = 0       # denoise level *
quality       = 90      # video quality *
sharpness     = 4       # sharpness *
saturation    = 10      # saturation *
fps           = 25      # camera fps
AF_f_mode     = 1       # AF camera focus mode *
AF_f_spot     = 0       # AF spot mode
AF_focus      = 1       # AF camera manual focus default *
IRF           = 0       # Waveshare IR Filter switch MODE *
IRF_on        = 0       # Waveshare IR Filter switch ON/OFF *
ir_on_hour    = 9       # Switch IR Filter ON Hour, 1 - 23, 0 will NOT SWITCH *
ir_of_hour    = 10      # Switch IR Filter OFF Hour, 1 - 23, 0 will NOT SWITCH *
ir_on_mins    = 0       # Switch IR Filter ON mins, 0 - 59 *
ir_of_mins    = 0       # Switch IR Filter OFF mins, 0 - 59 *
# setup for 2nd camera (Pi5 ONLY)
mode1         = 1       # set camera mode *
speed1        = 18      # set manual shutter , in shutters list *
gain1         = 0       # set gain , 0 = AUTO *
brightness1   = 0       # set camera brightness *
contrast1     = 7       # set camera contrast *
awb1          = 0       # auto white balance, 0 = AUTO *
red1          = 1.5     # red balance *
blue1         = 1.5     # blue balance *
meter1        = 0       # metering *
ev1           = -4      # eV *
denoise1      = 0       # denoise level *
quality1      = 90      # video quality *
sharpness1    = 4       # sharpness *
saturation1   = 10      # saturation *
fps1          = 25      # camera fps *
AF_f_mode1    = 1       # AF camera focus mode *
AF_f_spot1    = 0       # AF spot mode
AF_focus1     = 1       # AF camera manual focus default *
IRF1          = 0       # Waveshare IR Filter switch MODE *
IRF_on1       = 0       # Waveshare IR Filter switch ON/OFF *
ir_on_hour1   = 9       # Switch IR Filter ON Hour, 1 - 23, 0 will NOT SWITCH *
ir_of_hour1   = 10      # Switch IR Filter OFF Hour, 1 - 23, 0 will NOT SWITCH *
ir_on_mins1   = 0       # Switch IR Filter ON mins, 0 - 59 *
ir_of_mins1   = 0       # Switch IR Filter OFF mins, 0 - 59 *
#===========================================================================================
Capture       = 1       # CAPTURE AT BOOT , 0 = off, 1 = ON *
preview       = 0       # show detected changed pixels *
noframe       = 0       # set to 1 for no window frame
ES            = 1       # trigger external camera, 0 = OFF, 1 = SHORT, 2 = LONG *
SD_limit      = 90      # max SD card filled in % before copy to USB if available or STOP *
auto_save     = 1       # set to 1 to automatically copy to SD card
auto_time     = 10      # time after which auto save actioned, 0 = OFF *
ram_limit     = 150     # MBytes, copy from RAM to SD card when reached *
check_time    = 10      # fan sampling time in seconds *
fan_low       = 65      # fan OFF below this, 25% to 100% pwm above this *
fan_high      = 78      # fan 100% pwm above this *
sd_hour       = 0       # Shutdown Hour, 1 - 23, 0 will NOT SHUTDOWN *
on_hour       = 12      # Switch Camera 1-2 Hour, 1 - 23, 0 will NOT SWITCH *
of_hour       = 14      # Switch Camera 2-1 Hour, 1 - 23, 0 will NOT SWITCH *
on_mins       = 12      # Switch Camera 1-2 mins, 0 - 59 *
of_mins       = 14      # Switch Camera 2-1 mins, 0 - 59 *
m_alpha       = 130     # MASK ALPHA *
sync_time     = 120     # time sync check time in seconds *
camera        = 0       # camera in use *
camera_sw     = 0       # camera switch mode *

# * adjustable whilst running

# initialise parameters
config_file   = "PiVideoconfig035.txt"
old_camera    = camera
synced        = 0
show          = 0
reboot        = 0
stopped       = 0
record        = 0
timer         = 0
zoom          = 0
trace         = 0
timer10       = 0
col_filterp   = 0
a             = int(scr_width/3)
b             = int(scr_height/2)
fcount        = 0
dc            = 0
q             = 0
of            = 0
txtvids       = []
restart2      = 0
timer2        = time.monotonic()
res2          = 0
max_fcount    = 10
gcount        = 0
fstep         = 20
old_foc       = 0
min_foc       = 15
rep           = 0
fps2          = fps
stop_thread   = False
pause_thread  = False
vformat       = 0
sync_timer    = time.monotonic()
sw_act        = 1
menu          = -1
stop_rec      = 0
rec_stop      = 0
show_vid      = 1
old_show_vid  = show_vid

# apply timestamp to videos
def apply_timestamp(request):
  global mp4_anno
  if mp4_anno == 1:
      timestamp = time.strftime("%Y-%m-%d %X")
      with MappedArray(request, "main") as m:
          lst = list(origin)
          lst[0] += 370
          lst[1] -= 20
          end_point = tuple(lst)
          cv2.rectangle(m.array, origin, end_point, (0,0,0), -1) 
          cv2.putText(m.array, timestamp, origin, font, scale, colour, thickness)
      
# setup directories
Home_Files  = []
Home_Files.append(os.getlogin())
vid_dir = "/home/" + Home_Files[0]+ "/Videos/"

cameras       = ['', 'Pi v1', 'Pi v2', 'Pi v3', 'Pi HQ','Arducam 16MP','Arducam 64MP', 'Pi GS','Arducam Owlsight','imx290','imx500','ov9281']
camids        = ['','ov5647','imx219','imx708','imx477',      'imx519',      'arduca','imx296',          'ov64a4','imx290','imx500','ov9281']
max_gains     = [64,     255,      40,      64,      88,            64,            64,      64,                64,      64,      64,      64]
swidths       = [ 0,    2592,    3280,    4608,    4056,          4656,          9152,    1456,              9248,    1920,    1920,    1280]
sheights      = [ 0,    1944,     2464,   2592,    3040,          3496,          6944,    1088,              6944,    1080,    1080,     800]
modes         = ['manual','normal','short','long']
meters        = ['CentreWeighted','Spot','Matrix']
awbs          = ['auto','tungsten','fluorescent','indoor','daylight','cloudy','custom']
denoises      = ['off','fast','HQ']
col_filters   = ['RED','GREEN','BLUE','FULL']
noise_filters = ['OFF','LOW','HIGH']
AF_f_modes    = ['Manual','Auto','Continuous']
shutters      = [-4000,-2000,-1600,-1250,-1000,-800,-640,-500,-400,-320,-288,-250,-240,-200,-160,-144,-125,-120,-100,-96,-80,-60,
                -50,-48,-40,-30,-25,-20,-15,-13,-10,-8,-6,-5,-4,-3,0.4,0.5,0.6,0.8,1]
IR_filters    = ['Auto','Set Times','OFF','ON']
camera_sws    = ['Auto','Set Times','ONE','TWO']

#check linux version.
if os.path.exists ("/run/shm/lv.txt"): 
    os.remove("/run/shm/lv.txt")
os.system("cat /etc/os-release >> /run/shm/lv.txt")
with open("/run/shm/lv.txt", "r") as file:
        line = file.readline()
        while line:
           line = file.readline()
           if line[0:16] == "VERSION_CODENAME":
               lver = line
lvers = lver.split("=")
lver = lvers[1][0:6]

#check Pi model.
Pi = 0
if os.path.exists ('/run/shm/md.txt'): 
    os.remove("/run/shm/md.txt")
os.system("cat /proc/cpuinfo >> /run/shm/md.txt")
with open("/run/shm/md.txt", "r") as file:
        line = file.readline()
        while line:
           line = file.readline()
           if line[0:5] == "Model":
               model = line
mod = model.split(" ")
if mod[3] == "5":
    Pi = 5

# setup gpio if enabled
if use_gpio == 1:
    # external output triggers
    led_s_trig   = LED(s_trig)   # external camera trigger
    led_s_focus  = LED(s_focus)  # external camera focus
    led_sw_ir    = LED(sw_ir)    # waveshare IR filter camera 1
    led_sw_ir1   = LED(sw_ir1)   # waveshare IR filter camera 1
    led_ir_light = LED(ir_light) # IR light
    led_ir_light.off()
    led_s_trig.off()
    led_s_focus.off()
    # optional fan control
    if fan_ctrl == 1:
        led_fan = PWMLED(fan)
        led_fan.value = 0
    # external input triggers
    button_e_trig1 = Button(e_trig1,pull_up=False)
    button_e_trig2 = Button(e_trig2,pull_up=False)

# check Vid_configXX.txt exists, if not then write default values
if not os.path.exists(config_file):
    defaults = [h_crop,threshold,fps,mode,speed,gain,brightness,contrast,SD_limit,preview,awb,detection,int(red*10),int(blue*10),
              interval,v_crop,v_length,ev,meter,ES,a,b,sharpness,saturation,denoise,fan_low,fan_high,det_high,quality,
              check_time,sd_hour,vformat,threshold2,col_filter,nr,pre_frames,auto_time,ram_limit,mp4_fps,mp4_anno,SD_F_Act,dspeed,IRF,camera,
              mode1,speed1,gain1,brightness1,contrast1,awb1,int(red1*10),int(blue1*10),meter1,ev1,denoise1,quality1,sharpness1,saturation1,
              fps1,AF_f_mode1,AF_focus1,AF_f_mode,AF_focus,IRF_on,on_hour,of_hour,on_mins,of_mins,ir_on_hour,ir_of_hour,ir_on_mins,ir_of_mins,
              camera_sw,AF_f_spot,AF_f_spot1,ir_on_hour1,ir_of_hour1,ir_on_mins1,ir_of_mins1,IRF1,IRF_on1]
    with open(config_file, 'w') as f:
        for item in defaults:
            f.write("%s\n" % item)

# read config file
config = []
with open(config_file, "r") as file:
   line = file.readline()
   while line:
      config.append(line.strip())
      line = file.readline()
config = list(map(int,config))

h_crop      = config[0]
threshold   = config[1]
fps         = config[2]
mode        = config[3]
speed       = config[4]
gain        = config[5]
brightness  = config[6]
contrast    = config[7]
SD_limit    = config[8]
preview     = config[9]
awb         = config[10]
detection   = config[11]
red         = config[12]/10
blue        = config[13]/10
interval    = config[14]
v_crop      = config[15]
v_length    = config[16]
ev          = config[17]
meter       = config[18]
ES          = config[19]
a           = config[20]
b           = config[21]
sharpness   = config[22]
saturation  = config[23]
denoise     = config[24]
fan_low     = config[25]
fan_high    = config[26]
det_high    = config[27]
quality     = config[28]
check_time  = config[29]
sd_hour     = config[30]
vformat     = config[31]
threshold2  = config[32]
col_filter  = config[33]
nr          = config[34]
pre_frames  = config[35]
auto_time   = config[36]
ram_limit   = config[37]
mp4_fps     = config[38]
mp4_anno    = config[39]
SD_F_Act    = config[40]
dspeed      = config[41]
IRF         = config[42]
#camera      = config[43]
mode1       = config[44]
speed1      = config[45]
gain1       = config[46]
brightness1 = config[47]
contrast1   = config[48]
awb1        = config[49]
red1        = config[50]/10
blue1       = config[51]/10
meter1      = config[52]
ev1         = config[53]
denoise1    = config[54]
quality1    = config[55]
sharpness1  = config[56]
saturation1 = config[57]
fps1        = config[58]
AF_f_mode1  = config[59]
AF_focus1   = config[60]
AF_f_mode   = config[61]
AF_focus    = config[62]
IRF_on      = config[63]
on_hour     = config[64]
of_hour     = config[65]
on_mins     = config[66]
of_mins     = config[67]
ir_on_hour  = config[68]
ir_of_hour  = config[69] 
ir_on_mins  = config[70]
ir_of_mins  = config[71]
camera_sw   = config[72]
AF_f_spot   = config[73]
AF_f_spot1  = config[74]
ir_on_hour1 = config[75]
ir_of_hour1 = config[76]
ir_on_mins1 = config[77]
ir_of_mins1 = config[78]
IRF1        = config[79]
IRF_on1     = config[80]

if camera_sw == 3:
    camera = 1
    old_camera = camera
elif camera_sw == 2:
    camera = 0
    old_camera = camera

on_time     = (on_hour * 60) + on_mins
of_time     = (of_hour * 60) + of_mins
ir_on_time  = (ir_on_hour * 60) + ir_on_mins
ir_of_time  = (ir_of_hour * 60) + ir_of_mins
ir_on_time1 = (ir_on_hour1 * 60) + ir_on_mins1
ir_of_time1 = (ir_of_hour1 * 60) + ir_of_mins1



def suntimes():
    global sr_seconds,ss_seconds,now_seconds,ir_on_hour,ir_on_mins,ir_of_hour,ir_of_mins,menu,synced,Pi_Cam
    global on_hour,on_mins,of_hour,of_mins,camera_sw,on_time,of_time,IRF,IRF1,ir_on_time,ir_of_time,ir_on_time1,ir_of_time1
    global ir_on_hour1,ir_on_mins1,ir_of_hour1,ir_of_mins1
    sun = ephem.Sun()
    r1 = str(somewhere.next_rising(sun))
    sunrise = datetime.datetime.strptime(str(r1), '%Y/%m/%d %H:%M:%S')
    sr_timedelta = sunrise - datetime.datetime(2020, 1, 1)
    sr_seconds = sr_timedelta.total_seconds() + (UTC_offset * 3600)
    s1 = str(somewhere.next_setting(sun))
    sunset = datetime.datetime.strptime(str(s1), '%Y/%m/%d %H:%M:%S')
    ss_timedelta = sunset - datetime.datetime(2020, 1, 1)
    ss_seconds = ss_timedelta.total_seconds() + (UTC_offset * 3600)
    time1 = r1.split(" ")
    time1a = time1[1].split(":")
    time2 = s1.split(" ")
    time2a = time2[1].split(":")
    now = datetime.datetime.now()
    a_timedelta = now - datetime.datetime(2020, 1, 1)
    now_seconds = a_timedelta.total_seconds()
    if IRF == 0:
        ir_on_hour = int(time1a[0]) + UTC_offset
        if ir_on_hour > 23:
            ir_on_hour -= 24
        if ir_on_hour < 0:
            ir_on_hour += 24
        ir_on_mins = int(time1a[1])
        ir_of_hour = int(time2a[0]) + UTC_offset
        if ir_of_hour > 23:
            ir_of_hour -= 24
        if ir_of_hour < 0:
            ir_of_hour += 24
        ir_of_mins  = int(time2a[1])
        ir_on_time  = (ir_on_hour * 60) + ir_on_mins
        ir_of_time  = (ir_of_hour * 60) + ir_of_mins
        if menu == 2:
          if synced == 1:
            if ir_on_mins > 9:
                text(0,1,2,1,1,str(ir_on_hour) + ":" + str(ir_on_mins),14,7)
            else:
                text(0,1,2,1,1,str(ir_on_hour) + ":0" + str(ir_on_mins),14,7)
          else:
            if ir_on_mins > 9:
                text(0,1,0,1,1,str(ir_on_hour) + ":" + str(ir_on_mins),14,7)
            else:
                text(0,1,0,1,1,str(ir_on_hour) + ":0" + str(ir_on_mins),14,7)
          if synced == 1 :
            if ir_of_mins > 9:
                text(0,2,2,1,1,str(ir_of_hour) + ":" + str(ir_of_mins),14,7)
            else:
                text(0,2,2,1,1,str(ir_of_hour) + ":0" + str(ir_of_mins),14,7)
          else:
            if ir_of_mins > 9:
                text(0,2,0,1,1,str(ir_of_hour) + ":" + str(ir_of_mins),14,7)
            else:
                text(0,2,0,1,1,str(ir_of_hour) + ":0" + str(ir_of_mins),14,7)

    if IRF1 == 0:
        ir_on_hour1 = int(time1a[0]) + UTC_offset
        if ir_on_hour1 > 23:
            ir_on_hour1 -= 24
        if ir_on_hour1 < 0:
            ir_on_hour1 += 24
        ir_on_mins1 = int(time1a[1])
        ir_of_hour1 = int(time2a[0]) + UTC_offset
        if ir_of_hour1 > 23:
            ir_of_hour1 -= 24
        if ir_of_hour1 < 0:
            ir_of_hour1 += 24
        ir_of_mins1  = int(time2a[1])
        ir_on_time1 = (ir_on_hour1 * 60) + ir_on_mins1
        ir_of_time1 = (ir_of_hour1 * 60) + ir_of_mins1
        if menu == 7:
          if synced == 1:
            if ir_on_mins1 > 9:
                text(0,1,2,1,1,str(ir_on_hour1) + ":" + str(ir_on_mins1),14,7)
            else:
                text(0,1,2,1,1,str(ir_on_hour1) + ":0" + str(ir_on_mins1),14,7)
          else:
            if ir_on_mins1 > 9:
                text(0,1,0,1,1,str(ir_on_hour1) + ":" + str(ir_on_mins1),14,7)
            else:
                text(0,1,0,1,1,str(ir_on_hour1) + ":0" + str(ir_on_mins1),14,7)
          if synced == 1 :
            if ir_of_mins1 > 9:
                text(0,2,2,1,1,str(ir_of_hour1) + ":" + str(ir_of_mins1),14,7)
            else:
                text(0,2,2,1,1,str(ir_of_hour1) + ":0" + str(ir_of_mins1),14,7)
          else:
            if ir_of_mins1 > 9:
                text(0,2,0,1,1,str(ir_of_hour1) + ":" + str(ir_of_mins1),14,7)
            else:
                text(0,2,0,1,1,str(ir_of_hour1) + ":0" + str(ir_of_mins1),14,7)
                
    if camera_sw == 0:
        on_hour = int(time1a[0]) + UTC_offset
        if on_hour > 23:
            on_hour -= 24
        if on_hour < 0:
            on_hour += 24
        on_mins = int(time1a[1])
        of_hour = int(time2a[0]) + UTC_offset
        if of_hour > 23:
            of_hour -= 24
        if of_hour < 0:
            of_hour += 24
        of_mins = int(time2a[1])
        on_time = (on_hour * 60) + on_mins
        of_time = (of_hour * 60) + of_mins
        if menu == 3 and cam2 != "1":
            text(0,7,1,0,1,"SW 2>1 time",14,7)
            if synced == 1 and cam2 != "1":
                if on_mins > 9:
                    text(0,7,2,1,1,str(on_hour) + ":" + str(on_mins),14,7)
                else:
                    text(0,7,2,1,1,str(on_hour) + ":0" + str(on_mins),14,7)
            else:
                if on_mins > 9:
                    text(0,7,0,1,1,str(on_hour) + ":" + str(on_mins),14,7)
                else:
                    text(0,7,0,1,1,str(on_hour) + ":0" + str(on_mins),14,7)
            text(0,8,1,0,1,"SW 1>2 time",14,7)
            if synced == 1 and cam2 != "1":
                if of_mins > 9:
                    text(0,8,2,1,1,str(of_hour) + ":" + str(of_mins),14,7)
                else:
                    text(0,8,2,1,1,str(of_hour) + ":0" + str(of_mins),14,7)
            else:
                if of_mins > 9:
                    text(0,8,0,1,1,str(of_hour) + ":" + str(of_mins),14,7)
                else:
                    text(0,8,0,1,1,str(of_hour) + ":0" + str(of_mins),14,7)

bw = int(scr_width/8)
cwidth  = scr_width - bw
cheight = scr_height
old_vf  = vformat
focus = 0
shutter = shutters[speed]
if shutter < 0:
    shutter = abs(1/shutter)
sspeed = int(shutter * 1000000)
if (shutter * 1000000) - int(shutter * 1000000) > 0.5:
    sspeed +=1
if use_gpio == 1:
    if IRF == 0:
        led_sw_ir.off()
        led_sw_ir1.off()
    else:
        led_sw_ir.on()
        led_sw_ir1.on()

# timelapse interval timer (set Low Threshold = 0 and set interval timer)
if threshold == 0:
    timer10 = time.monotonic()
    if v_length > interval * 1000:
        v_length = (interval - 1) * 1000

def Camera_Version():
  global lores_width,lores_height,vid_width,vid_height,old_vf,bw,Pi_Cam,cam1,cam2,camera,camids,max_gain,max_vf,max_vfs,swidth,sheight
  global a,b,h_crop,v_crop,h_crop,v_crop,pre_width,pre_height,vformat,pre_height,cwidth,pre_width,scr_width,scr_height,scientif
  if os.path.exists('rpicams.txt'):
     os.rename('rpicams.txt', 'oldrpicams.txt')
  if lver != "bookwo" and lver != "trixie":
     os.system("libcamera-vid --list-cameras >> rpicams.txt")
  else:
     os.system("rpicam-vid --list-cameras >> rpicams.txt")
  time.sleep(0.5)
  # read rpicams.txt file
  camstxt = []
  with open("rpicams.txt", "r") as file:
    line = file.readline()
    while line:
        camstxt.append(line.strip())
        line = file.readline()
  cam1     = "0"
  cam2     = "1"
  vwidths  = []
  vheights = []
  cwidth   = scr_width - bw
  cheight  = scr_height
  for x in range(0,len(camstxt)):
    # Determine both cameras 
    if camstxt[x][0:4] == "0 : ":
        cam1 = camstxt[x][4:10]
    if camstxt[x][0:4] == "1 : ":
        cam2 = camstxt[x][4:10]
    if cam1 != "0" and cam2 == "1" and camera == 0:
        forms = camstxt[x].split(" ")
        for q in range(0,len(forms)):
           if "x" in forms[q] and "/" not in forms[q] and "m" not in forms[q] and "[" not in forms[q]:
              qwidth,qheight = forms[q].split("x")
              vwidths.append(int(qwidth))
              vheights.append(int(qheight))
    elif cam1 != "0" and cam2 != "1" and camera == 1:
        forms = camstxt[x].split(" ")
        for q in range(0,len(forms)):
           if "x" in forms[q] and "/" not in forms[q] and "m" not in forms[q] and "[" not in forms[q]:
              qwidth,qheight = forms[q].split("x")
              vwidths.append(int(qwidth))
              vheights.append(int(qheight))
              
  swidths[0]  = vwidths[-1]
  sheights[0] = vheights[-1]
  
  Pi_Cam = -1
  for x in range(0,len(camids)):
     if camera == 0:
        if cam1 == camids[x]:
            Pi_Cam = x
     elif camera == 1:
        if cam2 == camids[x]:
            Pi_Cam = x
  max_gain = max_gains[Pi_Cam]
  if a > pre_width - v_crop:
      a = int(pre_width/2)
  if b > pre_height - h_crop:
      b = int(pre_height/2)
  swidth  = swidths[Pi_Cam]
  sheight = sheights[Pi_Cam]
  # set video size
  if swidth < 1920:
      vid_width  = swidth
      vid_height = sheight
      # set lores size
      lores_width  = swidth
      lores_height = sheight
  else:
      vid_width  = 1920
      vid_height = 1080
      # set lores size
      lores_width  = 1280
      lores_height = 960
  if Pi_Cam != -1:
      print("Camera:",cameras[Pi_Cam])
  elif cam1 != "0" and camera == 0:
      Pi_Cam      = 0
      cameras[0]  = cam1
      camids[0]   = cam1[0:6]
      print("Camera:",cameras[Pi_Cam])
      max_gain    = max_gains[Pi_Cam]
      mag         = int(max_gain/4)
  elif cam2 != "1" and camera == 1:
      Pi_Cam      = 0
      cameras[0]  = cam2
      camids[0]   = cam2[0:6]
      print("Camera:",cameras[Pi_Cam])
      max_gain    = max_gains[Pi_Cam]
      mag         = int(max_gain/4)
  else:
      print("No Camera Found")
      pygame.display.quit()
      sys.exit()
            
Camera_Version()
suntimes()

print(Pi_Cam,cam1,cam2)

# mp4_annotation parameters
colour = (255, 255, 255)
origin = (int(vid_width/3), int(vid_height - 50))
font   = cv2.FONT_HERSHEY_SIMPLEX
scale  = 1
thickness = 2

#set variables
bh = int(scr_height/12)
font_size = int(min(bh, bw)/3)
start_up = time.monotonic()
col_timer = 0
pygame.init()
fxx = 0
fxy = 0
fxz = 1
USB_storage = 100

# find username
h_user = "/home/" + os.getlogin( )
m_user = "/media/" + os.getlogin( )

# generate a mask window
if not os.path.exists(h_user + '/CMask.bmp'):
   pygame.init()
   bredColor =   pygame.Color(100,100,100)
   mwidth = 200
   mheight = 200
   windowSurfaceObj = pygame.display.set_mode((mwidth, mheight), pygame.NOFRAME, 24)
   pygame.draw.rect(windowSurfaceObj,bredColor,Rect(0,0,mwidth,mheight))
   pygame.display.update()
   pygame.image.save(windowSurfaceObj,h_user + '/CMask.bmp')
   pygame.display.quit()

def MaskChange(): # used for masked window resizing
   global v_crop,h_crop
   mask = cv2.imread(h_user + '/CMask.bmp')
   mask = cv2.resize(mask, dsize=(v_crop * 2, h_crop * 2), interpolation=cv2.INTER_CUBIC)
   mask = cv2.cvtColor(mask,cv2.COLOR_RGB2GRAY)
   mask = mask.astype(np.int16)
   mask[mask >= 1] = 1
   change = 1
   return (mask,change)

mask,change = MaskChange()

if os.path.exists('mylist.txt'):
    os.remove('mylist.txt')

# determine /dev/v4l-subdevX for Pi v3 and Arducam 16/64MP cameras
foc_sub3 = -1
foc_sub5 = -1
for x in range(0,10):
    if os.path.exists("ctrls.txt"):
        os.remove("ctrls.txt")
    os.system("v4l2-ctl -d /dev/v4l-subdev" + str(x) + " --list-ctrls >> ctrls.txt")
    time.sleep(0.25)
    ctrlstxt = []
    with open("ctrls.txt", "r") as file:
        line = file.readline()
        while line:
            ctrlstxt.append(line.strip())
            line = file.readline()
    for j in range(0,len(ctrlstxt)):
        if ctrlstxt[j][0:51] == "focus_absolute 0x009a090a (int)    : min=0 max=4095":
            foc_sub5 = x
        if ctrlstxt[j][0:51] == "focus_absolute 0x009a090a (int)    : min=0 max=1023":
            foc_sub3 = x

def start_buffer():
    global lores_width,lores_height,vid_width,vid_height,picam2,encoder,encoding,ltime,Pi_Cam
    # start circular buffer
    lsize = (lores_width,lores_height)
    picam2 = Picamera2(camera)
    video_config = picam2.create_video_configuration(main={"size": (vid_width, vid_height), "format": "RGB888"},
                                             lores={"size": lsize, "format": "YUV420"},
                                             display="lores")
    picam2.configure(video_config)
    encoder = H264Encoder(4000000, repeat=True)
    encoder.output = CircularOutput(buffersize = pre_frames * fps)
    picam2.pre_callback = apply_timestamp
    picam2.start()
    picam2.start_encoder(encoder)
    encoding = False
    ltime = 0

start_buffer()

def set_parameters():
    global mode,sspeed,picam2,awb,AF_f_mode,brightness,contrast,gain,ev,meter,saturation,sharpness,denoise,fps,use_gpio,IRF,IRF_on,led_sw_ir,led_sw_ir1
    global a,b,h_crop,v_crop,swidth,sheight,fxx,fxy,fxz,fxa,AF_f_spot
    # setup camera parameters
    if mode == 0:
        picam2.set_controls({"AeEnable": False,"ExposureTime": sspeed})
    else:
        if mode == 1:
            picam2.set_controls({"AeEnable": True,"AeExposureMode": controls.AeExposureModeEnum.Normal})
        elif mode == 2:
            picam2.set_controls({"AeEnable": True,"AeExposureMode": controls.AeExposureModeEnum.Short})
        elif mode == 3:
            picam2.set_controls({"AeEnable": True,"AeExposureMode": controls.AeExposureModeEnum.Long})
    time.sleep(1)
    if awb == 0 and Pi_Cam != 11:
        picam2.set_controls({"AwbEnable": True,"AwbMode": controls.AwbModeEnum.Auto})
    elif awb == 1 and Pi_Cam != 11:
        picam2.set_controls({"AwbEnable": True,"AwbMode": controls.AwbModeEnum.Tungsten})
    elif awb == 2 and Pi_Cam != 11:
        picam2.set_controls({"AwbEnable": True,"AwbMode": controls.AwbModeEnum.Fluorescent})
    elif awb == 3 and Pi_Cam != 11:
        picam2.set_controls({"AwbEnable": True,"AwbMode": controls.AwbModeEnum.Indoor})
    elif awb == 4 and Pi_Cam != 11:
        picam2.set_controls({"AwbEnable": True,"AwbMode": controls.AwbModeEnum.Daylight})
    elif awb == 5 and Pi_Cam != 11:
        picam2.set_controls({"AwbEnable": True,"AwbMode": controls.AwbModeEnum.Cloudy})
    elif awb == 6 and Pi_Cam != 11:
        picam2.set_controls({"AwbEnable": True,"AwbMode": controls.AwbModeEnum.Custom})
        cg = (red,blue)
        picam2.set_controls({"AwbEnable": False,"ColourGains": cg})
    time.sleep(1)
    if (Pi_Cam == 3 or Pi_Cam == 8 or Pi_Cam == 6):
        if AF_f_mode == 0:
            picam2.set_controls({"AfMode": controls.AfModeEnum.Manual, "AfMetering" : controls.AfMeteringEnum.Windows,  "AfWindows" : [(int(vid_width* .33),int(vid_height*.33),int(vid_width * .66),int(vid_height*.66))]})
            picam2.set_controls({"LensPosition": AF_focus})
        elif AF_f_mode == 1:
            if AF_f_spot == 0:
                picam2.set_controls({"AfMode": controls.AfModeEnum.Auto, "AfMetering" : controls.AfMeteringEnum.Windows,  "AfWindows" : [(int(vid_width*.33),int(vid_height*.33),int(vid_width * .66),int(vid_height*.66))]})
                picam2.set_controls({"AfTrigger": controls.AfTriggerEnum.Start})
            else:
                fxx = int((a - h_crop) * (swidth/pre_width))
                fxy = int((b - v_crop) * (sheight/pre_height))
                fxz = int((h_crop * 2) * (swidth/pre_width))
                fxa = int((v_crop * 2) * (sheight/pre_height))
                picam2.set_controls({"AfMode" : controls.AfModeEnum.Auto,"AfMetering" : controls.AfMeteringEnum.Windows,"AfWindows" : [ (fxx,fxy,fxz,fxa) ] } )
                picam2.set_controls({"AfTrigger": controls.AfTriggerEnum.Start})

        elif AF_f_mode == 2:
            if AF_f_spot == 0:
                picam2.set_controls( {"AfMode" : controls.AfModeEnum.Continuous, "AfMetering" : controls.AfMeteringEnum.Windows,  "AfWindows" : [(int(vid_width*.33),int(vid_height*.33),int(vid_width * .66),int(vid_height*.66))] } )
                picam2.set_controls({"AfTrigger": controls.AfTriggerEnum.Start})
            else:
                fxx = int((a - h_crop) * (swidth/pre_width))
                fxy = int((b - v_crop) * (sheight/pre_height))
                fxz = int((h_crop * 2) * (swidth/pre_width))
                fxa = int((v_crop * 2) * (sheight/pre_height))
                picam2.set_controls({"AfMode" : controls.AfModeEnum.Continuous,"AfMetering" : controls.AfMeteringEnum.Windows,"AfWindows" : [ (fxx,fxy,fxz,fxa) ] } )
                picam2.set_controls({"AfTrigger": controls.AfTriggerEnum.Start})
    picam2.set_controls({"Brightness": brightness/10})
    picam2.set_controls({"Contrast": contrast/10})
    picam2.set_controls({"ExposureValue": ev/10})
    picam2.set_controls({"AnalogueGain": gain})
    if meter == 0:
        picam2.set_controls({"AeMeteringMode": controls.AeMeteringModeEnum.CentreWeighted})
    elif meter == 1:
        picam2.set_controls({"AeMeteringMode": controls.AeMeteringModeEnum.Spot})
    elif meter == 2:
        picam2.set_controls({"AeMeteringMode": controls.AeMeteringModeEnum.Matrix})
    if Pi_Cam != 11:
        picam2.set_controls({"Saturation": saturation/10})
    picam2.set_controls({"Sharpness": sharpness})
    if denoise == 0:
        picam2.set_controls({"NoiseReductionMode": controls.draft.NoiseReductionModeEnum.Off})
    elif denoise == 1:
        picam2.set_controls({"NoiseReductionMode": controls.draft.NoiseReductionModeEnum.Fast})
    elif denoise == 2:
        picam2.set_controls({"NoiseReductionMode": controls.draft.NoiseReductionModeEnum.HighQuality})
    picam2.set_controls({"FrameRate": fps})
    if use_gpio == 1:
        if IRF_on == 0 and IRF == 2:
            led_sw_ir.off()
            led_sw_ir1.off()
        elif IRF_on == 1 and IRF == 3:
            led_sw_ir1.on()
            led_sw_ir.on()

def set_parameters1():
    global mode1,sspeed1,picam2,awb1,AF_f_mode1,AF_focus1,AF_focus1,brightness1,contrast1,gain1,ev1,meter1,saturation1,sharpness1,denoise1,fps1,use_gpio,IRF_on,IRF
    global led_sw_ir,led_sw_ir1,a,b,h_crop,v_crop,swidth,sheight,fxx,fxy,fxz,fxa,AF_f_spot1
    # setup camera1 parameters
    time.sleep(1)
    if mode1 == 0:
        picam2.set_controls({"AeEnable": False,"ExposureTime": sspeed1})
    else:
        if mode1 == 1:
            picam2.set_controls({"AeEnable": True,"AeExposureMode": controls.AeExposureModeEnum.Normal})
        elif mode1 == 2:
            picam2.set_controls({"AeEnable": True,"AeExposureMode": controls.AeExposureModeEnum.Short})
        elif mode1 == 3:
            picam2.set_controls({"AeEnable": True,"AeExposureMode": controls.AeExposureModeEnum.Long})
    if awb1 == 0 and Pi_Cam != 11:
        picam2.set_controls({"AwbEnable": True,"AwbMode": controls.AwbModeEnum.Auto})
    elif awb1 == 1 and Pi_Cam != 11:
        picam2.set_controls({"AwbEnable": True,"AwbMode": controls.AwbModeEnum.Tungsten})
    elif awb1 == 2 and Pi_Cam != 11:
        picam2.set_controls({"AwbEnable": True,"AwbMode": controls.AwbModeEnum.Fluorescent})
    elif awb1 == 3 and Pi_Cam != 11:
        picam2.set_controls({"AwbEnable": True,"AwbMode": controls.AwbModeEnum.Indoor})
    elif awb1 == 4 and Pi_Cam != 11:
        picam2.set_controls({"AwbEnable": True,"AwbMode": controls.AwbModeEnum.Daylight})
    elif awb1 == 5 and Pi_Cam != 11:
        picam2.set_controls({"AwbEnable": True,"AwbMode": controls.AwbModeEnum.Cloudy})
    elif awb1 == 6 and Pi_Cam != 11:
        picam2.set_controls({"AwbEnable": True,"AwbMode": controls.AwbModeEnum.Custom})
        cg = (red1,blue1)
        picam2.set_controls({"AwbEnable": False,"ColourGains": cg})
    time.sleep(1)
    if (Pi_Cam == 3 or Pi_Cam == 8 or Pi_Cam == 6):
        if AF_f_mode1 == 0:
            picam2.set_controls({"AfMode": controls.AfModeEnum.Manual, "AfMetering" : controls.AfMeteringEnum.Windows,  "AfWindows" : [(int(vid_width* .33),int(vid_height*.33),int(vid_width * .66),int(vid_height*.66))]})
            picam2.set_controls({"LensPosition": AF_focus1})
        elif AF_f_mode1 == 1:
            if AF_f_spot1 == 0:
                picam2.set_controls({"AfMode": controls.AfModeEnum.Auto, "AfMetering" : controls.AfMeteringEnum.Windows,  "AfWindows" : [(int(vid_width*.33),int(vid_height*.33),int(vid_width * .66),int(vid_height*.66))]})
                picam2.set_controls({"AfTrigger": controls.AfTriggerEnum.Start})
            else:
                fxx = int((a - h_crop) * (swidth/pre_width))
                fxy = int((b - v_crop) * (sheight/pre_height))
                fxz = int((h_crop * 2) * (swidth/pre_width))
                fxa = int((v_crop * 2) * (sheight/pre_height))
                picam2.set_controls({"AfMode" : controls.AfModeEnum.Auto,"AfMetering" : controls.AfMeteringEnum.Windows,"AfWindows" : [ (fxx,fxy,fxz,fxa) ] } )
                picam2.set_controls({"AfTrigger": controls.AfTriggerEnum.Start})
        elif AF_f_mode1 == 2:
            if AF_f_spot1 == 0:
                picam2.set_controls( {"AfMode" : controls.AfModeEnum.Continuous, "AfMetering" : controls.AfMeteringEnum.Windows,  "AfWindows" : [(int(vid_width*.33),int(vid_height*.33),int(vid_width * .66),int(vid_height*.66))] } )
                picam2.set_controls({"AfTrigger": controls.AfTriggerEnum.Start})
            else:
                fxx = int((a - h_crop) * (swidth/pre_width))
                fxy = int((b - v_crop) * (sheight/pre_height))
                fxz = int((h_crop * 2) * (swidth/pre_width))
                fxa = int((v_crop * 2) * (sheight/pre_height))
                picam2.set_controls({"AfMode" : controls.AfModeEnum.Continuous,"AfMetering" : controls.AfMeteringEnum.Windows,"AfWindows" : [ (fxx,fxy,fxz,fxa) ] } )
                picam2.set_controls({"AfTrigger": controls.AfTriggerEnum.Start})

    picam2.set_controls({"Brightness": brightness1/10})
    picam2.set_controls({"Contrast": contrast1/10})
    picam2.set_controls({"ExposureValue": ev1/10})
    picam2.set_controls({"AnalogueGain": gain1})
    if meter1 == 0:
        picam2.set_controls({"AeMeteringMode": controls.AeMeteringModeEnum.CentreWeighted})
    elif meter1 == 1:
        picam2.set_controls({"AeMeteringMode": controls.AeMeteringModeEnum.Spot})
    elif meter1 == 2:
        picam2.set_controls({"AeMeteringMode": controls.AeMeteringModeEnum.Matrix})
    if Pi_Cam != 11:
        picam2.set_controls({"Saturation": saturation1/10})
    picam2.set_controls({"Sharpness": sharpness1})
    if denoise1 == 0:
        picam2.set_controls({"NoiseReductionMode": controls.draft.NoiseReductionModeEnum.Off})
    elif denoise1 == 1:
        picam2.set_controls({"NoiseReductionMode": controls.draft.NoiseReductionModeEnum.Fast})
    elif denoise1 == 2:
        picam2.set_controls({"NoiseReductionMode": controls.draft.NoiseReductionModeEnum.HighQuality})
    picam2.set_controls({"FrameRate": fps1})
    if use_gpio == 1:
        if IRF_on == 0 and IRF == 2:
            led_sw_ir.off()
            led_sw_ir1.off()
        elif IRF_on == 1 and IRF == 3:
            led_sw_ir1.on()
            led_sw_ir.on()

if camera == 0:
    set_parameters()
else:
    set_parameters1()
    
# check for usb_stick
USB_Files  = []
USB_Files  = (os.listdir(m_user + "/"))
print(USB_Files)
if len(USB_Files) > 0:
    usedusb = os.statvfs(m_user + "/" + USB_Files[0] + "/")
    USB_storage = ((1 - (usedusb.f_bavail / usedusb.f_blocks)) * 100)
    if not os.path.exists(m_user + "/'" + USB_Files[0] + "'/Videos/") :
        os.system('mkdir ' + m_user + "/'" + USB_Files[0] + "'/Videos/")
    if not os.path.exists(m_user + "/'" + USB_Files[0] + "'/Pictures/") :
        os.system('mkdir ' + m_user + "/'" + USB_Files[0] + "'/Pictures/")
   
# read list of existing Video Files
Videos = []
frames = 0
ram_frames = 0

# SD card
Videos = glob.glob(h_user + '/Videos/*.mp4')
Videos.sort()
Jpegs = glob.glob(h_user + '/Videos/*.jpg')
Jpegs.sort()
frames = len(Videos)
vf = str(ram_frames) + " - " + str(frames)


old_cap = Capture
restart = 0
menu    = -1
zoom    = 0

# get RAM free space
st = os.statvfs("/run/shm/")
sfreeram = (st.f_bavail * st.f_frsize)/1100000

# check if clock synchronised
if os.path.exists("/run/shm/sync.txt"):
    os.rename('/run/shm/sync.txt','/run/shm/oldsync.txt')
os.system("timedatectl >> /run/shm/sync.txt")
# read sync.txt file
try:
    sync = []
    with open("/run/shm/sync.txt", "r") as file:
        line = file.readline()
        while line:
            sync.append(line.strip())
            line = file.readline()
    if sync[4] == "System clock synchronized: yes":
        synced = 1
    else:
        synced = 0
    if trace > 0:
        print("SYNC: ", synced)
except:
    pass

# setup pygame window
if noframe == 0:
   windowSurfaceObj = pygame.display.set_mode((scr_width,scr_height), 0, 24)
else:
   windowSurfaceObj = pygame.display.set_mode((scr_width,scr_height), pygame.NOFRAME, 24)
   
pygame.display.set_caption('Action ' + cameras[Pi_Cam])

global greyColor, redColor, greenColor, blueColor, dgryColor, lgryColor, blackColor, whiteColor, purpleColor, yellowColor
bredColor =   pygame.Color(255,   0,   0)
lgryColor =   pygame.Color(192, 192, 192)
blackColor =  pygame.Color(  0,   0,   0)
whiteColor =  pygame.Color(250, 250, 250)
greyColor =   pygame.Color(128, 128, 128)
dgryColor =   pygame.Color( 64,  64,  64)
greenColor =  pygame.Color(  0, 255,   0)
purpleColor = pygame.Color(255,   0, 255)
yellowColor = pygame.Color(255, 255,   0)
blueColor =   pygame.Color(  0,   0, 255)
redColor =    pygame.Color(200,   0,   0)

def button(col,row, bColor):
    colors = [greyColor, dgryColor, whiteColor, redColor, greenColor,yellowColor]
    Color = colors[bColor]
    bx = scr_width - ((1-col) * bw) + 2
    by = row * bh
    pygame.draw.rect(windowSurfaceObj,Color,Rect(bx+1,by,bw-2,bh))
    pygame.draw.line(windowSurfaceObj,whiteColor,(bx,by),(bx,by+bh-1),2)
    pygame.draw.line(windowSurfaceObj,whiteColor,(bx,by),(bx+bw-1,by),1)
    pygame.draw.line(windowSurfaceObj,dgryColor,(bx,by+bh-1),(bx+bw-1,by+bh-1),1)
    pygame.draw.line(windowSurfaceObj,dgryColor,(bx+bw-2,by),(bx+bw-2,by+bh),2)
    pygame.display.update(bx, by, bw-1, bh)
    return

def text(col,row,fColor,top,upd,msg,fsize,bcolor):
   global font_size, fontObj, bh, bw, cwidth
   if os.path.exists ('/usr/share/fonts/truetype/freefont/FreeSerif.ttf'): 
       fontObj = pygame.font.Font('/usr/share/fonts/truetype/freefont/FreeSerif.ttf', int(fsize))
   else:
       fontObj = pygame.font.Font(None, int(fsize))
   colors =  [dgryColor, greenColor, yellowColor, redColor, greenColor, blueColor, whiteColor, greyColor, blackColor, purpleColor]
   Color  =  colors[fColor]
   bColor =  colors[bcolor]
   bx = scr_width - ((1-col) * bw)
   by = row * bh
   msgSurfaceObj = fontObj.render(msg, False, Color)
   msgRectobj = msgSurfaceObj.get_rect()
   if top == 0:
       pygame.draw.rect(windowSurfaceObj,bColor,Rect(bx+4,by+3,bw-2,int(bh/2)-4))
       msgRectobj.topleft = (bx + 7, by + 3)
   elif msg == "START - END" or msg == "<<   <    >   >>":
       pygame.draw.rect(windowSurfaceObj,bColor,Rect(bx+int(bw/4),by+int(bh/2)+1,int(bw/1.5),int(bh/2)-4))
       msgRectobj.topleft = (bx+7, by + int(bh/2))
   else:
       pygame.draw.rect(windowSurfaceObj,bColor,Rect(bx+int(bw/4),by+int(bh/2)+1,int(bw/1.5),int(bh/2)-4))
       msgRectobj.topleft = (bx+int(bw/4), by + int(bh/2))
   windowSurfaceObj.blit(msgSurfaceObj, msgRectobj)
   if upd == 1:
      pygame.display.update(bx, by, bw, bh)

def main_menu():
    global ram_frames,frames,menu,sd_hour,pf,vf,synced,Capture,show,zoom,preview,scr_height,cwidth,old_cap,Jpegs
    menu = -1
    show = 0
    preview = 0
    Capture = old_cap
    zoom = 0
    for d in range(0,11):
         button(0,d,0)
    button(0,1,3)
    Videos = glob.glob(h_user + '/Videos/2???????????.mp4')
    frames = len(Videos)
    Jpegs = glob.glob(h_user + '/Videos/2*.jpg')
    for x in range(0,len(Jpegs)):
        if not os.path.exists(Jpegs[x][:-4] + ".mp4"):
            os.remove(Jpegs[x])
    Rideos = glob.glob('/run/shm/2???????????.mp4')
    for x in range(0,len(Rideos)):
        Videos.append(Rideos[x])
    ram_frames = len(Rideos)
    Videos = glob.glob(h_user + '/Videos/2???????????.mp4')
    Videos.sort()
    frames = len(Videos)
    vf = str(ram_frames) + " - " + str(frames)
    if Capture == 0 and menu == -1:
        button(0,0,0)
        text(0,0,0,0,1,"CAPTURE",16,7)
        vf = str(ram_frames) + " - " + str(frames)
        text(0,0,3,1,1,vf,14,7)
    elif menu == -1:
        button(0,0,4)
        text(0,0,6,0,1,"CAPTURE",16,4)
        vf = str(ram_frames) + " - " + str(frames)
        text(0,0,3,1,1,vf,14,4)
    text(0,1,6,0,1,"RECORD",16,3)
    text(0,2,1,0,1,"DETECTION",14,7)
    text(0,2,1,1,1,"Settings",14,7)
    if cam2 != "1":
        text(0,3,1,0,1,"CAMERA 1",14,7)
    else:
        text(0,3,1,0,1,"CAMERA ",14,7)
    text(0,3,1,1,1,"Settings 1",14,7)
    if cam2 != "1":
        text(0,4,1,0,1,"CAMERA 1",14,7)
    else:
        text(0,4,1,0,1,"CAMERA ",14,7)
    text(0,4,1,1,1,"Settings 2",14,7)
    if Pi == 5 and cam2 != "1":
        text(0,5,1,0,1,"VIDEO & SW",14,7)
    else:
        text(0,5,1,0,1,"VIDEO     ",14,7)
    text(0,5,1,1,1,"Settings",14,7)
    text(0,7,1,0,1,"OTHER",14,7)
    text(0,7,1,1,1,"Settings ",14,7)
    if ((ram_frames > 0 or frames > 0) and menu == -1):
        text(0,6,1,0,1,"SHOW or",13,7)
        text(0,6,1,1,1,"DELETE",13,7)
    else:
        text(0,6,0,0,1,"SHOW or",13,7)
        text(0,6,0,1,1,"DELETE",13,7)
    if Pi == 5 and cam2 != "1":
        text(0,8,1,0,1,"CAMERA 2",14,7)
        text(0,8,1,1,1,"Settings 1",14,7)
        text(0,9,1,0,1,"CAMERA 2",14,7)
        text(0,9,1,1,1,"Settings 2",14,7)
    text(0,10,3,0,1,"EXIT",16,7)
    st = os.statvfs("/run/shm/")
    freeram = (st.f_bavail * st.f_frsize)/1100000
    free = (os.statvfs('/'))
    SD_storage = ((1 - (free.f_bavail / free.f_blocks)) * 100)
    ss = str(int(freeram)) + "MB - " + str(int(SD_storage)) + "%"
    if record == 0:
        text(0,1,6,1,1,ss,12,3)
    else:
         text(0,1,6,1,1,ss,12,0)

# clear ram
Rpegs = glob.glob('/run/shm/*.jpg')
for tt in range(0,len(Rpegs)):
    os.remove(Rpegs[tt])
Rideos = glob.glob('/run/shm/*.mp4')
for tt in range(0,len(Rideos)):
    os.remove(Rideos[tt])
    
main_menu()
oldimg = []
show   = 0
vidjr  = 0
Videos = []
last   = time.monotonic()
check_timer = time.monotonic()

# check sd card space
free = (os.statvfs('/'))
SD_storage = ((1 - (free.f_bavail / free.f_blocks)) * 100)
ss = str(int(sfreeram)) + "MB - " + str(int(SD_storage)) + "%"

# get cpu temperature
cpu_temp = str(CPUTemperature()).split("=")
temp = float(str(cpu_temp[1])[:-1])

old_capture = Capture

if awb == 0 and Pi_Cam != 11:
    picam2.set_controls({"AwbEnable": True,"AwbMode": controls.AwbModeEnum.Auto})

def watchdog(qq):
    global stop_thread,pause_thread
    while stop_thread == False:
        time.sleep(5)
        if qq.empty():
            pass
        else:
           timeval = qq.get()
        if timeval < time.monotonic() - 120 and pause_thread == False:
            now = datetime.datetime.now()
            timestamp = now.strftime("%y%m%d%H%M%S")
            with open("Watchdog.txt", 'a') as f:
               f.write(timestamp + "\n")
            os.system("reboot")

if watch == True:
    qq = Queue()
    qq.put(time.monotonic())
    watch_thread = threading.Thread(target=watchdog, args=(qq,))
    watch_thread.start()
watch_timer = time.monotonic()
watch_time  = 10
menu_timer  = time.monotonic()
menu_time   = 30

while True:
    time.sleep(1/dspeed)
    # read Pi5 temperature and fan speed
    if Pi == 5 and menu == 5:
        text(0,0,2,0,1,"CPU Temp/FAN",13,7)
        if os.path.exists ('fantxt.txt'): 
            os.remove("fantxt.txt")
        os.system("cat /sys/devices/platform/cooling_fan/hwmon/*/fan1_input >> fantxt.txt")
        time.sleep(0.25)
        with open("fantxt.txt", "r") as file:
            line = file.readline()
            if line == "":
                line = 0
            text(0,0,3,1,1,str(int(temp)) + " / " + str(int(line)),14,7)
    # read non Pi5 temperature
    elif menu == 5:
        text(0,0,2,0,1,"CPU Temp",14,7)
        text(0,0,3,1,1,str(int(temp)),14,7)
    # watchdog
    if time.monotonic() - watch_timer > watch_time and watch == True:
        qq.put(time.monotonic())
        watch_timer = time.monotonic()
    # menu timer
    if time.monotonic() - menu_timer > menu_time and menu != -1:
        menu_timer = time.monotonic()
        if camera != old_camera:
            camera = old_camera
            picam2.stop_encoder()
            picam2.close()
            picam2.stop()
            Camera_Version()
            pygame.display.set_caption('Action ' + cameras[Pi_Cam])
            # restart circular buffer
            start_buffer()
            if camera == 1:
                set_parameters1()
            else:
                set_parameters()
            main_menu()
    # time sync 
    if time.monotonic() - sync_timer > sync_time and not encoding:
        sync_timer = time.monotonic()
        if trace > 0:
              print ("Step SYNC TIME")
        try:
            if os.path.exists("/run/shm/sync.txt"):
                os.rename('/run/shm/sync.txt', '/run/shm/oldsync.txt')
            os.system("timedatectl >> /run/shm/sync.txt")
            # read sync.txt file
            sync = []
            with open("/run/shm/sync.txt", "r") as file:
                line = file.readline()
                while line:
                    sync.append(line.strip())
                    line = file.readline()
            if sync[4] == "System clock synchronized: yes":
                synced = 1
                if menu == 5:
                    text(0,9,3,1,1,str(sd_hour) + ":00",14,7)
            else:
                synced = 0
                if menu == 5:
                    text(0,9,0,1,1,str(sd_hour)+":00",14,7)
            if trace > 0:
                print("SYNC: ", synced)
        except:
            pass
          
    # check timer
    if time.monotonic() - check_timer > check_time and not encoding:
        check_timer = time.monotonic()
        if trace > 0:
              print ("Step CHECK TIME")
        # check current hour
        now = datetime.datetime.now()
        hour = int(now.strftime("%H"))
        mins = int(now.strftime("%M"))

        # get sunrise and sunset times
        suntimes()
        
        # switch cameras if switch time reached and clocked synced
        if camera_sw <= 1 and cam2 != "1": # AUTO (Sun) or SET TIMES - switch cameras on set times
          if synced == 1 and on_time < of_time and menu != 1 and menu != 2 and menu != 6 and menu != 7:
              if (((hour* 60) + mins >= on_time and (hour* 60) + mins < of_time) and camera == 1) or (camera == 1 and old_camera == 0):
                    camera = 0
                    if IRF_on == 1 and IRF_on1 == 1:
                        led_ir_light.off()
                    old_camera = camera
                    if menu == 3:
                        text(0,6,1,0,1,"Camera: " + str(camera + 1),14,7)
                        text(0,6,3,1,1,str(camera_sws[camera_sw]),14,7)
                    picam2.stop_encoder()
                    picam2.close()
                    picam2.stop()
                    Camera_Version()
                    pygame.display.set_caption('Action ' + cameras[Pi_Cam])
                    # restart circular buffer
                    start_buffer()
                    if camera == 0:
                        set_parameters()
                    else:
                        set_parameters1()
              elif (((hour* 60) + mins >= of_time or (hour* 60) + mins < on_time) and camera == 0)  or (camera == 0 and old_camera == 1):
                    camera = 1
                    led_ir_light.on()
                    old_camera = camera
                    if menu == 3:
                        text(0,6,1,0,1,"Camera: " + str(camera + 1),14,7)
                        text(0,6,3,1,1,str(camera_sws[camera_sw]),14,7)
                    picam2.stop_encoder()
                    picam2.close()
                    picam2.stop()
                    Camera_Version()
                    pygame.display.set_caption('Action ' + cameras[Pi_Cam])
                    # restart circular buffer
                    start_buffer()
                    if camera == 0:
                        set_parameters()
                    else:
                        set_parameters1()
              save_config = 1

        # switch IR filter / Light / RECORD if switch time reached and clocked synced
        if IRF <= 1 and camera == 0: # AUTO (Sun) or SET TIMES - switch IR filter / Light / RECORD at set times
            if synced == 1 and ir_on_time < ir_of_time:
                if (hour* 60) + mins >= ir_on_time and (hour* 60) + mins < ir_of_time:
                    # daytime switch IR filter ON and light OFF
                    IRF_on = 1
                    stop_rec = 0
                    led_sw_ir.on()
                    led_sw_ir1.off()
                    led_ir_light.off()
                    if menu == 2 :
                        text(0,0,1,0,1,"IR Filter",14,7)
                 
                elif ((hour* 60) + mins >= ir_of_time or (hour* 60) + mins < ir_on_time):
                    if rec_stop == 1: # night time, stop recording, all IR Filters and Light OFF
                        now = datetime.datetime.now()
                        timestamp = now.strftime("%y%m%d%H%M%S")
                        IRF_on = 0
                        led_sw_ir.off()
                        led_ir_light.off()
                        stop_rec = 1
                        if menu == 2 :
                            text(0,0,2,0,1,"IR Filter",14,7)
                    else: # night time switch IR filters OFF and light ON
                        IRF_on = 0
                        stop_rec = 0
                        led_sw_ir.off()
                        led_ir_light.on()
                        if menu == 2 :
                            text(0,0,2,0,1,"IR Filter",14,7)

        # switch IR filter1 / Light / RECORD if switch time reached and clocked synced
        if IRF1 <= 1 and camera == 1: # AUTO (Sun) or SET TIMES - switch IR filter / Light / RECORD at set times
            if synced == 1 and ir_on_time1 < ir_of_time1:
                if (hour* 60) + mins >= ir_on_time1 and (hour* 60) + mins < ir_of_time1:
                    # daytime switch IR filter ON and light OFF
                    IRF_on1 = 1
                    stop_rec = 0
                    led_sw_ir1.on()
                    led_sw_ir.off()
                    led_ir_light.off()
                    if menu == 7:
                        text(0,0,1,0,1,"IR Filter",14,7)
                elif ((hour* 60) + mins >= ir_of_time1 or (hour* 60) + mins < ir_on_time1):
                    if rec_stop == 1: # night time, stop recording, all IR Filters and Light OFF
                        now = datetime.datetime.now()
                        timestamp = now.strftime("%y%m%d%H%M%S")
                        IRF_on1 = 0
                        led_sw_ir1.off()
                        led_ir_light.off()
                        stop_rec = 1
                        if menu == 7:
                            text(0,0,2,0,1,"IR Filter",14,7)
                    else: # night time switch IR filters OFF and light ON
                        IRF_on1 = 0
                        stop_rec = 0
                        led_sw_ir1.off()
                        led_ir_light.on()
                        if menu == 7:
                            text(0,0,2,0,1,"IR Filter",14,7)
          
        # shutdown if shutdown hour reached and clocked synced
        if hour > sd_hour - 1 and sd_hour != 0 and time.monotonic() - start_up > 600 and synced == 1 and not encoding:
            # EXIT and SHUTDOWN
            if trace > 0:
                 print ("Step 13 TIMED EXIT")
            pause_thread = True
            # move any videos to SD Card
            if ram_frames > 0:
                if menu == -1 :
                    button(0,0,1)
                    text(0,0,5,0,1,"CAPTURE",16,0)
                    vf = str(ram_frames) + " - " + str(frames)
                    text(0,0,3,1,1,vf,14,4)
                Rideos = glob.glob('/run/shm/2???????????.mp4')
                Rideos.sort()
                for xx in range(0,len(Rideos)):
                    shutil.copy(Rideos[xx], h_user + '/Videos/')
                Rpegs = glob.glob('/run/shm/2*.jpg')
                Rpegs.sort()
                for xx in range(0,len(Rpegs)):
                    shutil.copy(Rpegs[xx], h_user + '/Videos/')
            # move mp4s to USB if present
            USB_Files  = []
            USB_Files  = (os.listdir(m_user))
            if len(USB_Files) > 0:
                usedusb = os.statvfs(m_user + "/" + USB_Files[0] + "/")
                USB_storage = ((1 - (usedusb.f_bavail / usedusb.f_blocks)) * 100)
            if len(USB_Files) > 0 and USB_storage < 90:
                Videos = glob.glob(h_user + '/Videos/*.mp4')
                Videos.sort()
                for xx in range(0,len(Videos)):
                    movi = Videos[xx].split("/")
                    if not os.path.exists(m_user + "/'" + USB_Files[0] + "'/" + movi[4]):
                        shutil.move(Videos[xx],m_user[0] + "/'" + USB_Files[0] + "'/")
            if use_gpio == 1 and fan_ctrl == 1:
                led_fan.value = 0
            stop_thread = True
            led_sw_ir.off()
            led_sw_ir1.off()
            led_ir_light.off()
            pygame.quit()
            time.sleep(5)
            os.system("sudo shutdown -h now")

        # set fan speed
        if fan_ctrl == 1 and not encoding:
            check_timer = time.monotonic()
            cpu_temp = str(CPUTemperature()).split("=")
            temp = float(str(cpu_temp[1])[:-1])
            dc = ((temp - fan_low)/(fan_high - fan_low))
            dc = max(dc,.25)
            dc = min(dc,1)
            if temp > fan_low and use_gpio == 1:
                led_fan.value = dc
                if menu == 5:
                    text(0,7,1,0,1,"Fan High  " + str(int(dc*100)) + "%",14,7)
            elif temp < fan_low and use_gpio == 1:
                led_fan.value = 0
                if menu == 5: 
                    text(0,7,2,0,1,"Fan High degC",14,7)
                
        # get RAM free space
        st = os.statvfs("/run/shm/")
        freeram = (st.f_bavail * st.f_frsize)/1100000

       
    # GET AN IMAGE
    cur = picam2.capture_array("lores")
    img = cv2.cvtColor(cur,cv2.COLOR_YUV420p2BGR)
    image = pygame.surfarray.make_surface(img)
    image = pygame.transform.scale(image,(pre_height,pre_width))
    image = pygame.transform.rotate(image,int(90))
    image = pygame.transform.flip(image,0,1)

    # IF NOT IN SHOW MODE
    if show == 0:
        if col_timer > 0 and time.monotonic() - col_timer > 3:
            col_timer = 0
        if camera == 0 or camera == 1:
          image2 = pygame.surfarray.pixels3d(image)
          # CROP DETECTION AREA
          crop = image2[a-h_crop:a+h_crop,b-v_crop:b+v_crop]
          if trace > 1:
            print ("CROP ", crop.size)
          # COLOUR FILTER
          if col_filter < 3:
            gray = crop[:,:,col_filter]
          else:
            gray = cv2.cvtColor(crop,cv2.COLOR_RGB2GRAY)
          if col_filter < 3 and (preview == 1 or col_timer > 0):
            im = Image.fromarray(gray)
            im.save("/run/shm/qw.jpg")
          gray = gray.astype(np.int16)
          detect = 0
           
        if np.shape(gray) == np.shape(oldimg):
            # SHOW FOCUS VALUE
            if menu == 0 or menu == 5 or menu == 2 or menu == 7 or menu == 1 or menu == 6:
                foc = cv2.Laplacian(gray, cv2.CV_64F).var()
                if menu == 2 or menu == 7: 
                    text(0,3,3,1,1,str(int(foc)),14,7)
                    text(0,3,2,0,1,"Focus Value",14,7)
            diff = np.sum(mask)
            diff = max(diff,1)
            # COMPARE NEW IMAGE WITH OLD IMAGE
            ar5 = abs(np.subtract(np.array(gray),np.array(oldimg)))
            # APPLY THRESHOLD VALUE
            ar5[ar5 <  threshold] = 0
            ar5[ar5 >= threshold2] = 0
            ar5[ar5 >= threshold] = 1
            # APPLY MASK
            if mask.shape == ar5.shape:
               ar5 = ar5 * mask
            # NOISE REDUCTION
               if nr > 0:
                pr = np.diff(np.diff(ar5))
                pr[pr < -2 ] = 0
                if nr > 1:
                    pr[pr > -1] = 0
                else:
                    pr[pr > -2] = 0
                pr[pr < 0 ] = -1
                mt = np.zeros((h_crop*2,1),dtype = 'int')
                pr = np.c_[mt,pr,mt]
  
                qc = np.swapaxes(ar5,0,1)
                qr = np.diff(np.diff(qc))
                qr[qr < -2 ] = 0
                if nr > 1:
                    qr[qr > -1] = 0
                else:
                    qr[qr > -2] = 0
                qr[qr < 0] = -1
                mt = np.zeros((v_crop*2,1),dtype = 'int')
                qr = np.c_[mt,qr,mt]
   
                qr = np.swapaxes(qr,0,1)
                qt = pr + qr
                qt[qt < -2] = 0
                if nr > 1:
                    qt[qt > -1] = 0
                else:
                    qt[qt > -2] = 0 
                qt[qt < 0] = -1
                ar5 = ar5 + qt
            sar5 = np.sum(ar5)
            
            if menu == 0:
                text(0,1,2,0,1,"Low Detect " + str(int((sar5/diff) * 100)) + "%",14,7)
            if menu == -1 and preview == 1:
                text(0,2,2,1,1,str(int((sar5/diff) * 100)) + "%",14,7)
            # MAKE PREVIEW OF DETECTED PIXELS
            if preview == 1:
                imagep = pygame.surfarray.make_surface(ar5 * 201)
                imagep.set_colorkey(0, pygame.RLEACCEL)
            # copy RAM video files to sd card if auto_save = 1 or low RAM, after defined period of no activity
            st = os.statvfs("/run/shm/")
            freeram = (st.f_bavail * st.f_frsize)/1100000
            if (ram_frames > 0 and auto_time > 0 and time.monotonic() - last > auto_time and auto_save == 1 and not encoding and menu == -1) or (ram_frames > 0 and freeram < ram_limit and not encoding and menu == -1):
              try:
                if trace > 0:
                    print ("Step 4 AUTO SAVE")
                if menu == -1:
                    text(0,0,5,0,1,"CAPTURE",16,0)
                # read list of existing RAM Video Files
                Videos = glob.glob('/run/shm/2???????????.mp4')
                Videos.sort()
                frames +=len(Videos)
                for xx in range(0,len(Videos)):
                    shutil.move(Videos[xx], h_user + '/Videos/')
                ram_frames = 0
                # read list of existing RAM Photo Files
                Jpegs = glob.glob('/run/shm/2*.jpg')
                Jpegs.sort()
                for xx in range(0,len(Jpegs)):
                    shutil.move(Jpegs[xx], h_user + '/Videos/')
                vf = str(ram_frames) + " - " + str(frames)
                if menu == -1 :
                    text(0,0,3,1,1,vf,14,7)
                if Capture == 0 and menu == -1:
                    button(0,0,0)
                    text(0,0,0,0,1,"CAPTURE",16,7)
                    vf = str(ram_frames) + " - " + str(frames)
                    text(0,0,3,1,1,vf,14,7)
                elif menu == -1 and frames + ram_frames == 0:
                    button(0,0,4)
                    text(0,0,6,0,1,"CAPTURE",16,4)
                    vf = str(ram_frames) + " - " + str(frames)
                    text(0,0,3,1,1,vf,14,4)
                elif menu == -1 :
                    button(0,0,5)
                    text(0,0,3,0,1,"CAPTURE",16,2)
                    vf = str(ram_frames) + " - " + str(frames)
                    text(0,0,3,1,1,vf,14,2)
                last = time.monotonic()
                st = os.statvfs("/run/shm/")
                freeram = (st.f_bavail * st.f_frsize)/1100000
                free = (os.statvfs('/'))
                SD_storage = ((1 - (free.f_bavail / free.f_blocks)) * 100)
                ss = str(int(freeram)) + "MB - " + str(int(SD_storage)) + "%"
                if menu == -1:
                    if record == 0:
                        text(0,1,6,1,1,ss,12,3)
                    else:
                        text(0,1,6,1,1,ss,12,0)
              except:
                  pass

            # external input triggers to RECORD
            if use_gpio == 1:
                if button_e_trig1.is_pressed or button_e_trig2.is_pressed:
                    record = 1
                
            # detection of motion
            if (((sar5/diff) * 100 > detection and (sar5/diff) * 100 < det_high and threshold != 0) or (time.monotonic() - timer10 > interval and timer10 != 0 and threshold == 0) or record == 1) and menu == -1:
                if trace > 0:
                    print ("Step 6 DETECTED " + str(int((sar5/diff) * 100)))
                if timer10 != 0:
                   timer10 = time.monotonic()
                if menu == 0:
                    text(0,1,1,0,1,"Low Detect "  + str(int((sar5/diff) * 100)) + "%",14,7)
                if Capture == 1 or record == 1:
                    # start recording
                    if not encoding:
                        now = datetime.datetime.now()
                        timestamp = now.strftime("%y%m%d%H%M%S")
                        encoder.output.fileoutput = "/run/shm/" + str(timestamp) + '.h264'
                        encoder.output.start()
                        encoding = True
                        print("New Motion", timestamp)
                        image3 = cv2.cvtColor(img,cv2.COLOR_BGR2RGB)
                    ltime = time.time()
                    detect = 1
                    # trigger external camera
                    if ES > 0 and use_gpio == 1: 
                        led_s_focus.on()
                        time.sleep(0.25)
                        led_s_trig.on()
                        if ES == 1:
                            time.sleep(0.25)
                            led_s_trig.off()
                            led_s_focus.off()
                    vid = 1
                    if menu == -1:
                        button(0,0,1)
                        text(0,0,3,0,1,"CAPTURE",16,0)
                        text(0,0,1,1,1," ",15,0)
                        vf = str(ram_frames) + " - " + str(frames)
                        text(0,0,3,1,1,vf,14,0)
                    start = time.monotonic()
                    start2 = time.monotonic()
                    fx = 1
                    st = os.statvfs("/run/shm/")
                    freeram = (st.f_bavail * st.f_frsize)/1100000
                    record = 0
                  
                else:
                    if Capture == 1 and menu == -1:
                        text(0,0,3,1,1,str(interval - (int(time.monotonic() - timer10))),15,0)
                if menu == 0:
                    text(0,1,2,0,1,"Low Detect " + str(int((sar5/diff) * 100)) + "%",14,7)
            else:
                # stop recording
                if encoding and time.time() - ltime > v_length/1000:
                    encoder.output.stop()
                    encoding = False
                    # convert to mp4
                    cmd = 'ffmpeg -framerate ' + str(mp4_fps) + ' -i ' + "/run/shm/" + str(timestamp) + '.h264 -c copy ' + "/run/shm/" + str(timestamp) + '.mp4'
                    os.system(cmd)
                    os.remove("/run/shm/" + str(timestamp) + '.h264')
                    if ES == 2 and use_gpio == 1:
                        led_s_trig.off()
                        led_s_focus.off()
                    Videos = glob.glob(h_user + '/Videos/2???????????.mp4')
                    frames = len(Videos)
                    Rideos = glob.glob('/run/shm/2???????????.mp4')
                    Rideos.sort()
                    ram_frames = len(Rideos)
                    for x in range(0,len(Rideos)):
                         Videos.append(Rideos[x])
                    Videos.sort()
                    vf = str(ram_frames) + " - " + str(frames)
                    if menu == -1:
                        text(0,0,3,1,1,vf,14,7)
                    cv2.imwrite("/run/shm/" + str(timestamp) + ".jpg",image3)
                    last = time.monotonic()    
                    st = os.statvfs("/run/shm/")
                    freeram = (st.f_bavail * st.f_frsize)/1100000
                    free = (os.statvfs('/'))
                    SD_storage = ((1 - (free.f_bavail / free.f_blocks)) * 100)
                    ss = str(int(freeram)) + " - " + str(int(SD_storage))
                    Jpegs = glob.glob(h_user + '/Videos/2*.jpg')
                    Rpegs = glob.glob('/run/shm/2*.jpg')
                    for x in range(0,len(Rpegs)):
                         Jpegs.append(Rpegs[x])
                    Jpegs.sort()
                    # if RAM space < RAM Limit
                    if ram_frames > 0 and freeram < ram_limit:
                        if trace > 0:
                            print ("Step 10 COPY TO SD")
                        if menu == -1:
                            text(0,0,5,0,1,"CAPTURE",16,0)
                            text(0,0,5,1,1," ",15,0)
                        Videos = glob.glob('/run/shm/2???????????.mp4')
                        Videos.sort()
                        # move Video RAM Files to SD card
                        for xx in range(0,len(Videos)):
                            if not os.path.exists(h_user + "/" + '/Videos/' + Videos[xx]):
                                shutil.move(Videos[xx], h_user + '/Videos/')
                        Rpegs = glob.glob('/run/shm/2*.jpg')
                        Rpegs.sort()
                        # move Photos RAM Files to SD card
                        for xx in range(0,len(Jpegs)):
                            if not os.path.exists(h_user + "/" + '/Videos/' + Jpegs[xx]):
                                shutil.move(Jpegs[xx], h_user + '/Videos/')
                        # read list of existing RAM Video Files
                        Rideos = glob.glob('/run/shm/2???????????.mp4')
                        Rideos.sort()
                        ram_frames = len(Rideos)
                        # read list of existing SD Card Video Files
                        if trace > 0:
                            print ("Step 11 READ SD FILES")
                        Videos = glob.glob(h_user + '/Videos/2???????????.mp4')
                        Videos.sort()
                        frames = len(Videos)
                        vf = str(ram_frames) + " - " + str(frames)
                        if menu == 4:
                            if ram_frames + frames > 0:
                                text(0,4,3,1,1,str(ram_frames + frames),14,7)
                            else:
                                text(0,4,3,1,1," ",14,7)
                    # check free RAM and SD storage space
                    st = os.statvfs("/run/shm/")
                    freeram = (st.f_bavail * st.f_frsize)/1100000
                    free = (os.statvfs('/'))
                    SD_storage = ((1 - (free.f_bavail / free.f_blocks)) * 100)
                    ss = str(int(freeram)) + "MB - " + str(int(SD_storage)) + "%"
                    if menu == -1:
                        text(0,0,3,1,1,vf,14,0)
                    record = 0
                    timer10 = time.monotonic()
                    oldimg = []
                    vidjr = 1

                    if ((ram_frames > 0 or frames > 0)  and menu == -1):
                        text(0,6,1,0,1,"SHOW,EDIT or",13,7)
                        text(0,6,1,1,1,"DELETE",14,7)
                    elif menu == -1:
                        text(0,6,0,0,1,"SHOW,EDIT or",13,7)
                        text(0,6,0,1,1,"DELETE",14,7)
                    USB_Files  = []
                    USB_Files  = (os.listdir(m_user))
                    if len(USB_Files) > 0:
                        usedusb = os.statvfs(m_user + "/" + USB_Files[0] + "/")
                        USB_storage = ((1 - (usedusb.f_bavail / usedusb.f_blocks)) * 100)
                    # check SD space for files ,move to usb stick (if available)
                    if SD_storage > SD_limit and len(USB_Files) > 0 and SD_F_Act == 2 and USB_storage < 90:
                        if trace > 0:
                            print ("Step 12 USED SD CARD > LIMIT")
                        if not os.path.exists(m_user + "/'" + USB_Files[0] + "'/Videos/") :
                            os.system('mkdir ' + m_user + "/'" + USB_Files[0] + "'/Videos/")
                        text(0,0,2,0,1,"CAPTURE",16,0)
                        while SD_storage > SD_limit:
                            Jpegs = glob.glob(h_user + '/Videos/2*.jpg')
                            Jpegs.sort()
                            if len(Jpegs) > 0:
                                for q in range(0,len(Jpegs)):
                                    if os.path.getsize(Jpegs[q]) > 0:
                                        shutil.move(Jpegs[q],m_user + "/'" + USB_Files[0] + "'/Videos/")
                            Videos = glob.glob(h_user + '/Videos/2???????????.mp4')
                            Videos.sort()
                            if len(Videos) > 0:
                                for q in range(0,len(Videos)):
                                    if os.path.getsize(Videos[q]) > 0:
                                        shutil.move(Videos[q],m_user + "/'" + USB_Files[0] + "'/Videos/")
                            free = (os.statvfs('/'))
                            SD_storage = ((1 - (free.f_bavail / free.f_blocks)) * 100)
                            ss = str(int(freeram)) + "MB - " + str(int(SD_storage)) + "%"
                            if record == 0:
                                text(0,1,6,1,1,ss,12,3)
                            else:
                                text(0,1,6,1,1,ss,12,0)
                            
                        text(0,0,6,0,1,"CAPTURE",16,0)
                    elif SD_storage > SD_limit:
                        #STOP CAPTURE IF NO MORE SD CARD SPACE AND NO USB STICK
                        if trace > 0:
                            print ("Step 12a sd card limit exceeded and no or full USB stick")
                        if SD_F_Act == 0:
                            Capture = 0 # stop
                        else:
                            # remove oldest video and jpg from SD card
                            Videos = glob.glob(h_user + '/Videos/2???????????.mp4')
                            Videos.sort()
                            if os.path.getsize(Videos[q]) > 0:
                                os.remove(Videos[0])
                                os.remove(Videos[0][:-4] + ".jpg")
                            frames -=1
                            vf = str(ram_frames) + " - " + str(frames)
                         
                    if Capture == 0 and menu == -1:
                        button(0,0,0)
                        text(0,0,0,0,1,"CAPTURE",16,7)
                        text(0,0,3,1,1,vf,14,7)
                    elif menu == -1 :
                        button(0,0,5)
                        text(0,0,3,0,1,"CAPTURE",16,2)
                        vf = str(ram_frames) + " - " + str(frames)
                        text(0,0,3,1,1,vf,14,2)
                    if menu == -1:
                        button(0,1,3)
                        text(0,1,6,0,1,"RECORD",16,3)
                        text(0,1,6,1,1,ss,12,3)
                    pause_thread = False
        if show == 0 and show_vid == 1:
          if trace > 0:
              print ("SHOW FRAME")
          if zoom == 0:
              cropped = pygame.transform.scale(image,(pre_width,pre_height))
          else:
              cropped = pygame.surfarray.make_surface(crop)
              cropped = pygame.transform.scale(cropped,(pre_width,pre_height))
          windowSurfaceObj.blit(cropped,(0, 0))
          # show colour filtering
          if col_filter < 3 and (preview == 1 or col_timer > 0):
            imageqw = pygame.image.load('/run/shm/qw.jpg')
            if zoom == 0:
                imagegray = pygame.transform.scale(imageqw, (v_crop*2,h_crop*2))
            else:
                imagegray = pygame.transform.scale(imageqw, (pre_height,pre_width))
            imagegray = pygame.transform.flip(imagegray, True, False)
            imagegray = pygame.transform.rotate(imagegray, 90)
            
            if zoom == 0:
                windowSurfaceObj.blit(imagegray, (a-h_crop,b-v_crop))
            else:
                windowSurfaceObj.blit(imagegray, (0,0))
          # show detected pixels if required
          if preview == 1 and np.shape(gray) == np.shape(oldimg):
            if zoom == 0:
                imagep = pygame.transform.scale(imagep, (h_crop*2,v_crop*2))
                windowSurfaceObj.blit(imagep, (a-h_crop,b-v_crop))
            elif preview == 1:
                imagep = pygame.transform.scale(imagep, (pre_width,pre_height))
                windowSurfaceObj.blit(imagep, (0,0))
          if zoom == 0:
              pygame.draw.rect(windowSurfaceObj, (0,255,0), Rect(a - h_crop,b - v_crop ,h_crop*2,v_crop*2), 2)
              nmask = pygame.surfarray.make_surface(mask)
              nmask = pygame.transform.scale(nmask, (h_crop*2,v_crop*2))
              nmask.set_colorkey((0,0,50))
              nmask.set_alpha(m_alpha)
              windowSurfaceObj.blit(nmask, (a - h_crop,b - v_crop))
          if (Pi_Cam == 3 or Pi_Cam == 8) and fxz != 1 and zoom == 0 and menu == 3:
            pygame.draw.rect(windowSurfaceObj,(200,0,0),Rect(int(fxx*cwidth),int(fxy*cheight*.75),int(fxz*cwidth),int(fxz*cheight)),1)
          pygame.display.update(0,0,scr_width-bw,scr_height)
          
        elif show_vid == 0 and show == 0:
            pygame.draw.rect(windowSurfaceObj,(0,0,0),Rect(0,0,pre_width,pre_height))
            pygame.display.update(0,0,pre_width,pre_height)
        if vidjr != 1:
           oldimg[:] = gray[:]
        vidjr = 0

        if fcount < max_fcount and Pi != 5 and (Pi_Cam == 5 or Pi_Cam == 6) and AF_f_mode == 0:
            Capture = 0
            if menu == -1:
                button(0,0,0)
                text(0,0,0,0,1,"CAPTURE",16,7)
                text(0,0,3,1,1,vf,14,7)
                rep = 0
        elif Pi != 5 and (Pi_Cam == 5 or Pi_Cam == 6) and rep == 0 and AF_f_mode == 0:
            Capture = old_capture
            if menu == -1:
                if Capture == 1 and frames + ram_frames == 0:
                    button(0,0,4)
                    text(0,0,6,0,1,"CAPTURE",16,4)
                    text(0,0,3,1,1,vf,14,4)
                elif Capture == 1 and frames + ram_frames > 0:
                    button(0,0,5)
                    text(0,0,3,0,1,"CAPTURE",16,2)
                    text(0,0,3,1,1,vf,14,2)
                else:
                    button(0,0,0)
                    text(0,0,0,0,1,"CAPTURE",16,7)
                    text(0,0,3,1,1,vf,14,7)
                text(0,9,3,0,1," ",14,7)
                text(0,9,3,1,1," ",14,7)
            rep = 1
               
    save_config = 0
    #check for any mouse button presses
    for event in pygame.event.get():
        if (event.type == MOUSEBUTTONUP):
            timer = time.monotonic()
            menu_timer  = time.monotonic()
            mousex, mousey = event.pos
            # set crop position
            if mousex < pre_width and zoom == 0 and ((menu != 7 or ((Pi_Cam == 3 or Pi_Cam == 8) and AF_f_mode == 1)) or (Pi_Cam == 5 or Pi_Cam == 6)) and event.button != 3:
                if (Pi_Cam == 5 or Pi_Cam == 6):
                    fcount = 0
                a = mousex
                b = mousey
                if a + h_crop > pre_width:
                   a = pre_width - h_crop
                if b + v_crop > pre_height:
                   b = pre_height - v_crop
                if a - h_crop < 0:
                   a = h_crop
                if b - v_crop < 0:
                   b = v_crop
                oldimg = []
                save_config = 1
                
            # set mask
            if mousex < pre_width and zoom == 0 and event.button == 3 :
                if mousex > a - h_crop and mousex < a + h_crop and mousey < b + v_crop and mousey > b - v_crop:
                    mx = int(mousex - (a - h_crop)) 
                    my = int(mousey - (b - v_crop))
                    su = int(h_crop/5)
                    sl = 0-su
                    if mask[mx][my] == 0:
                        for aa in range(sl,su):
                            for bb in range(sl,su):
                                if mx + bb > 0 and my + aa > 0 and mx + bb < h_crop * 2  and my + aa < v_crop * 2:
                                    mask[mx + bb][my + aa] = 1
                    else:
                        for aa in range(sl,su):
                            for bb in range(sl,su):
                                if mx + bb > 0 and my + aa > 0 and mx + bb < h_crop * 2  and my + aa < v_crop * 2:
                                    mask[mx + bb][my + aa] = 0
                    nmask = pygame.surfarray.make_surface(mask)
                    nmask = pygame.transform.scale(nmask, (200,200))
                    nmask = pygame.transform.rotate(nmask, 270)
                    nmask = pygame.transform.flip(nmask, True, False)
                    pygame.image.save(nmask,h_user + '/CMask.bmp')
                 
            # set AF camera autofocus position
            if mousex < pre_width and zoom == 0 and (menu == 2 or menu == 7) and (Pi_Cam == 3 or Pi_Cam == 8 or Pi_Cam == 5 or Pi_Cam == 6) and AF_f_mode > 0 and event.button != 3:
                a = mousex
                b = mousey
                if a + h_crop > pre_width:
                   a = pre_width - h_crop
                if b + v_crop > pre_height:
                   b = pre_height - v_crop
                if a - h_crop < 0:
                   a = h_crop
                if b - v_crop < 0:
                   b = v_crop
                fxx = int((a - h_crop) * (swidth/pre_width))
                fxy = int((b - v_crop) * (sheight/pre_height))
                fxz = int((h_crop * 2) * (swidth/pre_width))
                fxa = int((v_crop * 2) * (sheight/pre_height))
                picam2.set_controls({"AfMode" : controls.AfModeEnum.Continuous,"AfMetering" : controls.AfMeteringEnum.Windows,"AfWindows" : [ (fxx,fxy,fxz,fxa) ] } )
                text(0,4,3,1,1,"Spot",14,7)
                if camera == 0:
                    AF_f_spot = 1
                else:
                    AF_f_spot1 = 1
                oldimg = []
                save_config = 1
            # keys   
            elif mousex > cwidth:
                g = int(mousey/bh)
                gv = mousey - (g * bh)
                h = 0
                hp = (scr_width - mousex) / bw
                if hp < 0.5:
                    h = 1
                if g == 10 and menu == -1 and event.button == 3:
                    # EXIT
                    if trace > 0:
                         print ("Step 13 EXIT")
                    pause_thread = True
                    # Move RAM FRAMES to SD CARD
                    if ram_frames > 0:
                        if menu == -1 :
                            button(0,0,1)
                            text(0,0,5,0,1,"CAPTURE",16,0)
                        zpics = glob.glob('/run/shm/2*.jpg')
                        zpics.sort()
                        for xx in range(0,len(zpics)):
                            shutil.copy(zpics[xx], h_user + '/Videos/')
                        zpics = glob.glob('/run/shm/2???????????.mp4')
                        zpics.sort()
                        for xx in range(0,len(zpics)):
                            shutil.copy(zpics[xx], h_user + '/Videos/')
                    # Move MP4s to USB if present
                    USB_Files  = []
                    USB_Files  = (os.listdir(m_user))
                    if len(USB_Files) > 0:
                        Videos = glob.glob(h_user + '/Videos/*.mp4')
                        Videos.sort()
                        for xx in range(0,len(Videos)):
                            movi = Videos[xx].split("/")
                            if not os.path.exists(m_user + "/" + USB_Files[0] + "/Videos/" + movi[4]):
                                shutil.move(Videos[xx],m_user + "/" + USB_Files[0] + "/Videos/")
                    if use_gpio == 1 and fan_ctrl == 1:
                        led_fan.value = 0
                    stop_thread = True
                    led_sw_ir.off()
                    led_sw_ir1.off()
                    led_ir_light.off()
                    pygame.quit()

                elif g == 10 and menu != -1:
                    # BACK TO MAIN MENU
                    sframe = -1
                    eframe = -1
                    if os.path.exists('mylist.txt'):
                        os.remove('mylist.txt')
                    txtvids = []
                    if camera != old_camera:
                        camera = old_camera
                        picam2.stop_encoder()
                        picam2.close()
                        picam2.stop()
                        Camera_Version()
                        pygame.display.set_caption('Action ' + cameras[Pi_Cam])
                        # restart circular buffer
                        start_buffer()
                        if camera == 1:
                            set_parameters1()
                        else:
                            set_parameters()
                    main_menu()

# MENUS ====================================================================================================
                  
                elif g == 0 and menu == -1 :
                    # CAPTURE
                    Capture +=1
                    zoom = 0
                    if Capture > 1:
                        Capture = 0
                        button(0,0,0)
                        text(0,0,0,0,1,"CAPTURE",16,7)
                        text(0,0,3,1,1,vf,14,7)
                        timer10 = 0
                    else:
                        num = 0
                        button(0,0,4)
                        text(0,0,6,0,1,"CAPTURE",16,4)
                        text(0,0,3,1,1,vf,14,4)
                    old_cap = Capture
                    save_config = 1

                elif g == 1 and menu == -1:
                    # RECORD
                    record = 1
                    button(0,1,1)
                    text(0,1,3,0,1,"RECORD",16,0)

                elif menu == -1: 
                    # MENUS
                    # check for usb_stick
                    USB_Files  = []
                    USB_Files  = (os.listdir(m_user + "/"))
                    if show == 1 and menu != 3:
                        show = 0
                    if g == 2 and event.button != 3:
                        # detection menu
                        menu = 0
                        menu_timer  = time.monotonic()
                        old_capture = Capture
                        Capture = 0
                        for d in range(0,10):
                            button(0,d,0)
                        text(0,3,2,0,1,"Low Threshold",14,7)
                        text(0,3,3,1,1,str(threshold),14,7)
                        text(0,2,2,0,1,"High Detect %",14,7)
                        text(0,2,3,1,1,str(det_high),14,7)
                        text(0,1,2,0,1,"Low Detect %",14,7)
                        text(0,1,3,1,1,str(detection),14,7)
                        if preview == 1:
                            button(0,0,1)
                            text(0,0,1,0,1,"Preview",14,0)
                            text(0,0,1,1,1,"Threshold",13,0)
                        else:
                            button(0,0,0)
                            text(0,0,2,0,1,"Preview",14,7)
                            text(0,0,2,1,1,"Threshold",13,7)
                        text(0,4,2,0,1,"High Threshold",14,7)
                        text(0,4,3,1,1,str(threshold2),14,7)
                        text(0,5,2,0,1,"Horiz'l Crop",14,7)
                        text(0,5,3,1,1,str(h_crop),14,7)
                        text(0,6,2,0,1,"Vert'l Crop",14,7)
                        text(0,6,3,1,1,str(v_crop),14,7)
                        text(0,7,2,0,1,"Colour Filter",14,7)
                        text(0,7,3,1,1,str(col_filters[col_filter]),14,7)
                        text(0,8,2,0,1,"Det Speed",14,7)
                        text(0,8,3,1,1,str(dspeed),14,7)
                        text(0,9,2,0,1,"Noise Red'n",14,7)
                        text(0,9,3,1,1,str(noise_filters[nr]),14,7)
                        text(0,10,1,0,1,"MAIN MENU",14,7)

                    elif g == 2 and event.button == 3: # right click
                        # PREVIEW
                        preview +=1
                        if preview > 1:
                            preview = 0
                            text(0,2,1,1,1,"Settings",14,7)
                            
                    elif g == 3:
                        # camera 1 settings 1
                        menu = 1
                        menu_timer  = time.monotonic()
                        old_capture = Capture
                        Capture = 0
                        old_camera = camera
                        camera = 0
                        picam2.stop_encoder()
                        picam2.close()
                        picam2.stop()
                        Camera_Version()
                        pygame.display.set_caption('Action ' + cameras[Pi_Cam])
                        for d in range(0,10):
                            button(0,d,0)
                        text(0,7,5,0,1,"Meter",14,7)
                        text(0,7,3,1,1,meters[meter],14,7)
                        text(0,0,5,0,1,"fps",14,7)
                        text(0,0,3,1,1,str(fps),14,7)
                        text(0,1,5,0,1,"Mode",14,7)
                        text(0,1,3,1,1,modes[mode],14,7)
                        text(0,2,5,0,1,"Shutter",14,7)
                        shutter = shutters[speed]
                        if shutter < 0:
                            shutter = abs(1/shutter)
                        sspeed = int(shutter * 1000000)
                        if (shutter * 1000000) - int(shutter * 1000000) > 0.5:
                            sspeed +=1
                        if mode == 0:
                            if shutters[speed] < 0:
                                text(0,2,3,1,1,"1/" + str(abs(shutters[speed])),14,7)
                            else:
                                text(0,2,3,1,1,str(shutters[speed]),14,7)
                        else:
                            if shutters[speed] < 0:
                               text(0,2,0,1,1,"1/" + str(abs(shutters[speed])),14,7)
                            else:
                               text(0,2,0,1,1,str(shutters[speed]),14,7)
                        text(0,3,5,0,1,"gain",14,7)
                        if gain > 0:
                            text(0,3,3,1,1,str(gain),14,7)
                        else:
                            text(0,3,3,1,1,"Auto",14,7)
                        text(0,4,5,0,1,"Brightness",14,7)
                        text(0,4,3,1,1,str(brightness),14,7)
                        text(0,5,5,0,1,"Contrast",14,7)
                        text(0,5,3,1,1,str(contrast),14,7)
                        text(0,6,5,0,1,"eV",14,7)
                        text(0,6,3,1,1,str(ev),14,7)
                        text(0,7,5,0,1,"Metering",14,7)
                        text(0,7,3,1,1,str(meters[meter]),14,7)
                        text(0,8,5,0,1,"Sharpness",14,7)
                        text(0,8,3,1,1,str(sharpness),14,7)
                        if Pi_Cam != 11:
                            text(0,9,5,0,1,"Saturation",14,7)
                            text(0,9,3,1,1,str(saturation),14,7)
                        text(0,10,1,0,1,"MAIN MENU",14,7)
                        # restart circular buffer
                        start_buffer()
                        set_parameters()
 
                    elif g == 4:
                        # camera 1 settings 2
                        menu = 2
                        menu_timer  = time.monotonic()
                        old_camera = camera
                        camera = 0
                        picam2.stop_encoder()
                        picam2.close()
                        picam2.stop()
                        Camera_Version()
                        pygame.display.set_caption('Action ' + cameras[Pi_Cam] + ' : ' + str(camera))
                        for d in range(0,10):
                            button(0,d,0)
                        if Pi_Cam == 3 or Pi_Cam == 8 or Pi_Cam == 5 or Pi_Cam == 6:
                            text(0,4,2,0,1,"Focus",14,7)
                            if AF_f_mode == 0:
                                text(0,5,2,0,1,"Focus Manual",14,7)
                                if Pi_Cam == 3:
                                    fd = 1/(AF_focus)
                                    text(0,5,3,1,1,str(fd)[0:5] + "m",14,7)
                                else:
                                    text(0,5,3,1,1,str(int(101-(AF_focus * 10))),14,7)

                            text(0,4,3,1,1,AF_f_modes[AF_f_mode],14,7)
                            if AF_f_spot == 1:
                                text(0,0,3,1,1,"Spot",14,7)
                        if Pi_Cam > -1:
                            text(0,1,1,0,1,"IRF ON time",14,7)
                            if IRF == 0:
                                clr = 2
                            else:
                                clr = 3
                            if synced == 1:
                                if ir_on_mins > 9:
                                    text(0,1,clr,1,1,str(ir_on_hour) + ":" + str(ir_on_mins),14,7)
                                else:
                                    text(0,1,clr,1,1,str(ir_on_hour) + ":0" + str(ir_on_mins),14,7)
                            else:
                                if ir_on_mins > 9:
                                    text(0,1,0,1,1,str(ir_on_hour) + ":" + str(ir_on_mins),14,7)
                                else:
                                    text(0,1,0,1,1,str(ir_on_hour) + ":0" + str(ir_on_mins),14,7)
                            text(0,2,1,0,1,"IRF OFF time",14,7)
                            if synced == 1:
                                if ir_of_mins > 9:
                                    text(0,2,clr,1,1,str(ir_of_hour) + ":" + str(ir_of_mins),14,7)
                                else:
                                    text(0,2,clr,1,1,str(ir_of_hour) + ":0" + str(ir_of_mins),14,7)
                            else:
                                if ir_of_mins > 9:
                                    text(0,2,0,1,1,str(ir_of_hour) + ":" + str(ir_of_mins),14,7)
                                else:
                                    text(0,2,0,1,1,str(ir_of_hour) + ":0" + str(ir_of_mins),14,7)
                        if Pi_Cam != 11:
                            text(0,6,5,0,1,"AWB",14,7)
                            text(0,6,3,1,1,str(awbs[awb]),14,7)
                            text(0,7,5,0,1,"Red",14,7)
                            text(0,8,5,0,1,"Blue",14,7)
                            if awb == 6:
                                text(0,7,3,1,1,str(red)[0:3],14,7)
                                text(0,8,3,1,1,str(blue)[0:3],14,7)
                            else:
                                text(0,7,0,1,1,str(red)[0:3],14,7)
                                text(0,8,0,1,1,str(blue)[0:3],14,7)
                        text(0,9,5,0,1,"Denoise",14,7)
                        text(0,9,3,1,1,str(denoises[denoise]),14,7)
                        if IRF_on == 0:
                            text(0,0,2,0,1,"IR Filter",14,7)
                        else:
                            text(0,0,1,0,1,"IR Filter",14,7)
                        text(0,0,3,1,1,IR_filters[IRF],14,7)
                        text(0,10,1,0,1,"MAIN MENU",14,7)
                        ir_on_time = (ir_on_hour * 60) + ir_on_mins
                        ir_of_time = (ir_of_hour * 60) + ir_of_mins
                        # restart circular buffer
                        start_buffer()
                        set_parameters()

                    elif g == 5:
                        # video settings
                        menu = 3
                        menu_timer  = time.monotonic()
                        old_capture = Capture
                        Capture = 0
                        for d in range(0,10):
                            button(0,d,0)
                        if zoom == 0:
                            button(0,5,0)
                            text(0,5,2,0,1,"Zoom",14,7)
                        else:
                            button(0,5,1)
                            text(0,5,1,0,1,"Zoom",14,0)
                        if Pi == 5 and cam2 != "1":
                            text(0,6,1,0,1,"Camera: " + str(camera + 1),14,7)
                            text(0,6,3,1,1,camera_sws[camera_sw],14,7)
                        text(0,1,2,0,1,"V Length S (F)",14,7)
                        text(0,1,3,1,1,str(v_length/1000) + "  (" + str(int(fps*(v_length/1000))) +")",14,7)
                        text(0,2,2,0,1,"V Pre-Frames",14,7)
                        text(0,2,3,1,1,str(pre_frames) + " Secs",14,7)
                        text(0,0,2,0,1,"Interval S",14,7)
                        text(0,0,3,1,1,str(interval),14,7)
                        if cam2 != "1":
                            if camera_sw == 0:
                                clr = 2
                            else:
                                clr = 3
                            text(0,7,1,0,1,"SW 2>1 time",14,7)
                            if synced == 1 and cam2 != "1":
                                if on_mins > 9:
                                    text(0,7,clr,1,1,str(on_hour) + ":" + str(on_mins),14,7)
                                else:
                                    text(0,7,clr,1,1,str(on_hour) + ":0" + str(on_mins),14,7)
                            else:
                                if on_mins > 9:
                                    text(0,7,0,1,1,str(on_hour) + ":" + str(on_mins),14,7)
                                else:
                                    text(0,7,0,1,1,str(on_hour) + ":0" + str(on_mins),14,7)
                            text(0,8,1,0,1,"SW 1>2 time",14,7)
                            if synced == 1 and cam2 != "1":
                                if of_mins > 9:
                                    text(0,8,clr,1,1,str(of_hour) + ":" + str(of_mins),14,7)
                                else:
                                    text(0,8,clr,1,1,str(of_hour) + ":0" + str(of_mins),14,7)
                            else:
                                if of_mins > 9:
                                    text(0,8,0,1,1,str(of_hour) + ":" + str(of_mins),14,7)
                                else:
                                    text(0,8,0,1,1,str(of_hour) + ":0" + str(of_mins),14,7)
                        text(0,3,2,0,1,"MASK Alpha",14,7)
                        text(0,3,3,1,1,str(m_alpha),14,7)
                        text(0,4,2,0,1,"CLEAR Mask",14,7)
                        text(0,4,3,1,1," 0       1  ",14,7)
                        text(0,10,1,0,1,"MAIN MENU",14,7)                        

                    elif g == 6 and (ram_frames > 0 or frames > 0):
                        # show menu
                        menu = 4
                        menu_timer  = time.monotonic()
                        for d in range(0,10):
                            button(0,d,0)
                        show = 1
                        old_cap = Capture
                        Jpegs = glob.glob(h_user + '/Videos/2*.jpg')
                        frames = len(Jpegs)
                        Rpegs = glob.glob('/run/shm/2*.jpg')
                        Rpegs.sort()
                        ram_frames = len(Rpegs)
                        for x in range(0,len(Rpegs)):
                            Jpegs.append(Rpegs[x])
                        Jpegs.sort()
                        q = 0
                        if len(Jpegs) > 0:
                            image = pygame.image.load(Jpegs[q])
                            cropped = pygame.transform.scale(image, (pre_width,pre_height))
                            windowSurfaceObj.blit(cropped, (0, 0))
                            fontObj = pygame.font.Font(None, 25)
                            msgSurfaceObj = fontObj.render(str(Jpegs[q]), False, (255,255,0))
                            msgRectobj = msgSurfaceObj.get_rect()
                            msgRectobj.topleft = (10,10)
                            windowSurfaceObj.blit(msgSurfaceObj, msgRectobj)
                            msgSurfaceObj = fontObj.render((str(q+1) + "/" + str(ram_frames + frames)), False, (255,0,0))
                            msgRectobj = msgSurfaceObj.get_rect()
                            msgRectobj.topleft = (10,35)
                            windowSurfaceObj.blit(msgSurfaceObj, msgRectobj)
                            pygame.draw.rect(windowSurfaceObj,(0,0,0),Rect(0,pre_height,scr_width-bw,scr_height))
                            pygame.display.update()
                            text(0,1,3,1,1,str(q+1) + " / " + str(ram_frames + frames),14,7)
                        text(0,0,2,0,1,"SHOW Camera",14,7)
                        if old_show_vid == 0:
                            text(0,0,3,1,1,"OFF",14,7)
                        else:
                            text(0,0,3,1,1,"ON",14,7)
                        text(0,1,2,0,1,"Still",14,7)
                        text(0,2,2,0,1,"Show Video",14,7)
                        text(0,3,2,0,1,"MP4 fps",14,7)
                        text(0,3,3,1,1,str(mp4_fps),14,7)
                        text(0,4,2,0,1,"annotate MP4",14,7)
                        if mp4_anno == 0:
                            text(0,4,3,1,1,"No",14,7)
                        else:
                            text(0,4,3,1,1,"Yes",14,7)
                        if frames > 0:
                            text(0,5,2,0,1,"MOVE MP4s",14,7)
                            text(0,5,2,1,1,"to USB",14,7)
                        else:
                            text(0,5,0,0,1,"MOVE MP4s",14,7)
                            text(0,5,0,1,1,"to USB",14,7)
                        text(0,6,3,0,1,"DELETE ",14,7)
                        text(0,6,3,1,1,"VIDEO ",14,7)
                        text(0,7,3,0,1,"DELETE",14,7)
                        text(0,7,3,1,1,"ALL VIDS  ",14,7)
                        text(0,8,2,0,1,"SHOW ALL",14,7)
                        text(0,8,2,1,1,"Stills",14,7)
                        text(0,9,2,0,1,"MAKE FULL",14,7)
                        text(0,9,2,1,1,"MP4",14,7)
                        text(0,10,1,0,1,"MAIN MENU",14,7)
                       
                    elif g == 7:
                        # other settings
                        menu = 5
                        menu_timer  = time.monotonic()
                        old_capture = Capture
                        Capture = 0
                        for d in range(0,10):
                            button(0,d,0)
                        text(0,1,2,0,1,"Auto Time",14,7)
                        if Pi == 5:
                            text(0,0,2,0,1,"CPU Temp/FAN",13,7)
                            if os.path.exists ('fantxt.txt'): 
                                os.remove("fantxt.txt")
                            os.system("cat /sys/devices/platform/cooling_fan/hwmon/*/fan1_input >> fantxt.txt")
                            time.sleep(0.25)
                            with open("fantxt.txt", "r") as file:
                                line = file.readline()
                                if line == "":
                                    line = 0
                            text(0,0,3,1,1,str(int(temp)) + " / " + str(int(line)),14,7)
                        else:
                            text(0,0,2,0,1,"CPU Temp",14,7)
                            text(0,0,3,1,1,str(int(temp)),14,7)
                        if auto_time > 0:
                            text(0,1,3,1,1,str(auto_time),14,7)
                        else:
                            text(0,1,3,1,1,"OFF",14,7)
                        text(0,2,2,0,1,"RAM Limit MB",14,7)
                        text(0,2,3,1,1,str(int(ram_limit)),14,7)
                        text(0,3,2,0,1,"SD Limit %",14,7)
                        text(0,3,3,1,1,str(int(SD_limit)),14,7)
                        text(0,4,2,0,1,"SD Full Action",14,7)
                        if SD_F_Act == 0:
                            text(0,4,3,1,1,"STOP",14,7)
                        elif SD_F_Act == 1:
                            text(0,4,3,1,1,"DEL OLD",14,7)
                        else:
                            text(0,4,3,1,1,"To USB",14,7)
                        if use_gpio == 1:
                            if fan_ctrl == 1:
                                text(0,5,2,0,1,"Fan Time S",14,7)
                                text(0,5,3,1,1,str(check_time),14,7)
                                text(0,6,2,0,1,"Fan Low degC",14,7)
                                text(0,6,3,1,1,str(fan_low),14,7)
                                text(0,7,2,0,1,"Fan High degC",14,7)
                                text(0,7,3,1,1,str(fan_high),14,7)
                            text(0,8,2,0,1,"Ext. Trigger",14,7)
                            if ES == 0:
                                text(0,8,3,1,1,"OFF",14,7)
                            elif ES == 1:
                                text(0,8,3,1,1,"Short",14,7)
                            else:
                                text(0,8,3,1,1,"Long",14,7)
                        text(0,9,1,0,1,"Shutdown Hour",14,7)
                        if synced == 1:
                            text(0,9,3,1,1,str(sd_hour) + ":00",14,7)
                        else:
                            text(0,9,0,1,1,str(sd_hour) + ":00",14,7)
                        USB_Files  = []
                        USB_Files  = (os.listdir(m_user))
                        if len(USB_Files) > 0:
                            usedusb = os.statvfs(m_user + "/" + USB_Files[0] + "/Pictures/")
                            USB_storage = ((1 - (usedusb.f_bavail / usedusb.f_blocks)) * 100)
                        text(0,10,1,0,1,"MAIN MENU",14,7)

                    elif g == 8 and cam2 != "1":
                        # camera 2 settings 1
                        menu = 6
                        menu_timer  = time.monotonic()
                        old_capture = Capture
                        Capture = 0
                        old_camera = camera
                        camera = 1
                        picam2.stop_encoder()
                        picam2.close()
                        picam2.stop()
                        Camera_Version()
                        pygame.display.set_caption('Action ' + cameras[Pi_Cam])
                        for d in range(0,10):
                            button(0,d,0)
                        text(0,0,5,0,1,"fps",14,7)
                        text(0,0,3,1,1,str(fps1),14,7)
                        text(0,1,5,0,1,"Mode",14,7)
                        text(0,1,3,1,1,modes[mode1],14,7)
                        text(0,2,5,0,1,"Shutter",14,7)
                        shutter1 = shutters[speed1]
                        if shutter1 < 0:
                            shutter1 = abs(1/shutter1)
                        sspeed1 = int(shutter1 * 1000000)
                        if (shutter1 * 1000000) - int(shutter1 * 1000000) > 0.5:
                            sspeed1 +=1
                        if mode1 == 0:
                            if shutters[speed1] < 0:
                                text(0,2,3,1,1,"1/" + str(abs(shutters[speed1])),14,7)
                            else:
                                text(0,2,3,1,1,str(shutters[speed1]),14,7)
                        else:
                            if shutters[speed1] < 0:
                               text(0,2,0,1,1,"1/" + str(abs(shutters[speed1])),14,7)
                            else:
                               text(0,2,0,1,1,str(shutters[speed1]),14,7)
                        text(0,3,5,0,1,"gain",14,7)
                        if gain1 > 0:
                            text(0,3,3,1,1,str(gain1),14,7)
                        else:
                            text(0,3,3,1,1,"Auto",14,7)
                        text(0,4,5,0,1,"Brightness",14,7)
                        text(0,4,3,1,1,str(brightness1),14,7)
                        text(0,5,5,0,1,"Contrast",14,7)
                        text(0,5,3,1,1,str(contrast1),14,7)
                        text(0,6,5,0,1,"eV",14,7)
                        text(0,6,3,1,1,str(ev1),14,7)
                        text(0,7,5,0,1,"Metering",14,7)
                        text(0,7,3,1,1,str(meters[meter1]),14,7)
                        text(0,8,5,0,1,"Sharpness",14,7)
                        text(0,8,3,1,1,str(sharpness1),14,7)
                        if Pi_Cam != 11:
                            text(0,9,5,0,1,"Saturation",14,7)
                            text(0,9,3,1,1,str(saturation1),14,7)
                        text(0,10,1,0,1,"MAIN MENU",14,7)
                        # restart circular buffer
                        start_buffer()
                        set_parameters1()

                    elif g == 9 and cam2 != "1":
                        # camera 2 settings 2
                        menu = 7
                        menu_timer  = time.monotonic()
                        old_camera = camera
                        camera = 1
                        picam2.stop_encoder()
                        picam2.close()
                        picam2.stop()
                        Camera_Version()
                        pygame.display.set_caption('Action ' + cameras[Pi_Cam] + ' : ' + str(camera))
                        for d in range(0,10):
                            button(0,d,0)
                        if Pi_Cam == 3 or Pi_Cam == 8 or Pi_Cam == 5 or Pi_Cam == 6:
                            text(0,4,2,0,1,"Focus",14,7)
                            if AF_f_mode == 0:
                                text(0,5,2,0,1,"Focus Manual",14,7)
                                if Pi_Cam == 3:
                                    fd = 1/(AF_focus)
                                    text(0,5,3,1,1,str(fd)[0:5] + "m",14,7)
                                else:
                                    text(0,5,3,1,1,str(int(101-(AF_focus * 10))),14,7)
                            text(0,4,3,1,1,AF_f_modes[AF_f_mode],14,7)
                            if AF_f_spot1 == 1:
                                text(0,4,3,1,1,"Spot",14,7)
                        if Pi_Cam > -1:
                            text(0,1,1,0,1,"IRF ON time",14,7)
                            if IRF1 == 0:
                                clr = 2
                            else:
                                clr = 3
                            if synced == 1 and cam2 != "1":
                                if ir_on_mins1 > 9:
                                    text(0,1,clr,1,1,str(ir_on_hour1) + ":" + str(ir_on_mins1),14,7)
                                else:
                                    text(0,1,clr,1,1,str(ir_on_hour1) + ":0" + str(ir_on_mins1),14,7)
                            else:
                                if ir_on_mins1 > 9:
                                    text(0,1,0,1,1,str(ir_on_hour1) + ":" + str(ir_on_mins1),14,7)
                                else:
                                    text(0,1,0,1,1,str(ir_on_hour1) + ":0" + str(ir_on_mins1),14,7)
                            text(0,2,1,0,1,"IRF OFF time",14,7)
                            if synced == 1 and cam2 != "1":
                                if ir_of_mins1 > 9:
                                    text(0,2,clr,1,1,str(ir_of_hour1) + ":" + str(ir_of_mins1),14,7)
                                else:
                                    text(0,2,clr,1,1,str(ir_of_hour1) + ":0" + str(ir_of_mins1),14,7)
                            else:
                                if ir_of_mins1 > 9:
                                    text(0,2,0,1,1,str(ir_of_hour1) + ":" + str(ir_of_mins1),14,7)
                                else:
                                    text(0,2,0,1,1,str(ir_of_hour1) + ":0" + str(ir_of_mins1),14,7)
                        if Pi_Cam != 11:
                            text(0,6,5,0,1,"AWB",14,7)
                            text(0,6,3,1,1,str(awbs[awb1]),14,7)
                            text(0,7,5,0,1,"Red",14,7)
                            text(0,8,5,0,1,"Blue",14,7)
                            if awb1 == 6:
                                text(0,7,3,1,1,str(red1)[0:3],14,7)
                                text(0,8,3,1,1,str(blue1)[0:3],14,7)
                            else:
                                text(0,7,0,1,1,str(red1)[0:3],14,7)
                                text(0,8,0,1,1,str(blue1)[0:3],14,7)
                        text(0,9,5,0,1,"Denoise",14,7)
                        text(0,9,3,1,1,str(denoises[denoise1]),14,7)
                        if IRF_on == 0:
                            text(0,0,2,0,1,"IR Filter",14,7)
                        else:
                            text(0,0,1,0,1,"IR Filter",14,7)
                        text(0,0,3,1,1,IR_filters[IRF1],14,7)
                        text(0,10,1,0,1,"MAIN MENU",14,7)
                        # restart circular buffer
                        start_buffer()
                        set_parameters1()
                        

                                        
# MENU 0 ====================================================================================================
                elif menu == 0:
                  if g == 0:
                    # PREVIEW
                    preview +=1
                    if preview > 1:
                        preview = 0
                        button(0,0,0)
                        text(0,0,2,0,1,"Preview",14,7)
                        text(0,0,2,1,1,"Threshold",13,7)
                    else:
                        button(0,0,1)
                        text(0,0,1,0,1,"Preview",14,0)
                        text(0,0,1,1,1,"Threshold",13,0)
                    save_config = 1
                    
                  elif g == 1:
                    # Low Detection
                    if (h == 1 and event.button == 1) or event.button == 4:
                        detection +=1
                        detection = min(detection,100)
                    else:
                        detection -=1
                        detection = max(detection,0)
                    text(0,1,3,1,1,str(detection),14,7)
                    save_config = 1

                  elif g == 2:
                    # High Detection
                    if (h == 1 and event.button == 1) or event.button == 4:
                        det_high +=1
                        det_high = min(det_high,100)
                        text(0,2,3,1,1,str(det_high),14,7)
                    else:
                        det_high -=1
                        det_high = max(det_high,detection)
                        text(0,2,3,1,1,str(det_high),14,7)
                    save_config = 1
                    
                  elif g == 3:
                    # Threshold
                    if (h == 1 and event.button == 1) or event.button == 4:
                        threshold +=1
                        threshold = min(threshold,threshold2 - 1)
                        text(0,3,2,0,1,"Low Threshold",14,7)
                        text(0,3,3,1,1,str(threshold),14,7)
                        timer10 = 0
                    else:
                        threshold -=1
                        threshold = max(threshold,0)
                        text(0,3,2,0,1,"Low Threshold",14,7)
                        text(0,3,3,1,1,str(threshold),14,7)
                        timer10 = 0
                    if threshold == 0:
                        timer10 = time.monotonic()
                        if v_length > interval * 1000:
                           v_length = (interval - 1 * 1000)
                    save_config = 1

                  elif g == 4:
                    # High Threshold
                    if (h == 1 and event.button == 1) or event.button == 4:
                        threshold2 +=1
                        threshold2 = min(threshold2,255)
                        text(0,4,2,0,1,"High Threshold",14,7)
                        text(0,4,3,1,1,str(threshold2),14,7)
                    else:
                        threshold2 -=1
                        threshold2 = max(threshold2,threshold + 1)
                        text(0,4,2,0,1,"High Threshold",14,7)
                        text(0,4,3,1,1,str(threshold2),14,7)
                    save_config = 1

                  elif g == 5:
                    # H CROP
                    if (h == 1 and event.button == 1) or event.button == 4:
                        h_crop +=1
                        h_crop = min(h_crop,pre_width)
                        if a-h_crop < 1 or b-v_crop < 1 or a+h_crop > cwidth or b+v_crop > int(cwidth/(pre_width/pre_height)):
                            h_crop -=1
                            new_crop = 0
                            new_mask = 0
                        text(0,5,3,1,1,str(h_crop),14,7)
                    else:
                        h_crop -=1
                        h_crop = max(h_crop,1)
                        text(0,5,3,1,1,str(h_crop),14,7)
                    mask,change = MaskChange()
                    save_config = 1
                    
                  elif g == 6:
                    # V CROP
                    if (h == 1 and event.button == 1) or event.button == 4:
                        v_crop +=1
                        v_crop = min(v_crop,pre_height)
                        if a-h_crop < 1 or b-v_crop < 1 or a+h_crop > cwidth or b+v_crop > int(cwidth/(pre_width/pre_height)):
                            v_crop -=1
                        text(0,6,3,1,1,str(v_crop),14,7)
                    else:
                        v_crop -=1
                        v_crop = max(v_crop,1)
                        text(0,6,3,1,1,str(v_crop),14,7)
                    mask,change = MaskChange()
                    save_config = 1                    

                  elif g == 7:
                    # COLOUR FILTER
                    if (h == 0 and event.button == 1) or event.button == 5:
                        col_filter -=1
                        col_filter = max(col_filter,0)
                    else:
                        col_filter +=1
                        col_filter = min(col_filter,3)
                    text(0,7,3,1,1,str(col_filters[col_filter]),14,7)
                    save_config = 1
                    if col_filter < 4:
                        col_timer = time.monotonic()
                    else:
                        col_timer = 0

                  elif g == 8:
                    # DETECTION SPEED
                    if (h == 0 and event.button == 1) or event.button == 5:
                        dspeed -=1
                        dspeed = max(dspeed,1)
                    else:
                        dspeed +=1
                        dspeed = min(dspeed,100)
                    text(0,8,3,1,1,str(dspeed),14,7)
                    save_config = 1
                    
                  elif g == 9:
                    # NOISE REDUCTION
                    if (h == 0 and event.button == 1) or event.button == 5:
                        nr -=1
                        nr = max(nr,0)
                    else:
                        nr += 1
                        nr = min(nr,2)
                    text(0,9,3,1,1,str(noise_filters[nr]),14,7)
                    save_config = 1
                    
# MENU 1 ====================================================================================================
                elif menu == 1:    
                  if g == 0:
                    # FPS
                    if (h == 1 and event.button == 1) or event.button == 4:
                        fps +=1
                        fps = min(fps,120)
                    else:
                        fps -=1
                        fps = max(fps,5)
                    picam2.set_controls({"FrameRate": fps})
                    text(0,0,3,1,1,str(fps),14,7)
                    save_config = 1                    
                   
                  elif g == 1:
                    # MODE
                    if h == 1 :
                        mode +=1
                        mode = min(mode,3)
                    else:
                        mode -=1
                        mode = max(mode,0)
                    if mode == 0:
                        picam2.set_controls({"AeEnable": False})
                        picam2.set_controls({"ExposureTime": sspeed})
                        if shutters[speed] < 0:
                            text(0,2,3,1,1,"1/" + str(abs(shutters[speed])),14,7)
                        else:
                            text(0,2,3,1,1,str(shutters[speed]),14,7)
                        picam2.set_controls({"AnalogueGain": gain})
                    else:
                        picam2.set_controls({"AeEnable": True})
                        if shutters[speed] < 0:
                           text(0,2,0,1,1,"1/" + str(abs(shutters[speed])),14,7)
                        else:
                           text(0,2,0,1,1,str(shutters[speed]),14,7)
                        if mode == 1:
                            picam2.set_controls({"AeExposureMode": controls.AeExposureModeEnum.Normal})
                        if mode == 2:
                            picam2.set_controls({"AeExposureMode": controls.AeExposureModeEnum.Short})
                        if mode == 3:
                            picam2.set_controls({"AeExposureMode": controls.AeExposureModeEnum.Long})
                        picam2.set_controls({"AnalogueGain": gain})
                    text(0,1,3,1,1,modes[mode],14,7)
                    save_config = 1
                    
                  elif g == 2:
                    # Shutter Speed
                    if (h == 1 and event.button == 1) or event.button == 4:
                        speed +=1
                        speed = min(speed,len(shutters)-1)
                    else:
                        speed -=1
                        speed = max(speed,0)
                    shutter = shutters[speed]
                    if shutter < 0:
                        shutter = abs(1/shutter)
                    sspeed = int(shutter * 1000000)
                    if (shutter * 1000000) - int(shutter * 1000000) > 0.5:
                        sspeed +=1
                    fps = int(1/(sspeed/1000000))
                    fps = max(fps,1)
                    fps = min(fps,fps2)
                    if mode == 0:
                        picam2.set_controls({"FrameRate": fps})
                        picam2.set_controls({"ExposureTime": sspeed})
                    if mode == 0:
                        if shutters[speed] < 0:
                            text(0,2,3,1,1,"1/" + str(abs(shutters[speed])),14,7)
                        else:
                            text(0,2,3,1,1,str(shutters[speed]),14,7)
                    else:
                        if shutters[speed] < 0:
                            text(0,2,0,1,1,"1/" + str(abs(shutters[speed])),14,7)
                        else:
                            text(0,2,0,1,1,str(shutters[speed]),14,7)
                    save_config = 1
                    
                  elif g == 3:
                    # GAIN
                    if (h == 1 and event.button == 1) or event.button == 4:
                        gain +=1
                        gain = min(gain,max_gain)
                    else:
                        gain -=1
                        gain = max(gain,0)
                    picam2.set_controls({"AnalogueGain": gain})
                    if gain > 0:
                        text(0,3,3,1,1,str(gain),14,7)
                    else:
                        text(0,3,3,1,1,"Auto",14,7)
                    save_config = 1
                    
                  elif g == 4:
                    # BRIGHTNESS
                    if (h == 1 and event.button == 1) or event.button == 4:
                        brightness +=1
                        brightness = min(brightness,20)
                    else:
                        brightness -=1
                        brightness = max(brightness,0)
                    picam2.set_controls({"Brightness": brightness/10})
                    text(0,4,3,1,1,str(brightness),14,7)
                    save_config = 1
                    
                  elif g == 5:
                    # CONTRAST
                    if (h == 1 and event.button == 1) or event.button == 4:
                        contrast +=1
                        contrast = min(contrast,20)
                    else:
                        contrast -=1
                        contrast = max(contrast,0)
                    picam2.set_controls({"Contrast": contrast/10})
                    text(0,5,3,1,1,str(contrast),14,7)
                    save_config = 1

                  elif g == 6:
                    # EV
                    if (h == 1 and event.button == 1) or event.button == 4:
                        ev +=1
                        ev = min(ev,20)
                    else:
                        ev -=1
                        ev = max(ev,-20)
                    picam2.set_controls({"ExposureValue": ev/10})
                    text(0,6,5,0,1,"eV",14,7)
                    text(0,6,3,1,1,str(ev),14,7)
                    save_config = 1
                    
                  elif g == 7:
                    # Metering
                    if h == 1:
                        meter +=1
                        meter = min(meter,len(meters)-1)
                    else:
                        meter -=1
                        meter = max(meter,0)
                    if meter == 0:
                        picam2.set_controls({"AeMeteringMode": controls.AeMeteringModeEnum.CentreWeighted})
                    elif meter == 1:
                        picam2.set_controls({"AeMeteringMode": controls.AeMeteringModeEnum.Spot})
                    elif meter == 2:
                        picam2.set_controls({"AeMeteringMode": controls.AeMeteringModeEnum.Matrix})
                    text(0,7,3,1,1,str(meters[meter]),14,7)
                    save_config = 1

                  elif g == 8:
                    # SHARPNESS
                    if(h == 1 and event.button == 1) or event.button == 4:
                        sharpness +=1
                        sharpness = min(sharpness,16)
                    else:
                        sharpness -=1
                        sharpness = max(sharpness,0)
                    picam2.set_controls({"Sharpness": sharpness})
                    text(0,8,3,1,1,str(sharpness),14,7)
                    save_config = 1

                  elif g == 9 and Pi_Cam != 11:
                    # SATURATION
                    if (h == 1 and event.button == 1) or event.button == 4:
                        saturation +=1
                        saturation = min(saturation,32)
                    else:
                        saturation -=1
                        saturation = max(saturation,0)
                    picam2.set_controls({"Saturation": saturation/10})
                    text(0,9,3,1,1,str(saturation),14,7)
                    save_config = 1
                    
# MENU 2 ====================================================================================================
                elif menu == 2:
                  if g == 0:
                    # IR FILTER
                    if (h == 1 and event.button == 1) or event.button == 4:
                        IRF +=1
                        IRF = min(IRF,len(IR_filters)-1)
                    else:
                        IRF -=1
                        IRF = max(IRF,0)
                    text(0,0,3,1,1,IR_filters[IRF],14,7)
                    if IRF == 2:
                        IRF_on = 0
                        led_sw_ir.off()
                        led_ir_light.on()
                        text(0,0,2,0,1,"IR Filter",14,7)
                    elif IRF == 3:
                        IRF_on = 1
                        led_sw_ir.on()
                        if IRF_on1 == 1:
                            led_ir_light.off()
                        text(0,0,1,0,1,"IR Filter",14,7)
                    if IRF == 0:
                        suntimes()
                    if synced == 1 and IRF == 0:
                        if ir_on_mins > 9:
                            text(0,1,2,1,1,str(ir_on_hour) + ":" + str(ir_on_mins),14,7)
                        else:
                            text(0,1,2,1,1,str(ir_on_hour) + ":0" + str(ir_on_mins),14,7)
                    elif IRF == 0:
                        if ir_on_mins > 9:
                            text(0,1,0,1,1,str(ir_on_hour) + ":" + str(ir_on_mins),14,7)
                        else:
                            text(0,1,0,1,1,str(ir_on_hour) + ":0" + str(ir_on_mins),14,7)
                    if synced == 1 and IRF == 0:                
                        if ir_of_mins > 9:
                            text(0,2,2,1,1,str(ir_of_hour) + ":" + str(ir_of_mins),14,7)
                        else:
                            text(0,2,2,1,1,str(ir_of_hour) + ":0" + str(ir_of_mins),14,7)
                    elif IRF == 0:
                        if ir_of_mins > 9:
                            text(0,2,0,1,1,str(ir_of_hour) + ":" + str(ir_of_mins),14,7)
                        else:
                            text(0,2,0,1,1,str(ir_of_hour) + ":0" + str(ir_of_mins),14,7)
                    save_config = 1
                    
                  elif g == 1 and IRF == 1:
                    # SWITCH IR FILTER ON TIME
                    if h == 1 and event.button == 3:
                        ir_on_hour +=1
                        if ir_on_hour > 23:
                            ir_on_hour = 0

                    elif h == 0 and event.button == 3:
                        ir_on_hour -=1
                        if ir_on_hour < 0:
                            ir_on_hour = 23
                                
                    elif h == 1 and event.button != 3:
                        ir_on_mins +=1
                        if ir_on_mins > 59:
                            ir_on_mins = 0
                            ir_on_hour += 1
                            if ir_on_hour > 23:
                                ir_on_hour = 0
                    elif h == 0 and event.button != 3:
                        ir_on_mins -=1
                        if ir_on_mins  < 0:
                            ir_on_hour -= 1
                            ir_on_mins = 59
                            if ir_on_hour < 0:
                                ir_on_hour = 23
                    if ir_on_mins > 9:
                        text(0,1,3,1,1,str(ir_on_hour) + ":" + str(ir_on_mins),14,7)
                    else:
                        text(0,1,3,1,1,str(ir_on_hour) + ":0" + str(ir_on_mins),14,7)
                    ir_on_time = (ir_on_hour * 60) + ir_on_mins
                    ir_of_time = (ir_of_hour * 60) + ir_of_mins
                    if ir_on_time >= ir_of_time:
                        ir_of_hour = ir_on_hour
                        ir_of_mins = ir_on_mins + 1
                        if ir_of_mins > 59:
                            ir_of_mins = 0
                            ir_of_hour += 1
                            if ir_of_hour > 23:
                                ir_of_hour = 0
                        if ir_of_mins > 9:
                            text(0,2,3,1,1,str(ir_of_hour) + ":" + str(ir_of_mins),14,7)
                        else:
                            text(0,2,3,1,1,str(ir_of_hour) + ":0" + str(ir_of_mins),14,7)
                    ir_of_time = (ir_of_hour * 60) + ir_of_mins
                    save_config = 1

                  elif g == 2 and IRF == 1:
                    # SWITCH IR FILTER OFF TIME
                    if h == 1 and event.button == 3:
                        ir_of_hour +=1
                        if ir_of_hour > 23:
                            ir_of_hour = 0

                    elif h == 0 and event.button == 3:
                        ir_of_hour -=1
                        if ir_of_hour < 0:
                            ir_of_hour = 23
                            
                    elif h == 1:
                        ir_of_mins +=1
                        if ir_of_mins > 59:
                            ir_of_mins = 0
                            ir_of_hour += 1
                            if ir_of_hour > 23:
                                ir_of_hour = 0
                    elif h == 0:
                        ir_of_mins -=1
                        if ir_of_mins  < 0:
                            ir_of_hour -= 1
                            ir_of_mins = 59
                            if ir_of_hour < 0:
                                ir_of_hour = 23
                    if ir_of_mins > 9:
                        text(0,2,3,1,1,str(ir_of_hour) + ":" + str(ir_of_mins),14,7)
                    else:
                        text(0,2,3,1,1,str(ir_of_hour) + ":0" + str(ir_of_mins),14,7)
                    ir_on_time = (ir_on_hour * 60) + ir_on_mins
                    ir_of_time = (ir_of_hour * 60) + ir_of_mins
                    if ir_of_time <= ir_on_time:
                        ir_on_hour = ir_of_hour
                        ir_on_mins = ir_of_mins - 1
                        if ir_on_mins  < 0:
                            ir_on_hour -= 1
                            ir_on_mins = 59
                            if ir_on_hour < 0:
                                ir_on_hour = 23
                        if ir_on_mins > 9:
                            text(0,1,3,1,1,str(ir_on_hour) + ":" + str(ir_on_mins),14,7)
                        else:
                            text(0,1,3,1,1,str(ir_on_hour) + ":0" + str(ir_on_mins),14,7)
                      
                    ir_on_time = (ir_on_hour * 60) + ir_on_mins
                    save_config = 1

                  # g == 3 USED FOR FOCUS VALUE

                  elif g == 4 and (Pi_Cam == 3 or Pi_Cam == 8 or Pi_Cam == 5 or Pi_Cam == 6):
                    # camera0 focus mode
                    if (h == 0 and event.button == 1) or event.button == 5:
                        AF_f_mode -=1
                        AF_f_mode = max(AF_f_mode,0)
                    else:
                        AF_f_mode +=1
                        AF_f_mode = min(AF_f_mode,2)
                    if AF_f_mode == 0:
                        AF_f_spot = 0
                        fxx = 0
                        fxy = 0
                        fxz = 1
                        picam2.set_controls({"AfMode": controls.AfModeEnum.Manual, "AfMetering" : controls.AfMeteringEnum.Windows,  "AfWindows" : [(int(vid_width* .33),int(vid_height*.33),int(vid_width * .66),int(vid_height*.66))]})
                    elif AF_f_mode == 1:
                        AF_f_spot = 0
                        fxx = 0
                        fxy = 0
                        fxz = 1
                        picam2.set_controls({"AfMode": controls.AfModeEnum.Auto, "AfMetering" : controls.AfMeteringEnum.Windows,  "AfWindows" : [(int(vid_width* .33),int(vid_height*.33),int(vid_width * .66),int(vid_height*.66))]})
                        picam2.set_controls({"AfTrigger": controls.AfTriggerEnum.Start})
                    elif AF_f_mode == 2:
                        AF_f_spot = 0
                        fxx = 0
                        fxy = 0
                        fxz = 1
                        picam2.set_controls( {"AfMode" : controls.AfModeEnum.Continuous, "AfMetering" : controls.AfMeteringEnum.Windows,  "AfWindows" : [(int(vid_width* .33),int(vid_height*.33),int(vid_width * .66),int(vid_height*.66))] } )
                        picam2.set_controls({"AfTrigger": controls.AfTriggerEnum.Start})
                    text(0,4,3,1,1,AF_f_modes[AF_f_mode],14,7)
                    if AF_f_mode == 0:
                        picam2.set_controls({"LensPosition": AF_focus})
                        text(0,5,2,0,1,"Focus Manual",14,7)
                        if Pi_Cam == 3:
                            if AF_focus > 0:
                                fd = 1/(AF_focus)
                            text(0,5,3,1,1,str(fd)[0:5] + "m",14,7)
                        else:
                            text(0,5,3,1,1,str(int(101-(AF_focus * 10))),14,7)
                    else:
                        text(0,5,3,0,1," ",14,7)
                        text(0,5,3,1,1," ",14,7)
                    fxx = 0
                    fxy = 0
                    fxz = 1
                    if Pi_Cam == 5 or Pi_Cam == 6:
                        fcount = 0
                    save_config = 1

                  elif g == 5 and AF_f_mode == 0 and (Pi_Cam == 3 or Pi_Cam == 8 or Pi_Cam == 5 or Pi_Cam == 6):
                    # Camera0 focus manual
                    menu_timer  = time.monotonic()
                    if gv < bh/3:
                        mp = 1 - hp
                        AF_focus = int((mp * 8.9) + 1)
                    else:
                        if (h == 0 and event.button == 1) or event.button == 5:
                            AF_focus -= .1
                        else:
                            AF_focus += .1
                    AF_focus = max(AF_focus,0)
                    AF_focus = min(AF_focus,10)
                    picam2.set_controls({"LensPosition": AF_focus})
                    if AF_focus == 0:
                        text(0,5,3,1,1,"Inf",14,7)
                    else:
                        if Pi_Cam == 3:
                            if AF_focus > 0:
                                fd = 1/(AF_focus)
                            text(0,5,3,1,1,str(fd)[0:5] + "m",14,7)
                        else:
                            text(0,5,3,1,1,str(int(101-(AF_focus * 10))),14,7)
                            
               
                  elif g == 6 and Pi_Cam != 11:
                    # AWB setting
                    if (h == 1 and event.button == 1) or event.button == 4:
                        awb +=1
                        awb = min(awb,len(awbs)-1)
                    else:
                        awb -=1
                        awb = max(awb,0)
                    if awb == 0:
                        picam2.set_controls({"AwbEnable": True,"AwbMode": controls.AwbModeEnum.Auto})
                    elif awb == 1 and Pi_Cam != 11:
                        picam2.set_controls({"AwbEnable": True,"AwbMode": controls.AwbModeEnum.Tungsten})
                    elif awb == 2 and Pi_Cam != 11:
                        picam2.set_controls({"AwbEnable": True,"AwbMode": controls.AwbModeEnum.Fluorescent})
                    elif awb == 3 and Pi_Cam != 11:
                        picam2.set_controls({"AwbEnable": True,"AwbMode": controls.AwbModeEnum.Indoor})
                    elif awb == 4 and Pi_Cam != 11:
                        picam2.set_controls({"AwbEnable": True,"AwbMode": controls.AwbModeEnum.Daylight})
                    elif awb == 5 and Pi_Cam != 11:
                        picam2.set_controls({"AwbEnable": True,"AwbMode": controls.AwbModeEnum.Cloudy})
                    elif awb == 6 and Pi_Cam != 11:
                        picam2.set_controls({"AwbEnable": True,"AwbMode": controls.AwbModeEnum.Custom})
                        cg = (red,blue)
                        picam2.set_controls({"AwbEnable": False,"ColourGains": cg})
                    text(0,6,3,1,1,str(awbs[awb]),14,7)
                    if awb == 6:
                        text(0,7,3,1,1,str(red)[0:3],14,7)
                        text(0,8,3,1,1,str(blue)[0:3],14,7)
                    else:
                        text(0,7,0,1,1,str(red)[0:3],14,7)
                        text(0,8,0,1,1,str(blue)[0:3],14,7)
                    save_config = 1
                    
                  elif g == 7 and awb == 6 and Pi_Cam != 11:
                    # RED
                    if h == 0 or event.button == 5:
                        red -=0.1
                        red = max(red,0.1)
                    else:
                        red +=0.1
                        red = min(red,8)
                    cg = (red,blue)
                    picam2.set_controls({"ColourGains": cg})
                    text(0,7,3,1,1,str(red)[0:3],14,7)
                    save_config = 1
                    
                  elif g == 8 and awb == 6 and Pi_Cam != 11:
                    # BLUE
                    if h == 0 or event.button == 5:
                        blue -=0.1
                        blue = max(blue,0.1)
                    else:
                        blue +=0.1
                        blue = min(blue,8)
                    cg = (red,blue)
                    picam2.set_controls({"ColourGains": cg})
                    text(0,8,3,1,1,str(blue)[0:3],14,7)
                    save_config = 1
                   
                  elif g == 9:
                    # DENOISE
                    if (h == 1 and event.button == 1) or event.button == 4:
                        denoise +=1
                        denoise = min(denoise,2)
                    else:
                        denoise -=1
                        denoise = max(denoise,0)
                    if denoise == 0:
                        picam2.set_controls({"NoiseReductionMode": controls.draft.NoiseReductionModeEnum.Off})
                    elif denoise == 1:
                        picam2.set_controls({"NoiseReductionMode": controls.draft.NoiseReductionModeEnum.Fast})
                    elif denoise == 2:
                        picam2.set_controls({"NoiseReductionMode": controls.draft.NoiseReductionModeEnum.HighQuality})

                    text(0,9,3,1,1,str(denoises[denoise]),14,7)
                    save_config = 1
                    
# MENU 3 ====================================================================================================
                elif menu == 3:
                  if g == 0:
                    # INTERVAL
                    if (h == 1 and event.button == 1) or event.button == 4:
                        interval +=1
                        interval = min(interval,180)
                    else:
                        interval -=1
                        interval = max(interval,0)
                    text(0,0,3,1,1,str(interval),14,7)
                    save_config = 1

                  elif g == 1:
                    # VIDEO LENGTH
                    if (h == 0 and event.button == 1) or event.button == 5:
                        if v_length > 1000:
                           v_length -=1000
                        else:
                           v_length -=100
                        v_length = max(v_length,100)
                    else:
                        if v_length > 900:
                            v_length +=1000
                        else:
                           v_length +=100
                        v_length = min(v_length,100000)
                    text(0,1,3,1,1,str(v_length/1000) + "  (" + str(int(fps*(v_length/1000))) +")",14,7)
                    save_config = 1
                    
                  elif g == 2:
                    # PRE FRAMES
                    if h == 1 and event.button == 1:
                        pre_frames +=1
                        pre_frames = min(pre_frames,10)
                    else:
                        pre_frames -=1
                        pre_frames = max(pre_frames,1)
                    text(0,2,0,1,1,str(pre_frames) + " Secs",14,7)
                    picam2.stop_encoder()
                    picam2.stop()
                    encoder.output = CircularOutput(buffersize = pre_frames * fps)
                    picam2.start()
                    picam2.start_encoder(encoder)
                    time.sleep(pre_frames)
                    text(0,2,3,1,1,str(pre_frames) + " Secs",14,7)
                    save_config = 1

                  elif g == 5:
                    # ZOOM
                    zoom +=1
                    if zoom == 1:
                        button(0,5,1)
                        text(0,5,1,0,1,"Zoom",14,0)
                        if event.button == 3:
                            preview = 1
                    else:
                        zoom = 0
                        button(0,5,0)
                        text(0,5,2,0,1,"Zoom",14,7)
                        preview = 0

                  elif g == 6 and Pi == 5 and cam2 != "1":
                    # SWITCH CAMERA MODE
                    if (h == 1 and event.button == 1) or event.button == 4:
                        camera_sw +=1
                        if camera_sw > len(camera_sws)-1:
                            camera_sw = 0
                    else:
                        camera_sw -=1
                        camera_sw = max(camera_sw,0)
                    text(0,6,3,1,1,str(camera_sws[camera_sw]),14,7)
                    if camera_sw == 2:
                        camera = 0
                        if IRF_on == 1:
                            led_ir_light.off()
                        text(0,6,1,0,1,"Camera: " + str(camera + 1),14,7)
                    elif camera_sw == 3:
                        camera = 1
                        led_ir_light.on()
                        text(0,6,1,0,1,"Camera: " + str(camera + 1),14,7)
                    if camera_sw >= 2:
                        old_camera = camera
                        picam2.stop_encoder()
                        picam2.close()
                        picam2.stop()
                        Camera_Version()
                        pygame.display.set_caption('Action ' + cameras[Pi_Cam])
                        # restart circular buffer
                        start_buffer()
                        if camera == 0:
                            set_parameters()
                        else:
                            set_parameters1()
                    if camera_sw == 0:
                      suntimes()
                      if synced == 1 and cam2 != "1":
                        if on_mins > 9:
                            text(0,7,clr,1,1,str(on_hour) + ":" + str(on_mins),14,7)
                        else:
                            text(0,7,clr,1,1,str(on_hour) + ":0" + str(on_mins),14,7)
                      else:
                        if on_mins > 9:
                            text(0,7,0,1,1,str(on_hour) + ":" + str(on_mins),14,7)
                        else:
                            text(0,7,0,1,1,str(on_hour) + ":0" + str(on_mins),14,7)
                      if synced == 1 and cam2 != "1":
                        if of_mins > 9:
                            text(0,8,clr,1,1,str(of_hour) + ":" + str(of_mins),14,7)
                        else:
                            text(0,8,clr,1,1,str(of_hour) + ":0" + str(of_mins),14,7)
                      else:
                        if of_mins > 9:
                            text(0,8,0,1,1,str(of_hour) + ":" + str(of_mins),14,7)
                        else:
                            text(0,8,0,1,1,str(of_hour) + ":0" + str(of_mins),14,7)
                    save_config = 1                        

                  elif g == 7 and camera_sw == 1:
                    # SWITCH to CAMERA 2 HOUR
                    if h == 1 and event.button == 3:
                        on_hour +=1
                        if on_hour > 23:
                            on_hour = 0

                    elif h == 0 and event.button == 3:
                        on_hour -=1
                        if on_hour < 0:
                            on_hour = 23
                            
                    elif h == 1:
                        on_mins +=1
                        if on_mins > 59:
                            on_mins = 0
                            on_hour += 1
                            if on_hour > 23:
                                on_hour = 0
                    elif h == 0:
                        on_mins -=1
                        if on_mins  < 0:
                            on_hour -= 1
                            on_mins = 59
                            if on_hour < 0:
                                on_hour = 23
                    if on_mins > 9:
                        text(0,7,3,1,1,str(on_hour) + ":" + str(on_mins),14,7)
                    else:
                        text(0,7,3,1,1,str(on_hour) + ":0" + str(on_mins),14,7)
                    on_time = (on_hour * 60) + on_mins
                    of_time = (of_hour * 60) + of_mins
                    if on_time >= of_time:
                        of_hour = on_hour
                        of_mins = on_mins + 1
                        if of_mins > 59:
                            of_hour += 1
                            of_mins = 0
                            if of_hour > 23:
                                of_hour = 0
                        if of_mins > 9:
                            text(0,8,3,1,1,str(of_hour) + ":" + str(of_mins),14,7)
                        else:
                            text(0,8,3,1,1,str(of_hour) + ":0" + str(of_mins),14,7)
                        of_time = (of_hour * 60) + of_mins
                    save_config = 1

                  elif g == 8 and camera_sw == 1:
                    # SWITCH to CAMERA 1 HOUR
                    if h == 1 and event.button == 3:
                        of_hour +=1
                        if of_hour > 23:
                            of_hour = 0

                    elif h == 0 and event.button == 3:
                        of_hour -=1
                        if of_hour < 0:
                            of_hour = 23
                            
                    elif h == 1:
                        of_mins +=1
                        if of_mins > 59:
                            of_mins = 0
                            of_hour += 1
                            if of_hour > 23:
                                of_hour = 0
                    elif h == 0:
                        of_mins -=1
                        if of_mins  < 0:
                            of_hour -= 1
                            of_mins = 59
                            if of_hour < 0:
                                of_hour = 23
                    if of_mins > 9:
                        text(0,8,3,1,1,str(of_hour) + ":" + str(of_mins),14,7)
                    else:
                        text(0,8,3,1,1,str(of_hour) + ":0" + str(of_mins),14,7)
                    on_time = (on_hour * 60) + on_mins
                    of_time = (of_hour * 60) + of_mins
                    if of_time <= on_time:
                        on_hour = of_hour
                        on_mins = of_mins - 1
                        if on_mins  < 0:
                            on_hour -= 1
                            on_mins = 59
                            if on_hour < 0:
                                on_hour = 23
                        if on_mins > 9:
                            text(0,7,3,1,1,str(on_hour) + ":" + str(on_mins),14,7)
                        else:
                            text(0,7,3,1,1,str(on_hour) + ":0" + str(on_mins),14,7)
                        on_time = (on_hour * 60) + on_mins
                    save_config = 1

                  elif g == 3:
                    # MASK ALPHA
                    if (h == 0 and event.button == 1) or event.button == 5:
                        m_alpha -= 10
                        m_alpha = max(m_alpha,0)
                    else:
                        m_alpha += 10
                        m_alpha = min(m_alpha,250)
                    text(0,3,3,1,1,str(m_alpha)[0:4],14,7)
                    
                  elif g == 4 :
                    # CLEAR MASK
                    if event.button == 3:
                        if h == 0:
                            mp = 0
                        else:
                            mp = 1
                        for bb in range(0,int(h_crop * 2)):
                            for aa in range(0,int(v_crop * 2 )):
                                mask[bb][aa] = mp
                        nmask = pygame.surfarray.make_surface(mask)
                        nmask = pygame.transform.scale(nmask, (200,200))
                        nmask = pygame.transform.rotate(nmask, 270)
                        nmask = pygame.transform.flip(nmask, True, False)
                        pygame.image.save(nmask,h_user + '/CMask.bmp')
                        mask,change = MaskChange()                                        
                    
# MENU 4 ====================================================================================================
                elif menu == 4:
                  if g == 0:
                   # SHOW CAMERA
                   show_vid +=1
                   if show_vid > 1:
                       show_vid = 0
                   old_show_vid = show_vid
                   if show_vid == 0:
                       text(0,0,3,1,1,"OFF",14,7)
                   else:
                       text(0,0,3,1,1,"ON",14,7)
                            
                  elif g == 1 and show == 1 and (frames > 0 or ram_frames > 0):
                    # SHOW next still
                    menu_timer  = time.monotonic()
                    if menu == 4:
                        text(0,6,3,1,1,"VIDEO ",14,7)
                        text(0,7,3,1,1,"ALL VIDS ",14,7)
                    Jpegs = glob.glob(h_user + '/Videos/2*.jpg')
                    Rpegs = glob.glob('/run/shm/2*.jpg')
                    for x in range(0,len(Rpegs)):
                       Jpegs.append(Rpegs[x])
                    Jpegs.sort()
                    if (h == 1 and event.button == 1) or event.button == 4:
                        q +=1
                        if q > len(Jpegs)-1:
                            q = 0
                    else:
                        q -=1
                        if q < 0:
                            q = len(Jpegs)-1
                    if os.path.getsize(Jpegs[q]) > 0:
                        text(0,1,3,1,1,str(q+1) + " / " + str(ram_frames + frames),14,7)
                        if len(Jpegs) > 0:
                            image = pygame.image.load(Jpegs[q])
                            cropped = pygame.transform.scale(image, (pre_width,pre_height))
                            windowSurfaceObj.blit(cropped, (0, 0))
                            fontObj = pygame.font.Font(None, 25)
                            msgSurfaceObj = fontObj.render(str(Jpegs[q]), False, (255,255,0))
                            msgRectobj = msgSurfaceObj.get_rect()
                            msgRectobj.topleft = (10,10)
                            windowSurfaceObj.blit(msgSurfaceObj, msgRectobj)
                            msgSurfaceObj = fontObj.render((str(q+1) + "/" + str(ram_frames + frames)), False, (255,0,0))
                            msgRectobj = msgSurfaceObj.get_rect()
                            msgRectobj.topleft = (10,35)
                            windowSurfaceObj.blit(msgSurfaceObj, msgRectobj)
                            pygame.display.update()

                  elif g == 2  and show == 1:
                    #Show Video
                    vids = glob.glob(vid_dir + '2*.mp4')
                    Rids = glob.glob('/run/shm/2*.mp4')
                    for x in range(0,len(Rids)):
                       vids.append(Rids[x])
                    vids.sort()
                    if len(Jpegs) > 0:
                      jpgs = Jpegs[q].split("/")
                      if jpgs[1] != 'run':
                        jp = jpgs[4][:-4]
                      else:
                        jp = jpgs[3][:-4]
                      stop = 0
                      for x in range(len(vids)-1,-1,-1):
                        vide = vids[x].split("/")
                        if vide[1] != 'run':
                            vid = vide[4][:-4]
                        else:
                            vid = vide[3][:-4]
                        if vid == jp and stop == 0:
                            if vide[1] != 'run':
                                os.system("vlc /" + vide[1] + "/" + vide[2] + "/" + vide[3] + "/" + vid + '.mp4')
                            else:
                                os.system("vlc /" + vide[1] + "/" + vide[2] + "/" + vid + '.mp4')

                            stop = 1

                  elif g == 3:
                    # MP4 FPS
                    if (h == 1 and event.button == 1) or event.button == 4:
                        mp4_fps +=1
                        mp4_fps = min(mp4_fps,100)
                    else:
                        mp4_fps -=1
                        mp4_fps = max(mp4_fps,5)
                    text(0,3,3,1,1,str(mp4_fps),14,7)
                    save_config = 1

                  elif g == 4:
                    # mp4_annoTATE MP4
                    if h == 0 and event.button == 1:
                        mp4_anno -= 1
                        mp4_anno = max(mp4_anno,0)
                    else:
                        mp4_anno += 1
                        mp4_anno = min(mp4_anno,1)
                    if mp4_anno == 1:
                        text(0,4,3,1,1,"Yes",14,7)
                    else:
                        text(0,4,3,1,1,"No",14,7)
                        
                  elif g == 5:
                    #move MP4 to usb
                    menu_timer  = time.monotonic()
                    if os.path.exists('mylist.txt'):
                        os.remove('mylist.txt')
                    Mideos = glob.glob(h_user + '/Videos/*.mp4')
                    Jpegs = glob.glob(h_user + '/Videos/*.jpg')
                    USB_Files  = []
                    USB_Files  = (os.listdir(m_user))
                    if len(USB_Files) > 0 and frames > 0:
                        pause_thread = True
                        if not os.path.exists(m_user + "/'" + USB_Files[0] + "'/Videos/") :
                            os.system('mkdir ' + m_user + "/'" + USB_Files[0] + "'/Videos/")
                        text(0,5,3,0,1,"MOVING",14,7)
                        text(0,5,3,1,1,"MP4s",14,7)
                        Videos = glob.glob(h_user + '/Videos/*.mp4')
                        Videos.sort()
                        for xx in range(0,len(Videos)):
                            movi = Videos[xx].split("/")
                            if os.path.exists(m_user + "/" + USB_Files[0] + "/Videos/" + movi[4]):
                                os.remove(m_user + "/" + USB_Files[0] + "/Videos/" + movi[4])
                            shutil.copy(Videos[xx],m_user + "/" + USB_Files[0] + "/Videos/")
                            if os.path.exists(Videos[xx][:-4] + ".jpg"):
                                shutil.copy(Videos[xx][:-4] + ".jpg",m_user + "/" + USB_Files[0] + "/Pictures/")
                            if os.path.exists(m_user + "/" + USB_Files[0] + "/Videos/" + movi[4]):
                                os.remove(Videos[xx])
                                if Videos[xx][len(Videos[xx]) - 5:] == "f.mp4":
                                    if os.path.exists(Videos[xx][:-5] + ".jpg"):
                                        os.remove(Videos[xx][:-5] + ".jpg")
                                else:
                                    if os.path.exists(Videos[xx][:-4] + ".jpg"):
                                        os.remove(Videos[xx][:-4] + ".jpg")
                        Videos = glob.glob(h_user + '/Videos/*.mp4')
                        Jpegs = glob.glob(h_user + '/Videos/*.jpg')
                        for xx in range(0,len(Jpegs)):
                            os.remove(Jpegs[xx])
                        frames = len(Videos)
                        text(0,5,0,0,1,"MOVE MP4s",14,7)
                        text(0,5,0,1,1,"to USB",14,7)
                    pause_thread = False
                    main_menu()
                    
                  elif g == 6 and show == 1 and frames + ram_frames > 0 and (frames > 0 or ram_frames > 0) and event.button == 3:
                    # DELETE A VIDEO
                    menu_timer  = time.monotonic()
                    try:
                      Videos = glob.glob(h_user + '/Videos/2???????????.mp4')
                      frames = len(Videos)
                      Rideos = glob.glob('/run/shm/2???????????.mp4')
                      Rideos.sort()
                      ram_frames = len(Rideos)
                      for x in range(0,len(Rideos)):
                         Videos.append(Rideos[x])
                      Videos.sort()
                      Jpegs = glob.glob(h_user + "/" + '/Videos/2*.jpg')
                      Rpegs = glob.glob('/run/shm/2*.jpg')
                      for x in range(0,len(Rpegs)):
                         Jpegs.append(Rpegs[x])
                      Jpegs.sort()
                      fontObj = pygame.font.Font(None, 70)
                      msgSurfaceObj = fontObj.render("DELETING....", False, (255,0,0))
                      msgRectobj = msgSurfaceObj.get_rect()
                      msgRectobj.topleft = (10,100)
                      windowSurfaceObj.blit(msgSurfaceObj, msgRectobj)
                      pygame.display.update()
                      os.remove(Jpegs[q])
                      os.remove(Jpegs[q][:-4] + ".mp4")
                    except:
                        pass
                    Videos = glob.glob(h_user + '/Videos/2???????????.mp4')
                    frames = len(Videos)
                    Rideos = glob.glob('/run/shm/2???????????.mp4')
                    Rideos.sort()
                    for x in range(0,len(Rideos)):
                         Videos.append(Rideos[x])
                    Videos.sort()
                    ram_frames = len(Rideos)
                    if q > len(Videos)-1:
                        q -=1
                    if len(Videos) > 0:
                      try:
                        image = pygame.image.load(Videos[q][:-4] + ".jpg")
                        cropped = pygame.transform.scale(image, (pre_width,pre_height))
                        windowSurfaceObj.blit(cropped, (0, 0))
                        fontObj = pygame.font.Font(None, 25)
                        msgSurfaceObj = fontObj.render(str(Videos[q]), False, (255,255,0))
                        msgRectobj = msgSurfaceObj.get_rect()
                        msgRectobj.topleft = (10,10)
                        windowSurfaceObj.blit(msgSurfaceObj, msgRectobj)
                        msgSurfaceObj = fontObj.render((str(q+1) + "/" + str(ram_frames + frames)), False, (255,0,0))
                        msgRectobj = msgSurfaceObj.get_rect()
                        msgRectobj.topleft = (10,35)
                        windowSurfaceObj.blit(msgSurfaceObj, msgRectobj)
                        pygame.display.update()
                      except:
                          pass
                    else:
                        show = 0
                        main_menu()
                        q = 0
                        of = 0
                        ram_frames = 0
                        frames = 0
                        snaps = 0
                         
                    if ram_frames + frames > 0 and menu == 4:
                        text(0,1,3,1,1,str(q+1) + " / " + str(ram_frames + frames),14,7)
                    elif menu == 4:
                        text(0,1,3,1,1," ",14,7)
                    vf = str(ram_frames) + " - " + str(frames)
                    pygame.draw.rect(windowSurfaceObj,(0,0,0),Rect(0,cheight,scr_width-bw,scr_height))
                    oldimg = []
                    time.sleep(0.5)
                        
                  elif g == 7:
                    # DELETE ALL VIDEOS
                    menu_timer  = time.monotonic()
                    text(0,3,3,1,1," ",14,7)
                    if event.button == 3:
                        fontObj = pygame.font.Font(None, 70)
                        msgSurfaceObj = fontObj.render("DELETING....", False, (255,0,0))
                        msgRectobj = msgSurfaceObj.get_rect()
                        msgRectobj.topleft = (10,100)
                        windowSurfaceObj.blit(msgSurfaceObj, msgRectobj)
                        pygame.display.update()
                        try:
                            Rpegs = glob.glob('/run/shm/2*.jpg')
                            for xx in range(0,len(Rpegs )):
                                os.remove(Rpegs[xx])
                            Rideos = glob.glob('/run/shm/2???????????.mp4')
                            for xx in range(0,len(Rideos)):
                                os.remove(Rideos[xx])
                            ram_frames = 0
                            Jpegs = glob.glob(h_user + '/Videos/2*.jpg')
                            for xx in range(0,len(Jpegs)):
                                os.remove(Jpegs[xx])
                            Videos = glob.glob(h_user + '/Videos/2???????????.mp4')
                            for xx in range(0,len(Videos)):
                                os.remove(Videos[xx])
                            frames = 0
                            vf = str(ram_frames) + " - " + str(frames)
                        except:
                             pass
                        text(0,1,3,1,1," ",14,7)
                        menu = -1
                        Capture = old_cap
                        main_menu()
                        pygame.draw.rect(windowSurfaceObj,(0,0,0),Rect(0,cheight,scr_width-bw,scr_height))
                        show = 0
                        oldimg = []
                    
                  elif g == 8 and ( frames > 0 or ram_frames > 0):
                    # SHOW ALL STILLS
                    menu_timer  = time.monotonic()
                    text(0,8,2,0,1,"STOP",14,7)
                    text(0,8,2,1,1,"     ",14,7)
                    st = 0
                    nq = 0
                    while st == 0:
                        for q in range (0,len(Jpegs)):
                            for event in pygame.event.get():
                                if (event.type == MOUSEBUTTONUP):
                                    mousex, mousey = event.pos
                                    if mousex > cwidth:
                                        buttonx = int(mousey/bh)
                                        nq = q
                                        if buttonx == 8:
                                            st = 1
                            
                            if os.path.getsize(Jpegs[q]) > 0 and st == 0:
                                text(0,1,3,1,1,str(q+1) + " / " + str(ram_frames + frames),14,7)
                                if len(Jpegs) > 0:
                                    image = pygame.image.load(Jpegs[q])
                                    cropped = pygame.transform.scale(image, (pre_width,pre_height))
                                    windowSurfaceObj.blit(cropped, (0, 0))
                                    fontObj = pygame.font.Font(None, 25)
                                    msgSurfaceObj = fontObj.render(str(Jpegs[q]), False, (255,0,0))
                                    msgRectobj = msgSurfaceObj.get_rect()
                                    msgRectobj.topleft = (10,10)
                                    windowSurfaceObj.blit(msgSurfaceObj, msgRectobj)
                                    msgSurfaceObj = fontObj.render((str(q+1) + "/" + str(ram_frames + frames) ), False, (255,0,0))
                                    msgRectobj = msgSurfaceObj.get_rect()
                                    msgRectobj.topleft = (10,35)
                                    windowSurfaceObj.blit(msgSurfaceObj, msgRectobj)
                                    pygame.display.update()
                                    time.sleep(0.5)
                    text(0,8,2,0,1,"SHOW ALL",14,7)
                    text(0,8,2,1,1,"Stills",14,7)
                    q = nq - 1

                  elif g == 9 and show == 1:
                   # MAKE FULL MP4
                    menu_timer  = time.monotonic()
                    if os.path.exists('mylist.txt'):
                        os.remove('mylist.txt')
                    Videos = glob.glob(h_user + '/Videos/2???????????.mp4')
                    Rideos = glob.glob('/run/shm/2???????????.mp4')
                    for x in range(0,len(Rideos)):
                        Videos.append(Rideos[x])
                    Videos.sort()
                    if len(Videos) > 0:
                        pause_thread = True
                        if use_gpio == 1 and fan_ctrl == 1:
                            led_fan.value = 1
                        frame = 0
                        text(0,9,3,0,1,"MAKING",14,7)
                        text(0,9,3,1,1,"FULL MP4",14,7)
                        pygame.display.update()
                        if os.path.exists('mylist.txt'):
                            os.remove('mylist.txt')
                        for w in range(0,len(Videos)):
                            if Videos[w][len(Videos[w]) - 5:] != "f.mp4":
                                txt = "file " + Videos[w]
                                with open('mylist.txt', 'a') as f:
                                    f.write(txt + "\n")
                                if os.path.exists(h_user + '/Videos/' + Videos[w] + ".jpg"):
                                    image = pygame.image.load( h_user + '/Videos/' + Videos[w] + ".jpg")
                                elif os.path.exists('/run/shm/' + Videos[w] + ".jpg"):
                                    image = pygame.image.load('/run/shm/' + Videos[w] + ".jpg")

                                imageo = pygame.transform.scale(image, (pre_width,pre_height))
                                windowSurfaceObj.blit(imageo, (0, 0))
                                fontObj = pygame.font.Font(None, 25)
                                msgSurfaceObj = fontObj.render(str(Videos[w] + " " + str(w+1) + "/" + str(len(Videos))), False, (255,0,0))
                                msgRectobj = msgSurfaceObj.get_rect()
                                msgRectobj.topleft = (0,10)
                                windowSurfaceObj.blit(msgSurfaceObj, msgRectobj)
                                text(0,1,3,1,1,str(w+1) + " / " + str(ram_frames + frames),14,7)
                                pygame.display.update()
                                nam = Videos[0].split("/")
                                outfile = vid_dir + str(nam[len(nam)-1])[:-4] + "f.mp4"
                        if not os.path.exists(outfile):
                            os.system('ffmpeg -f concat -safe 0 -i mylist.txt -c copy ' + outfile)
                            # delete individual MP4s leaving the FULL MP4 only.
                            # read mylist.txt file
                            txtconfig = []
                            with open('mylist.txt', "r") as file:
                                line = file.readline()
                                line2 = line.split(" ")
                                while line:
                                    txtconfig.append(line2[1].strip())
                                    line = file.readline()
                                    line2 = line.split(" ")
                            for x in range(0,len(txtconfig)):
                                if os.path.exists(txtconfig[x] ) and txtconfig[x][len(txtconfig[x]) - 5:] != "f.mp4":
                                    os.remove(txtconfig[x] )
                            #os.remove('mylist.txt')
                            txtvids = []
                            #move MP4 to usb
                            USB_Files  = []
                            USB_Files  = (os.listdir(m_user))
                            if len(USB_Files) > 0:
                                if not os.path.exists(m_user + "/'" + USB_Files[0] + "'/Videos/") :
                                    os.system('mkdir ' + m_user + "/'" + USB_Files[0] + "'/Videos/")
                                text(0,8,3,0,1,"MOVING",14,7)
                                text(0,8,3,1,1,"MP4s",14,7)
                                Videos = glob.glob(h_user + '/Videos/*.mp4')
                                Videos.sort()
                                for xx in range(0,len(Videos)):
                                    movi = Videos[xx].split("/")
                                    if os.path.exists(m_user + "/" + USB_Files[0] + "/Videos/" + movi[4]):
                                        os.remove(m_user + "/" + USB_Files[0] + "/Videos/" + movi[4])
                                    shutil.copy(Videos[xx],m_user + "/" + USB_Files[0] + "/Videos/")
                                    if os.path.exists(m_user + "/" + USB_Files[0] + "/Videos/" + movi[4]):
                                         os.remove(Videos[xx])
                                         if Videos[xx][len(Videos[xx]) - 5:] == "f.mp4":
                                             if os.path.exists(Videos[xx][:-5] + ".jpg"):
                                                 os.remove(Videos[xx][:-5] + ".jpg")
                                         else:
                                             if os.path.exists(Videos[xx][:-4] + ".jpg"):
                                                 os.remove(Videos[xx][:-4] + ".jpg")
                                Videos = glob.glob(h_user + '/Videos/*.mp4')
                                frames = len(Videos)
                                text(0,8,0,0,1,"MOVE MP4s",14,7)
                                text(0,8,0,1,1,"to USB",14,7)
                       
                        Videos = glob.glob(h_user + '/Videos/2???????????.mp4')
                        USB_Files  = (os.listdir(m_user))
                        Videos.sort()
                        w = 0
                        text(0,7,2,0,1,"MAKE FULL",14,7)
                        text(0,7,2,1,1,"MP4",14,7)
                        text(0,1,3,1,1,str(q+1) + " / " + str(ram_frames + frames),14,7)
                        USB_Files  = (os.listdir(m_user))
                        if len(USB_Files) > 0:
                            usedusb = os.statvfs(m_user + "/" + USB_Files[0] + "/")
                            USB_storage = ((1 - (usedusb.f_bavail / usedusb.f_blocks)) * 100)
                        if len(USB_Files) > 0 and len(Videos) > 0:
                            text(0,8,2,0,1,"MOVE MP4s",14,7)
                            text(0,8,2,1,1,"to USB " + str(int(USB_storage))+"%",14,7)
                        else:
                            text(0,8,0,0,1,"MOVE MP4s",14,7)
                            text(0,8,0,1,1,"to USB",14,7)
                        pygame.display.update()
                        Capture = old_cap
                        pause_thread = False
                        main_menu()
                        show = 0
                        if use_gpio == 1 and fan_ctrl == 1:
                             led_fan.value = dc
                    
# MENU 5 ====================================================================================================
                elif menu == 5:             
                  if g == 1:
                    # AUTO TIME
                    if (h == 0 and event.button == 1) or event.button == 5:
                        auto_time -=1
                        auto_time = max(auto_time,0)
                    else:
                        auto_time += 1
                        auto_time = min(auto_time,200)
                    if auto_time > 0:
                        text(0,1,3,1,1,str(auto_time),14,7)
                    else:
                        text(0,1,3,1,1,"OFF",14,7)
                    save_config = 1
                    
                  elif g == 2:
                    # RAM LIMIT
                    if (h == 0 and event.button == 1) or event.button == 5:
                        ram_limit -=10
                        ram_limit = max(ram_limit,10)
                    else:
                        ram_limit += 10
                        ram_limit = min(ram_limit,int(sfreeram) - 100)
                    text(0,2,3,1,1,str(int(ram_limit)),14,7)
                    save_config = 1

                  elif g == 3:
                    # SD LIMIT
                    if (h == 0 and event.button == 1) or event.button == 5:
                        SD_limit -=1
                        SD_limit = max(SD_limit,10)
                    else:
                        SD_limit += 1
                        SD_limit = min(SD_limit,99)
                    text(0,3,3,1,1,str(int(SD_limit)),14,7)
                    save_config = 1

                  elif g == 4:
                    # SD DELETE
                    if (h == 0 and event.button == 1) or event.button == 5:
                        SD_F_Act -=1
                        SD_F_Act = max(SD_F_Act,0)
                    else:
                        SD_F_Act += 1
                        SD_F_Act = min(SD_F_Act,2)
                    if SD_F_Act == 0:
                        text(0,4,3,1,1,"STOP",14,7)
                    elif SD_F_Act == 1:
                        text(0,4,3,1,1,"DEL OLD",14,7)
                    else:
                        text(0,4,3,1,1,"To USB",14,7)
                    save_config = 1
                    
                  elif g == 5 and use_gpio == 1 and fan_ctrl == 1:
                    # FAN TIME
                    if (h == 0 and event.button == 1) or event.button == 5:
                        check_time -=1
                        check_time = max(check_time,2)
                    else:
                        check_time += 1
                        check_time = min(check_time,60)
                    text(0,5,3,1,1,str(check_time),14,7)
                    save_config = 1
                    
                  elif g == 6 and use_gpio == 1 and fan_ctrl == 1:
                    # FAN LOW
                    if (h == 0 and event.button == 1) or event.button == 5:
                        fan_low -=1
                        fan_low = max(fan_low,30)
                    else:
                        fan_low += 1
                        fan_low = min(fan_low,fan_high - 1)
                    text(0,6,3,1,1,str(fan_low),14,7)
                    save_config = 1

                  elif g == 7 and use_gpio == 1 and fan_ctrl == 1:
                    # FAN HIGH
                    if (h == 0 and event.button == 1) or event.button == 5:
                        fan_high -=1
                        fan_high = max(fan_high,fan_low + 1)
                    else:
                        fan_high +=1
                        fan_high = min(fan_high,80)
                    text(0,7,3,1,1,str(fan_high),14,7)
                    save_config = 1
                    
                  elif g == 8 and use_gpio == 1:
                    # EXT Trigger
                    ES +=1
                    if ES > 2:
                        ES = 0
                    if ES == 0:
                        text(0,8,3,1,1,"OFF",14,7)
                    elif ES == 1:
                        text(0,8,3,1,1,"Short",14,7)
                    else:
                        text(0,8,3,1,1,"Long",14,7)
                    save_config = 1

                  elif g == 9:
                    # SHUTDOWN HOUR
                    if h == 1:
                        sd_hour +=1
                        if sd_hour > 23:
                            sd_hour = 0
                    if h == 0:
                        sd_hour -=1
                        if sd_hour  < 0:
                            sd_hour = 23
                    text(0,9,1,0,1,"Shutdown Hour",14,7)
                    text(0,9,3,1,1,str(sd_hour) + ":00",14,7)
                    start_up = time.monotonic()
                    save_config = 1
                    
# MENU 6 ====================================================================================================
                elif menu == 6:    
                  if g == 0:
                    # FPS1
                    if (h == 1 and event.button == 1) or event.button == 4:
                        fps1 +=1
                        fps1 = min(fps1,120)
                    else:
                        fps1 -=1
                        fps1 = max(fps1,5)
                    picam2.set_controls({"FrameRate": fps1})
                    text(0,0,3,1,1,str(fps1),14,7)
                    save_config = 1
                    
                  elif g == 1:
                    # MODE1
                    if h == 1 :
                        mode1 +=1
                        mode1 = min(mode1,3)
                    else:
                        mode1 -=1
                        mode1 = max(mode1,0)
                    if mode1 == 0:
                        picam2.set_controls({"AeEnable": False})
                        picam2.set_controls({"ExposureTime": sspeed1})
                        if shutters[speed1] < 0:
                            text(0,2,3,1,1,"1/" + str(abs(shutters[speed1])),14,7)
                        else:
                            text(0,2,3,1,1,str(shutters[speed1]),14,7)
                        picam2.set_controls({"AnalogueGain": gain1})
                    else:
                        picam2.set_controls({"AeEnable": True})
                        if shutters[speed1] < 0:
                           text(0,2,0,1,1,"1/" + str(abs(shutters[speed1])),14,7)
                        else:
                           text(0,2,0,1,1,str(shutters[speed1]),14,7)
                        if mode1 == 1:
                            picam2.set_controls({"AeExposureMode": controls.AeExposureModeEnum.Normal})
                        if mode1 == 2:
                            picam2.set_controls({"AeExposureMode": controls.AeExposureModeEnum.Short})
                        if mode1 == 3:
                            picam2.set_controls({"AeExposureMode": controls.AeExposureModeEnum.Long})
                        picam2.set_controls({"AnalogueGain": gain1})
                    text(0,1,3,1,1,modes[mode1],14,7)
                    save_config = 1
                    
                  elif g == 2:
                    # Shutter Speed1
                    if (h == 1 and event.button == 1) or event.button == 4:
                        speed1 +=1
                        speed1 = min(speed1,len(shutters)-1)
                    else:
                        speed1 -=1
                        speed1 = max(speed1,0)
                    shutter1 = shutters[speed1]
                    if shutter1 < 0:
                        shutter1 = abs(1/shutter1)
                    sspeed1 = int(shutter1 * 1000000)
                    if (shutter1 * 1000000) - int(shutter1 * 1000000) > 0.5:
                        sspeed1 +=1
                    fps1 = int(1/(sspeed1/1000000))
                    fps1 = max(fps1,1)
                    fps1 = min(fps1,fps2)
                    if mode1 == 0:
                        picam2.set_controls({"FrameRate": fps1})
                        picam2.set_controls({"ExposureTime": sspeed1})
                    if mode1 == 0:
                        if shutters[speed1] < 0:
                            text(0,2,3,1,1,"1/" + str(abs(shutters[speed1])),14,7)
                        else:
                            text(0,2,3,1,1,str(shutters[speed1]),14,7)
                    else:
                        if shutters[speed1] < 0:
                            text(0,2,0,1,1,"1/" + str(abs(shutters[speed1])),14,7)
                        else:
                            text(0,2,0,1,1,str(shutters[speed1]),14,7)
                    save_config = 1
                    
                  elif g == 3:
                    # GAIN1
                    if (h == 1 and event.button == 1) or event.button == 4:
                        gain1 +=1
                        gain1 = min(gain1,max_gain)
                    else:
                        gain1 -=1
                        gain1 = max(gain1,0)
                    picam2.set_controls({"AnalogueGain": gain1})
                    if gain1 > 0:
                        text(0,3,3,1,1,str(gain1),14,7)
                    else:
                        text(0,3,3,1,1,"Auto",14,7)
                    save_config = 1
                    
                  elif g == 4:
                    # BRIGHTNESS1
                    if (h == 1 and event.button == 1) or event.button == 4:
                        brightness1 +=1
                        brightness1 = min(brightness1,20)
                    else:
                        brightness1 -=1
                        brightness1 = max(brightness1,0)
                    picam2.set_controls({"Brightness": brightness1/10})
                    text(0,4,3,1,1,str(brightness1),14,7)
                    save_config = 1
                    
                  elif g == 5:
                    # CONTRAST1
                    if (h == 1 and event.button == 1) or event.button == 4:
                        contrast1 +=1
                        contrast1 = min(contrast1,20)
                    else:
                        contrast1 -=1
                        contrast1 = max(contrast1,0)
                    picam2.set_controls({"Contrast": contrast1/10})
                    text(0,5,3,1,1,str(contrast1),14,7)
                    save_config = 1

                  elif g == 6:
                    # EV1
                    if (h == 1 and event.button == 1) or event.button == 4:
                        ev1 +=1
                        ev1 = min(ev1,20)
                    else:
                        ev1 -=1
                        ev1 = max(ev1,-20)
                    picam2.set_controls({"ExposureValue": ev1/10})
                    text(0,6,5,0,1,"eV",14,7)
                    text(0,6,3,1,1,str(ev1),14,7)
                    save_config = 1
                    
                  elif g == 7:
                    # Metering1
                    if h == 1:
                        meter1 +=1
                        meter1 = min(meter1,len(meters)-1)
                    else:
                        meter1 -=1
                        meter1 = max(meter1,0)
                    if meter1 == 0:
                        picam2.set_controls({"AeMeteringMode": controls.AeMeteringModeEnum.CentreWeighted})
                    elif meter1 == 1:
                        picam2.set_controls({"AeMeteringMode": controls.AeMeteringModeEnum.Spot})
                    elif meter1 == 2:
                        picam2.set_controls({"AeMeteringMode": controls.AeMeteringModeEnum.Matrix})
                    text(0,7,3,1,1,str(meters[meter1]),14,7)
                    save_config = 1

                  elif g == 8:
                    # SHARPNESS1
                    if(h == 1 and event.button == 1) or event.button == 4:
                        sharpness1 +=1
                        sharpness1 = min(sharpness1,16)
                    else:
                        sharpness1 -=1
                        sharpness1 = max(sharpness1,0)
                    picam2.set_controls({"Sharpness": sharpness1})
                    text(0,8,3,1,1,str(sharpness1),14,7)
                    save_config = 1
                
                  elif g == 9 and Pi_Cam != 11:
                    # SATURATION1
                    if (h == 1 and event.button == 1) or event.button == 4:
                        saturation1 +=1
                        saturation1 = min(saturation1,32)
                    else:
                        saturation1 -=1
                        saturation1 = max(saturation1,0)
                    picam2.set_controls({"Saturation": saturation1/10})
                    text(0,9,3,1,1,str(saturation1),14,7)
                    save_config = 1
                    
# MENU 7 ====================================================================================================
                elif menu == 7:
                  if g == 0:
                    # IR FILTER
                    if (h == 1 and event.button == 1) or event.button == 4:
                        IRF1 +=1
                        IRF1 = min(IRF1,len(IR_filters)-1)
                    else:
                        IRF1 -=1
                        IRF1 = max(IRF1,0)
                    text(0,0,3,1,1,IR_filters[IRF1],14,7)
                    if IRF1 == 2:
                        IRF_on1 = 0
                        led_sw_ir1.off()
                        led_ir_light.on()
                        text(0,0,2,0,1,"IR Filter",14,7)
                    elif IRF1 == 3:
                        IRF_on1 = 1
                        led_sw_ir1.on()
                        if IRF_on == 1:
                            led_ir_light.off()
                        text(0,0,1,0,1,"IR Filter",14,7)
                    if IRF1 == 0:
                        suntimes()
                    if synced == 1 and IRF1 == 0:
                        if ir_on_mins1 > 9:
                            text(0,1,2,1,1,str(ir_on_hour1) + ":" + str(ir_on_mins1),14,7)
                        else:
                            text(0,1,2,1,1,str(ir_on_hour1) + ":0" + str(ir_on_mins1),14,7)
                    elif IRF1 == 0:
                        if ir_on_mins1 > 9:
                            text(0,1,0,1,1,str(ir_on_hour1) + ":" + str(ir_on_mins1),14,7)
                        else:
                            text(0,1,0,1,1,str(ir_on_hour1) + ":0" + str(ir_on_mins1),14,7)
                    if synced == 1 and IRF1 == 0:                
                        if ir_of_mins1 > 9:
                            text(0,2,2,1,1,str(ir_of_hour1) + ":" + str(ir_of_mins1),14,7)
                        else:
                            text(0,2,2,1,1,str(ir_of_hour1) + ":0" + str(ir_of_mins1),14,7)
                    elif IRF1 == 0:
                        if ir_of_mins1 > 9:
                            text(0,2,0,1,1,str(ir_of_hour1) + ":" + str(ir_of_mins1),14,7)
                        else:
                            text(0,2,0,1,1,str(ir_of_hour1) + ":0" + str(ir_of_mins1),14,7)
                    save_config = 1
                    
                  if g == 1 and IRF1 == 1:
                    # SWITCH IR1 FILTER ON TIME
                    if h == 1 and event.button == 3:
                        ir_on_hour1 +=1
                        if ir_on_hour1 > 23:
                            ir_on_hour1 = 0

                    elif h == 0 and event.button == 3:
                        ir_on_hour1 -=1
                        if ir_on_hour1 < 0:
                            ir_on_hour1 = 23
                            
                    elif h == 1:
                        ir_on_mins1 +=1
                        if ir_on_mins1 > 59:
                            ir_on_mins1 = 0
                            ir_on_hour1 += 1
                            if ir_on_hour1 > 23:
                                ir_on_hour1 = 0
                    elif h == 0:
                        ir_on_mins1 -=1
                        if ir_on_mins1  < 0:
                            ir_on_hour1 -= 1
                            ir_on_mins1 = 59
                            if ir_on_hour1 < 0:
                                ir_on_hour1 = 23
                    if ir_on_mins1 > 9:
                        text(0,1,3,1,1,str(ir_on_hour1) + ":" + str(ir_on_mins1),14,7)
                    else:
                        text(0,1,3,1,1,str(ir_on_hour1) + ":0" + str(ir_on_mins1),14,7)
                    ir_on_time1 = (ir_on_hour1 * 60) + ir_on_mins1
                    ir_of_time1 = (ir_of_hour1 * 60) + ir_of_mins1
                    if ir_on_time1 >= ir_of_time1:
                        ir_of_hour1 = ir_on_hour1
                        ir_of_mins1 = ir_on_mins1 + 1
                        if ir_of_mins1 > 59:
                            ir_of_mins1 = 0
                            ir_of_hour1 += 1
                            if ir_of_hour1 > 23:
                                ir_of_hour1 = 0
                        if ir_of_mins1 > 9:
                            text(0,2,3,1,1,str(ir_of_hour1) + ":" + str(ir_of_mins1),14,7)
                        else:
                            text(0,2,3,1,1,str(ir_of_hour1) + ":0" + str(ir_of_mins1),14,7)
                    ir_of_time1 = (ir_of_hour1 * 60) + ir_of_mins1
                    save_config = 1

                  elif g == 2 and IRF1 == 1:
                    # SWITCH IR1 FILTER OFF TIME
                    if h == 1 and event.button == 3:
                        ir_of_hour1 +=1
                        if ir_of_hour1 > 23:
                            ir_of_hour1 = 0

                    elif h == 0 and event.button == 3:
                        ir_of_hour1 -=1
                        if ir_of_hour1 < 0:
                            ir_of_hour1 = 23
                            
                    elif h == 1:
                        ir_of_mins1 +=1
                        if ir_of_mins1 > 59:
                            ir_of_mins1 = 0
                            ir_of_hour1 += 1
                            if ir_of_hour1 > 23:
                                ir_of_hour1 = 0
                    elif h == 0:
                        ir_of_mins1 -=1
                        if ir_of_mins1  < 0:
                            ir_of_hour1 -= 1
                            ir_of_mins1 = 59
                            if ir_of_hour1 < 0:
                                ir_of_hour1 = 23
                    if ir_of_mins1 > 9:
                        text(0,2,3,1,1,str(ir_of_hour1) + ":" + str(ir_of_mins1),14,7)
                    else:
                        text(0,2,3,1,1,str(ir_of_hour1) + ":0" + str(ir_of_mins1),14,7)
                    ir_on_time1 = (ir_on_hour1 * 60) + ir_on_mins1
                    ir_of_time1 = (ir_of_hour1 * 60) + ir_of_mins1
                    if ir_of_time1 <= ir_on_time1:
                        ir_on_hour1 = ir_of_hour1
                        ir_on_mins1 = ir_of_mins1 - 1
                        if ir_on_mins1  < 0:
                            ir_on_hour1 -= 1
                            ir_on_mins1 = 59
                            if ir_on_hour1 < 0:
                                ir_on_hour1 = 23
                        if ir_on_mins1 > 9:
                            text(0,1,3,1,1,str(ir_on_hour1) + ":" + str(ir_on_mins1),14,7)
                        else:
                            text(0,1,3,1,1,str(ir_on_hour1) + ":0" + str(ir_on_mins1),14,7)
                      
                    ir_on_time = (ir_on_hour1 * 60) + ir_on_mins1
                    save_config = 1

                  # g == 3 USED FOR FOCUS VALUE
                    
                  elif g == 4 and (Pi_Cam == 3 or Pi_Cam == 8 or Pi_Cam == 5 or Pi_Cam == 6):
                    # camera1 focus mode
                    if (h == 0 and event.button == 1) or event.button == 5:
                        AF_f_mode1 -=1
                        AF_f_mode1 = max(AF_f_mode1,0)
                    else:
                        AF_f_mode1 +=1
                        AF_f_mode1 = min(AF_f_mode1,2)
                    if AF_f_mode1 == 0:
                        AF_f_spot = 0
                        fxx = 0
                        fxy = 0
                        fxz = 1
                        picam2.set_controls({"AfMode": controls.AfModeEnum.Manual, "AfMetering" : controls.AfMeteringEnum.Windows,  "AfWindows" : [(int(vid_width* .33),int(vid_height*.33),int(vid_width * .66),int(vid_height*.66))]})
                    elif AF_f_mode1 == 1:
                        AF_f_spot = 0
                        fxx = 0
                        fxy = 0
                        fxz = 1
                        picam2.set_controls({"AfMode": controls.AfModeEnum.Auto, "AfMetering" : controls.AfMeteringEnum.Windows,  "AfWindows" : [(int(vid_width* .33),int(vid_height*.33),int(vid_width * .66),int(vid_height*.66))]})
                        picam2.set_controls({"AfTrigger": controls.AfTriggerEnum.Start})
                    elif AF_f_mode1 == 2:
                        AF_f_spot = 0
                        fxx = 0
                        fxy = 0
                        fxz = 1
                        picam2.set_controls( {"AfMode" : controls.AfModeEnum.Continuous, "AfMetering" : controls.AfMeteringEnum.Windows,  "AfWindows" : [(int(vid_width* .33),int(vid_height*.33),int(vid_width * .66),int(vid_height*.66))] } )
                        picam2.set_controls({"AfTrigger": controls.AfTriggerEnum.Start})
                    text(0,4,3,1,1,AF_f_modes[AF_f_mode1],14,7)
                    if AF_f_mode1 == 0:
                        picam2.set_controls({"LensPosition": AF_focus1})
                        text(0,1,2,0,1,"Focus Manual",14,7)
                        if Pi_Cam == 3:
                            if AF_focus == 0:
                                AF_focus = 0.01
                            fd = 1/(AF_focus1)
                            text(0,5,3,1,1,str(fd)[0:5] + "m",14,7)
                        else:
                            text(0,5,3,1,1,str(int(101-(AF_focus1 * 10))),14,7)
                    else:
                        text(0,5,3,0,1," ",14,7)
                        text(0,5,3,1,1," ",14,7)
                    fxx = 0
                    fxy = 0
                    fxz = 1
                    if Pi_Cam == 5 or Pi_Cam == 6:
                        fcount = 0
                    save_config = 1

                  elif g == 5 and AF_f_mode1 == 0 and (Pi_Cam == 3 or Pi_Cam == 8 or Pi_Cam == 5 or Pi_Cam == 6):
                    # Camera1 focus manual
                    menu_timer  = time.monotonic()
                    if gv < bh/3:
                        mp = 1 - hp
                        AF_focus1 = int((mp * 8.9) + 1)
                    else:
                        if (h == 0 and event.button == 1) or event.button == 5:
                            AF_focus1 -= .1
                        else:
                            AF_focus1 += .1
                    AF_focus1 = max(AF_focus1,0)
                    AF_focus1 = min(AF_focus1,10)
                    picam2.set_controls({"LensPosition": AF_focus1})
                    if AF_focus1 == 0:
                        text(0,1,3,1,1,"Inf",14,7)
                    else:
                        if Pi_Cam == 3:
                            fd = 1/(AF_focus1)
                            text(0,5,3,1,1,str(fd)[0:5] + "m",14,7)
                        else:
                            text(0,5,3,1,1,str(int(101-(AF_focus1 * 10))),14,7)
                                 
                  elif g == 6 and Pi_Cam != 11:
                    # AWB1 setting
                    if (h == 1 and event.button == 1) or event.button == 4:
                        awb1 +=1
                        awb1 = min(awb1,len(awbs)-1)
                    else:
                        awb1 -=1
                        awb1 = max(awb1,0)
                    if awb1 == 0 and Pi_Cam != 11:
                        picam2.set_controls({"AwbEnable": True,"AwbMode": controls.AwbModeEnum.Auto})
                    elif awb1 == 1 and Pi_Cam != 11:
                        picam2.set_controls({"AwbEnable": True,"AwbMode": controls.AwbModeEnum.Tungsten})
                    elif awb1 == 2 and Pi_Cam != 11:
                        picam2.set_controls({"AwbEnable": True,"AwbMode": controls.AwbModeEnum.Fluorescent})
                    elif awb1 == 3 and Pi_Cam != 11:
                        picam2.set_controls({"AwbEnable": True,"AwbMode": controls.AwbModeEnum.Indoor})
                    elif awb1 == 4 and Pi_Cam != 11:
                        picam2.set_controls({"AwbEnable": True,"AwbMode": controls.AwbModeEnum.Daylight})
                    elif awb1 == 5 and Pi_Cam != 11:
                        picam2.set_controls({"AwbEnable": True,"AwbMode": controls.AwbModeEnum.Cloudy})
                    elif awb1 == 6 and Pi_Cam != 11:
                        picam2.set_controls({"AwbEnable": True,"AwbMode": controls.AwbModeEnum.Custom})
                        cg = (red1,blue1)
                        picam2.set_controls({"AwbEnable": False,"ColourGains": cg})
                    text(0,6,3,1,1,str(awbs[awb1]),14,7)
                    if awb1 == 6:
                        text(0,7,3,1,1,str(red1)[0:3],14,7)
                        text(0,8,3,1,1,str(blue1)[0:3],14,7)
                    else:
                        text(0,7,0,1,1,str(red1)[0:3],14,7)
                        text(0,8,0,1,1,str(blue1)[0:3],14,7)
                    save_config = 1
                    
                  elif g == 7 and awb1 == 6 and Pi_Cam != 11:
                    # RED1
                    if h == 0 or event.button == 5:
                        red1 -=0.1
                        red1 = max(red1,0.1)
                    else:
                        red1 +=0.1
                        red1 = min(red1,8)
                    cg = (red1,blue1)
                    picam2.set_controls({"ColourGains": cg})
                    text(0,7,3,1,1,str(red1)[0:3],14,7)
                    save_config = 1
                    
                  elif g == 8 and awb1 == 6 and Pi_Cam != 11:
                    # BLUE1
                    if h == 0 or event.button == 5:
                        blue1 -=0.1
                        blue1 = max(blue1,0.1)
                    else:
                        blue1 +=0.1
                        blue1 = min(blue1,8)
                    cg = (red1,blue1)
                    picam2.set_controls({"ColourGains": cg})
                    text(0,8,3,1,1,str(blue1)[0:3],14,7)
                    save_config = 1
                   
                  elif g == 9:
                    # DENOISE1
                    if (h == 1 and event.button == 1) or event.button == 4:
                        denoise1 +=1
                        denoise1 = min(denoise1,2)
                    else:
                        denoise1 -=1
                        denoise1 = max(denoise1,0)
                    if denoise1 == 0:
                        picam2.set_controls({"NoiseReductionMode": controls.draft.NoiseReductionModeEnum.Off})
                    elif denoise1 == 1:
                        picam2.set_controls({"NoiseReductionMode": controls.draft.NoiseReductionModeEnum.Fast})
                    elif denoise1 == 2:
                        picam2.set_controls({"NoiseReductionMode": controls.draft.NoiseReductionModeEnum.HighQuality})

                    text(0,9,3,1,1,str(denoises[denoise1]),14,7)
                    save_config = 1
                        
            # save config if changed
            if save_config == 1:
                config[0]  = h_crop
                config[1]  = threshold
                config[2]  = fps
                config[3]  = mode
                config[4]  = speed
                config[5]  = gain
                config[6]  = brightness
                config[7]  = contrast
                config[8]  = SD_limit
                config[9]  = preview
                config[10] = awb
                config[11] = detection
                config[12] = int(red*10)
                config[13] = int(blue*10)
                config[14] = interval
                config[15] = v_crop
                config[16] = v_length
                config[17] = ev
                config[18] = meter
                config[19] = ES
                config[20] = a
                config[21] = b
                config[22] = sharpness
                config[23] = saturation
                config[24] = denoise
                config[25] = fan_low
                config[26] = fan_high
                config[27] = det_high
                config[28] = quality
                config[29] = check_time
                config[30] = sd_hour
                config[31] = vformat
                config[32] = threshold2
                config[33] = col_filter
                config[34] = nr
                config[35] = pre_frames
                config[36] = auto_time
                config[37] = ram_limit
                config[38] = mp4_fps
                config[39] = mp4_anno
                config[40] = SD_F_Act
                config[41] = dspeed
                config[42] = IRF
                config[43] = camera
                config[44] = mode1
                config[45] = speed1
                config[46] = gain1 
                config[47] = brightness1 
                config[48] = contrast1
                config[49] = awb1 
                config[50] = int(red1*10)
                config[51] = int(blue1*10)
                config[52] = meter1 
                config[53] = ev1 
                config[54] = denoise1 
                config[55] = quality1
                config[56] = sharpness1
                config[57] = saturation1
                config[58] = fps1 
                config[59] = AF_f_mode1 
                config[60] = int(AF_focus1)
                config[61] = AF_f_mode 
                config[62] = int(AF_focus)
                config[63] = IRF_on
                config[64] = on_hour
                config[65] = of_hour
                config[66] = on_mins
                config[67] = of_mins
                config[68] = ir_on_hour
                config[69] = ir_of_hour
                config[70] = ir_on_mins
                config[71] = ir_of_mins
                config[72] = camera_sw
                config[73] = AF_f_spot
                config[74] = AF_f_spot1
                config[75] = ir_on_hour1
                config[76] = ir_of_hour1
                config[77] = ir_on_mins1
                config[78] = ir_of_mins1
                config[79] = IRF1
                config[80] = IRF_on1

              
                with open(config_file, 'w') as f:
                    for item in config:
                        f.write("%s\n" % item)
                        
       



            





                  





                      

