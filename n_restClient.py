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

#restExecute("drop/da1=29,da2=12,da3=23.21:51,da4=-18.91")
