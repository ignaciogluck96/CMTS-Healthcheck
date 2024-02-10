# coding: utf-8
########################################################################################################################
###########################################                       ######################################################
###########################################  READ ONLY LIBRARIES  ######################################################
###########################################                       ######################################################
########################################################################################################################
import json
import logging
import os
import sys
sys.path.append(os.path.dirname(__file__))
log = logging.getLogger(__name__)
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators import MyInstanceInitOperator, MyInstanceExitOperator, MyPythonOperator, DummyOperator, MyBranchOperator, MyAnsiblePlaybookOperator
from airflow.utils.trigger_rule import TriggerRule
from airflow.exceptions import AirflowException
from my_lib import *
from my_error_management import MyWorkflowErrorManagement
from my_success_management import MyWorkflowSuccessManagement
from my_runtime import * 
########################################################################################################################
#######################################                                  ###############################################
#######################################  CUSTOM LIBRARIES AND VARIABLES  ###############################################
#######################################                                  ###############################################
########################################################################################################################

try:
    import usecase
except ImportError:
    pass

########################################################################################################################
##############################################                  ########################################################
##############################################  DAG DEFINITION  ########################################################
##############################################                  ########################################################
########################################################################################################################


default_args = {
    'owner': 'Iquall',
    'depends_on_past': False,
    'provide_context': True
}

dag = DAG(dag_id='es4-88j-6iy', description='', start_date=datetime(2021,10,20), schedule_interval=None, catchup=False, on_failure_callback=MyWorkflowErrorManagement, on_success_callback=MyWorkflowSuccessManagement, default_args=default_args)


########################################################################################################################
##############################################                    ######################################################
##############################################  CUSTOM FUNCTIONS  ######################################################
##############################################                    ######################################################
########################################################################################################################
        
def load_variables(**kwargs):
    job = kwargs.get("job")
    job.progress = 20
    form = getForm(kwargs)
    
    inv = Inventory()
    
    # Key functions (kwargs, The name of the environment variable, The value of the environment variable)
    # Call as many times as needed for environment variables
    # setEnvironment(kwargs, "hosts", groupedHosts)
    # setRuntime(kwargs, "hosts", ips_list)
    
    return True


def write_influx_partial_stats(**kwargs):
    job = kwargs.get("job")
    task_id = kwargs["task_instance"].task.task_id
    task_path = MyDirectories(kwargs).task(task_id)
    job.log.info("Task Path: " + task_path)

    # It now always reads the same file, then we need to make sure files are saved with name <hostname_variables.json> and insert/update the corresponding one
    files = glob.glob(task_path + "/*_variables.json")
    
    for file in files:
        json_file = open(file, "r")
        contents = json_file.read()
        variables = json.loads(contents)
        
        sh_env = eval(variables['sh_env']) #eval(variables['cmts_summary'][i])
        cmts_summary = eval(variables['cmts_summary']) #eval(variables['cmts_summary'][i])
        hostname = variables['hostname'] #variables['hostname'][i]
        vendor = variables['vendor'] #variables['hostname'][i]
        
        nodes_affected_per_cmts = {}
        nodes_not_affected_per_cmts = {}
        pems_affected_per_cmts = {}
        pems_not_affected_per_cmts = {}
        
        nodes_affected_per_cmts[hostname] = []
        nodes_not_affected_per_cmts[hostname] = []
        pems_affected_per_cmts[hostname] = []
        pems_not_affected_per_cmts[hostname] = []
        
        # Missing loop to iterate through all hosts of the vendor
        
        # Node iteration
        for interface in cmts_summary:
            if interface['Offline'] == '':
                interface['Offline'] = str(int(interface['Total']) - int(interface['Active']))
            
            if int(interface['Total']) != 0:
                offline_percentage = int(float(int(interface['Offline'])) * 100 / float(int(interface['Total'])))
            else:
                offline_percentage = 0
                
            if offline_percentage >= 10:
                nodes_affected_per_cmts[hostname].append(interface['INTERFACE'])
            else:
                nodes_not_affected_per_cmts[hostname].append(interface['INTERFACE'])
                
        for pem in sh_env:
            if pem['state'] == 'WARNING':
                pems_affected_per_cmts[hostname].append(pem['name'])
            if pem['state'] == 'NORMAL':
                pems_not_affected_per_cmts[hostname].append(pem['name'])
            
                
        print(pems_affected_per_cmts)
        print(pems_not_affected_per_cmts)
        
        setRuntime(kwargs, "nodes_affected_per_cmts_" + vendor, nodes_affected_per_cmts[hostname]) # Hardcoded, remove the hostname index and send by vendor
        setRuntime(kwargs, "nodes_not_affected_per_cmts_" + vendor, nodes_not_affected_per_cmts[hostname])
        setRuntime(kwargs, "pems_affected_per_cmts" + vendor, pems_affected_per_cmts[hostname]) # Hardcoded, remove the hostname index and send by vendor
        setRuntime(kwargs, "pems_not_affected_per_cmts" + vendor, pems_not_affected_per_cmts[hostname])
        
    return True
    
    
def write_influx_total_stats(**kwargs):
    job = kwargs.get("job")
    task_id = kwargs["task_instance"].task.task_id
    task_path = MyDirectories(kwargs).task(task_id)
    job.log.info("Task Path: " + task_path)
    
    nodes_affected = []
    nodes_affected_per_vendor = {}
    nodes_not_affected_per_vendor = {}
    
    total_nodes_affected_counter = 0
    total_nodes_not_affected_counter = 0
        
    vendors = ['cisco','casa_systems','arris']

    for vendor in vendors:
        nodes_affected_per_vendor[vendor] = getRuntime(kwargs, "nodes_affected_per_cmts_" + vendor)
        nodes_not_affected_per_vendor[vendor] = getRuntime(kwargs, "nodes_not_affected_per_cmts_" + vendor)
    
    tags = dict(description = 'CMTS Cisco Affection')
    fields = {'OFFLINE': len(nodes_affected_per_vendor['cisco']), 'OK': len(nodes_not_affected_per_vendor['cisco'])}
    mat_write_influx(measurement = 'CMTS Cisco Affection', tags=tags, fields=fields)

    tags = dict(description = 'CMTS Casa Systems Affection')
    fields = {'OFFLINE': len(nodes_affected_per_vendor['casa_systems']), 'OK': len(nodes_not_affected_per_vendor['casa_systems'])}
    mat_write_influx(measurement = 'CMTS Casa Systems Affection', tags=tags, fields=fields)

    tags = dict(description = 'CMTS Arris Affection')
    fields = {'OFFLINE': len(nodes_affected_per_vendor['arris']), 'OK': len(nodes_not_affected_per_vendor['arris'])}
    mat_write_influx(measurement = 'CMTS Arris Affection', tags=tags, fields=fields)
    
    total_nodes_affected_counter = len(nodes_affected_per_vendor['cisco']) + len(nodes
