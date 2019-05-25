import boto3
import botocore
from datetime import datetime
import json
import time

ec2_client = boto3.client('ec2')
ec2_res = boto3.resource('ec2')
asg_client = boto3.client('autoscaling')

def lambda_handler(event, context = None):
  """ 
  Lambda Handler

  Takes the event from asg life cycle hook and attach secondary eni

  :param event: takes event triggered by cloudwatch rule from asg
  """
  
  # printing event received:
  log(f'event received: {event}')

  event_type = event["detail-type"]

  if event_type == "EC2 Instance-launch Lifecycle Action":
    try:
      instance_id = event["detail"]["EC2InstanceId"]
      life_cycle_hook_name = event['detail']['LifecycleHookName']
      auto_scaling_group_name = event['detail']['AutoScalingGroupName']

      # getting instance id
      interface_name = get_interface_name(instance_id)
      
      if not instance_name or instance_name is None:
        raise Exception("Error finding the instance name for {} : {}".format(instance_id,e.response['Error']['Code']))

      # getting network interface
      network_interface = get_interface(eni_desc=interface_name)
      if not network_interface or network_interface is None:
        raise Exception("Error finding the network interface for {} : {}".format(interface_name,e.response['Error']['Code']))

      network_interface_id = network_interface['NetworkInterfaces'][0]['NetworkInterfaceId']
      network_interface_status = network_interface['NetworkInterfaces'][0]['Status']

      # checking status
      if network_interface_status != 'available':
        log("Not Available so Detaching it first.")
        network_attachment_id = network_interface['NetworkInterfaces'][0]['Attachment']['AttachmentId']

        # check if detachment is successful
        if not detach_eni(network_interface_id, instance_id,network_attachment_id):
            complete_lifecycle_action_failure(life_cycle_hook_name, auto_scaling_group_name, instance_id)
            raise Exception(
              "Unable to detach interface"
            )
      else:
        log('ENI Already Available so attaching it')
        attachment = attach_interface(network_interface_id,instance_id,device_index=1)

        if not attachment:
          complete_lifecycle_action_failure(life_cycle_hook_name, auto_scaling_group_name, instance_id)
          raise Exception("Unable to attach interface {}". format(interface))

      try:
        complete_lifecycle_action_success(life_cycle_hook_name, auto_scaling_group_name, instance_id)
      except botocore.exceptions.ClientError as e:
        complete_lifecycle_action_failure(life_cycle_hook_name, auto_scaling_group_name, instance_id)
        raise Exception("Error completing life cycle hook for instance {}: {}".format(instance_id,e.response['Error']['Code']))

    except botocore.exceptions.ClientError as e:
      log(str(e))
    except Exception as e:
      log(str(e))
 
  else:
    log("Irrelevant Event Identified")

def get_interface_name(instance_id):
  """
  read tags from instance and fetch specific tag value which contains interface description i.e. Eth1

  :param instance_id: Instance id of the instance launch by asg life cycle event
  """
  try:
      instance = ec2_res.Instance(instance_id)
      interface_name = next((item['Value'] for item in instance.tags if item['Key'] == 'Eth1'), None)
      log ("Interface name {}".format(instance_name))

  except botocore.exceptions.ClientError as e:
      raise Exception("Error describing the instance {} : {}".format(instance_id,e.response['Error']['Code']))
      interface_name = None
  
  return interface_name

def get_interface(eni_desc):
  """ 
  Match eni description and return that eni

  :param eni_desc: eni description to match with network interfaces list
  """

  network_interface = None
  try:
      network_interface = ec2_client.describe_network_interfaces(Filters=[{'Name':'description','Values':[eni_desc]}])
      
      # network_interface_id = network_interface['NetworkInterfaces'][0]['NetworkInterfaceId']
      log("Found network interface: {}".format(network_interface))
  except botocore.exceptions.ClientError as e:
      log("Error retrieving network interface: {}".format(e.response['Error']['Code']))
      raise Exception("Error retrieving network interface: {}".format(e.response['Error']['Code']))
      
  return network_interface

def detach_eni(network_interface_id, instance_id, attachment_id):
  """
  detach network interface if it's attached to instance

  :param network_interface_id: network interface id that 
                               we get from network interface description 
                               which we get from instance tag

  :param instance_id: Instance id of the instance launch by asg life cycle event
  """

  # Retry logic:
  count = 0
  while count <= 5:
    try:
      detachment_eni = ec2_client.detach_network_interface(
          AttachmentId=attachment_id,
          Force=True
      )
      log("Detaching ENI", detachment_eni)
      
      if detachment_eni['ResponseMetadata']['HTTPStatusCode'] == 200:
        log("Detached Successfuly")
        attachment = attach_interface(network_interface_id,instance_id,device_index=1)
        if attachment:
          return True
        else: 
          return False
      else:
        count = count + 1
        time.sleep(10)
          
    except botocore.exceptions.ClientError as e:
      if count >= 5: 
        raise Exception ("Error detaching eni {}: {}".format(attachment_id,e.response['Error']['Code']))
      else:
        count = count + 1
        time.sleep(10)

  return False

def attach_interface(network_interface_id, instance_id, device_index):

  attachment = None
  count = 0
  if network_interface_id and instance_id:
    # retry logic
    while count <= 5:
      try:
        log(f'Trying to attach retry: {count}')
        attach_elastic_interface = ec2_client.attach_network_interface (
            NetworkInterfaceId = network_interface_id,
            InstanceId = instance_id,
            DeviceIndex = device_index
        )
        log(f'Attach_interface {attach_elastic_interface}')
        attachment = attach_elastic_interface['AttachmentId']
        log("Created network attachment: {}".format(attachment))
        
        if attachment:
          return attachment
        else:
          count = count + 1
          time.sleep(10)
      except botocore.exceptions.ClientError as e:
        if count >= 5: 
          raise Exception ("Error attaching interface: {}:{}".format(e.response['Error']['Code'], e.response['Error']['Message']))
        else:
          count = count + 1
          time.sleep(10)
    return False

def complete_lifecycle_action_success(hookname,groupname,instance_id):
  """ 
  Complete Lifecycle Action Success

  Complete the lifecycle with success if no exception occurs

  :param hookname: Life cycle hook name
  :param groupname: Autoscaling group name
  :param instanceid: Instance id for newly launched instance

  """

  try:
      asg_client.complete_lifecycle_action(
              LifecycleHookName=hookname,
              AutoScalingGroupName=groupname,
              InstanceId=instance_id,
              LifecycleActionResult='CONTINUE'
          )
      log("Lifecycle hook CONTINUEd for: {}".format(instance_id))
  except botocore.exceptions.ClientError as e:
      raise Exception("Error completing life cycle hook for instance {}: {}".format(instance_id, e.response['Error']))
            
def complete_lifecycle_action_failure(hookname,groupname,instance_id):
  """ 
  Complete Lifecycle Action Failure

  Complete the lifecycle with failure if exception occurs

  :param hookname: Life cycle hook name
  :param groupname: Autoscaling group name
  :param instanceid: Instance id for newly launched instance

  """
  try:
      asg_client.complete_lifecycle_action(
              LifecycleHookName=hookname,
              AutoScalingGroupName=groupname,
              InstanceId=instance_id,
              LifecycleActionResult='ABANDON'
          )
      log("Lifecycle hook ABANDONed for: {}".format(instance_id))
  except botocore.exceptions.ClientError as e:
      raise Exception("Error completing life cycle hook for instance {}: {}".format(instance_id, e.response['Error']))
          
def log(message):
  """ 
  Log

  takes message as an input and print it with time in iso format 
  """
  print (datetime.utcnow().isoformat() + 'Z ' + message)  
