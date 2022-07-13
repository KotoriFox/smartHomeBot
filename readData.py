from solarman import Inverter

class collector:
  def __init__(self, serial, ip):
     self.inv = Inverter(serial,ip,8899,1)
  def readData(self):
     self.inv.get_statistics()
  def getData(self):
     s = self.inv.get_current_val()
     s["ts"] = self.inv.status_lastUpdate
     return s

#x = collector(1730210877, "192.168.111.32")
#x.readData()
#res = x.getData()
#for i in res:
#  print(i," = ",res[i])


