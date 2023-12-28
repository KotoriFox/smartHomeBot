import n_restClient
import datetime

class heatingLogic:
  def __init__(self):
     self.idt=0
     self.idw=0
     self.odt=0
     self.odw=0
     self.temps = {}
     self.onoff = [24,28]
     self.offonminutes = [20,15]
     self.oomEventTime = datetime.datetime.now()
     self.oomAction = 0

  def calcInside(self,name,weight):
     if name in self.temps:
       self.idt += self.temps[name] * weight
       self.idw += weight
  def insideDelta(self):
     allinner={"Ванна":4,
               "Кабінет":2,
               "Вітальня":7,
               "Тамбур":1,
               "Коридор":3 }
     self.idt=0
     self.idw=0
     for i in allinner:
        self.calcInside(i, allinner[i])
     if self.idw == 0:
        return 0 #no data -> no delta
     self.idt /= self.idw
     req = self.onoff[0]-4
     return req-self.idt

  def calcOutside(self,name,weight):
     if name in self.temps:
       self.odt += self.temps[name] * weight
       self.odw += weight
  def outsideDelta(self):
     allouter={"в_Південь" : 2,
               "в_ПідБудинком" : 9,
               "в_Північ" : 6,
               "в_Земля" : 8,
              }
     self.odt=0
     self.odw=0
     for i in allouter:
        self.calcOutside(i, allouter[i])
     if self.odw == 0:
        return 0 #no data -> no delta
     temp = self.odt / self.odw
     delta = 11.27-temp/6-(1300*((temp+717)**(2/3))+(temp*2/3+20)**3)/12100
     on = self.onoff[0]+delta
     off= self.onoff[1]+delta
     print("outside delta %f" % delta)
     return on,off

  def radiantCalc(self):
   if "в_Південь" in self.temps:
      return int(self.temps["в_Південь"] < 15)
   mo = datetime.datetime.now().month
   return int((mo>4) and (mo<10))^1

  def doHeat(self, on, off):
   temp = self.temps["_ТеплаПідлога"]
   tank = self.temps["NewTank"]
   if tank-1 < off:
       print(f"Tank {tank-1} < {off} off heating")
       n_restClient.restSetVar("sw1_giver", 0)
       n_restClient.restSetVar("sw2_radiant", 0)
       return
   raa = self.radiantCalc()
   n_restClient.restSetVar("sw2_radiant", raa)
   if (temp > off):
       print("off heating")
       n_restClient.restSetVar("sw1_giver", 0)
       return
   if temp < on:
       print("on heating")
       n_restClient.restSetVar("sw1_giver", 1)

  def doHeatFallback(self):
    raa = self.radiantCalc()
    n_restClient.restSetVar("sw2_radiant", raa)
    if raa == 0:
       n_restClient.restSetVar("sw1_giver", 0)
       print("Fallback no need heating")
       return
    secs = self.offonminutes[self.oomAction] * 60
    cur = datetime.datetime.now()
    delta = cur-self.oomEventTime
    if delta.seconds >= secs:
      self.oomEventTime = cur
      self.oomAction ^= 1
      n_restClient.restSetVar("sw1_giver", self.oomAction)
      print("Fallback heating ",self.oomAction)

  def heatLogic(self):
   self.temps = n_restClient.restGetTemps()
   self.onoff = n_restClient.restGetVar("onoff")
   normal = ("_ТеплаПідлога" in self.temps) and ("NewTank" in self.temps)
   if not normal:
      self.offonminutes = n_restClient.restGetVar("offonminutes")
      self.doHeatFallback()
      return
   on,off = self.outsideDelta()
   x = self.insideDelta()
   print("delta inside %f" % x)
   x = x*2
   on += x
   off += x
   ronoff = ["%.2f" % on, "%.2f" % off]
   n_restClient.restSetVar("realonoff", str(ronoff))
   print("on %.2f off %.2f" %(on,off))
   self.doHeat(on, off)


if __name__ == '__main__':
    h = heatingLogic()
    while 1:
      h.heatLogic()
      time.sleep(1)
