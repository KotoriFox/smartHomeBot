TEHs=[3,4,5,1,7] #1kw, 2kw, 2.5kw, 2.5kw, 2.5kw
cur2pw = [0,1000,2000,2500,3000,3500,4500,5500]
#future refactoring start
pw2bm = {0    : [1,1,1],
         1000 : [0,1,1],
         2000 : [1,0,1],
         2500 : [1,1,0],
         3000 : [0,0,1],
         3500 : [0,1,0],
         4500 : [1,0,0],
         5500 : [0,0,0]}

def applypw(i2c, pw, extra=0):
   bm = pw2bm[pw]
   if extra:
     bm.append(0)
     bm.append(0)
   else:
     bm.append(1)
     bm.append(1)
   for i in zip(TEHs, bm):
     if i2c.relayGet(i[0]) != i[1]:
       i2c.relaySet(i[0],i[1])
   i2c.relaySet(0,int(pw==0))
#future refactoring end

def calcTEH(cur):
   st = [1,1,1,1,1] # 1 = disable here
   if cur >= 6:
#     st = [0,0,0,1,1] # 5.5kw
#   elif cur == 6:
     st = [1,0,0,1,1] # 4.5kw
   elif cur == 5:
     st = [0,1,0,1,1] # 3.5kw
   elif cur == 4:
     st = [0,0,1,1,1] # 3kw
   elif cur == 3:
     st = [1,1,0,1,1] # 2.5kw
   elif cur == 2:
     st = [1,0,1,1,1] # 2kw
   elif cur == 1:
     st = [0,1,1,1,1] # 1kw
   return st

def calcCur(st):
   if st == [0,1,1,1,1]:
      return 1;
   if st == [1,0,1,1,1]:
      return 2;
   if st == [1,1,0,1,1]:
      return 3;
   if st == [0,0,1,1,1]:
      return 4;
   if st == [0,1,0,1,1]:
      return 5;
   if st == [1,0,0,1,1]:
      return 6;
   if st == [0,0,0,1,1]:
      return 7;
   return 0;

def calcPow(st):
   res = 0
   pow = [1000,2000,2500,0,0]
   for i in zip(st, pow):
     if i[0] == 0:
       res += i[1]
   return res


def setTEH(i2c,pw):
   st = calcTEH(pw)
   for i in zip(TEHs, st):
     if i2c.relayGet(i[0]) != i[1]:
       i2c.relaySet(i[0],i[1])
   i2c.relaySet(0,int(pw==0))

def getCur(i2c):
   st = []
   for i in TEHs:
     if i2c.relayGet(i):
        st.append(1)
     else:
        st.append(0)
   pw = calcCur(st)
   return pw

def heatLogic(h):
   tb = h.temp['01193cb260aa']
   cur = getCur(h.r.i2c)
   currr = calcPow(calcTEH(cur))
   oldPw = calcPow(calcTEH(cur))
   d = h.coll.getData()
   buy = d["External CT L1 Power"]
   use = d["PV1 Power"]+d["PV2 Power"]
   batt = d["Battery Current"] * d["Battery Voltage"]
   h.log.info("cur %d(%d) buy %d solar %d batt %d temp %d" % (cur, currr, buy, use, batt, tb))
   if d["Grid-connected Status"] == "Off-Grid":
     h.log.info("offgrid! set cur 0")
     setTEH(h.r.i2c, 0)
     return     
   if use+buy+batt < currr:
     h.log.info("system collapse, restore")
     setTEH(h.r.i2c, 0)
     return
#   if use+buy > 4500:
#     h.log.info("Risk of overuse, set cur %d" % (cur-1))
#     setTEH(h.r.i2c, cur-1)
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
   if tb >= h._conf["tmax"]:
       h.log.info("Max tank temp reached")
       cur = 0
   newPw = cur2pw[cur]
   if oldPw < newPw:
       if newPw-oldPw+use > 5000:
          cur -= 1
   h.log.info("Set cur %d" % cur)
   setTEH(h.r.i2c, cur)

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
