#!/usr/bin/env python3
import time
import cv2
import numpy as np
import pygame
from pygame.locals import *
from PIL import Image
import os, subprocess, glob
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

version = "0.04"

# set screen size
scr_width  = 800
scr_height = 480

# set preview size
pre_width  = 640
pre_height = 480

# use GPIO for external camera triggers and optional FAN.
# DISABLE Pi FAN CONTROL in Preferences > Performance to GPIO 14 !!
use_gpio = 1

# ext camera trigger output gpios (if use_gpio = 1)
s_focus  = 16
s_trig   = 12

# ext trigger input gpios (if use_gpio = 1)
e_trig1   = 21
e_trig2   = 20

# fan ctrl gpio (if use_gpio = 1) This is not the Pi5 active cooler !!
# DISABLE Pi FAN CONTROL in Preferences > Performance to GPIO 14 !!
fan      = 14
fan_ctrl = 1  # 0 for OFF. 
   

# set default config parameters
v_crop        = 120     # size of vertical detection window *
h_crop        = 120     # size of horizontal detection window *
threshold     = 20      # minm change in pixel luminance *
threshold2    = 255     # maxm change in pixel luminance *
detection     = 10      # % of pixels detected to trigger, in % *
det_high      = 100     # max % of pixels detected to trigger, in %  *
fps           = 25      # set camera fps *
mp4_fps       = 25      # set MP4 fps *
mode          = 1       # set camera mode *
speed         = 80000   # set manual shutter speed in mS x 1000 *
gain          = 0       # set gain , 0 = AUTO *
brightness    = 0       # set camera brightness *
contrast      = 7       # set camera contrast *
Capture       = 1       # 0 = off, 1 = ON *
preview       = 0       # show detected changed pixels *
noframe       = 0       # set to 1 for no window frame
awb           = 0       # auto white balance *
red           = 1.5     # red balance *
blue          = 1.5     # blue balance *
meter         = 0       # metering *
ev            = 0       # eV *
interval      = 0       # wait between capturing Pictures *
v_length      = 10000   # video length in mS *
ES            = 1       # trigger external camera, 0 = OFF, 1 = SHORT, 2 = LONG *
denoise       = 0       # denoise level *
quality       = 90      # video quality *
sharpness     = 14      # sharpness *
saturation    = 10      # saturation *
SD_limit      = 90      # max SD card filled in % before copy to USB if available or STOP *
auto_save     = 1       # set to 1 to automatically copy to SD card
auto_time     = 10      # time after which auto save actioned, 0 = OFF
ram_limit     = 150     # MBytes, copy from RAM to SD card when reached *
fan_time      = 10      # fan sampling time in seconds *
fan_low       = 65      # fan OFF below this, 25% to 100% pwm above this *
fan_high      = 78      # fan 100% pwm above this *
sd_hour       = 0       # Shutdown Hour, 1 - 23, 0 will NOT SHUTDOWN *
vformat       = 0       # SEE VWIDTHS/VHEIGHTS *
col_filter    = 3       # 3 = FULL, SEE COL_FILTERS *
nr            = 0       # Noise reduction *
pre_frames    = 2       # seconds *
scientific    = 0       # scientific for HQ camera * 
v3_f_mode     = 1       # v3 camera focus mode *
v3_focus      = 0       # v3 camera manual focus default , 0 = infinity*
dspeed        = 100     # detection speed 1-100, 1 = slowest *
anno          = 1       # annotate MP4s with date and time , 1 = yes, 0 = no *
SD_F_Act      = 0       # Action on SD FULL, 0 = STOP, 1 = DELETE OLDEST VIDEO, 2 = COPY TO USB (if fitted) *
m_alpha       = 130     # MASK ALPHA *

# * adjustable whilst running

# initialise parameters
camera        = 0
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
config_file   = "PiVideoconfig102.txt"
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

# Camera max exposure (Note v1 is currently 1 second not the raspistill 6 seconds)
# whatever value set it MUST be in shutters list !!
max_v1      = 1
max_v2      = 11
max_v3      = 112
max_hq      = 650
max_16mp    = 200
max_64mp    = 435
max_gs      = 15

# apply timestamp to videos
def apply_timestamp(request):
  global anno
  if anno == 1:
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

cameras       = ['Unknown','Pi v1','Pi v2','Pi v3','Pi HQ','Arducam 16MP','Arducam 64MP','Pi GS']
camids        = ['','ov5647','imx219','imx708','imx477','imx519','arduc','imx296']
swidths       = [0,2592,3280,4608,4056,4656,9152,1456]
sheights      = [0,1944,2464,2592,3040,3496,6944,1088]
max_gains     = [64,     255,      40,      64,      88,      64,      64,      64]
max_shutters  = [0,   max_v1, max_v2,   max_v3,  max_hq,max_16mp,max_64mp,  max_gs]
mags          = [64,     255,      40,      64,      88,      64,      64,      64]
modes         = ['manual','normal','short','long']
meters        = ['CentreWeighted','Spot','Matrix']
awbs          = ['auto','tungsten','fluorescent','indoor','daylight','cloudy','custom']
denoises      = ['off','fast','HQ']
col_filters   = ['RED','GREEN','BLUE','FULL']
noise_filters = ['OFF','LOW','HIGH']
v3_f_modes    = ['Manual','Auto','Continuous']

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
    led_s_trig  = LED(s_trig)
    led_s_focus = LED(s_focus)
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
              fan_time,sd_hour,vformat,threshold2,col_filter,nr,pre_frames,auto_time,ram_limit,mp4_fps,anno,SD_F_Act,dspeed]
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
fan_time    = config[29]
sd_hour     = config[30]
vformat     = config[31]
threshold2  = config[32]
col_filter  = config[33]
nr          = config[34]
pre_frames  = config[35]
auto_time   = config[36]
ram_limit   = config[37]
mp4_fps     = config[38]
anno        = config[39]
SD_F_Act    = config[40]
dspeed      = config[41]


bw = int(scr_width/8)
cwidth  = scr_width - bw
cheight = scr_height
old_vf  = vformat
focus = 0

# timelapse interval timer (set Low Threshold = 0 and set interval timer)
if threshold == 0:
    timer10 = time.monotonic()
    if v_length > interval * 1000:
        v_length = (interval - 1) * 1000

def Camera_Version():
  global swidth,sheight,vid_width,vid_height,old_vf,bw,Pi_Cam,cam1,cam2,camera,camids,max_camera,same_cams,max_gain,max_vf,max_vfs,a,b,h_crop,v_crop,h_crop,v_crop,pre_width,pre_height,vformat,pre_height,cwidth,vwidths,vheights,pre_width,scr_width,scr_height
  if os.path.exists('libcams.txt'):
   os.rename('libcams.txt', 'oldlibcams.txt')
  os.system("rpicam-vid --list-cameras >> libcams.txt")
  time.sleep(0.5)
  # read libcams.txt file
  camstxt = []
  with open("libcams.txt", "r") as file:
    line = file.readline()
    while line:
        camstxt.append(line.strip())
        line = file.readline()
  max_camera = 0
  same_cams  = 0
  cam1 = "1"
  cam2 = "2"
  vwidths  = []
  vheights = []
  cwidth = scr_width - bw
  cheight = scr_height
  for x in range(0,len(camstxt)):
    # Determine if both cameras are the same model
    if camstxt[x][0:4] == "0 : ":
        cam1 = camstxt[x][4:10]
    elif camstxt[x][0:4] == "1 : ":
        cam2 = camstxt[x][4:10]
    elif cam1 != "1" and cam2 == "2" and camera == 0:
        forms = camstxt[x].split(" ")
        for q in range(0,len(forms)):
           if "x" in forms[q] and "/" not in forms[q]:
              qwidth,qheight = forms[q].split("x")
              vwidths.append(int(qwidth))
              vheights.append(int(qheight))
    elif cam1 != "1" and cam2 != "2" and camera == 1:
        forms = camstxt[x].split(" ")
        for q in range(0,len(forms)):
           if "x" in forms[q] and "/" not in forms[q]:
              qwidth,qheight = forms[q].split("x")
              vwidths.append(int(qwidth))
              vheights.append(int(qheight))
        
    # Determine MAXIMUM number of cameras available 
    if camstxt[x][0:4] == "3 : " and max_camera < 3:
        max_camera = 3
    elif camstxt[x][0:4] == "2 : " and max_camera < 2:
        max_camera = 2
    elif camstxt[x][0:4] == "1 : " and max_camera < 1:
        max_camera = 1
        
  if max_camera == 1 and cam1 == cam2:
      same_cams = 1
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
  swidth = swidths[Pi_Cam]
  sheight = sheights[Pi_Cam]
  # set video size
  if Pi_Cam == 7:
      vid_width  = 1456
      vid_height = 1088
  else:
      vid_width  = 1920
      vid_height = 1080
  if Pi_Cam == -1:
        print("No Camera Found")
        pygame.display.quit()
        sys.exit()
            
Camera_Version()

print(Pi_Cam,cam1,cam2)

# annotation parameters
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

if os.path.exists('/usr/share/rpicam/ipa/rpi/vc4/imx477_scientific.json') and Pi_Cam == 4:
    scientif = 1
else:
    scientif = 0

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

# determine /dev/v4l-subdevX for Pi v3 and Arducam 16/64MP (Hawkeye) cameras
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

# start circular buffer
lsize = (pre_width, pre_height)
picam2 = Picamera2()
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

# setup camera parameters
if mode == 0:
    picam2.set_controls({"AeEnable": False,"ExposureTime": speed})
else:
    if mode == 1:
         picam2.set_controls({"AeEnable": True,"AeExposureMode": controls.AeExposureModeEnum.Normal})
    elif mode == 2:
         picam2.set_controls({"AeEnable": True,"AeExposureMode": controls.AeExposureModeEnum.Short})
    elif mode == 3:
         picam2.set_controls({"AeEnable": True,"AeExposureMode": controls.AeExposureModeEnum.Long})
time.sleep(1)
if awb == 0:
    picam2.set_controls({"AwbEnable": True,"AwbMode": controls.AwbModeEnum.Auto})
elif awb == 1:
    picam2.set_controls({"AwbEnable": True,"AwbMode": controls.AwbModeEnum.Tungsten})
elif awb == 2:
    picam2.set_controls({"AwbEnable": True,"AwbMode": controls.AwbModeEnum.Fluorescent})
elif awb == 3:
    picam2.set_controls({"AwbEnable": True,"AwbMode": controls.AwbModeEnum.Indoor})
elif awb == 4:
    picam2.set_controls({"AwbEnable": True,"AwbMode": controls.AwbModeEnum.Daylight})
elif awb == 5:
    picam2.set_controls({"AwbEnable": True,"AwbMode": controls.AwbModeEnum.Cloudy})
elif awb == 6:
    picam2.set_controls({"AwbEnable": True,"AwbMode": controls.AwbModeEnum.Custom})
    cg = (red,blue)
    picam2.set_controls({"AwbEnable": False,"ColourGains": cg})
time.sleep(1)
if Pi_Cam == 3:
    if v3_f_mode == 0:
        picam2.set_controls({"AfMode": controls.AfModeEnum.Manual, "AfMetering" : controls.AfMeteringEnum.Windows,  "AfWindows" : [(int(vid_width* .33),int(vid_height*.33),int(vid_width * .66),int(vid_height*.66))]})
    elif v3_f_mode == 1:
        picam2.set_controls({"AfMode": controls.AfModeEnum.Auto, "AfMetering" : controls.AfMeteringEnum.Windows,  "AfWindows" : [(int(vid_width*.33),int(vid_height*.33),int(vid_width * .66),int(vid_height*.66))]})
        picam2.set_controls({"AfTrigger": controls.AfTriggerEnum.Start})
    elif v3_f_mode == 2:
        picam2.set_controls( {"AfMode" : controls.AfModeEnum.Continuous, "AfMetering" : controls.AfMeteringEnum.Windows,  "AfWindows" : [(int(vid_width*.33),int(vid_height*.33),int(vid_width * .66),int(vid_height*.66))] } )
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
picam2.set_controls({"Saturation": saturation/10})
picam2.set_controls({"Sharpness": sharpness})
cg = (red,blue)
picam2.set_controls({"ColourGains": cg})
if denoise == 0:
    picam2.set_controls({"NoiseReductionMode": controls.draft.NoiseReductionModeEnum.Off})
elif denoise == 1:
    picam2.set_controls({"NoiseReductionMode": controls.draft.NoiseReductionModeEnum.Fast})
elif denoise == 2:
    picam2.set_controls({"NoiseReductionMode": controls.draft.NoiseReductionModeEnum.HighQuality})
picam2.set_controls({"FrameRate": fps})

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
os.system("timedatectl >> sync.txt")
# read sync.txt file
try:
    sync = []
    with open("sync.txt", "r") as file:
        line = file.readline()
        while line:
            sync.append(line.strip())
            line = file.readline()
    if sync[4] == "System clock synchronized: yes":
        synced = 1
    else:
        synced = 0
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
   pygame.draw.line(windowSurfaceObj,whiteColor,(bx+1,by),(bx+bw,by))
   pygame.draw.line(windowSurfaceObj,greyColor,(bx+bw-1,by),(bx+bw-1,by+bh))
   pygame.draw.line(windowSurfaceObj,whiteColor,(bx,by),(bx,by+bh-1))
   pygame.draw.line(windowSurfaceObj,dgryColor,(bx+1,by+bh-1),(bx+bw-1,by+bh-1))
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
       pygame.draw.rect(windowSurfaceObj,bColor,Rect(bx+3,by+1,bw-2,int(bh/2)))
       msgRectobj.topleft = (bx + 7, by + 3)
   elif msg == "START - END" or msg == "<<   <    >   >>":
       pygame.draw.rect(windowSurfaceObj,bColor,Rect(bx+int(bw/4),by+int(bh/2),int(bw/1.5),int(bh/2)-1))
       msgRectobj.topleft = (bx+7, by + int(bh/2))
   else:
       pygame.draw.rect(windowSurfaceObj,bColor,Rect(bx+int(bw/4),by+int(bh/2),int(bw/1.5),int(bh/2)-1))
       msgRectobj.topleft = (bx+int(bw/4), by + int(bh/2))
   windowSurfaceObj.blit(msgSurfaceObj, msgRectobj)
   if upd == 1:
      pygame.display.update(bx, by, bw, bh)

def main_menu():
    global ram_frames,frames,menu,sd_hour,pf,vf,synced,Capture,show,zoom,preview,scr_height,cwidth,photos,old_cap,Jpegs
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
    text(0,3,1,0,1,"CAMERA",14,7)
    text(0,3,1,1,1,"Settings 1",14,7)
    text(0,4,1,0,1,"CAMERA",14,7)
    text(0,4,1,1,1,"Settings 2",14,7)
    text(0,5,1,0,1,"CAMERA",14,7)
    text(0,5,1,1,1,"Settings 3",14,7)
    text(0,7,1,0,1,"OTHER",14,7)
    text(0,7,1,1,1,"Settings ",14,7)
    if ((ram_frames > 0 or frames > 0) and menu == -1):
        text(0,6,1,0,1,"SHOW,EDIT or",13,7)
        text(0,6,1,1,1,"DELETE",13,7)
    else:
        text(0,6,0,0,1,"SHOW,EDIT or",13,7)
        text(0,6,0,1,1,"DELETE",13,7)
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
fan_timer = time.monotonic()

# check sd card space
free = (os.statvfs('/'))
SD_storage = ((1 - (free.f_bavail / free.f_blocks)) * 100)
ss = str(int(sfreeram)) + "MB - " + str(int(SD_storage)) + "%"

# get cpu temperature
cpu_temp = str(CPUTemperature()).split("=")
temp = float(str(cpu_temp[1])[:-1])

old_capture = Capture

if awb == 0:
    picam2.set_controls({"AwbEnable": True,"AwbMode": controls.AwbModeEnum.Auto})

while True:
    time.sleep(1/dspeed)
    if Pi == 5 and menu == 4:
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
    elif menu == 4:
        text(0,0,2,0,1,"CPU Temp",14,7)
        text(0,0,3,1,1,str(int(temp)),14,7)
    # fan (NOT Pi5 active cooler) and shutdown ctrl
    if time.monotonic() - fan_timer > fan_time and not encoding:
        if trace == 1:
              print ("Step  FAN TIME")
        try:
            if os.path.exists("sync.txt"):
                os.rename('sync.txt', 'oldsync.txt')
            os.system("timedatectl >> sync.txt")
            # read sync.txt file
            sync = []
            with open("sync.txt", "r") as file:
                line = file.readline()
                while line:
                    sync.append(line.strip())
                    line = file.readline()
            if sync[4] == "System clock synchronized: yes":
                synced = 1
                if menu == 4:
                    text(0,9,3,1,1,str(sd_hour) + ":00",14,7)
            else:
                synced = 0
                if menu == 4:
                    text(0,9,0,1,1,str(sd_hour)+":00",14,7)
        except:
            pass
        # check current hour
        now = datetime.datetime.now()
        hour = int(now.strftime("%H"))
        # shutdown if shutdown hour reached and clocked synced
        if hour > sd_hour - 1 and sd_hour != 0 and time.monotonic() - start_up > 600 and synced == 1 and not encoding:
            # EXIT and SHUTDOWN
            if trace == 1:
                 print ("Step 13 TIMED EXIT")
            # move any videos to SD Card
            if ram_frames > 0:
                if menu == -1 :
                    button(0,0,1)
                    text(0,0,5,0,1,"CAPTURE",16,0)
                    vf = str(ram_frames) + " - " + str(frames)
                    if Pi == 5 and cam2 != "2":
                        vf = vf + " - " + str(len(photos))
                    text(0,0,3,1,1,vf,14,4)
                Rideos = glob.glob('/run/shm/2???????????.mp4')
                Rideos.sort()
                for xx in range(0,len(Rideos)):
                    shutil.copy(Rideos[xx], h_user + '/Videos/')
                Rpegs = glob.glob('/run/shm/2*.jpg')
                Rpegs.sort()
                for xx in range(0,len(Rpegs)):
                    shutil.copy(Rpegs[xx], h_user + '/Videos/')
            # move h264s to USB if present
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
            pygame.quit()
            time.sleep(5)
            os.system("sudo shutdown -h now")

        # set fan speed
        if fan_ctrl == 1 and not encoding:
            fan_timer = time.monotonic()
            cpu_temp = str(CPUTemperature()).split("=")
            temp = float(str(cpu_temp[1])[:-1])
            dc = ((temp - fan_low)/(fan_high - fan_low))
            dc = max(dc,.25)
            dc = min(dc,1)
            if temp > fan_low and use_gpio == 1:
                led_fan.value = dc
                if menu ==4 :
                    text(0,7,1,0,1,"Fan High  " + str(int(dc*100)) + "%",14,7)
            elif temp < fan_low and use_gpio == 1:
                led_fan.value = 0
                if menu == 4: 
                    text(0,7,2,0,1,"Fan High degC",14,7)
                
        # get RAM free space
        st = os.statvfs("/run/shm/")
        freeram = (st.f_bavail * st.f_frsize)/1100000

    if trace == 1:
        print ("GLOB FILES")
        
    # GET AN IMAGE
    cur = picam2.capture_array("lores")
    img = cv2.cvtColor(cur,cv2.COLOR_YUV420p2BGR)
    image = pygame.surfarray.make_surface(img)
    image = pygame.transform.rotate(image, int(90))
    image = pygame.transform.flip(image,0,1)

    # IF NOT IN SHOW MODE
    if show == 0:
        if col_timer > 0 and time.monotonic() - col_timer > 3:
            col_timer = 0
        if camera == 0 or camera == 1:
          image2 = pygame.surfarray.pixels3d(image)
          # CROP DETECTION AREA
          crop = image2[a-h_crop:a+h_crop,b-v_crop:b+v_crop]
          if trace == 1:
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
            if menu == 0 or menu == 4 or menu == 7 or menu == 1 or menu == 8:
                foc = cv2.Laplacian(gray, cv2.CV_64F).var()
                if menu == 0 or menu == 8:
                    if zoom == 0:
                        text(0,10,6,1,1,str(int(foc)),14,7)
                    else:
                        text(0,10,6,1,1,str(int(foc)),14,0)
                elif menu == 7: 
                    text(0,2,3,1,1,str(int(foc)),14,7)
                    text(0,2,2,0,1,"Focus Value",14,7)
                elif menu == 1: 
                    if zoom == 0:
                        text(0,9,6,1,1,str(int(foc)),14,7)
                    else:
                        text(0,9,6,1,1,str(int(foc)),14,0)
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
            # copy 1 set of video files to sd card if auto_save = 1 or low RAM, after 10 seconds of no activity
            st = os.statvfs("/run/shm/")
            freeram = (st.f_bavail * st.f_frsize)/1100000
            if (ram_frames > 0 and auto_time > 0 and time.monotonic() - last > auto_time and auto_save == 1 and not encoding and menu == -1) or (ram_frames > 0 and freeram < ram_limit and not encoding and menu == -1):
              try:
                if trace == 1:
                    print ("Step 4 AUTO SAVE")
                if menu == -1:
                    text(0,0,5,0,1,"CAPTURE",16,0)
                # read list of existing RAM Video Files
                Videos = glob.glob('/run/shm/2???????????.mp4')
                Videos.sort()
                for xx in range(0,len(Videos)):
                    shutil.move(Videos[xx], h_user + '/Videos/')
                ram_frames -=1
                frames +=1
                # read list of existing RAM Photo Files
                Jpegs = glob.glob('/run/shm/2*.jpg')
                Jpegs.sort()
                for xx in range(0,len(Jpegs)):
                    shutil.move(Jpegs[xx], h_user + '/Videos/')
                vf = str(ram_frames) + " - " + str(frames)
                if Pi == 5 and cam2 != "2":
                    vf = vf + " - " + str(len(photos))
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
                if trace == 1:
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
                        image3 = image
                    ltime = time.time()
                    detect = 1
                    if ES > 0 and use_gpio == 1: # trigger external camera
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
                    pygame.image.save(image3,"/run/shm/" + str(timestamp) + ".jpg")
                    last = time.monotonic()    
                    st = os.statvfs("/run/shm/")
                    freeram = (st.f_bavail * st.f_frsize)/1100000
                    free = (os.statvfs('/'))
                    SD_storage = ((1 - (free.f_bavail / free.f_blocks)) * 100)
                    ss = str(int(freeram)) + " - " + str(int(SD_storage))
                    Jpegs = glob.glob(h_user + "/" + '/Videos/2*.jpg')
                    Rpegs = glob.glob('/run/shm/2*.jpg')
                    for x in range(0,len(Rpegs)):
                         Jpegs.append(Rpegs[x])
                    Jpegs.sort()
                    # if RAM space < RAM Limit
                    if ram_frames > 0 and freeram < ram_limit:
                        if trace == 1:
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
                        if trace == 1:
                            print ("Step 11 READ SD FILES")
                        Videos = glob.glob(h_user + '/Videos/2???????????.mp4')
                        Videos.sort()
                        frames = len(Videos)
                        vf = str(ram_frames) + " - " + str(frames)
                        if menu == 3:
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

                    if ((ram_frames > 0 or frames > 0 or len(photos) > 0)  and menu == -1):
                        text(0,6,1,0,1,"SHOW,EDIT or",13,7)
                        text(0,6,1,1,1,"DELETE",14,7)
                    elif menu == -1:
                        text(0,6,0,0,1,"SHOW,EDIT or",13,7)
                        text(0,6,0,1,1,"DELETE",14,7)
                    if (ram_frames > 0 or frames > 0) and menu == -1:
                        text(0,8,1,0,1,"MAKE",14,7)
                        text(0,8,1,1,1,"MP4",14,7)
                    elif menu == -1:
                        text(0,8,0,0,1,"MAKE",14,7)
                        text(0,8,0,1,1,"MP4",14,7)
                    USB_Files  = []
                    USB_Files  = (os.listdir(m_user))
                    if len(USB_Files) > 0:
                        usedusb = os.statvfs(m_user + "/" + USB_Files[0] + "/")
                        USB_storage = ((1 - (usedusb.f_bavail / usedusb.f_blocks)) * 100)
                    # check SD space for files ,move to usb stick (if available)
                    if SD_storage > SD_limit and len(USB_Files) > 0 and SD_F_Act == 2 and USB_storage < 90:
                        if trace == 1:
                            print ("Step 12 USED SD CARD > LIMIT")
                        os.killpg(p.pid, signal.SIGTERM)
                         
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
                        if trace == 1:
                            print ("Step 12a sd card limit exceeded and no or full USB stick")
                        if SD_F_Act == 0:
                            Capture = 0 # stop
                        else:
                            # remove oldest video from SD card
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
                        if Pi == 5 and cam2 != "2":
                            vf = vf + " - " + str(len(photos))
                        text(0,0,3,1,1,vf,14,2)
                    if menu == -1:
                        button(0,1,3)
                        text(0,1,6,0,1,"RECORD",16,3)
                        text(0,1,6,1,1,ss,12,3)
        # show frame
        gcount +=1
        if gcount > 0:
          gcount = 0
          if zoom == 0:
              cropped = pygame.transform.scale(image, (pre_width,pre_height))
          else:
              cropped = pygame.surfarray.make_surface(crop)
              cropped = pygame.transform.scale(cropped, (pre_width,pre_height))
          windowSurfaceObj.blit(cropped, (0, 0))
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
          if Pi_Cam == 3 and fxz != 1 and zoom == 0 and menu == 7:
            pygame.draw.rect(windowSurfaceObj,(200,0,0),Rect(int(fxx*cwidth),int(fxy*cheight*.75),int(fxz*cwidth),int(fxz*cheight)),1)
          pygame.display.update(0,0,scr_width-bw,scr_height)

        if vidjr != 1:
           oldimg[:] = gray[:]
        vidjr = 0

        if fcount < max_fcount and Pi != 5 and (Pi_Cam == 5 or Pi_Cam == 6) and v3_f_mode == 0:
            Capture = 0
            if menu == -1:
                button(0,0,0)
                text(0,0,0,0,1,"CAPTURE",16,7)
                text(0,0,3,1,1,vf,14,7)
                rep = 0
        elif Pi != 5 and (Pi_Cam == 5 or Pi_Cam == 6) and rep == 0 and v3_f_mode == 0:
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

        # ARDUCAM AF
        if (Pi_Cam == 5 or Pi_Cam == 6) and v3_f_mode == 0 and fcount < max_fcount and Pi != 5:
                foc = cv2.Laplacian(gray, cv2.CV_64F).var()
                if menu == -1:
                    text(0,9,3,0,1,"Focusing...",14,7)
                    text(0,9,3,1,1,str(int(foc)),14,7)
                if foc >= min_foc:
                    ran = 0
                else:
                    focus = random.randint(10,3990)
                    fcount = 1
                    ran = 1
                    old_foc = foc
                if (int(foc) >= int(old_foc) or fcount == 0) and ran == 0:
                    if fcount == 0:
                        if focus < int(2000):
                            focus  += fstep
                        else:
                            focus  -= fstep
                    else:        
                        focus  += fstep
                elif ran == 0:
                    fstep = -fstep
                    focus += fstep
                old_foc = foc
                if focus < 10 or focus > 3990:
                    focus = int(2000)
                    fcount = 0
                os.system("v4l2-ctl -d /dev/v4l-subdev" + str(foc_sub5) + " -c focus_absolute=" + str(focus))
                time.sleep(.5)
                fcount += 1
                
    save_config = 0
    #check for any mouse button presses
    for event in pygame.event.get():
        if (event.type == MOUSEBUTTONUP):
            timer = time.monotonic()
            mousex, mousey = event.pos
            # set crop position
            if mousex < pre_width and zoom == 0 and ((menu != 7 or (Pi_Cam == 3 and v3_f_mode == 1)) or (Pi_Cam == 5 or Pi_Cam == 6)) and event.button != 3:
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
                 
            # set v3 camera autofocus position 
            if mousex < pre_width and zoom == 0 and menu == 7 and Pi_Cam == 3 and v3_f_mode > 0 :
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
                text(0,0,3,1,1,"Spot",14,7)
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
                if g == 0 and menu == -1 :
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

                elif g == 10 and menu == -1 and event.button == 3:
                    # EXIT
                    if trace == 1:
                         print ("Step 13 EXIT")
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
                    pygame.quit()
                     
                elif g == 0 and menu == 0:
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
                    
                elif g == 1 and menu == 0:
                    # Low Detection
                    if (h == 1 and event.button == 1) or event.button == 4:
                        detection +=1
                        detection = min(detection,100)
                    else:
                        detection -=1
                        detection = max(detection,0)
                    text(0,1,3,1,1,str(detection),14,7)
                    save_config = 1
                    
                elif g == 3 and menu == 0:
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

                elif g == 4 and menu == 0:
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

                elif g == 2 and menu == 0:
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
                    
                elif g == 1 and menu == -1:
                    # RECORD
                    record = 1
                    button(0,1,1)
                    text(0,1,3,0,1,"RECORD",16,0)
                    
                elif g == 8 and menu == 4 and use_gpio == 1:
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

                elif g == 9 and menu == 4:
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
                    save_config = 1
                    
                elif g == 9 and (menu == 1 or menu == 8):
                    # ZOOM
                    zoom +=1
                    if zoom == 1:
                        button(0,9,1)
                        text(0,9,1,0,1,"Zoom",14,0)
                        if event.button == 3:
                            preview = 1
                    else:
                        zoom = 0
                        button(0,9,0)
                        text(0,9,2,0,1,"Zoom",14,7)
                        preview = 0

                elif g == 0 and menu == 8:
                    # Photo Timer
                    if (h == 1 and event.button == 1) or event.button == 4:
                        photo_timer +=0.1
                        photo_timer = min(photo_timer,10)
                        text(0,0,3,1,1,str(photo_timer)[0:3],14,7)
                    else:
                        photo_timer -=0.1
                        photo_timer = max(photo_timer,0.3)
                        text(0,0,3,1,1,str(photo_timer)[0:3],14,7)
                    save_config = 1

                elif g == 3 and menu == 7:
                    # ZOOM
                    zoom +=1
                    if zoom == 1:
                        button(0,3,1)
                        text(0,3,1,0,1,"Zoom",14,0)
                        if event.button == 3:
                            preview = 1
                    else:
                        zoom = 0
                        button(0,3,0)
                        text(0,3,2,0,1,"Zoom",14,7)
                        preview = 0
                    
                elif g == 1 and menu == 1:
                    # MODE
                    if h == 1 :
                        mode +=1
                        mode = min(mode,3)
                    else:
                        mode -=1
                    if mode == 0:
                        picam2.set_controls({"AeEnable": False})
                        picam2.set_controls({"ExposureTime": speed})
                        text(0,2,3,1,1,str(int(speed/1000)),14,7)
                    else:
                        picam2.set_controls({"AeEnable": True})
                        text(0,2,0,1,1,str(int(speed/1000)),14,7)
                        if mode == 1:
                            picam2.set_controls({"AeExposureMode": controls.AeExposureModeEnum.Normal})
                        if mode == 2:
                            picam2.set_controls({"AeExposureMode": controls.AeExposureModeEnum.Short})
                        if mode == 3:
                            picam2.set_controls({"AeExposureMode": controls.AeExposureModeEnum.Long})
                    text(0,1,3,1,1,modes[mode],14,7)
                    save_config = 1
                    
                elif g == 2 and menu == 1:
                    # Shutter Speed
                    if (h == 1 and event.button == 1) or event.button == 4:
                        speed +=1000
                        if speed > 50000:
                            speed +=9000
                        speed = min(speed,1000000)
                    else:
                        speed -=1000
                        if speed > 50000:
                            speed -=9000
                        speed = max(speed,1000)
                    fps = int(1/(speed/1000000))
                    fps = max(fps,1)
                    picam2.set_controls({"FrameRate": fps})
                    picam2.set_controls({"ExposureTime": speed})
                    if mode != 0:
                        text(0,2,0,1,1,str(int(speed/1000)),14,7)
                    else:
                        text(0,2,3,1,1,str(int(speed/1000)),14,7)
                    save_config = 1
                    
                elif g == 3 and menu == 1:
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
                    
                elif g == 4 and menu == 1:
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
                    
                elif g == 5 and menu == 1:
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

                elif g == 6 and menu == 1:
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
                    
                elif g == 7 and menu == 1:
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

                elif g == 3 and menu == 2:
                    # PRE FRAMES
                    if h == 1 and event.button == 1:
                        pre_frames +=1
                        pre_frames = min(pre_frames,50)
                    else:
                        pre_frames -=1
                        pre_frames = max(pre_frames,1)
                    text(0,3,0,1,1,str(pre_frames) + " Secs",14,7)
                    picam2.stop_encoder()
                    picam2.stop()
                    encoder.output = CircularOutput(buffersize = pre_frames * fps)
                    picam2.start()
                    picam2.start_encoder(encoder)
                    time.sleep(pre_frames)
                    text(0,3,3,1,1,str(pre_frames) + " Secs",14,7)
                    save_config = 1
                    
                elif g == 7 and menu == 2:
                    # SATURATION
                    if (h == 1 and event.button == 1) or event.button == 4:
                        saturation +=1
                        saturation = min(saturation,32)
                    else:
                        saturation -=1
                        saturation = max(saturation,0)
                    picam2.set_controls({"Saturation": saturation/10})
                    text(0,7,3,1,1,str(saturation),14,7)
                    save_config = 1
                   
                elif g == 9 and menu == 7 and scientif == 1:
                    # SCIENTIFIC
                    if (h == 1 and event.button == 1) or event.button == 4:
                        scientific +=1
                        scientific = min(scientific,1)
                    else:
                        scientific -=1
                        scientific = max(scientific,0)
                    text(0,9,3,1,1,str(scientific),14,7)

                elif g == 2 and menu == 2:
                    # FPS
                    if (h == 1 and event.button == 1) or event.button == 4:
                        fps +=1
                        fps = min(fps,120)
                    else:
                        fps -=1
                        fps = max(fps,5)
                    picam2.set_controls({"FrameRate": fps})
                    text(0,2,3,1,1,str(fps),14,7)
                    text(0,1,3,1,1,str(v_length/1000) + "  (" + str(int(fps*(v_length/1000))) +")",14,7)
                    save_config = 1

                elif g == 0 and menu == 2:
                    # MP4 FPS
                    if (h == 1 and event.button == 1) or event.button == 4:
                        mp4_fps +=1
                        mp4_fps = min(mp4_fps,100)
                    else:
                        mp4_fps -=1
                        mp4_fps = max(mp4_fps,5)
                    text(0,0,3,1,1,str(mp4_fps),14,7)
                    save_config = 1

                elif g == 4 and menu == 2:
                    # AWB setting
                    if (h == 1 and event.button == 1) or event.button == 4:
                        awb +=1
                        awb = min(awb,len(awbs)-1)
                    else:
                        awb -=1
                        awb = max(awb,0)
                    if awb == 0:
                        picam2.set_controls({"AwbEnable": True,"AwbMode": controls.AwbModeEnum.Auto})
                    elif awb == 1:
                        picam2.set_controls({"AwbEnable": True,"AwbMode": controls.AwbModeEnum.Tungsten})
                    elif awb == 2:
                        picam2.set_controls({"AwbEnable": True,"AwbMode": controls.AwbModeEnum.Fluorescent})
                    elif awb == 3:
                        picam2.set_controls({"AwbEnable": True,"AwbMode": controls.AwbModeEnum.Indoor})
                    elif awb == 4:
                        picam2.set_controls({"AwbEnable": True,"AwbMode": controls.AwbModeEnum.Daylight})
                    elif awb == 5:
                        picam2.set_controls({"AwbEnable": True,"AwbMode": controls.AwbModeEnum.Cloudy})
                    elif awb == 6:
                        picam2.set_controls({"AwbEnable": True,"AwbMode": controls.AwbModeEnum.Custom})
                        cg = (red,blue)
                        picam2.set_controls({"AwbEnable": False,"ColourGains": cg})
                    text(0,4,3,1,1,str(awbs[awb]),14,7)
                    if awb == 6:
                        text(0,5,3,1,1,str(red)[0:3],14,7)
                        text(0,6,3,1,1,str(blue)[0:3],14,7)
                    else:
                        text(0,5,0,1,1,str(red)[0:3],14,7)
                        text(0,6,0,1,1,str(blue)[0:3],14,7)
                    save_config = 1
                    
                elif g == 5 and menu == 2 and awb == 6:
                    # RED
                    if h == 0 or event.button == 5:
                        red -=0.1
                        red = max(red,0.1)
                    else:
                        red +=0.1
                        red = min(red,8)
                    cg = (red,blue)
                    picam2.set_controls({"ColourGains": cg})
                    text(0,5,3,1,1,str(red)[0:3],14,7)
                    save_config = 1
                    
                elif g == 6 and menu == 2  and awb == 6:
                    # BLUE
                    if h == 0 or event.button == 5:
                        blue -=0.1
                        blue = max(blue,0.1)
                    else:
                        blue +=0.1
                        blue = min(blue,8)
                    cg = (red,blue)
                    picam2.set_controls({"ColourGains": cg})
                    text(0,6,3,1,1,str(blue)[0:3],14,7)
                    save_config = 1

                elif g == 8 and menu == 1:
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
                   
                elif g == 8 and menu == 2:
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

                    text(0,8,3,1,1,str(denoises[denoise]),14,7)
                    save_config = 1
                    
                elif g == 1 and menu == 3 and show == 1 and (frames > 0 or ram_frames > 0):
                    # SHOW next video
                    if menu == 3:
                        text(0,6,3,1,1,"VIDEO ",14,7)
                        text(0,7,3,1,1,"ALL VIDS ",14,7)
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

                elif g == 6 and menu == 3 and show == 1 and frames + ram_frames > 0 and (frames > 0 or ram_frames > 0) and event.button == 3:
                    # DELETE A VIDEO
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
                         
                    if ram_frames + frames > 0 and menu == 3:
                        text(0,1,3,1,1,str(q+1) + " / " + str(ram_frames + frames),14,7)
                    elif menu == 3:
                        text(0,1,3,1,1," ",14,7)
                    vf = str(ram_frames) + " - " + str(frames)
                    pygame.draw.rect(windowSurfaceObj,(0,0,0),Rect(0,cheight,scr_width-bw,scr_height))
                    oldimg = []
                    time.sleep(0.5)
                        
                elif g == 7 and menu == 3:
                    # DELETE ALL VIDEOS
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

                elif g == 8 and menu == 3 and ( frames > 0 or ram_frames > 0):
                    # SHOW ALL videos
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
                    text(0,8,2,1,1,"Videos",14,7)
                    q = nq - 1
                    
                elif g == 5 and menu == 0:
                    # H CROP
                    if (h == 1 and event.button == 1) or event.button == 4:
                        h_crop +=1
                        h_crop = min(h_crop,180)
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
                    
                elif g == 6 and menu == 0:
                    # V CROP
                    if (h == 1 and event.button == 1) or event.button == 4:
                        v_crop +=1
                        v_crop = min(v_crop,180)
                        if a-h_crop < 1 or b-v_crop < 1 or a+h_crop > cwidth or b+v_crop > int(cwidth/(pre_width/pre_height)):
                            v_crop -=1
                        text(0,6,3,1,1,str(v_crop),14,7)
                    else:
                        v_crop -=1
                        v_crop = max(v_crop,1)
                        text(0,6,3,1,1,str(v_crop),14,7)
                    mask,change = MaskChange()
                    save_config = 1
                    
                elif g == 9 and menu == 2:
                    # INTERVAL
                    if (h == 1 and event.button == 1) or event.button == 4:
                        interval +=1
                        interval = min(interval,180)
                    else:
                        interval -=1
                        interval = max(interval,0)
                    text(0,9,3,1,1,str(interval),14,7)
                    save_config = 1
                    
                elif g == 1 and menu == 2:
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
                    
                elif g == 7 and menu == 0:
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

                elif g == 9 and menu == 0:
                    # NOISE REDUCTION
                    if (h == 0 and event.button == 1) or event.button == 5:
                        nr -=1
                        nr = max(nr,0)
                    else:
                        nr += 1
                        nr = min(nr,2)
                    text(0,9,3,1,1,str(noise_filters[nr]),14,7)
                    save_config = 1

                elif g == 8 and menu == 7 :
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

                elif g == 1 and menu == 4 :
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
                    
                elif g == 2 and menu == 4 :
                    # RAM LIMIT
                    if (h == 0 and event.button == 1) or event.button == 5:
                        ram_limit -=10
                        ram_limit = max(ram_limit,10)
                    else:
                        ram_limit += 10
                        ram_limit = min(ram_limit,int(sfreeram) - 100)
                    text(0,2,3,1,1,str(int(ram_limit)),14,7)
                    save_config = 1

                elif g == 3 and menu == 4 :
                    # SD LIMIT
                    if (h == 0 and event.button == 1) or event.button == 5:
                        SD_limit -=1
                        SD_limit = max(SD_limit,10)
                    else:
                        SD_limit += 1
                        SD_limit = min(SD_limit,99)
                    text(0,3,3,1,1,str(int(SD_limit)),14,7)
                    save_config = 1

                elif g == 4 and menu == 4 :
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
                    
                elif g == 5 and menu == 4 and use_gpio == 1 and fan_ctrl == 1:
                    # FAN TIME
                    if (h == 0 and event.button == 1) or event.button == 5:
                        fan_time -=1
                        fan_time = max(fan_time,2)
                    else:
                        fan_time += 1
                        fan_time = min(fan_time,60)
                    text(0,5,3,1,1,str(fan_time),14,7)
                    save_config = 1
                    
                elif g == 6 and menu == 4 and use_gpio == 1 and fan_ctrl == 1:
                    # FAN LOW
                    if (h == 0 and event.button == 1) or event.button == 5:
                        fan_low -=1
                        fan_low = max(fan_low,30)
                    else:
                        fan_low += 1
                        fan_low = min(fan_low,fan_high - 1)
                    text(0,6,3,1,1,str(fan_low),14,7)
                    save_config = 1

                elif g == 7 and menu == 4 and use_gpio == 1 and fan_ctrl == 1:
                    # FAN HIGH
                    if (h == 0 and event.button == 1) or event.button == 5:
                        fan_high -=1
                        fan_high = max(fan_high,fan_low + 1)
                    else:
                        fan_high +=1
                        fan_high = min(fan_high,80)
                    text(0,7,3,1,1,str(fan_high),14,7)
                    save_config = 1

                elif g == 8 and menu == 0:
                    # DETECTION SPEED
                    if (h == 0 and event.button == 1) or event.button == 5:
                        dspeed -=1
                        dspeed = max(dspeed,1)
                    else:
                        dspeed +=1
                        dspeed = min(dspeed,100)
                    text(0,8,3,1,1,str(dspeed),14,7)
                    save_config = 1

                elif g == 0 and menu == 7 and (Pi_Cam == 3 or Pi_Cam == 5):
                    # v3 camera focus mode
                    if (h == 0 and event.button == 1) or event.button == 5:
                        v3_f_mode -=1
                        v3_f_mode = max(v3_f_mode,0)
                    else:
                        v3_f_mode +=1
                        v3_f_mode = min(v3_f_mode,2)
                    if v3_f_mode == 0:
                        picam2.set_controls({"AfMode": controls.AfModeEnum.Manual, "AfMetering" : controls.AfMeteringEnum.Windows,  "AfWindows" : [(int(vid_width* .33),int(vid_height*.33),int(vid_width * .66),int(vid_height*.66))]})
                    elif v3_f_mode == 1:
                        picam2.set_controls({"AfMode": controls.AfModeEnum.Auto, "AfMetering" : controls.AfMeteringEnum.Windows,  "AfWindows" : [(int(vid_width* .33),int(vid_height*.33),int(vid_width * .66),int(vid_height*.66))]})
                        picam2.set_controls({"AfTrigger": controls.AfTriggerEnum.Start})
                    elif v3_f_mode == 2:
                        picam2.set_controls( {"AfMode" : controls.AfModeEnum.Continuous, "AfMetering" : controls.AfMeteringEnum.Windows,  "AfWindows" : [(int(vid_width* .33),int(vid_height*.33),int(vid_width * .66),int(vid_height*.66))] } )
                        picam2.set_controls({"AfTrigger": controls.AfTriggerEnum.Start})
                    text(0,0,3,1,1,v3_f_modes[v3_f_mode],14,7)
                    if v3_f_mode == 0:
                        picam2.set_controls({"LensPosition": v3_focus})
                        text(0,1,2,0,1,"Focus Manual",14,7)
                        if v3_focus == 0 and Pi_Cam == 3:
                            text(0,1,3,1,1,"inf",14,7)
                        elif (Pi_Cam == 5 or Pi_Cam == 6):
                            text(0,1,3,1,1,str(focus),14,7)
                        else:
                            fd = 1/(v3_focus)
                            text(0,1,3,1,1,str(fd)[0:5] + "m",14,7)
                    else:
                        text(0,1,3,0,1," ",14,7)
                        text(0,1,3,1,1," ",14,7)
                    fxx = 0
                    fxy = 0
                    fxz = 1
                    if Pi_Cam == 5 or Pi_Cam == 6:
                        fcount = 0
                    save_config = 1

                elif g == 1 and menu == 7 and v3_f_mode == 0 and Pi_Cam == 3:
                    # v3 camera focus manual
                    if gv < bh/3:
                        mp = 1 - hp
                        v3_focus = int((mp * 8.9) + 1)
                    else:
                        if (h == 0 and event.button == 1) or event.button == 5:
                            v3_focus -= .1
                        else:
                            v3_focus += .1
                    v3_focus = max(v3_focus,0)
                    v3_focus = min(v3_focus,10)
                    picam2.set_controls({"LensPosition": v3_focus})
                    if v3_focus == 0:
                        text(0,1,3,1,1,"Inf",14,7)
                    else:
                        fd = 1/(v3_focus)
                        text(0,1,3,1,1,str(fd)[0:5] + "m",14,7)

                elif g == 1 and menu == 7 and v3_f_mode == 0 and (Pi_Cam == 5 or Pi_Cam == 6):
                    # Arducam camera focus manual
                    if gv < bh/3:
                        mp = 1 - hp
                        focus = int((mp * 3900) + 100)
                    else:
                        if (h == 0 and event.button == 1) or event.button == 5:
                            focus -= 10
                        else:
                            focus += 10
                    focus = max(focus,100)
                    focus = min(focus,2500)
                    os.system("v4l2-ctl -d /dev/v4l-subdev" + str(foc_sub5) + " -c focus_absolute=" + str(focus))
                    text(0,1,3,1,1,str(focus),14,7)

                elif g == 6 and menu == 7:
                    # ANNOTATE MP4
                    if h == 0 and event.button == 1:
                        anno -= 1
                        anno = max(anno,0)
                    else:
                        anno += 1
                        anno = min(anno,1)
                    if anno == 1:
                        text(0,6,3,1,1,"Yes",14,7)
                    else:
                        text(0,6,3,1,1,"No",14,7)

                elif g == 7 and menu == 7:
                    # MASK ALPHA
                    if (h == 0 and event.button == 1) or event.button == 5:
                        m_alpha -= 10
                        m_alpha = max(m_alpha,0)
                    else:
                        m_alpha += 10
                        m_alpha = min(m_alpha,250)
                    text(0,7,3,1,1,str(m_alpha)[0:4],14,7)
               
                elif g == 9 and menu == 3 and show == 1:
                 # MAKE FULL MP4
                 if os.path.exists('mylist.txt'):
                     os.remove('mylist.txt')
                 Videos = glob.glob(h_user + '/Videos/2???????????.mp4')
                 Rideos = glob.glob('/run/shm/2???????????.mp4')
                 for x in range(0,len(Rideos)):
                     Videos.append(Rideos[x])
                 Videos.sort()    
                 if len(Videos) > 0:
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
                      if os.path.exists(outfile):
                          os.remove(outfile)
                      os.system('ffmpeg -f concat -safe 0 -i mylist.txt -c copy ' + outfile)
                      # delete individual MP4s leaving the FULL MP4 only.
                      # read mylist.txt file
                      txtconfig = []
                      with open('mylist.txt', "r") as file:
                          line = file.readline()
                          line2 = line.split(" ")
                          while line:
                              txtconfig.append(line2[1][0:-6].strip())
                              line = file.readline()
                              line2 = line.split(" ")
                      for x in range(0,len(txtconfig)):
                          if os.path.exists(txtconfig[x] + ".mp4"):
                              os.remove(txtconfig[x] + ".mp4")
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
                  main_menu()
                  show = 0
                  if use_gpio == 1 and fan_ctrl == 1:
                      led_fan.value = dc

                elif menu == 3 and g == 5:
                    #move MP4 to usb
                    if os.path.exists('mylist.txt'):
                        os.remove('mylist.txt')
                    Mideos = glob.glob(h_user + '/Videos/*.mp4')
                    USB_Files  = []
                    USB_Files  = (os.listdir(m_user))
                    if len(USB_Files) > 0 and frames > 0:
                        if not os.path.exists(m_user + "/'" + USB_Files[0] + "'/Videos/") :
                            os.system('mkdir ' + m_user + "/'" + USB_Files[0] + "'/Videos/")
                        text(0,5,3,0,1,"MOVING",14,7)
                        text(0,5,3,1,1,"MP4s",14,7)
                        Videos = glob.glob( h_user + '/Videos/*.mp4')
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
                        Jpegs = glob.glob(h_user + '/Videos/*.jpg')
                        for xx in range(0,len(Jpegs)):
                            os.remove(Jpegs[xx])
                        frames = len(Videos)
                        text(0,5,0,0,1,"MOVE MP4s",14,7)
                        text(0,5,0,1,1,"to USB",14,7)
                    main_menu()
                  
                elif (menu == -1 and g > 1) or (menu != -1 and g == 10) or (menu == 3 and g == 9):
                    # MENUS
                    # check for usb_stick
                    USB_Files  = []
                    USB_Files  = (os.listdir(m_user + "/"))
                    if show == 1 and menu != 3:
                        show = 0
                    if g == 2 and event.button != 3:
                        menu = 0
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

                    if g == 2 and event.button == 3:
                        # PREVIEW
                        preview +=1
                        if preview > 1:
                            preview = 0
                            text(0,2,1,1,1,"Settings",14,7)
                            
                    if g == 3:
                        menu = 1
                        old_capture = Capture
                        Capture = 0
                        for d in range(0,10):
                            button(0,d,0)
                        text(0,7,5,0,1,"Meter",14,7)
                        text(0,7,3,1,1,meters[meter],14,7)
                        text(0,1,5,0,1,"Mode",14,7)
                        text(0,1,3,1,1,modes[mode],14,7)
                        text(0,2,5,0,1,"Shutter mS",14,7)
                        if mode == 0:
                            text(0,2,3,1,1,str(int(speed/1000)),14,7)
                        else:
                            text(0,2,0,1,1,str(int(speed/1000)),14,7)
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
                        if zoom == 0:
                            button(0,9,0)
                            text(0,9,2,0,1,"Zoom",14,7)
                        else:
                            button(0,9,1)
                            text(0,9,1,0,1,"Zoom",14,0)
                        if scientif == 1:
                            text(0,9,5,0,1,"Scientific",14,7)
                            text(0,9,3,1,1,str(scientific),14,7)
                        text(0,10,1,0,1,"MAIN MENU",14,7)
                      

                    if g == 4:
                        menu = 2
                        for d in range(0,10):
                            button(0,d,0)
                        text(0,0,5,0,1,"MP4 fps",14,7)
                        text(0,0,3,1,1,str(mp4_fps),14,7)
                        text(0,4,5,0,1,"AWB",14,7)
                        text(0,4,3,1,1,str(awbs[awb]),14,7)
                        text(0,2,5,0,1,"fps",14,7)
                        text(0,2,3,1,1,str(fps),14,7)
                        text(0,5,5,0,1,"Red",14,7)
                        text(0,6,5,0,1,"Blue",14,7)
                        if awb == 6:
                            text(0,5,3,1,1,str(red)[0:3],14,7)
                            text(0,6,3,1,1,str(blue)[0:3],14,7)
                        else:
                            text(0,5,0,1,1,str(red)[0:3],14,7)
                            text(0,6,0,1,1,str(blue)[0:3],14,7)
                        text(0,7,5,0,1,"Saturation",14,7)
                        text(0,7,3,1,1,str(saturation),14,7)
                        text(0,3,2,0,1,"V Pre-Frames",14,7)
                        text(0,3,3,1,1,str(pre_frames) + " Secs",14,7)
                        text(0,8,5,0,1,"Denoise",14,7)
                        text(0,8,3,1,1,str(denoises[denoise]),14,7)
                        text(0,9,2,0,1,"Interval S",14,7)
                        text(0,9,3,1,1,str(interval),14,7)
                        text(0,1,2,0,1,"V Length S (F)",14,7)
                        text(0,1,3,1,1,str(v_length/1000) + "  (" + str(int(fps*(v_length/1000))) +")",14,7)
                        text(0,10,1,0,1,"MAIN MENU",14,7)
                        
                    if g == 6 and (ram_frames > 0 or frames > 0 or len(photos) > 0):
                        menu = 3
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
                        text(0,1,2,0,1,"Video",14,7)
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
                        text(0,8,2,1,1,"Videos",14,7)
                        text(0,9,2,0,1,"MAKE FULL",14,7)
                        text(0,9,2,1,1,"MP4",14,7)
                        text(0,10,1,0,1,"MAIN MENU",14,7)
                        
                    if g == 5:
                        menu = 7
                        old_capture = Capture
                        Capture = 0
                        for d in range(0,10):
                            button(0,d,0)
                        if zoom == 0:
                            button(0,3,0)
                            text(0,3,2,0,1,"Zoom",14,7)
                        else:
                            button(0,3,1)
                            text(0,3,1,0,1,"Zoom",14,0)
                        text(0,6,2,0,1,"Annotate MP4",14,7)
                        if anno == 0:
                            text(0,6,3,1,1,"No",14,7)
                        else:
                            text(0,6,3,1,1,"Yes",14,7)
                        text(0,7,2,0,1,"MASK Alpha",14,7)
                        text(0,7,3,1,1,str(m_alpha),14,7)
                        text(0,8,3,0,1,"CLEAR Mask",14,7)
                        text(0,8,3,1,1," 0       1  ",14,7)
                        if scientif == 1 and Pi_Cam == 4:
                            text(0,9,5,0,1,"Scientific",14,7)
                            text(0,9,3,1,1,str(scientific),14,7)
                        if Pi_Cam == 3 or Pi_Cam == 5:
                            text(0,0,2,0,1,"Focus",14,7)
                            if v3_f_mode == 1:
                                text(0,1,2,0,1,"Focus Manual",14,7)
                                if v3_focus == 0 and Pi_Cam == 3:
                                    text(0,1,3,1,1,"inf",14,7)
                                elif (Pi_Cam == 5 or Pi_Cam == 6):
                                    text(0,1,3,1,1,str(focus),14,7)
                                else:
                                    fd = 1/(v3_focus/100)
                                    text(0,1,3,1,1,str(fd)[0:5] + "m",14,7)
                            text(0,0,3,1,1,v3_f_modes[v3_f_mode],14,7)
                            if fxz != 1:
                                text(0,0,3,1,1,"Spot",14,7)
                        text(0,10,1,0,1,"MAIN MENU",14,7)
                        
                    if g == 7:
                        menu = 4
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
                                text(0,5,3,1,1,str(fan_time),14,7)
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
                        

                    if g == 10 and menu != -1:
                        sframe = -1
                        eframe = -1
                        if os.path.exists('mylist.txt'):
                            os.remove('mylist.txt')
                        txtvids = []
                        if menu == 8 and cam2 != "2":
                            restart2 = 1
                            camera = 0
                             
                            pygame.draw.rect(windowSurfaceObj,(0,0,0),Rect(0,0,scr_width-bw,scr_height))
                            pygame.display.update(0,0,scr_width-bw,scr_height)
                            time.sleep(1)
                        main_menu()
                        
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
                config[29] = fan_time
                config[30] = sd_hour
                config[31] = vformat
                config[32] = threshold2
                config[33] = col_filter
                config[34] = nr
                config[35] = pre_frames
                config[36] = auto_time
                config[37] = ram_limit
                config[38] = mp4_fps
                config[39] = anno
                config[40] = SD_F_Act
                config[41] = dspeed
              
                with open(config_file, 'w') as f:
                    for item in config:
                        f.write("%s\n" % item)
                        
       



            





                  





                      

