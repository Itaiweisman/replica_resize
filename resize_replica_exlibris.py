__author__  =  "Itai Weisman"

from infinisdk import InfiniBox
from capacity import *
import base64
import requests
import json
import pprint
from infinini import ibox_login, pass_decode

## Replcae the following with argparse
source_box_name_or_fqdn='ibox1499'
target_box_name_or_fqdn='ibox628'
map_host='kuku'
volume='XL1'
size=10*GiB
#
def get_vol_cg(box,vol):
	vol_object = box.volumes.find(name=vol).to_list()
	#print vol_object
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
		vol_list.append(dataset['remote_entity_id'])
		pairs[dataset['local_entity_id']]=dataset['remote_entity_id']
	return pairs


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
		remote_vol=remotebox.volumes.find(id=vol).to_list()

		if remote_vol:
			print "Adding {} to maplist ".format(remote_vol[0])
			map_list.append(remote_vol[0])
			pairs[vol]=remote_vol[0].get_id()
		else:
			print "Not remote vol {}".format(remote_vol)
			return None
	for vol_obj in map_list:
		print "mapping to {} vol {}".format(mapping_to.get_name(), vol_obj.get_name())
		mapping_to.map_volume(vol_obj)
	return mapping_to

def deassign_vols_from_host(box,map_host,vol_dict):
	for vol in vol_dict.values():
		print "vol to deassign {}".format(vol)
		to_remove=box.volumes.find(id=vol)
		if to_remove:
			print "removing {}".format(to_remove[0])
			map_host.unmap_volume(to_remove[0])

def resize_volume(sourcebox,remotebox,pairs,vol_to_resize,size):
	vol=sourcebox.volumes.find(name=volume).to_list()
	print vol[0].get_id()
	print pairs
	if vol:
		print "id is {}".format(pairs[vol[0].get_id()])
		paired=remotebox.volumes.find(id=pairs[vol[0].get_id()])
		if paired:
			print "Paired"
			print "volume to resize {} and {}".format(vol[0].get_name(), paired[0].get_name())
			#return(vol.resize(size))
			resize_source=vol[0].resize(size)
			resize_target=paired[0].resize(size)
			return resize_source and resize_target
	else:
		print "NO can't "
		return None


def replica_break(box_ip,local_credentials, remote_credentials, replica):
	creds=remote_credentials[0]+":"+remote_credentials[1]
	print "in replica break"
	hashed_auth='Basic ' + base64.b64encode(creds)
	#print hashed_auth
	url='http://'+box_ip+'/api/rest/replicas/'+str(replica.get_id())+'?approved=true'
	headers={'X-Remote-Authorization':hashed_auth}
	return requests.delete(url=url,auth=local_credentials,headers=headers).json()

def replica_create(source,local_auth,remote_auth,old_replica):
	#pprint.pprint(old_replica)
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
		new_item['remote_base_action']=item['remote_base_action']
		new_item['remote_entity_id']=item['remote_entity_id']
		new_item['local_base_action']=item['local_base_action']
		new_replica['entity_pairs'].append(new_item)
	return new_replica

		
		
		





if __name__ == '__main__':
	try:
		source_box, source_box_auth=ibox_login(source_box_name_or_fqdn)
		target_box, target_box_auth=ibox_login(target_box_name_or_fqdn)
		print "Getting CG Object"
		cg_object=get_vol_cg(source_box,volume)
		if (not cg_object):
			raise Exception("unable to get volume CG")
		print "CG is {}".format(cg_object.get_name())
		print "Getting CG ID"
		cg_id=cg_object.get_id()
		#print "cg id is {}".format(cg_id)
		print "Getting Replica"
		replica_object, replica_json=get_cg_replica(source_box,source_box_name_or_fqdn, source_box_auth, cg_id)
		print "Replica ID is {}".format(replica_object.get_id())
		if (not replica_object or replica_json['error']):	
			raise Exception("Unable to get Consistency Group Replica")
		#print replica_json
		
		volumes_pairs=get_volumes_to_assign(replica_object)
		print "volume pairs are {}, attempt to map".format(volumes_pairs)
		mapping_host_object=assign_vols_to_host(target_box,map_host,volumes_pairs)
		print "mapped to {}".format(mapping_host_object.get_name())
		if (not mapping_host_object):
			raise Exception("Unable to assign volumes to mount host")

		
		print "Breaking the replication Link"
		broken=replica_break(source_box_name_or_fqdn, source_box_auth, target_box_auth, replica_object)
		if broken['error']:
			raise Exception(broken['error'])
		print "Replication is broken"
		### Idan's part
		# 1. Rescan SCSI
		# 2. retreive devices from volumes
		# 3. run SCSI UNMAP against each
		# End of Idan's Part
		print "resizing volume "
		resize_volume(source_box,target_box,volumes_pairs,volume,size)
		#exit()
		print "deassinging volumes from map host"
		deassign_vols_from_host(target_box,mapping_host_object,volumes_pairs)
		print "Recreating replication"
		created=replica_create(source_box_name_or_fqdn, source_box_auth, target_box_auth,get_new_replica_json(replica_json))

		if (created['error']):
			raise Exception(created['error'])
		print "Created. Done"
	except Exception as E:
		print "Can't {}".format(E)








