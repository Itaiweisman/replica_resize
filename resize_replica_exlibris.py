from infinisdk import InfiniBox
from capacity import *
import base64
import requests
import json

#from infinini import 

def get_cg_id(box,cg_name):
	cg=box.cons_groups.find(name=cg_name).to_list()[0]
	cg_id=cg.get_field('id')
	replicated=cg.get_field('replicated')
	if (cg_id and replicated):
		return cg_id
	else:
		return Null

def get_cg_replica(box,cg_id):
	replicas=box.replicas.to_list()
	for replica in replicas:
		cur_id=eplica.get_field('entity_pairs')[0]['local_entity']['cg_id']
		myreplica=Null
		if cur_id == cg_id:
			myreplica=replica
			break
	return myreplica

def get_volumes_to_assign(replica):
	vol_list=[]
	for dataset in replica.get_field('entity_pairs'):
		vol_list.push(dataset['remote_id_pair'])
	return vol_list


def assign_vols_to_host(remotebox,map_host,vol_list):
	host=remotebox.hosts.find(name=map_host)
	for vol in vol_list:
		remote_vol=remotebox.volumes.find(id=vol)
		host.map_volume(remote_vol)
	return vol_list

def deassign_vols_from_host(map_host,vol_list):
	for vol in vol_list:
		host.unmap_volume(vol)

def resize_volume(box,volume,size):
	vol=box.volumes.find(name=volume).to_list()
	if vol:
		return(vol.resize(size))


def replica_break(box_ip,local_credentials, remote_credentials, replica):
	hashed_auth='Basic ' + base64.b64encode(remote_credentials)
	print hashed_auth
	url='http://'+box_ip+'/api/rest/replicas/'+str(replica.get_id())+'?approved=true'
	headers={'X-Remote-Authorization':hashed_auth}
	return requests.delete(url=url,auth=local_credentials,headers=headers).json()

def get_new_replica_json(old_replica):
	new_replica={}
	new_replica['local_cg_id']=old_replica['result']['local_cg_id']
	new_replica['remote_cg_id']=old_replica['result']['remote_cg_id']
	new_replica['entity_type']=old_replica['result']['entity_type']
	new_replica['replication_type']=old_replica['result']['replication_type']
	new_replica['rpo_type']=old_replica['result']['replication_type']
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
	#Init source and target_box
		#cg_id=get_cg_id(box,cg_name)
		#replica=get_cg_replica(box,cg_id)
		#volumes_to_assign=get_volumes_to_assign(replica)
		#vols=assign_vols_to_host(target_box,map_host,volumes_to_assign)
		box_name='ibox1499'
		auth=('iscsi','123456')
		remote_auth='admin:123456'
		box_object=InfiniBox(box_name,auth)
		box_object.login()
		box_replicas=box_object.replicas.to_list()
		our_replica=box_object.replicas.get(id='90415')
		result=replica_break(box_name,auth,remote_auth,our_replica)
		print result
		### Idan's part
	except Exception as E:
		print "Can't {}".format(E)








