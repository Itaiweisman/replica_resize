from infinisdk import InfiniBox
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
	host=remotebox.hosts.find('name'=map_host)
	for vol in vol_list:
		remote_vol=remotebox.volumes.find('id'=vol)
		host.map_volume(remote_vol)
	return vol_list

def deassign_vols_from_host(map_host,vol_list):
	for vol in vol_list:
		host.unmap_volume(vol)

def resize_volume(box,volume,size):
	vol=box.volumes.find(name=volume).to_list()
	if vol:
		volume=vol[0]
		
if __name__ == '__main__':
	try:
	#Init source and target_box
		cg_id=get_cg_id(box,cg_name)
		replica=get_cg_replica(box,cg_id)
		volumes_to_assign=get_volumes_to_assign(replica)
		vols=assign_vols_to_host(target_box,map_host,volumes_to_assign)
		### Idan's part







