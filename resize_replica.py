#! /usr/bin/env python
from infinisdk import InfiniBox
from capacity import *
import base64
import requests
import json
import pprint
from infinini import ibox_login, pass_decode
import sys
import os
import fcntl
import struct
import getopt
import logging
import time
from time import strftime
import argparse

IOCTL_BLKGETSIZE64 = 0x80081272
IOCTL_BLKDISCARD = 0x1277

def get_args():
    """
    Supports the command-line arguments listed below.
    """
    parser = argparse.ArgumentParser(description="Resize a replicated volume that is a member of a cg.")
    parser.add_argument('-v', '--volume', nargs=1, required=True, help='The volume name to resize', dest='volume', type=str)
    parser.add_argument('-i', '--increaseby', nargs=1, required=True, help='Size to be increased by (default in Gib)', dest='size', type=int)
    args = parser.parse_args()
    return args

def args_from_cfgfile():
    conf_file = {}
    scriptpath = os.path.dirname(os.path.abspath(__file__))
    with open(scriptpath+"/config.txt") as cfg:
        for line in cfg:
            (key, val) = line.split()
            conf_file[key] = val
        return conf_file

def setup_logger(map_host):
	file=map_host+"-"+strftime("%Y-%m-%d_%H%M%S")+".log"
	logging.basicConfig(format='%(asctime)s %(message)s',filename=file,level=logging.DEBUG)
	print ("logfile is {}".format(file))
	logging.info("Started")

def get_vol_cg(box,vol):
	vol_object = box.volumes.find(name=vol).to_list()
	if vol_object:
		return vol_object[0].get_field('cons_group') 
	else: 
		return None

def get_cg_id(box,cg_name):
	cg=box.cons_groups.find(name=cg_name).to_list()[0]
	cg_id=cg.get_field('id')
	replicated=cg.get_field('replicated')
	if (cg_id and replicated):
		return cg_id
	else:
		return None

def get_cg_replica(box,box_fqdn,auth,cg_id):
	replicas=box.replicas.to_list()
	for replica in replicas:
		cur_id=replica.get_field('entity_pairs')[0]['local_entity']['cg_id']
		myreplica=None
		if cur_id == cg_id:
			myreplica=replica
			myid=myreplica.get_id()
			url='http://'+box_fqdn+'/api/rest/replicas/'+str(myid)
			replica_json=requests.get(auth=auth,url=url).json()
			break
	return myreplica, replica_json

def get_volumes_to_assign(replica):
	vol_list=[]
	pairs={}
	for dataset in replica.get_field('entity_pairs'):
		vol_list.append(dataset['remote_entity_name'])
		pairs[dataset['local_entity_id']]=dataset['remote_entity_id']

	return pairs,vol_list

def assign_vols_to_host(remotebox,map_host,vol_dict):
	host=remotebox.hosts.find(name=map_host).to_list()
	if (not host):
		print "Not Host!"
		return None
	mapping_to=host[0]
	map_list=[]
	pairs={}
	for vol in vol_dict.values():
		print "searching for volume with ID {}".format(vol)
		logging.info("searching for volume with ID {}".format(vol))
		remote_vol=remotebox.volumes.find(id=vol).to_list()

		if remote_vol:
			logging.info("Adding {} to maplist ".format(remote_vol[0]))
			map_list.append(remote_vol[0])
			pairs[vol]=remote_vol[0].get_id()
		else:
			print "Not remote vol {}".format(remote_vol)
			logging.info("Not remote vol {}".format(remote_vol))
			return None
	for vol_obj in map_list:
		print "mapping to {} vol {}".format(mapping_to.get_name(), vol_obj.get_name())
		logging.info("mapping to {} vol {}".format(mapping_to.get_name(), vol_obj.get_name()))
		mapping_to.map_volume(vol_obj)
	return mapping_to

def deassign_vols_from_host(box,map_host,vol_dict):
	for vol in vol_dict.values():
		logging.info("vol to deassign {}".format(vol))
		to_remove=box.volumes.find(id=vol)
		if to_remove:
			logging.info("removing {}".format(to_remove[0]))
			map_host.unmap_volume(to_remove[0])

def resize_volume(sourcebox,remotebox,pairs,vol_to_resize,size):
	vol=sourcebox.volumes.find(name=volume).to_list()
	logging.info(vol[0].get_id())
	if vol:
		logging.info("id is {}".format(pairs[vol[0].get_id()]))
		paired=remotebox.volumes.find(id=pairs[vol[0].get_id()])
		if paired:
			print "Paired"
			print "volume to resize {} and {}".format(vol[0].get_name(), paired[0].get_name())
			logging.info("volume to resize {} and {}".format(vol[0].get_name(), paired[0].get_name()))
			resize_source=vol[0].resize(size)
			resize_target=paired[0].resize(size)
			return resize_source and resize_target
	else:
		print "NO can't"
		return None


def replica_break(box_ip,local_credentials, remote_credentials, replica):
	creds=remote_credentials[0]+":"+remote_credentials[1]
	print "in replica break"
	hashed_auth='Basic ' + base64.b64encode(creds)
	url='http://'+box_ip+'/api/rest/replicas/'+str(replica.get_id())+'?approved=true'
	headers={'X-Remote-Authorization':hashed_auth}
	return requests.delete(url=url,auth=local_credentials,headers=headers).json()

def replica_create(source,local_auth,remote_auth,old_replica):
	creds=remote_auth[0]+":"+remote_auth[1]
	hashed_auth='Basic ' + base64.b64encode(creds)
	url='http://'+source+'/api/rest/replicas/'
	headers={'X-Remote-Authorization':hashed_auth, 'Content-Type':'application/json'}
	return requests.post(url=url, auth=local_auth, headers=headers, data = json.dumps(old_replica)).json()
	
def get_new_replica_json(old_replica):
	new_replica={}
	new_replica['local_cg_id']=old_replica['result']['local_cg_id']
	new_replica['remote_cg_id']=old_replica['result']['remote_cg_id']
	new_replica['entity_type']=old_replica['result']['entity_type']
	new_replica['replication_type']=old_replica['result']['replication_type']
	new_replica['rpo_type']=old_replica['result']['rpo_type']
	new_replica['rpo_value']=old_replica['result']['rpo_value']
	new_replica['link_id']=old_replica['result']['link_id']
	new_replica['entity_pairs']=[]
	for item in old_replica['result']['entity_pairs']:
		new_item={}
		new_item['local_entity_id']=item['local_entity_id']
		new_item['remote_base_action']='NO_BASE_DATA'
		new_item['remote_entity_id']=item['remote_entity_id']
		new_item['local_base_action']='NO_BASE_DATA'
		new_replica['entity_pairs'].append(new_item)
	return new_replica

def ioctl(fd, req, fmt, *args):
    buf = struct.pack(fmt, *(args or [0]))
    buf = fcntl.ioctl(fd, req, buf)
    return struct.unpack(fmt, buf)[0]

def wipe(fd):
    size = ioctl(fd, IOCTL_BLKGETSIZE64, 'L')
    ioctl(fd, IOCTL_BLKDISCARD, 'LL', 0, size)
    logging.info("wipe finished")

def callwipe(vol):
    with open(vol, 'w') as dev:
        wipe(dev.fileno())

def infirescan():
    from subprocess import check_output,CalledProcessError,PIPE
    retcode = 0
    try:
            print "rescanning..."
            output = check_output("infinihost rescan",shell=True,stderr=PIPE)
    except CalledProcessError as e:
        retcode = e.returncode

def vlist():
    from infi.storagemodel.vendor.infinidat.shortcuts import get_infinidat_block_devices
    infivols = get_infinidat_block_devices()
    global volsdict 
    volsdict = {}
    for ivol in infivols:
            volsdict[ivol.get_vendor().get_volume_name()]=ivol.get_display_name()
    return volsdict

def checkvol(volist):
    for vol in volist:
        if vol in volsdict:
            dev="/dev/mapper/"+volsdict[vol]
            print("starting wipe on {}").format(vol)
            logging.info("starting wipe on {}".format(dev))
            callwipe(dev)
        else:
            print("Volume {} Not found".format(vol))	



if __name__ == '__main__':
    args = get_args()
    cfgargs = args_from_cfgfile()
    source_box_name_or_fqdn=cfgargs['source_system']
    target_box_name_or_fqdn=cfgargs['target_system']
    map_host=cfgargs['map_to']
    volume=args.volume[0]
    size=(args.size[0])*GiB
    setup_logger(map_host)
    try:
        source_box, source_box_auth=ibox_login(source_box_name_or_fqdn)
        target_box, target_box_auth=ibox_login(target_box_name_or_fqdn)
        print "Getting CG Object"
        logging.info("Getting CG Object")
        cg_object=get_vol_cg(source_box,volume)
        if (not cg_object):
            logging.error("unable to get volume CG")
            raise Exception("unable to get volume CG")
        print "CG is {}".format(cg_object.get_name())
        logging.info("CG is {}".format(cg_object.get_name()))
        print "Getting CG ID"
        logging.info("Getting CG ID")
        cg_id=cg_object.get_id()
        print "Getting Replica"
        logging.info("Getting Replica")
        replica_object, replica_json=get_cg_replica(source_box,source_box_name_or_fqdn, source_box_auth, cg_id)
        print "Replica ID is {}".format(replica_object.get_id())
        logging.info("Replica ID is {}".format(replica_object.get_id()))
        if (not replica_object or replica_json['error']):	
        	logging.error("Unable to get Consistency Group Replica")
        	raise Exception("Unable to get Consistency Group Replica")

        volumes_pairs,target_volume_list=get_volumes_to_assign(replica_object)
        print "volume pairs are {}, attempt to map".format(volumes_pairs)
        logging.info("volume pairs are {}, attempt to map".format(volumes_pairs))
        print "volume target are {}".format(target_volume_list)
        logging.info("volume target are {}".format(target_volume_list))
        mapping_host_object=assign_vols_to_host(target_box,map_host,volumes_pairs)
        print "mapped to {}".format(mapping_host_object.get_name())
        logging.info("mapped to {}".format(mapping_host_object.get_name()))
        if (not mapping_host_object):
        	logging.error("Unable to assign volumes to mount host")
        	raise Exception("Unable to assign volumes to mount host")

        print "Breaking the replication Link"
        logging.info("Breaking the replication Link")
        broken=replica_break(source_box_name_or_fqdn, source_box_auth, target_box_auth, replica_object)
        if broken['error']:
        	raise Exception(broken['error'])
        print "Replication is broken"
        logging.info("Replication is broken")
        infirescan()
        vlist()
        checkvol(target_volume_list)
        print "resizing volume "
        logging.info("resizing volume ")
        resize_volume(source_box,target_box,volumes_pairs,volume,size)
        print "removing volumes from host"
        logging.info("removing volumes from host")
        deassign_vols_from_host(target_box,mapping_host_object,volumes_pairs)
        print "Recreating replication"
        logging.info("Recreating replication")
        new_rep=get_new_replica_json(replica_json)
        time.sleep(3)
        created=replica_create(source_box_name_or_fqdn, source_box_auth, target_box_auth,new_rep)
        if (created['error']):
        	logging.error(created['error'])
        	raise Exception(created['error'])
        print "Created. Done"
        logging.info("Created. Done")
    except Exception as E:
		print "Can't {}".format(E)
		logging.error("Can't {}".format(E))
