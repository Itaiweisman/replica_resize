__author__  =  "Itai Weisman"
from infinisdk import InfiniBox
import base64, sys

def pass_decode(file):
    try:
        F=open(file,'r')
        user,enc_pass=F.read().split()
        dec_pass=base64.b64decode(enc_pass).rstrip()
	auth=(user,dec_pass)
        return auth
    except Exception as E:
    	print "failed with exception: {}".format(E)
    	exit(1)


def ibox_login(ibox):
	try:
		pass_file="."+ibox+".sec"
		system=InfiniBox(ibox,pass_decode(pass_file))
		system.login()
		return system
	except Exception as E:
		print "failed due to {}".format(E)







