import http.client

def restExecute(url,host="localhost:8080"):
  conn = http.client.HTTPConnection(host)
  conn.request("GET", "/"+url, headers={"Host": host})
  response = conn.getresponse()
  if response.status != 200:
     return ""
  return eval(response.read())

def restDropTemp(tdict):
  url = "drop/"
  for i in tdict:
     url += f"{i}={tdict[i]},"
  url = url[:-1]
  restExecute(url)
def restGetTemps():
  return restExecute("temps")
def restSetVar(name,value):
   restExecute(f"var/{name}/{value}")
def restGetVar(name):
   return restExecute(f"var/{name}")
def restDropInv(idict):
   data = str(idict)
   restExecute(f"inv/{data}")
def restGetInv():
   return restExecute("inv")
def restInvGetLastN(names,n):
	import datetime
	d = restExecute("invhistory")
	keys = list(d)
	keys = keys[-n:]
	res = {}
	for i in keys:
		t = datetime.datetime.strptime(i, "%Y-%m-%d %H:%M:%S")
		data = {}
		for j in names:
			data[j] = d[i][j]
		res[t] = data
	return res

def restPlot(self, name, keys):
    import matplotlib
    import datetime
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt2
    import matplotlib.dates as mdates
    fig = plt2.figure()
    plt = fig.add_subplot(111)
    formatter = mdates.DateFormatter("%H:%M")
    plt.xaxis.set_major_formatter(formatter)
    locator = mdates.HourLocator()
    plt.xaxis.set_major_locator(locator)
    invKeys = list(restGetInv())
    if keys[0] in invKeys:
    	for i in keys:
    		h = restInvGetLastN([i],5000)
    		d = list(h)
    		v = []
    		for j in h:
    			v.append(h[j][i])
    		plt.plot(d, v, label=i)
    else:
    	for i in keys:
        url = "history/"+i
        res = restExecute(url)
        ti = []
        for j in res[0]:
            t = datetime.datetime.strptime(j, "%Y-%m-%d %H:%M:%S")
            ti.append(t)
        if len(ti):
            plt.plot(ti, res[1], label=i)
    plt.legend()
    plt.grid()
    plt2.gcf().autofmt_xdate()
    fig.savefig(name)
    plt2.close(fig)

def solarConvert(x):
   keys = {"Update Time" : lambda x: x["ts"],
           "Area 1 V" : lambda x: x["PV1 Voltage"],
           "Area 2 V" : lambda x: x["PV2 Voltage"],
           "Area 3 V" : lambda x: x["PV3 Voltage"],
           "Area 4 V" : lambda x: x["PV4 Voltage"],
           "Solar Power W" : lambda x: x["PV1 Power"]+x["PV2 Power"]+x["PV3 Power"]+x["PV4 Power"],
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
           "Daily Production" : lambda x: x["Daily Production"],
           "Total Battery Discharge" : lambda x: x["Total Battery Discharge"],
          }
   res = {}
   for i in keys:
   	try:
         res[i] = keys[i](x)
      except:
      	res[i] = "N/A"
   return res    

#restExecute("drop/da1=29,da2=12,da3=23.21:51,da4=-18.91")
