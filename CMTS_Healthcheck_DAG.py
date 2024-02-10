# Description:
# This Python script contains a Directed Acyclic Graph (DAG) for performing routine health checks on Cable Modem Termination Systems (CMTS)
# within a network infrastructure. The script utilizes Apache Airflow, a platform for programmatically authoring, scheduling, and monitoring workflows,
# to orchestrate the execution of various tasks involved in the health check process.
#
# Key Features:
# 1. Modular Architecture: The script is organized into modular components, allowing for easy maintenance, scalability, and reuse of code.
# 2. Custom Libraries: Custom libraries such as my_lib, my_error_management, and my_success_management provide error handling,
#    success management, and runtime functionalities tailored to the specific requirements of the health check workflow.
# 3. Task Definitions: Tasks are defined for initializing the workflow (MyInstanceInitOperator), executing health checks on Cisco,
#    Casa Systems, and Arris CMTS devices using Ansible playbooks (MyAnsiblePlaybookOperator), and finalizing the workflow (MyInstanceExitOperator).
#    Additionally, a task (MyPythonOperator) is included for aggregating and writing partial and total statistics to an InfluxDB database.
# 4. Environment Configuration: The script supports loading variables from the environment to customize the health check process based on specific configurations.
# 5. Error Handling and Logging: Comprehensive error handling mechanisms are implemented to ensure robustness and reliability during task execution.
#    Detailed logging is provided to track the progress and status of each task.
#
# Usage:
# To execute the CMTS health check workflow, deploy the script within an Apache Airflow environment and schedule the DAG (es4-88j-6iy) accordingly.
# Ensure that the required dependencies, such as Ansible playbooks and custom libraries, are accessible to the Airflow environment.
#
# Note: This script serves as a foundation for automating the health check process of CMTS devices, offering flexibility for customization and extension
# to meet specific network monitoring requirements.



# coding: utf-8
########################################################################################################################
###########################################                       ######################################################
###########################################  READ ONLY LIBRARIES  ######################################################
###########################################                       ######################################################
########################################################################################################################
import json, logging, os, sys
sys.path.append(os.path.dirname(__file__))
log = logging.getLogger(__name__)
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators import MyInstanceInitOperator, MyInstanceExitOperator, MyPythonOperator, DummyOperator, MyBranchOperator, MyAnsiblePlaybookOperator
from airflow.utils.trigger_rule import TriggerRule
from airflow.exceptions import AirflowException
from mylib import *
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
except:
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

dag = DAG(dag_id='MY_DAG', description='', start_date=datetime(2021,10,20), schedule_interval=None, catchup=False, on_failure_callback=MyWorkflowErrorManagement, on_success_callback=MyWorkflowSuccessManagement, default_args=default_args)


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

    # The key functions (kwargs, The name of the environment variable, The value of the environment variable)
    # Call as many times as needed for environment variables
    # setEnvironment(kwargs, "hosts", groupedHosts)
    # setRuntime(kwargs, "hosts", ips_list)

    return True


def write_influx_partial_stats(**kwargs):
    job = kwargs.get("job")
    task_id = kwargs["task_instance"].task.task_id
    task_path = MyDirectories(kwargs).task(task_id)
    job.log.info("Task Path: " + task_path)

    # Always read the same file for now, then files should be saved with name <hostname_variables.json> and insert/update the corresponding one
    files = glob.glob(task_path + "/*_variables.json")



    for file in files:
        json_file = open(file, "r")
        contents = json_file.read()
        hosts = json.loads(contents)

        cmts_list_per_vendor = []
        nodes_per_cmts = {}
        interfaces_per_cmts = {}

        # For each host of the same vendor
        for host in hosts:
            cmts_summary = eval(host['cmts_summary'])
            hostname = host['hostname']
            vendor = host['vendor']

            print("\nHostname: " + hostname)
            #print("\nCMTS summary: " + str(cmts_summary))
            print("\n"+ vendor)

            cmts = {'hostname': hostname, 'interfaces': [], 'nodes': [], 'total': 0, 'active': 0, 'offline': 0, 'number_nodes_degraded': 0, 'number_nodes_affected': 0, 'number_nodes_optimum': 0}

            nodes_per_cmts[hostname] = []
            interfaces_per_cmts[hostname] = []

            # Grouping and structure of a node
            nodes = {}
            interfaces = []
            for parsed_interface in cmts_summary:

                # Extracting data
                interface_name = parsed_interface['INTERFACE']
                total = int(parsed_interface['Total'])
                active = int(parsed_interface['Active'])
                if parsed_interface['Offline'] == '':
                    offline = total - active
                else:
                    offline = int(parsed_interface['Offline'])

                # Calculation of offline percentage of the interface
                if total != 0:
                    offline_percentage = int(float(offline) * 100 /  float(total))
                else:
                    offline_percentage = 0
                interface = {'interface': interface_name, 'total': total, 'active': active, 'offline': offline, 'percentage': offline_percentage}
                interfaces.append(interface)

                # Adding data to the cmts dict
                cmts['interfaces'].append(interface_name)
                cmts['total'] += total
                cmts['active'] += active
                cmts['offline'] += offline
                # Adding interface to the node dict
                node_name = parsed_interface['Description']
                if node_name == ' ' or node_name == '':
                    node_name = 'NO_NAME'
                if node_name not in nodes.keys():
                    nodes[node_name] = {}
                    node_interfaces = []
                    node_interfaces.append(interface_name)
                    nodes[node_name] = {'interfaces': node_interfaces, 'total': total, 'active': active, 'offline': offline}
                else:
                    nodes[node_name]['interfaces'].append(interface_name)
                    nodes[node_name]['total'] += total
                    nodes[node_name]['active'] += active
                    nodes[node_name]['offline'] += offline

            # Calculation of offline percentage of the nodes
            for node_name, node_data in nodes.items():
                if node_data['offline'] != 0:
                    node_data['percentage'] = int(float(node_data['offline']) * 100 /  float(node_data['total']))
                else:
                    node_data['percentage'] = 0
                if (node_data['percentage'] >= 10) and (node_data['percentage'] < 100):
                    node_data['state'] = 'DEGRADED' #####################
                    cmts['number_nodes_degraded'] += 1
                elif node_data['percentage'] == 100:
                    node_data['state'] = 'AFFECTED' #########################
                    cmts['number_nodes_affected'] += 1
                else:
                    node_data['state'] = 'OPTIMUM'
                    cmts['number_nodes_optimum'] += 1

                cmts['nodes'].append(node_name)

            nodes_per_cmts[hostname] = nodes
            interfaces_per_cmts[hostname] = interfaces

            # Calculation of offline percentage of the cmts
            for node_name, node_data in nodes.items():
                if cmts['offline'] != 0:
                    cmts['percentage'] = int(float(cmts['offline']) * 100 /  float(cmts['total']))
                else:
                    cmts['percentage'] = 0

            cmts_list_per_vendor.append(cmts)

        print('\n\nnodes_per_cmts:\n')
        print(json.dumps(nodes_per_cmts, indent=4))
        print('\n\ninterfaces_per_cmts:\n')
        print(json.dumps(interfaces_per_cmts, indent=4))
        print('\n\ncmts_list_per_vendor:\n')
        print(json.dumps(cmts_list_per_vendor, indent=4))

        setRuntime(kwargs, "cmts_list_per_vendor_" + vendor, cmts_list_per_vendor)
        setRuntime(kwargs, "nodes_per_vendor_" + vendor, nodes_per_cmts)
        setRuntime(kwargs, "interfaces_per_vendor_" + vendor, interfaces_per_cmts)

    return True


def write_influx_total_stats(**kwargs):
    job = kwargs.get("job")
    task_id = kwargs["task_instance"].task.task_id
    task_path = MyDirectories(kwargs).task(task_id)
    job.log.info("Task Path: " + task_path)

    cmts_list_per_vendor = {}
    nodes_per_vendor = {}
    interfaces_per_vendor = {}

    for vendor in ['Vendor1', 'Vendor2', 'Vendor3']:
        cmts_list_per_vendor[vendor] = getRuntime(kwargs, "cmts_list_per_vendor_" + vendor)
        nodes_per_vendor[vendor] = getRuntime(kwargs, "nodes_per_vendor_" + vendor)
        interfaces_per_vendor[vendor] = getRuntime(kwargs, "interfaces_per_vendor_" + vendor)

    total_cmts = {'affected_list': [], 'number_cmts_affected': 0, 'number_cmts_optimum': 0, 'number_cmts_degraded': 0}

    # Send data for each CMTS
    exit = False
    for vendor in ['Vendor1', 'Vendor2', 'Vendor3']:
        for cmts in cmts_list_per_vendor[vendor]:
            if cmts['percentage'] >= 10:
                total_cmts['affected_list'].append(cmts['hostname'])
                total_cmts['number_cmts_affected'] += 1
                cmts['state'] = 'AFFECTED'
            else:
                if cmts['number_nodes_affected'] + cmts['number_nodes_degraded'] > 0:
                    total_cmts['number_cmts_degraded'] += 1
                    cmts['state'] = 'DEGRADED'
                else:
                    total_cmts['number_cmts_optimum'] += 1
                    cmts['state'] = 'OPTIMUM'

            tags = dict(VENDOR = vendor, HOSTNAME = cmts['hostname'])
            fields = {'TOTAL MODEMS': cmts['total'], 'ONLINE': cmts['active'], 'OFFLINE': cmts['offline'], 'PERCENTAGE': cmts['percentage'], 'NODES NOT OPTIMUM': cmts['number_nodes_affected'] + cmts['number_nodes_degraded'], 'STATE': cmts['state']}
            my_write_influx(measurement = 'PER CMTS STATUS', tags=tags, fields=fields)

    print('\n\ntotal_cmts:\n')
    print(json.dumps(total_cmts, indent=4))

    tags = {}
    fields = {'AFFECTED': total_cmts['number_cmts_affected'], 'DEGRADED': total_cmts['number_cmts_degraded'], 'OPTIMUM': total_cmts['number_cmts_optimum']}
    my_write_influx(measurement = 'TOTAL CMTS STATUS', tags=tags, fields=fields)

    # Send data per node
    for vendor in ['Vendor1', 'Vendor2', 'Vendor3']:
        for cmts_name, cmts_data in nodes_per_vendor[vendor].items():
            for node_name, node_data in cmts_data.items():
                tags = dict(VENDOR = vendor, HOSTNAME = cmts_name, NODE = node_name)
                fields = {'TOTAL MODEMS': node_data['total'], 'ONLINE': node_data['active'], 'OFFLINE': node_data['offline'], 'PERCENTAGE': node_data['percentage'], 'STATE': node_data['state']}
                my_write_influx(measurement = 'PER NODE STATUS', tags=tags, fields=fields)

    # Send data per node
    total_nodes_affected = 0
    total_nodes_optimum = 0
    total_nodes_degraded = 0
    for vendor in ['Vendor1', 'Vendor2', 'Vendor3']:
        for cmts in cmts_list_per_vendor[vendor]:
            total_nodes_affected += cmts['number_nodes_affected']
            total_nodes_optimum += cmts['number_nodes_optimum']
            total_nodes_degraded += cmts['number_nodes_degraded']


    tags = {}
    fields = {'AFFECTED': total_nodes_affected, 'DEGRADED': total_nodes_degraded, 'OPTIMUM': total_nodes_optimum}
    my_write_influx(measurement = 'TOTAL NODES STATUS', tags=tags, fields=fields)


    return True
################################################################################################################
###############################################  BRANCHING  ####################################################
################################################################################################################

# detectCase = MyBranchOperator(task_id='Routine_Select', python_callable=detect_case, provide_context=True, dag=dag)

########################################################################################################################
###############################################                     ####################################################
###############################################  TASKS DEFINITIONS  ####################################################
###############################################                     ####################################################
########################################################################################################################


init = MyInstanceInitOperator(task_id='My_Initialize', dag=dag)

Vendor1_CMTS = MyAnsiblePlaybookOperator(
    task_id = 'Vendor1_CMTS',
    playbook = 'vendor1_pb.yml',
    load_environment = load_variables,
    process_output = write_influx_partial_stats,
    keep_run_files = True,
    #limitQuery = f"data.networkRole.data.name=CMTS&data.vendorModel.data.vendor=Vendor1"
    dag=dag
)

Vendor2_CMTS = MyAnsiblePlaybookOperator(
    task_id = 'Vendor2_CMTS',
    playbook = 'vendor2_pb.yml',
    load_environment = load_variables,
    process_output = write_influx_partial_stats,
    keep_run_files = True,
    #limitQuery = f"data.networkRole.data.name=CMTS&data.vendorModel.data.vendor=Vendor2"
    dag=dag
)

Vendor3_CMTS = MyAnsiblePlaybookOperator(
    task_id = 'Vendor3_CMTS',
    playbook = 'vendor3_pb.yml',
    load_environment = load_variables,
    process_output = write_influx_partial_stats,
    keep_run_files = True,
    #limitQuery = f"data.networkRole.data.name=CMTS&data.vendorModel.data.vendor=Vendor3",
    dag=dag
)

Get_Stats_CMTS = MyPythonOperator(
    task_id = 'Get_Stats_CMTS',
    python_callable=write_influx_total_stats,
    dag=dag
)


end = MyInstanceExitOperator(task_id='My_Finalize', trigger_rule='one_success', dag=dag)


########################################################################################################################
################################################                  ######################################################
################################################  TASKS WORKFLOW  ######################################################
################################################                  ######################################################
########################################################################################################################

init >> [Vendor1_CMTS, Vendor2_CMTS, Vendor3_CMTS] >> Get_Stats_CMTS >> end
