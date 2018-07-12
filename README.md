# replica_resize 

## Prerequisites
The script requiers the following packages to be installed: 
* gcc
* python-devel

On fedora distributions this can be done using: `yum install -y gcc python-devel`

The script requiers the following python modules to be installed:
* infinisdk
* infi.storagemodel

These can be install using `pip install `

please also install  [Infinidat's Host Power Tools](https://repo.infinidat.com/home/main-stable#host-power-tools) on the relevant host and make sure its prepared for volumes to be mapped to it.

## Authentication
Make sure to prepare two credential files, each representing the source and target machines.
file name should be in the following syntax:
`.<ibox>.sec`
and its content should include:

`username password`

password should be encrypted using base64

## Config File
please use the attached config file for host and source/target system defintion.


## Usage
```
usage: resize_replica.py [-h]  -v VOLUME -i SIZE

Resize a replicated volume that is a member of a cg.

optional arguments:
  -h, --help            show this help message and exit
  -v VOLUME, --volume VOLUME
                        The volume name to resize
  -i SIZE, --increaseby SIZE
                        Size to be increased by (in Gib)

```
## Example
`python resize_replica.py -v vol60gx -i 5`



