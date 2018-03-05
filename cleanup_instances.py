#!/usr/bin/env python

import urllib2
from datetime import datetime, timedelta

import boto3
from botocore.exceptions import ClientError

ec2 = boto3.resource('ec2')


def cleanup_images_older_than(timedelta_=timedelta(days=365)):
    for image in ec2.images.all():
        image_creation_date = datetime.strptime(image.creation_date, '%Y-%m-%dT%H:%M:%S.000Z')
        if datetime.now() - image_creation_date > timedelta_:
            try:
                image.deregister()
            except ClientError as e:
                continue


def terminate_stopped_instances():
    instances = []
    for instance in ec2.instances.all():
        instance_state_name = instance.state['Name']
        health_check_status = dns_health_check_status(instance.public_dns_name)

        if instance_state_name == 'stopped':
            image_created = create_image(instance)
            if image_created:
                terminate(instance)
                instance_state_name = 'terminated'

        instances.append(
            {
                'name': instance.instance_id,
                'image_id': instance.image_id,
                'public_dns_name': instance.public_dns_name,
                'status': instance_state_name,
                'dns_health': health_check_status
            }
        )

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
    except urllib2.URLError as e:
        return 'connection error'
    else:
        return 'ok'


def create_image(instance):
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
    except ClientError as e:
        return False


def terminate(instance):
    instance.terminate()
    instance.wait_until_terminated()


def print_instances(instances):
    for instance in instances:
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

        print name_, \
            image_id_, \
            dns_name_, \
            status_, \
            health_


instance_list = terminate_stopped_instances()
cleanup_images_older_than(timedelta(days=7))
print_instances(instance_list)
