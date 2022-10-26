TEHs=[6,4,5,3,2] #1kw, 2kw, 2.5kw, 2.5kw, 2.5kw
TEH_pw=[1000,2000,2500]
cur2pw = [0,1000,2000,2500,3000,3500,4500,5500]
pw2cur = {0:0,1000:1,2000:2,2500:3,3000:4,3500:5,4500:6,5500:7}
pw2bm = {0    : [1,1,1],
         1000 : [0,1,1],
         2000 : [1,0,1],
         2500 : [1,1,0],
         3000 : [0,0,1],
         3500 : [0,1,0],
         4500 : [1,0,0],
         5500 : [0,0,0]}
cur2Res = {0:0, 1:1, 2:2, 3:2, 4:2, 5:2, 6:2}
minBuy=40
def applypw(i2c, pw, h):
   tb = h.temp['01193cb260aa']
   bm = pw2bm[pw]
   if (tb >= minBuy) or (h.r.isReserve()):
     bm.append(1)
     bm.append(1)
     h.log.info("%u >= %u or on reserve, 5kW off" % (tb, minBuy))
   else:
     bm.append(0)
     bm.append(0)
     pw+=5000
     h.log.info("%u < %u, 5kW on" % (tb, minBuy))
   for i in zip(TEHs, bm):
     if i2c.relayGet(i[0]) != i[1]:
       i2c.relaySet(i[0],i[1])
   i2c.relaySet(0,int(pw!=0))
def bm2pw(st):
   st = [not i for i in st]
   return sum([i[0]*i[1] for i in zip(st,TEH_pw)])
def getPwNow(i2c):
   st = []
   for i in TEHs:
     if i2c.relayGet(i):
        st.append(1)
     else:
        st.append(0)
   st = st[:3]
   return bm2pw(st)

#===============================================
def stopHeat(h):
   applypw(h.r.i2c, 0, h)
def heatLogic(h):
   tb = h.temp['01193cb260aa']
   oldPw = getPwNow(h.r.i2c)
   currr = oldPw
   cur = pw2cur[oldPw]
   d = h.coll.getData()
   soc = d["Battery SOC"]
   buy = d["External CT L1 Power"]
   solar = d["PV1 Power"]+d["PV2 Power"]
   batt = d["Battery Current"] * d["Battery Voltage"]
   h.log.info(f'cur {cur}({oldPw}) buy {buy} solar {solar} batt {batt} soc {soc} temp {tb}')
   if tb >= h._conf["tmax"]:
       h.log.info("Max tank temp reached")
       applypw(h.r.i2c, 0, h)
       return
   if d["Grid-connected Status"] == "Off-Grid":
     pwplus = {0 : 1000, 1000 : 2000, 2000 : 3000, 2500 : 3000, 3000 : 3000, 3500 : 3000}
     h.log.info("offgrid! set batt %u" % batt) # reserve limited to 1+2kW pins
     cur = cur2Res[cur]
     oldPw = cur2pw[cur]
     if (batt < 0) and (soc > 98): #charging above 98%
       oldPw = pwplus[oldPw]
     else:
       while batt > 400:
         batt -= 1000
         oldPw -= 1000
     h.log.info("offgrid! set pw %u" % oldPw)
     applypw(h.r.i2c, oldPw, h)
     return     
   if solar+buy+batt < currr:
     h.log.info("system collapse, restore")
     applypw(h.r.i2c, 0, h)
     return
#   if solar+buy > 4500:
#     h.log.info("Risk of overuse, set cur %d" % (cur-1))
#     applypw(h.r.i2c, cur-1)
#     return
   if buy < -100:
     # we're selling, handle all sell
     while buy < -100:
        cur+=1
        npw = cur2pw[cur]
        buy += npw-currr
        currr = npw
   elif buy < 100:
     if (d["Battery Current"] < -19) and (d["Battery Voltage"] > 54):
       cur+=1
     elif d["Battery SOC"] > 99:
       cur+=1
   btmp = batt
   while ((btmp > 100) and (cur > 0)):
       btmp -= cur2pw[cur]-cur2pw[cur-1]
       cur-=1
   while buy > 700:
     if cur == 0:
       break
     currr = cur2pw[cur]
     cur-=1
     currr2 = cur2pw[cur]
     buy -= currr-currr2
   if cur > 0:
     if (tb > 60) and (buy > 200):
       cur-=1
     elif (tb > 40) and (buy > 400):
       cur-=1
   newPw = cur2pw[cur]
   if oldPw < newPw:
       if newPw-oldPw+solar > 5000:
          cur -= 1
   h.log.info("Set cur %d" % cur)
   applypw(h.r.i2c, cur2pw[cur], h)

def convert(x):
   keys = {"Update Time" : lambda x: x["ts"],
           "Area 1 V" : lambda x: x["PV1 Voltage"],
           "Area 2 V" : lambda x: x["PV2 Voltage"],
           "Solar Power W" : lambda x: x["PV1 Power"]+x["PV2 Power"],
           "Buying W" : lambda x: x["Total Grid Power"],
           "Battery V" : lambda x: x["Battery Voltage"],
           "Battery Charge W" : lambda x: (-1)*x["Battery Voltage"]*x["Battery Current"],
           "Battery SOC" : lambda x : x["Battery SOC"],
           "Home Usage W" : lambda x: x["Total Load Power"],
           "CT W" : lambda x: str(x["Internal CT L1 Power"])+"/"+str(x["External CT L1 Power"]),
           "Temp Battery" : lambda x: x["Battery Temperature"],
           "Temp DC" : lambda x: x["DC Temperature"],
           "Temp AC" : lambda x: x["AC Temperature"],
           "Daily Energy Bought" : lambda x: x["Daily Energy Bought"],
           "Daily Load Consumption" : lambda x: x["Daily Load Consumption"],
          }
   res = {}
   for i in keys:
     res[i] = keys[i](x)
   return res
