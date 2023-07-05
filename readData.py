from solarman import Inverter

class collector:
  def printData(self, res):
     for i in res:
         print(i," = ",res[i])
  def __init__(self, serial, ip, serial2=None, ip2=None):
     self.inv = Inverter(serial,ip,8899,1)
     self.inv2 = None
     self.data = {}
     if serial2 and ip2:
         self.inv2 = Inverter(serial2,ip2,8899,1)
  def readData(self):
     self.inv.get_statistics()
     s = self.inv.get_current_val()
     if s:
       self.data = s
       self.data["PV3 Voltage"] = 0
       self.data["PV4 Voltage"] = 0
       self.data["PV3 Power"] = 0
       self.data["PV4 Power"] = 0
     else:
       self.data = {}
     if self.inv2:
        self.inv2.get_statistics()
        s = self.inv2.get_current_val()
        if s:
           self.addData(s)
  def getData(self):
     s = self.data
     s["ts"] = self.inv.status_lastUpdate
     return s
  def addData(self, s):
     if not ("Inverter ID" in self.data):
         self.data = s
         return
     self.data["PV3 Voltage"] = s["PV1 Voltage"]
     self.data["PV4 Voltage"] = s["PV2 Voltage"]
     self.data["PV3 Power"] = s["PV1 Power"]
     self.data["PV4 Power"] = s["PV2 Power"]
     self.data["Daily Production"] += s["Daily Production"]
     self.data["Total Production"] += s["Total Production"]
     self.data["Total Battery Charge"] += s["Total Battery Charge"]
     self.data["Total Battery Discharge"] += s["Total Battery Discharge"]
     self.data["Daily Energy Bought"] += s["Daily Energy Bought"]
     self.data["Total Energy Bought"] += s["Total Energy Bought"]
     self.data["Daily Load Consumption"] += s["Daily Load Consumption"]
     self.data["Battery Power"] += s["Battery Power"]
     self.data["Total Load Power"] += s["Total Load Power"]
     self.data["Battery Current"] += s["Battery Current"]
     self.data["Total Grid Power"] += s["Total Grid Power"]
     self.data["Battery Voltage"] = (s["Battery Voltage"]+self.data["Battery Voltage"])/2
     self.data["DC Temperature"] = (s["DC Temperature"]+self.data["DC Temperature"])/2
     self.data["AC Temperature"] = (s["AC Temperature"]+self.data["AC Temperature"])/2
     self.data["Internal CT L1 Power"] += s["Internal CT L1 Power"]
     self.data["External CT L1 Power"] += s["External CT L1 Power"]
	

fields = '''
PV1 Current  =  0.4
PV2 Current  =  0.4
Daily Energy Sold  =  0
Total Energy Sold  =  0
Total Grid Production  =  1.5
Total Load Consumption  =  1.6
Running Status  =  Normal
Inverter ID  =  2210076417
Communication Board Version No.  =  50010
Control Board Version No.  =  13172
Alert  =  ['0x0', '0x0', '0x0', '0x0', '0x0', '0x0']
PV1 Power  =  169
PV2 Power  =  163
Micro-inverter Power  =  0
Battery Status  =  Charge
Battery Power  =  -108
Battery SOC  =  99
Battery Temperature  =  25
Grid Voltage L1  =  225.5
Grid Voltage L2  =  0
Internal CT L2 Power  =  0
External CT L2 Power  =  0
Load L1 Power  =  206
Load L2 Power  =  0
Load Voltage  =  224.20000000000002
SmartLoad Enable Status  =  LOOKUP
Total Power  =  193
Current L1  =  1.2
Current L2  =  0
Inverter L1 Power  =  193
Inverter L2 Power  =  0
Grid-connected Status  =  On-Grid
Gen-connected Status  =  none
Gen Power  =  0
Time of use  =  LOOKUP
Work Mode  =  Zero-Export to Home&Solar Sell
'''


#x = collector(1730210877, "192.168.111.32", 2718848451, "192.168.111.10")
#x.readData()
#res = x.getData()
#for i in res:
#  print(i," = ",res[i])


