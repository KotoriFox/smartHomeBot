#!/usr/bin/python3

from flask import Flask, render_template, request
import datetime
import sqlite3
import os

class sqldatabase:
  def __init__(self,filename):
    self.name = filename
  def execute(self, sql, params):
    con = sqlite3.connect(self.name)
    cur = con.cursor()
    cur.execute(sql, params)
    res = cur.fetchall()
    con.commit()
    con.close()
    return res
  def makeTables(self):
    os.remove(self.name)
    sql = "CREATE TABLE tempData(time, name, temp, humidity)"
    self.execute(sql,())
    sql = "CREATE TABLE variables(name, val)"
    self.execute(sql,())
  def getVar(self, n):
    sql = f"select val from variables where name = '{n}';"
    tmp = self.execute(sql,())
    return tmp[0][0]
  def setVar(self,n,v):
    sql = f"delete from variables where name = '{n}';"
    self.execute(sql,())
    sql = "insert into variables(name,val) values(?,?)"
    ttt = (n,v)
    self.execute(sql,ttt)
    return f"{n} = {v}"
  def printVar(self):
    sql = "select name,val from variables order by name asc;"
    tmp = self.execute(sql,())
    res = {}
    for i in tmp:
       res[i[0]] = i[1]
    return res
  def addTemp(self, n,t,h):
    n1 = datetime.datetime.now()
    ts = n1.strftime("%Y-%m-%d %H:%M:%S")
    sql = "INSERT INTO tempData(time, name, temp, humidity) VALUES(?,?,?,?)"
    ttt = (ts,n,t,h)
    self.execute(sql,ttt)
  def getTemp(self):
    n1 = datetime.datetime.now()-datetime.timedelta(minutes=1)
    ts = n1.strftime("%Y-%m-%d %H:%M:%S")
    sql = f"select name,temp,humidity from tempData where time > datetime('{ts}') order by time asc;"
    print([sql])
    tmp = self.execute(sql,())
    res = {}
    for i in tmp:
      res[i[0]] = (i[1], i[2])
    return res
  def getHistory(self,  name):
    n1 = datetime.datetime.now()-datetime.timedelta(minutes=1440)
    ts = n1.strftime("%Y-%m-%d %H:%M:%S")
    sql = f"select time,temp from tempData where time > datetime('{ts}') and name = '{name}' order by time asc;"
    print([sql])
    tmp = self.execute(sql,())
    li1 = []
    li2 = []
    for i in tmp:
        li1.append(i[0])
        li2.append(float(i[1]))
    return [li1,  li2]
  def addInv(self,data):
    n1 = datetime.datetime.now()
    ts = n1.strftime("%Y-%m-%d %H:%M:%S")
    sql = "INSERT INTO inverter(time, data) VALUES(?,?)"
    ttt = (ts,data)
    self.execute(sql,ttt)
  def getInv(self):
    n1 = datetime.datetime.now()-datetime.timedelta(minutes=1)
    ts = n1.strftime("%Y-%m-%d %H:%M:%S")
    sql = f"select data from inverter where time > datetime('{ts}') order by time asc;"
    tmp = self.execute(sql,())
    res = ""
    for i in tmp:
      res = i[0]
    return res

app = Flask("monitoring")
sql = sqldatabase("smart.db")
#sql.makeTables()

@app.route('/')
def index():
   return render_template("show.html")

@app.route('/config', methods = ['POST', 'GET'])
def config():
   if request.method == 'POST':
       form_data = request.form
       n = form_data['Name']
       v = form_data['Value']
       sql.setVar(n,v)
   var = sql.printVar()
   res = "<html><table>"
   for i in var:
     res += f"<tr><td>{i}</td><td>=</td><td>{var[i]}</td></tr>"
   res += "</table>"
   res += '''
          <form action="/config" method = "POST">
          <p>Name <input type = "text" name = "Name" /></p>
          <p>Value <input type = "text" name = "Value" /></p>
          <p><input type = "submit" value = "Submit" /></p>
          </form>
          '''
   res += "</html>"
   return res

@app.route("/drop/<data>")
def drop(data):
    res = {}
    s = data.split(",")
    for i in s:
      x = i.split("=")
      key = x[0]
      temp = x[1]
      humidity = 0
      if ':' in temp:
        x = temp.split(':')
        temp = x[0]
        humidity = x[1]
      sql.addTemp(key, temp, humidity)
      res[key] = (temp, humidity)
    return res

@app.route("/temps")
def temps():
    res = sql.getTemp()
    return res

@app.route("/inv/<data>")
def iAdd(data):
  sql.addInv(data)
  return "0"

@app.route("/inv")
def iGet():
  return sql.getInv()

@app.route("/var/<name>")
def varGet(name):
    res = sql.getVar(name)
    return res

@app.route("/var/<name>/<value>")
def varSet(name,value):
    res = sql.setVar(name, value)
    return res

@app.route("/history/<name>")
def historyGet(name):
    res = sql.getHistory(name)
    return str(res)

if __name__ == '__main__':
   app.run(debug=True,host='0.0.0.0',port=8080)
