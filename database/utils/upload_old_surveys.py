import os
import sys
import logging
import time
import datetime as dt
import os.path
import tarfile
import psycopg2
import boto3
from glob import glob
from boto3.s3.transfer import TransferConfig
import urllib3.request
import importlib.util
spec = importlib.util.spec_from_file_location("Objectstore", "/home/ger063/Objectstore/get_access_keys.py")
foo = importlib.util.module_from_spec(spec)
sys.modules["Objectstore.get_access_keys"] = foo
spec.loader.exec_module(foo)

from Objectstore.get_access_keys import *
from db_interface import *

endpoint = 'https://projects.pawsey.org.au'
project = 'askap'
bucket = "flash-pilot2-spectra"
my_certs_file = "/home/ger063/my_certs.json"
exclude_sbids = [33616,34546,34547,34548,34549,34551,34552,34553,34554,34555,37797,34556, 34557, 34558, 34559, 34560, 34561, 34562, 34563, 34564, 34565, 34566, 34567, 34568, 34569, 34570, 34571, 34572, 34576, 34577, 34578, 34580, 34581, 34584, 34597, 34781, 34783, 34917, 34939, 34941, 35939, 35943, 37431, 37432, 37448, 37449, 37450, 37451, 37452, 37453, 37475]

def get_list_of_tars(client,bucket,seed,suffix='.tar'):
    
    tar_list = [f['Key'] for f in client.list_objects_v2(Bucket=bucket)['Contents'] if seed in f['Key'] and f['Key'].endswith(suffix)]
    for sbid in exclude_sbids:
        for tar in tar_list:
            if str(sbid) in tar:
                tar_list.remove(tar)
    return tar_list

def get_tarball(client,bucket,key,filename):
    
    with open(filename,'wb') as data:
        client.download_fileobj(bucket,key,data)
    
def process_tarball(conn,sbids):
    dataDict = createDataDir(sbids=sbids)
    cur = add_spect_run(conn,SBIDS=sbids,
                        config_dir="",
                        errlog="",
                        stdlog="",
                        dataDict=dataDict,
                        platform="magnus.pawsey.org.au")
    
    return cur

if __name__ == "__main__":

    starttime = time.time()
    (ja3_access_id,ja3_secret_id,quota) = get_access_keys(my_certs_file,endpoint,project)

    client = boto3.client(service_name='s3',aws_access_key_id=ja3_access_id,aws_secret_access_key=ja3_secret_id, endpoint_url=endpoint)
    tar_list = get_list_of_tars(client,bucket,"flash-pilot2-reobs-SB")
    conn = connect()
    sbids = []
    tarnames = glob("./*.tar")
    for tar in tar_list:
        if tar in tarnames:
            print(f"Using existing {tar}")
        else:
            print(f"Retrieving {tar} from Acacia")
            get_tarball(client,bucket,tar,tar)
        print(f"Processing {tar}")
        sbid = int(tar.split("SB")[1][:5])
        sbids.append(sbid)
        print(sbid)
        os.system(f"tar -xvf {tar}")
        cur = process_tarball(conn,[sbid])
        conn.commit()
        os.system(f"rm -R {sbid}* {tar}")
        cur.close()
    conn.close()
    print(f"Job took {time.time()-starttime} sec for {len(sbids)} sbids {sbids}")

