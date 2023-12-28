import RPi.GPIO as GPIO
import time
import board
import n_restClient

from pcf8575 import PCF8575

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

class powerRelay():
    def __init__(self, li):
        self.forceSw1 = li['fsw1']
        GPIO.setmode (GPIO.BCM)
        GPIO.setup(21,GPIO.OUT)#sw1 heating pump, blue
        GPIO.setup(20,GPIO.OUT)#sw2 radiant floor pump, brown
        GPIO.setup(26,GPIO.OUT)#sw3 heater pump
        GPIO.setup(19,GPIO.OUT)#room cooler
        GPIO.setup(16,GPIO.IN)#220v check, if high - no power
        self.n2p = {'sw1' : [21,li['sw1']],
                    'sw2' : [20,li['sw2']],
                    'sw3' : [26,li['sw3']],
                    'sw4' : [19,li['sw4']],
                    }
        for j in self.n2p.values():
            GPIO.output(j[0],j[1])
    def sync(self, li):
        if self.forceSw1 != li['fsw1']:
           self.setForceSw1(li['fsw1'])
        for i in self.n2p:
            if self.n2p[i][1] != li[i]:
               self.set(i,li[i])
    def isReserve(self):
        return GPIO.input(16)
    def set(self, n, s):
        if s:
            self.on(n)
        else:
            self.off(n)
    def on(self,n):
        pin = self.n2p[n][0]
        GPIO.output(pin,1)
        self.n2p[n][1] = 1
    def setForceSw1(self, s):
        self.forceSw1 = s
        if s:
           self.on('sw1')
        else:
           self.off('sw1')
    def off(self,n):
        if (n == 'sw1') and (self.forceSw1):
           return
        pin = self.n2p[n][0]
        GPIO.output(pin,0)
        self.n2p[n][1] = 0
    def status(self,n):
        return self.n2p[n][1]

def readRelays():
   res = {}
   res['sw1'] = n_restClient.restGetVar("sw1_giver")
   res['sw2'] = n_restClient.restGetVar("sw2_radiant")
   res['sw3'] = n_restClient.restGetVar("sw3_syncer")
   res['sw4'] = n_restClient.restGetVar("sw4_cooler")
   res['fsw1'] = n_restClient.restGetVar("fsw1_pool")
   res['lanes'] = n_restClient.restGetVar("lanes")
   return res

if __name__ == '__main__':
    x = readRelays()
    i2c = i2cRelay()
    p = powerRelay(x)
    while 1:
      res = p.isReserve()
      n_restClient.restSetVar("inner_reserve", res)
      i2c.lanes(x['lanes'])
      time.sleep(0.2)
      x = readRelays()
      p.sync(x)
