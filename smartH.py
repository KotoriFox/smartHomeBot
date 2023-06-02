import discord
import asyncio
import threading
import re
import datetime
import logging

from w1thermsensor import W1ThermSensor
import RPi.GPIO as GPIO
import time
import board
import adafruit_dht

from os.path import exists

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt2
import matplotlib.dates as mdates

import urllib.request

from readData import collector

from pcf8575 import PCF8575

def full_stack():
    import traceback, sys
    exc = sys.exc_info()[0]
    stack = traceback.extract_stack()[:-1]  # last one would be full_stack()
    if exc is not None:  # i.e. an exception is present
        del stack[-1]       # remove call of full_stack, the printed exception
                            # will contain the caught exception caller instead
    trc = 'Traceback (most recent call last):\n'
    stackstr = trc + ''.join(traceback.format_list(stack))
    if exc is not None:
         stackstr += '  ' + traceback.format_exc().lstrip(trc)
    return stackstr

def logInit():
    logging.basicConfig(filename = "smart.log", filemode = 'a',
                        format = '%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
                        datefmt = '%H:%M%S',
                        level=logging.DEBUG)
    logging.info("smart house app started")

class i2cRelay:
    def __init__(self):
        self.pcf = PCF8575(1,0x20)
        self.i = 0
        self.a = [0 for i in range(8)]+[1 for i in range(8)]
        self.pcf.port = self.a
    def blinkTemp(self):
        if self.i == 4:
            self.i = 0
        idx = self.i*2 + 8
        self.a[idx] = False
        self.a[idx+1] = False
        self.pcf.port = self.a
        time.sleep(5)
        self.a[idx] = True
        self.a[idx+1] = True
        self.pcf.port = self.a
        self.i += 1
    def blink(self, line):
        idx = line*2 + 8
        self.a[idx] = False
        self.a[idx+1] = False
        self.pcf.port = self.a
        time.sleep(10)
        self.a[idx] = True
        self.a[idx+1] = True
        self.pcf.port = self.a
        time.sleep(10)
    def set(self, lane, v):
        idx=lane*2+8
        self.a[idx] = v
        self.a[idx+1] = v
        self.pcf.port = self.a
    def relaySet(self, idx, v):
        self.a[idx] = not v
        self.pcf.port = self.a
    def relayGet(self, idx):
        return not self.a[idx]
    def lanes(self, l):
        v=[(i,l[i]) for i in range(4)]
        for i in v:
            self.set(i[0],i[1])
        time.sleep(5)

class urlRelay:
  def _run(self,t):
     req = urllib.request.Request(t, headers={'User-Agent' : 'Mozilla/5.0'})
     return str(urllib.request.urlopen(req).read())
  def __init__(self, ip):
     self.url = "http://"+ip
     self.uon = "/RELAY=ON"
     self.uoff= "/RELAY=OFF"
  def test(self):
    x = self._run(self.url)
    w = x.find(" is now: ")
    if x[w+9:w+11] == 'ON':
      return 1
    return 0
  def on(self):
    self._run(self.url+self.uon)
  def off(self):
    self._run(self.url+self.uoff)


class plotter():
    def plot(self, name, his):
        fig = plt2.figure()
        plt = fig.add_subplot(111)
        #ax = plt2.gca()
        formatter = mdates.DateFormatter("%H:%M")
        plt.xaxis.set_major_formatter(formatter)
        locator = mdates.HourLocator()
        plt.xaxis.set_major_locator(locator)
        for i in his:
            plt.plot(his[i][0], his[i][1], label=i)
        plt.legend()
        plt.grid()
        plt2.gcf().autofmt_xdate()
        fig.savefig(name)
        plt2.close(fig)
        

class Heating(threading.Thread):
    def _readDHT(self):
      try:
        dhtDevice = adafruit_dht.DHT22(board.D18, use_pulseio=False)
        temperature_c = dhtDevice.temperature
        humidity = dhtDevice.humidity
        return (temperature_c, humidity)
      except:
        return None
    def C2F(self, temperature_c):
        return temperature_c * (9 / 5) + 32
    def readDHT(self):
        a = self._readDHT()
        while not a:
            a = self.readDHT()
        temperature_c, humidity = a
        return (temperature_c, humidity)
    def normalize(self, name, temp):
        #return temp
        temp = temp + self.tuning[name]
        temp = temp *1000
        temp = round(temp)
        temp = temp / 1000.0
        return temp
    def readLane(self, idx, tmpT):
        readcc = 0
        tries = 0
        while readcc < self.lanesCnt[idx]:
            tries += 1
            readcc = 0
            print ("reading lane ", idx, " expected ", self.lanesCnt[idx])
            try:
                for i in self.onewire[idx]:
                  t = i.get_temperature()
                  t = self.normalize(i.id, t)
                  n = self.nameConv(i.id)
                  condi = 1
                  if i.id in tmpT:
                    condi = (abs(t-tmpT[i.id]) < 20)
                  if condi:
                    self.newTemp[i.id] = t
                    readcc += 1
                    if i.id == self.heaterKey:
                      self.valid = 1
                    print (n, " Temp = ", t)
                  else:
                    print (n, " Temp invalid = ", t)
            except:
                pass
            if tries > 20:
                l = [1,1,1,1]
                l[idx] = 0
                self.r.i2c.lanes(l)
                time.sleep(0.02)
                self.r.i2c.lanes([1,1,1,1])
                tries = 0
    def readTemp(self):
      self.valid = 0
      self.time = datetime.datetime.now()
      tmpT = self.temp
      self.newTemp = {}
      for i in range(4):
          print("Read Lane ", i)
          self.readLane(i,tmpT)
      self.temp = self.newTemp
      return 0
    def configSync(self):
        import os
        config = 'smart_config'
        _conf = {}
        if os.path.isfile(config) == False:
            _conf["onoff"] = [25,27]
            _conf["noti"] = [857687460566007849]
            with open(config,'w') as f:
                f.write(str(_conf))
        with open(config,'r') as f:
            vv = f.read()
            vv = eval(vv)
            for i in vv:
              self._conf[i] = vv[i]
    def saveConfig(self):
        config = 'smart_config'
        with open(config,'w') as f:
            f.write(str(self._conf))
    def heat(self):
        try:
          import smartRemote
          import importlib
          importlib.reload(smartRemote)
          smartRemote.heatLogic(self)
        except:
          s = full_stack()
          print(s)
          for i in s.split('\n'):
            self.log.error(i)
    def solarCalc(self):
        try:
          import smartSolar
          import importlib
          importlib.reload(smartSolar)
          smartSolar.heatLogic(self)
        except:
          s = full_stack()
          print(s)
          for i in s.split('\n'):
            self.log.error(i)
    def add2Hist(self, key, val):
        if not key in self.history:
          self.history[key] = [[],[]]
          #tt = str(self.time.hour)+':'+str(self.time.minute)
        while len(self.history[key][0]) >= self.depth:
          #overflow remove 1st element
          self.history[key][0].pop(0)
          self.history[key][1].pop(0)
        self.history[key][0].append(self.time)
        self.history[key][1].append(val)
    def save2Hist(self):
        for i in self.temp:
            j = self.namesMap[i]
            self.add2Hist(j,self.temp[i])
        d = self.coll.getData()
        j = "Сонце"
        self.add2Hist(j, d["PV1 Power"]+d["PV2 Power"])
        j = "Споживання"
        self.add2Hist(j, d["Total Load Power"])
        config = 'temp_hist'
        with open(config,'w') as f:
            f.write(str(self.history))
    def loadHist(self):
        import os
        config = 'temp_hist'
        if os.path.isfile(config):
            with open(config,'r') as f:
               vv = f.read()
               self.history = eval(vv)
    def recalcTune(self, hist):
        dif = {}
        for i in hist:
            if not i in dif:
                dif[i] = []
            for j in range(len(hist[i])):
              dif[i].append(hist[i][j]-hist['Base'][j])
        print(dif)
        for i in dif:
            s = 0
            for j in dif[i]:
                s+=j
            s = s / len(dif[i])
            self.tuning[i] -= s
        print(self.tuning)
    def nameConv(self,name) :
        if name in self.namesMap:
            return self.namesMap[name]
        return name
    def printTemp(self):
        i1 = 0
        for i in self.temp:
            n = self.nameConv(i)
            print (i1, ") ", n, " = ", self.temp[i])
            i1+=1
    def getTemp(self):
        res = []
        #i1 = 0
        for i in self.temp:
            n = self.nameConv(i)
            s = str(n)+" : "+str(self.temp[i])+' C'
            res.append(s)
        res.sort()
        return self.humidity,res
    def init1Wire(self):
        # enable all lanes
        self.r.i2c.lanes([1,1,1,1])
        total = sum(self.lanesCnt.values())
        cc = 0
        tries = 0
        while cc < total:
          time.sleep(1)
          tries +=1
          try:
            cc = len(W1ThermSensor.get_available_sensors())
            print("%d vs %d" % (cc,total))
          except:
            cc = 0
          if tries > 20:
            self.r.i2c.lanes([0,0,0,0])
            time.sleep(0.1)
            self.r.i2c.lanes([1,1,1,1])
            time.sleep(5)
            tries = 0
        self.onewire = {}
        for i in W1ThermSensor.get_available_sensors():
           lane = self.lanesMap[i.id]
           if not (lane in self.onewire):
               self.onewire[lane] = []
           self.onewire[lane].append(i)
        print(self.onewire)

    def verifyReset(self):
        for lane in range(4):
            if self.lanesCnt[lane] == 0:
                continue
            if self.lanesReset[lane] > 0:
                self.log.info(f'>>> {lane} = skipped {self.lanesReset[lane]}')
                self.lanesReset[lane]-=1
                continue
            keys = self.laneToKeys[lane]
            lh = [self.history[self.namesMap[key]][1][-30:] for key in keys]
            dvst = sum([len(set(i)) for i in lh])/len(lh)
            pname = ', '.join([self.namesMap[i] for i in keys])
            self.log.info(f'>>> {lane} = {pname} diversity {dvst}, if < 1.4 = reset')
            if dvst < 1.4:
                self.r.i2c.blink(lane)
                self.lanesReset[lane] = 30
        
    def __init__(self, relays, disCl):
        super().__init__()
        self.lanesReset = [0,0,0,0]
        with open('adj.data', 'r') as f:
          x = f.read()
          self.tuning = eval(x)
        self.namesMap = {'Base' : 'Малина',
                         '011933991f9a' : 'Ванна',
                         '3c01b556fe32' : 'Кабінет',
                         '011933a43229' : 'Вітальня',
                         
                         #'3c01a8162fb0' : 'Тамбур',
                         #'3c01a816bf53' : 'Коридор',
                         '01193ce99459' : 'в_Південь',
                         
                         '3c01b55634fd' : 'Паливна',
                         '01193cb260aa' : '_Бак',
                         '01193cc5f4a9' : '_ТеплаПідлога',
                         '01193cb40a10' : 'ТрубаВерх',
                         '01193cb58b09' : 'NewTank',
                         
                         #'01193cbde6d6' : 'в_Земля',
                         #'01193ce058f1' : 'в_Північ',
                         #'01193cd5001d' : 'в_ПідБудинком'
                         }
        self.lanesMap = {'011933991f9a' : 0,
                         '3c01b556fe32' : 0,
                         '011933a43229' : 0,
                         
                         #'3c01a8162fb0' : 3,
                         #'3c01a816bf53' : 3,
                         '01193ce99459'  : 3,
                         
                         '3c01b55634fd' : 2,
                         '01193cb260aa' : 2,
                         '01193cc5f4a9' : 2,
                         '01193cb40a10' : 2,
                         '01193cb58b09' : 2,
                         
                         #'01193cbde6d6' : 1,
                         #'01193ce058f1' : 1,
                         #'01193cd5001d' : 1
                         }
        self.lanesCnt = {0:0,1:0,2:0,3:0}
        self.laneToKeys = [[i for i,j in self.lanesMap.items() if j == lane] for lane in range(4)]
        #laneToKeys[lane]
        for i in self.lanesMap:
            self.lanesCnt[self.lanesMap[i]] += 1
        self.client = disCl
        self.r = relays
        self.noti = {} # channels to notify
        self.temp = {}
        self.history = {}
        self.historyPow=[0,0,0]
        self.loadHist()
        self.depth = 2500
        self.humidity = 0
        GPIO.setmode (GPIO.BCM)
        self.keepon = 1;
        self.p = plotter()
        self.time = datetime.datetime.now()
        self.valid = 0
        self.heaterKey = '01193cc5f4a9'
        self.tankKey = '01193cb260aa'
        self.tank2Key = '01193cb58b09'
        self._conf = {"tmax" : 70}
        self.configSync()
        self.heater2nd = urlRelay("192.168.111.16")
        self.heater2nd.off()
        self.reserve = 0
        self.ronoff=[255,255]
        self.log = logging.getLogger('smartLog')
        self.coll = collector(1730210877, "192.168.111.32")
        self.init1Wire()
        #self.r.i2c.lanes([0,0,0,0])
    async def notify(self):
        nv = self.r.isReserve()
        s = "220 on, running on grid\n"
        if nv:
            s = "220 off, running on battery\n"
            if nv != self.reserve:
              self.heater2nd.on()
              self.reserve = nv
        else:
            if nv != self.reserve:
              self.heater2nd.off()
              self.reserve = nv
        for i in self._conf["noti"]:
            if not i in self.noti:
                self.noti[i] = 50
            if nv != self.noti[i]:
                self.noti[i] = nv
                cha = self.client.get_channel(i)
                await cha.send(s)

    def run(self):
        rdt = datetime.timedelta(seconds=30)
        tnow = datetime.datetime.now()
        while self.keepon:
            if self.readTemp() != 0:
                continue
            if self.valid:
                self.heat()
            else:
                self.r.off('sw1')
                
            self.coll.readData()
            self.solarCalc()

            self.save2Hist()
            self.verifyReset()

            import smartWeb
            import importlib
            importlib.reload(smartWeb)
            html = smartWeb.show(self)
            with open("templates/show.html",'w') as f:
               f.write(html)
            
            nt = datetime.datetime.now()
            tdiff = nt-tnow
            if tdiff.seconds < 30:
              stime = (rdt-tdiff).seconds
              print("read took %d sec, now wait %d sec" % (tdiff.seconds, stime))
              time.sleep(stime)
            else:
              print("read took %d sec, no waiting" % (tdiff.seconds))
            tnow = datetime.datetime.now()
    def reset(self):
        self.history = {}
    def plot(self, li):
        hh = {}
        xx = 0
        for i in self.history:
            if i in li:
                hh[i] = self.history[i]
                xx = len(hh[i][0])
                print(xx)
        self.p.plot("%d.png" % xx, hh)
        return ["%d.png" % xx]
        return ["last1000.png", "new1000.png"]
    def plotName(self, li, fname):
        hh = {}
        xx = 0
        for i in self.history:
            if i in li:
                hh[i] = self.history[i]
                xx = len(hh[i][0])
        self.p.plot("%s.png" % fname, hh)
    
    
class temps():
    def __init__(self, cli, hea):
        self.client = cli
        self.cmd = "temp"
        self.h = hea
    def getDHT(self):
        dhtDevice = adafruit_dht.DHT22(board.D18, use_pulseio=False)
        temperature_c = dhtDevice.temperature
        humidity = dhtDevice.humidity
        return (temperature_c, humidity)
    def getW1(self):
        return W1ThermSensor.get_available_sensors()
    def oldOne(self):
      try:
        t,h = self.getDHT()
        s = "Temp = " + str(t) + " Humidity = " + str(h)
      except:
        s = "Error, try again"
      return(s)
    async def execute(self, msg):
      #self.h.readTemp()
      h,s = self.h.getTemp()
      await msg.channel.send('Вологість '+str(h)+'%\n```\n'+'\n'.join(s)+'```')

class tempGraph():
    def __init__(self, cli, hea):
        self.client = cli
        self.cmd = "graph"
        self.h = hea
    async def execute(self, msg):
      x = msg.content
      x = x.split()
      if len(x) == 0:
          await msg.channel.send("Specify names to be included into graph, max 10")
          return
      s = self.h.plot(x)
      for i in s:
          if exists(i):
            with open(i,'rb') as f:
                ff = discord.File(f)
                await msg.channel.send(i, file=ff)

class reset():
    def __init__(self,cli,hea,pc):
        self.client = cli
        self.cmd = "reset"
        self.h = hea
        self.p = pc
    async def execute(self, msg):
        await msg.channel.send("Blinking lane 1")
        self.p.i2c.blinkTemp()
        await msg.channel.send("Blinking lane 2")
        self.p.i2c.blinkTemp()
        await msg.channel.send("Blinking lane 3")
        self.p.i2c.blinkTemp()
        await msg.channel.send("Blinking lane 4")
        self.p.i2c.blinkTemp()
        await msg.channel.send("Waiting for data to load")
        time.sleep(5)
        self.h.reset()
        rc = self.h.readTemp()
        if rc == 1:
            await msg.channel.send("History reset, new data load failed")
        else:
            await msg.channel.send("History reset, new data load")
        
class getHeat():
    def __init__(self,cli,hea):
        self.client = cli
        self.cmd = "get"
        self.h = hea
    async def execute(self, msg):
        import smartSolar
        import importlib
        importlib.reload(smartSolar)
        pw = smartSolar.getPwStr(self.h.r.i2c)
        s  = "On  temp = " + str(self.h._conf["onoff"][0]) + "(" + str(self.h.ronoff[0]) + ")\n"
        s += "Off temp = " + str(self.h._conf["onoff"][1]) + "(" + str(self.h.ronoff[1]) + ")\n"
        s += "Current temp   = " + str(self.h.temp[self.h.heaterKey]) + "\n"
        s += "Current status = " + str(self.h.r.status('sw1')) + "\n"
        s += "Tank temp  = " + str(self.h.temp[self.h.tankKey]) + "\n"
        s += "Tank max   = " + str(self.h._conf["tmax"]) + '\n'
        s += "On battery = " + str(self.h.r.isReserve()) + "\n"
        s += "Tank Heating = " + str(pw) + " W\n"
        await msg.channel.send(s)
        
class getHistory():
    def __init__(self,cli):
        self.client = cli
        self.cmd = "history"
    async def execute(self, msg):
        with open('temp_hist', 'rb') as f:
          df = discord.File(f, filename="history.log")
          await msg.channel.send("Temperature History", file = df)
          
class selfGet():
    def __init__(self,cli):
        self.client = cli
        self.cmd = "selfget"
    async def execute(self, msg):
        df = discord.File('smartH.py')
        await msg.channel.send("CoreCode:", file = df)
          
class getLogic():
    def __init__(self,cli):
        self.client = cli
        self.cmd = "logicGet"
    async def execute(self, msg):
        with open('smartRemote.py', 'r') as f:
            lo = f.read()
            if len(lo)<1900:
                s = "```python\n"+lo+"\n```"
                await msg.channel.send(s)
                return
        df = discord.File("smartRemote.py")
        await msg.channel.send("Logic file used:", file = df)
class getLogicSol():
    def __init__(self,cli):
        self.client = cli
        self.cmd = "losolGet"
    async def execute(self, msg):
        with open('smartSolar.py', 'r') as f:
            lo = f.read()
            if len(lo)<1900:
                s = "```python\n"+lo+"\n```"
                await msg.channel.send(s)
                return
        df = discord.File("smartSolar.py")
        await msg.channel.send("Logic file used:", file = df)
        
class getLog():
    def __init__(self,cli):
        self.client = cli
        self.cmd = "logGet"
    async def execute(self, msg):
        result = []
        with open('smart.log') as f:
            for line in f:
                if 'smartLog' in line:
                    if not 'discord' in line:
                      result.append(line)
        s = result[-30:]
        s = '\n'.join(s)
        if len(s) < 1900:
            s = "```\n"+s+"\n```"
            await msg.channel.send(s)
            return
        with open('log.tmp', 'w') as f:
            f.write(s)
        df = discord.File("log.tmp")
        await msg.channel.send("Logfile:", file = df)
class setLogic():
    def __init__(self,cli):
        self.client = cli
        self.cmd = "logicSet"
    async def execute(self, msg):
        if len(msg.attachments) != 1:
            await msg.channel.send("Attach single python file with new logic")
            return
        await msg.attachments[0].save('smartRemote.py')
        await msg.channel.send("Logic file saved")
class setLogicSol():
    def __init__(self,cli):
        self.client = cli
        self.cmd = "losolSet"
    async def execute(self, msg):
        if len(msg.attachments) != 1:
            await msg.channel.send("Attach single python file with new logic")
            return
        await msg.attachments[0].save('smartSolar.py')
        await msg.channel.send("Logic file saved")

class setHeat():
    def __init__(self,cli,hea):
        self.client = cli
        self.cmd = "set"
        self.h = hea
    async def execute(self, msg):
        x = msg.content
        try:
          x = x.split()
          on = int(x[0])
          off = int(x[1])
          tmax = int(x[2])
        except:
          await msg.channel.send("Specify on temp and off temp like 'set 20 24'")
          return
        self.h._conf["onoff"][0] = on
        self.h._conf["onoff"][1] = off
        self.h._conf["tmax"] = tmax
        self.h.saveConfig()
        await msg.channel.send("On set to %d and off set to %d, Tank max temp set to %d" % (on, off, tmax))
class forceHeat():
    def __init__(self,cli,hea):
        self.client = cli
        self.cmd = "force"
        self.h = hea
    async def execute(self, msg):
        x = msg.content
        try:
            opt = int(x)
            if opt == 0:
                self.h.r.off('sw1')
                self.h.r.off('sw2')
                self.h.r.off('sw3')
            if opt == 1:
                self.h.r.on('sw1')
                self.h.r.on('sw2')
                self.h.r.on('sw3')
            await msg.channel.send("Changed state to %d" % opt)
        except:
            await msg.channel.send("'force 1' to ON, 'force 0' to OFF")
            
class solarGet():
    def __init__(self,cli,hea):
        self.client = cli
        self.cmd = "sol"
        self.h = hea
    async def execute(self, msg):
        x = self.h.coll.getData()
        try:
          import smartSolar
          import importlib
          importlib.reload(smartSolar)
          x = smartSolar.convert(x)
          res = "```\n"
          for i in x:
              res += i + " = " + str(x[i]) + "\n"          
        except:
          s = full_stack()
          print(s)
          for i in s.split('\n'):
            self.log.error(i)
          res = s
        await msg.channel.send(res+"```")

class solarGetNow():
    def __init__(self,cli,hea):
        self.client = cli
        self.cmd = "sall"
        self.h = hea
    async def execute(self, msg):
        #self.h.coll.readData()
        x = self.h.coll.getData()
        res = ""
        for i in x:
            res += i + " = " + str(x[i]) + "\n"
        await msg.channel.send(res)

class NotifyMe():
    def __init__(self,cli,hea):
        self.client = cli
        self.cmd = "noti"
        self.h = hea
    async def execute(self, msg):
        cha = msg.channel.id
        if cha in self.h.noti:
            self.h.noti.pop(cha, None)
            self.h._conf["noti"].remove(cha)
            self.h.saveConfig()
            await msg.channel.send("Removed notifications here")
        else:
            self.h.noti[cha] = 50
            self.h._conf["noti"].append(cha)
            self.h.saveConfig()
            await msg.channel.send("Added notifications here")
            await self.h.notify()

class stopSolarUse():
    def __init__(self,cli,hea):
        self.client = cli
        self.cmd = "stop"
        self.h = hea
    async def execute(self, msg):
        try:
          import smartSolar
          import importlib
          importlib.reload(smartSolar)
          x = smartSolar.stopHeat(self.h)
          res = "Stopped all usage"
        except:
          s = full_stack()
          print(s)
          for i in s.split('\n'):
            self.log.error(i)
          res = s
        await msg.channel.send(res)

class powerRelay():
    def __init__(self):
        #GPIO.setmode (GPIO.BCM)
        GPIO.setup(21,GPIO.OUT)#sw1 heating pump, blue
        GPIO.setup(20,GPIO.OUT)#sw2 radiant floor pump, brown
        GPIO.setup(26,GPIO.OUT)#sw3 heater pump
        GPIO.setup(16,GPIO.IN)#220v check, if high - no power
        self.n2p = {'sw1' : [21,0],
                    'sw2' : [20,0],
                    'sw3' : [26,1],
                    }
        for j in self.n2p.values():
            GPIO.output(j[0],0)
        self.i2c = i2cRelay()
    def isReserve(self):
        return GPIO.input(16)
    def on(self,n):
        pin = self.n2p[n][0]
        GPIO.output(pin,1)
        self.n2p[n][1] = 1
    def off(self,n):
        pin = self.n2p[n][0]
        GPIO.output(pin,0)
        self.n2p[n][1] = 0
    def status(self,n):
        return self.n2p[n][1]
import urllib.request
def connect(host='http://google.com'):
  try:
    urllib.request.urlopen(host) #Python 3.x
    return True
  except:
    return False

class smarty():
    def __init__(self):
        self.ready = 0
        self.client = discord.Client()
        self.client.event(self.on_ready)
        self.client.event(self.on_message)
        self.parts = []        
        self.pr = powerRelay()
        self.h = Heating(self.pr, self.client)
        #self.pr.on('sw2')
        time.sleep(2)        
        self.h.start()
        self.ready = 1
    def run(self):
         with open('token.data', 'r') as f:
            x = f.read()
            self.client.run(x)
    def isAdmin(self, msg):
        #if msg.author.id == 215548836419076106 return True
        return isinstance(msg.channel, discord.abc.GuildChannel) and msg.channel.permissions_for(msg.author).manage_guild
    async def on_ready(self):
        print('Logged in as')
        print(self.client.user.name)
        print(self.client.user.id)
        print("Servers: ", [i.name for i in self.client.guilds])
        print('------')
        g = discord.Game("!!help")
        await self.client.change_presence(activity=g)
        self.parts.append(temps(self.client, self.h))
        self.parts.append(tempGraph(self.client, self.h))
        self.parts.append(reset(self.client, self.h, self.pr))
        self.parts.append(getHeat(self.client, self.h))
        self.parts.append(setHeat(self.client, self.h))
        self.parts.append(forceHeat(self.client, self.h))
        self.parts.append(solarGet(self.client, self.h))
        self.parts.append(solarGetNow(self.client, self.h))
        self.parts.append(NotifyMe(self.client, self.h))
        self.parts.append(getHistory(self.client))
        self.parts.append(getLogic(self.client))
        self.parts.append(setLogic(self.client))
        self.parts.append(getLogicSol(self.client))
        self.parts.append(setLogicSol(self.client))
        self.parts.append(getLog(self.client))
        self.parts.append(selfGet(self.client))
        self.parts.append(stopSolarUse(self.client, self.h))
        #more parts add here
    async def on_message(self, message):
        if message.type != discord.MessageType.default:
            return
        if not message.content.startswith("!!"):
            return
        message.content = message.content[2:].strip()
        if message.content == "help":
            lst = []
            for i in self.parts:
                lst.append(i.cmd)
            await message.channel.send("Available commands:\n"+'\n'.join(lst))
            return
        for i in self.parts:
            if message.content.startswith(i.cmd):
                message.content = message.content[len(i.cmd):].strip()
                await i.execute(message)
                return
        await message.channel.send("Command not found")

while not connect():
    time.sleep(2)
    

while not connect("http://192.168.111.16"):
    time.sleep(2)

from discord.ext import tasks

bot = smarty()

@tasks.loop(seconds=30.0)
async def notifyAll():
    #print("   Loop noti")
    await bot.h.notify()
@notifyAll.before_loop
async def before():
    print("   Loop noti wait")
    await bot.client.wait_until_ready()

logInit()

notifyAll.start()

bot.run()

