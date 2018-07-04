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
		print "Opening {}".format(pass_file)
		auth=pass_decode(pass_file)
		system=InfiniBox(ibox,auth)
		system.login()
		return system,auth
	except Exception as E:
		print "failed due to {}".format(E)







