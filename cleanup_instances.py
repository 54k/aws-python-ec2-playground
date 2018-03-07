#!/usr/bin/env python

import socket
import urllib2
from datetime import datetime, timedelta

import boto3
from botocore.exceptions import ClientError

ec2 = boto3.resource('ec2')


def deregister_outdated_images(timedelta_=timedelta(days=365)):
    for image in ec2.images.filter(Owners=['self']):
        image_creation_date = datetime.strptime(image.creation_date, '%Y-%m-%dT%H:%M:%S.000Z')
        if datetime.now() - image_creation_date > timedelta_:
            try:
                image.deregister()
            except ClientError:
                continue


def get_ip_by_dns_name(dns):
    return socket.gethostbyname(dns)


def find_instances_by_ip_and_terminate_if_needed(ip, dns):
    instances = []
    filters = [{'Name': 'ip-address', 'Values': [ip]}]
    query_result = list(ec2.instances.filter(Filters=filters))

    if not query_result:
        instances.append({
            'name': 'not found',
            'image_id': 'not found',
            'public_dns_name': dns,
            'status': 'unknown',
            'dns_health': dns_health_check_status(dns)
        })
        return instances

    for instance in query_result:
        instance_state_name = instance.state['Name']
        health_check_status = dns_health_check_status(dns)

        if instance_state_name == 'stopped' and try_create_image(instance):
            terminate(instance)
            instance_state_name = 'terminated'

        instances.append({
            'name': instance.instance_id,
            'image_id': instance.image_id,
            'public_dns_name': dns,
            'status': instance_state_name,
            'dns_health': health_check_status
        })

    return instances


def dns_health_check_status(dns_name):
    if dns_name == '':
        return 'no dns name'

    try:
        request = urllib2.Request('http://' + dns_name)
        urllib2.urlopen(request)
    except urllib2.HTTPError as e:
        if e.code != 500:
            return 'ok'
        else:
            return 'http error'
    except urllib2.URLError:
        return 'connection error'
    else:
        return 'ok'


def try_create_image(instance):
    try:
        image = instance.create_image(
            InstanceId=instance.instance_id,
            Name=instance.instance_id + '-' + datetime.now().strftime('%H%m%S%d%M%Y')
        )
        image.wait_until_exists()
        image_tag = {'Key': 'Created At',
                     'Value': 'For instance with id ' + instance.instance_id + ' at ' + datetime.now().strftime(
                         '%H:%m:%S %d/%M/%Y')}
        image.create_tags(
            Tags=[
                image_tag
            ]
        )
        return True
    except ClientError:
        return False


def terminate(instance):
    instance.terminate()
    instance.wait_until_terminated()


def print_instance(instance):
    name_ = instance['name']
    image_id_ = instance['image_id']
    dns_name_ = instance['public_dns_name']
    status_ = instance['status']

    if status_ == 'running':
        status_ = '\033[1;42m' + status_ + '\033[1;m'
    elif status_ == 'terminated':
        status_ = '\033[1;41m' + status_ + '\033[1;m'
    else:
        status_ = '\033[1;43m' + status_ + '\033[1;m'

    health_ = instance['dns_health']

    if health_ == 'ok':
        health_ = '\033[1;42m' + health_ + '\033[1;m'
    elif health_ == 'no dns name':
        health_ = '\033[1;43m' + health_ + '\033[1;m'
    else:
        health_ = '\033[1;41m' + health_ + '\033[1;m'

    print name_, image_id_, dns_name_, status_, health_


# hue hue hue
deregister_outdated_images(timedelta(days=7))

instance_list = []
for t in [(get_ip_by_dns_name(d.strip()), d.strip()) for d in open('domain.list', 'r')]:
    res = find_instances_by_ip_and_terminate_if_needed(t[0], t[1])
    instance_list.extend(res)

[print_instance(i) for i in instance_list]
