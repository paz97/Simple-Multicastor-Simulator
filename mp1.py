# authors: Yumo Chi, Joel 
# netid: yumochi2, jpmathe2
############################
# This is meant to be a simple illustration of multicasting between VMs
# as well as a display of ordering schemes
############################

# imports
import socket   
from collections import defaultdict
import yaml
import argparse
import pdb
from threading import Thread
from threading import Timer
import random
from datetime import datetime
import struct
import json
from collections import deque

class multicastor(object):
	def __init__(self, vmDict, host, port, idnum, causal):
		self.host = host
		self.port = port
		self.idnum = idnum
		self.clientTable = vmDict
		self.Tmax = self.clientTable[self.idnum]['max'] 
		self.Tmin = self.clientTable[self.idnum]['min']
		# dictionary to hold messages from other processes
		self.causal = causal
		# count to be used for total order
		self.count = 0
		self.msgCount = 0
		self.messageDict = defaultdict()
		if not self.causal:
			for vm in self.clientTable:
				self.messageDict[vm] = defaultdict()
		else:
			for vm in self.clientTable:
				self.messageDict[vm] = deque([])

		self.tMessageDict = defaultdict()
		self.stamp = [0, 0, 0, 0]
		self.ownReceiveCount = 0
		self.listener = Thread(target=self.listen)
		self.listener.daemon=True
		self.listener.start()
		self.monitor = Thread(target=self.msgMonitor)
		self.monitor.daemon=True
		self.monitor.start()
		self.fakestamp = [2,0,0,0]
		print('start listening thread')
		if self.causal:
			print('operating under causal order')
		else:
			print('operating under total order')
	def msgMonitor(self):
		deleteList = []
		while True:
			while(len(self.messageDict) != 0):
				if self.causal:
					for p in self.messageDict:
						for j in range(len(self.messageDict[p])):
							msgTuple = self.messageDict[p][j]
							rMF = True
							msg = msgTuple[1]
							if self.idnum != p:
								if self.stamp[p] == msgTuple[0][p] - 1:
									for i in range(len(msgTuple[0])):
										if i != p:
											if self.stamp[i] < msgTuple[0][i]:
												rMF = False	
								else:
									rMF = False

							elif self.idnum == p:
								if self.ownReceiveCount == msgTuple[0][p] - 1:
									for i in range(len(msgTuple[0])):
										if i != p:
											if self.stamp[i] < msgTuple[0][i]:
												rMF = False
								else:
									rMF = False

							if rMF:
								deleteList.append((p, j))
								##################### This instead #############################
								if self.idnum == p:
									self.stamp[p] += 1
									self.ownReceiveCount += 1

								else:
									self.stamp[p] = max(self.stamp[p], self.messageDict[p][j][0][p]) 
								##################### This instead #############################
								self.unicast_recieve(p, msg)
					while len(deleteList) != 0:
						deleitem = deleteList.pop()
						p = deleitem[0]
						index = deleitem[1]
						del self.messageDict[p][index]
				# monitor total ordering
				else:
					if self.count in self.tMessageDict:
						src = self.tMessageDict[self.count]['src']
						msgCount = self.tMessageDict[self.count]['msgCount']
						if msgCount in self.messageDict[src]:
							msg = self.messageDict[src][msgCount]
							self.unicast_recieve(src, msg)
							self.count += 1


	def listen(self):
	# 	Set up the sockets to listen to response
		s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		s.bind((self.host, self.port))
		s.listen(len(self.clientTable)) ## listen to the rest of 9 VMs

		# keep receiving msgs from other VMs
		while True:
			conn, addr = s.accept()
			rmtHost= socket.gethostbyaddr(addr[0])[0]
			#print('Server connected by {}'.format(addr))

			while True:
				# try:
				src = self.receiveMsg(conn)


				# except Exception as e:
				# 	print("Caught exception socket.error: ", e)
				# 	break

				# chekcing type of msg received 
				if not src:					
					#print('Receiving stop signal from clients {}'.format(rmtHost))
					break
				# else:
					#print('msg ended from {}:{}\n'.format(self.host, self.port))
			conn.close()



		print('Closing server on {}:{}\n'.format(self.host, self.port))
		s.close()
		return 1

	def start(self): 

		print('process {} starts'.format(self.idnum))
		while True:
			reply = input("What do you want to do? (type help for usage info)")
			replylist = reply.split()
			#print('replylist: ', replylist)

			# assume all input can only take 3 forms
				# send dst msg
				# msend msg
				# help
			# if this is a message to send
			if len(replylist) == 0:
				print('Invalid input, please try again.') 
			else:
				# unicast_send
				if replylist[0] == 'send':
					dst = replylist[1]
					#print('dst 1st time: ', dst)
					if not dst.isdigit():
						print('Invalid input, please try again.')
					else:
						dst = int(dst)
						#print('dst 2nd time:', dst)
						if dst > 3:
							print('Invalid input, please try again.')
						else:
							msg = ''
							for i in range(len(replylist)):
								if i > 1:
									term = replylist[i]
									if i != len(replylist) - 1:
										msg += term + ' '
									else:
										msg += term
							self.unicast_send(dst, msg)
				# multicast_send
				elif replylist[0] == 'msend':
					if len(replylist) < 2:
						print('Invalid input, please try again.') 
					else:
						msg = ''
						for i in range(len(replylist)):
							if i != 0:
								term = replylist[i]
								if i != len(replylist) - 1:
									msg += term + ' '
								else:
									msg += term

						self.multicast(msg)
				elif replylist[0] == 'help':
					print('Use following format to operate multicastor')
					print('help - to enact helping messages')
					print('send destination message - sending message to destination process')	
					print('msend message - sending message to everyone')
					print('show clientTable - to show client table')
					print('show messageDict - to show message table')
					print('show tMessageDict - to show meta message information')
					print('show stamp - to show time stamp')
					print('exit - to exit program')

				elif replylist[0] == 'show':
					if replylist[1] == 'messageDict':
						print(self.messageDict)
					elif replylist[1] == 'clientTable':
						print(self.clientTable)
					elif replylist[1] == 'tMessageDict':
						print(self.tMessageDict)
					elif replylist[1] == 'stamp':
						print(self.stamp)
				elif  replylist[0] == 'exit':
					break
				else:
					print('Invalid input, please try again.')
		return 

	def unicast_send(self, dst, msg):

		mCflag = 0
		# call delay layer
		delayThread = Thread(target=self.delayLayer, args= [dst, msg, mCflag, ])
		delayThread.daemon=True
		delayThread.start()


	
	def delayLayer(self, dst, msg, mCflag):

		# set timer and call send
		# set multicast flag to 0 to indicate unicast
		t = Timer(random.uniform(self.Tmin, self.Tmax)/1000, self.send, args=[dst, msg, mCflag, ])
		# t = Timer(10, self.send, args=[dst, msg, mCflag, ])
		t.start()


	def send(self, dst, msg, mCflag):
		# Create a socket object
		dst = int(dst)
		s = socket.socket()  

		# Define the port on which you want to connect
		port = self.clientTable[dst]['port']            

		host = self.clientTable[dst]['ip']

		s.connect((host, port))

		encodeMsg = self.encode(msg.encode('ascii'), mCflag)

		s.send(encodeMsg)

		# receive data from the server
		print()
		print('Sent {} to process {}, system time is {}'.format(msg, dst, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
		print()
		# close the connection
		s.close()

		#print('sending thread ends')
		return

	def unicast_recieve(self, src, msg):
		print()
		print('Recieved {} from process {}, system time is {}'.format(msg, src, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
		print()

	#	function for recieving info
	def receiveMsg(self,sckt):

		# a bit ugly
		raw_msgLen = self.decode(sckt,4)
		raw_idnum = self.decode(sckt,4)
		raw_mCflag = self.decode(sckt,4)

		while(not raw_idnum  or not raw_msgLen or not raw_mCflag):
			raw_msgLen = self.decode(sckt,4)
			raw_idnum = self.decode(sckt,4)
			raw_mCflag = self.decode(sckt,4)

		raw_msgLen = raw_msgLen.encode('ascii')
		raw_idnum = raw_idnum.encode('ascii')
		raw_mCflag = raw_mCflag.encode('ascii')

		if not raw_msgLen or not raw_idnum:
			return None

		[msgLen, src] = [struct.unpack('>I',raw_msgLen)[0], struct.unpack('>I',raw_idnum)[0]]
		mCflag = struct.unpack('>I',raw_mCflag)[0]
		msg = self.decode(sckt, msgLen)

		if mCflag == 1:
			# multicast message recieved
			# causal order
			if self.causal:
				msg = self.decodeMsg(msg)
				self.messageDict[src].append((msg['stamp'], msg['msg']))
			# total order
			else:
				# check if the message is from the sequencer
				msg = self.decodeMsg(msg)
				# print(msg)
				if src == 0:
					#regular multicast
					if 'msg' in msg:
						# sequencer code
						if self.idnum == 0:
							msgCount = msg['msgCount']
							# save information on meta message table
							# self.tMessageDict[self.count] = {src: msgCount}
							# display msg on screen
							self.unicast_recieve(src, msg['msg'])
							# multicast meta data to other processes
							self.seqMultiCast(self.count, src, msgCount)
							# increment count to signify recieving message
							self.count += 1
						# non-sequencer code
						else:
							msgCount = msg['msgCount']
							# regular message
							# save message into messageDict
							self.messageDict[src][msgCount] = msg['msg']
					# meta data from sequencer
					else:
						# if self.idnum == 0:
						# 	msgCount = msg['msgCount']
						# 	self.messageDict[src][msgCount] = msg['msg']
						if self.idnum != 0:
							if msg['count'] >= self.count:
								receiveCount = msg['count']
								receiveMsgCount = msg['msgCount']
								receiveSrc = msg['src']
								self.tMessageDict[receiveCount] = {'src': receiveSrc, 'msgCount': receiveMsgCount }
				else:
					if self.idnum == 0:
						msgCount = msg['msgCount']
						# save information on meta message table
						# self.tMessageDict[self.count] = {src: msgCount}
						# display msg on screen
						self.unicast_recieve(src, msg['msg'])
						# multicast meta data to other processes
						#self.seqMultiCast(self.count, src, msgCount)
						
						if self.count == 0:
							self.seqMultiCast(self.count, 3, 0)
						if self.count == 1:
							self.seqMultiCast(self.count, 1, 0)
						if self.count == 2:
							self.seqMultiCast(self.count, 2, 0)

						# increment count to signify recieving message
						self.count += 1

					else:	
						msgCount = msg['msgCount']
						self.messageDict[src][msgCount] = msg['msg']
		else:
		# set timer and call receive
			t = Timer(random.uniform(self.Tmin, self.Tmax)/1000, self.unicast_recieve, args=[src, msg,])
			t.start()
			return src

	def multicast(self, msg):
		#causual ordering 
		if self.causal:
			# increment time stamp
			
			# if msg == 'hello':
			# 	msg = {'msg': msg, 'stamp': self.fakestamp}
			# else:
			# 	self.stamp[self.idnum] += 1
			# 	msg = {'msg': msg, 'stamp': self.stamp}
			self.stamp[self.idnum] += 1
			msg = {'msg': msg, 'stamp': self.stamp}
			encodeMsg = self.encodeMsg(msg)

		#total ordering
		else:
			msg = {'msg': msg, 'msgCount': self.msgCount}
			encodeMsg = self.encodeMsg(msg) 
			# increment msgCount for process
			self.msgCount += 1

		for i in self.clientTable:
			self.mcUnicast_send(i, encodeMsg)


	def seqMultiCast(self, count, src ,msgCount):
		msg = { 'count' : count, 'src' : src, 'msgCount': msgCount  }
		encodeMsg = self.encodeMsg(msg)

		for i in self.clientTable:
			self.mcUnicast_send(i, encodeMsg)

	def mcUnicast_send(self, dst, msg):
		mCflag = 1

		delayThread = Thread(target=self.delayLayer, args= [dst, msg, mCflag, ])
		delayThread.daemon=True
		delayThread.start()
		

	def encodeMsg(self,dict):
		return json.dumps(dict)

	# decode the recieved string into a json dict
	def decodeMsg(self,msg):
		msg_json = json.loads(msg)
		return msg_json


	def decode(self,sckt,n):
		msg = ''
		while len(msg) < n:
			packet = sckt.recv(n - len(msg))
			if not packet:
				return None
			msg += packet.decode('ascii')
		return msg
	

	def encode(self, data, mCflag):
		return struct.pack('>III', len(data), self.idnum, mCflag) + data


if __name__ == '__main__':

	#parse information from commandline
	parser = argparse.ArgumentParser()
	parser.add_argument("--idnum",'-i', type=int,default=0)
	parser.add_argument("--causal",'-c', type=int,default=0)

	args = parser.parse_args()
	# pdb.set_trace()

	# create vmDict to hold info for servers

	# layout of vmDict
	'''
	{idnum:
			ip:	xxxx
			port: xxxx
			min: xxxx
			max: xxxx 
	}
	'''

	# import config file
	with open('config.yml', 'r') as stream:
		try:
			vmDict = yaml.load(stream)
			print('read configuration file')
		except yaml.YAMLError as exc:
			print(exc)

	idnum = args.idnum

	# if positive then it is causal
	# if args.causal > 0:
	# 	causal = True
	# else:
	# 	causal = False
	causal = args.causal > 0

	mc = multicastor(vmDict=vmDict, host=vmDict[idnum]['ip'], port= vmDict[idnum]['port'], idnum= idnum, causal=causal)
			
	mc.start()


			