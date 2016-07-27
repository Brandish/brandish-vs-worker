from datetime import date
from fabric.api import *
from fabric.operations import *
from boto import ec2


STAGING_IP = '52.2.52.222'
REGION = 'us-west-2'

assert env.AWS_ACCESS_KEY
assert env.AWS_SECRET_KEY


def get_git_hash():
    return local('git rev-parse --short HEAD', capture=True)


def create_image():
    conn = ec2.connect_to_region(
        REGION,
        aws_access_key_id=env.AWS_ACCESS_KEY,
        aws_secret_access_key=env.AWS_SECRET_KEY)

    elastic_ips = conn.get_all_addresses([STAGING_IP, ])
    assert len(elastic_ips) == 1

    instance_id = elastic_ips[0].instance_id

    image_id = conn.create_image(
        instance_id,
        'brandish-vs-worker-{0}-{1}'.format(date.today().isoformat(), get_git_hash()),
        no_reboot=False)
    print 'Created AMI {0}'.format(image_id)


def staging():
    env.hosts = [STAGING_IP, ]
    env.user = "ubuntu"
    env.branch = "master"


def update():
    require("hosts", provided_by=[staging, ])

    with settings(warn_only=True):
        sudo("docker rm $(docker ps -aq)")
        sudo("docker rmi $(docker images --filter dangling=true --quiet)")
        sudo("service brandish-vs-worker stop")

    sudo("docker pull registry.vokal.io/brandish-vs-worker")

    sudo("service brandish-vs-worker start")
