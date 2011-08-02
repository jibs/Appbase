#!/usr/bin/env python
# encoding: utf-8

"""
fabfile.py

Fabric config file for code deployment etc

Heavily influenced by: 
    http://www.caktusgroup.com/blog/2010/04/22/basic-django-deployment-with-virtualenv-fabric-pip-and-rsync/

----------
This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
----------
"""

import os

from fabric.api import *
from fabric import utils
from fabric.decorators import hosts
from fabric.contrib.project import rsync_project

import yaml

RSYNC_EXCLUDE = (
    '.DS_Store',
    '.git',
    '*.pyc',
    '*.example',
    '*.db',
    'local_settings.py',
    'fabfile.py',
    'bootstrap.py',
)
env.project = 'testapp'
env.conf = yaml.load(open('./configs/server.yaml'))

def _setup_path():
    env.root = os.path.join(env.home, 'www', env.environment)
    env.code_root = os.path.join(env.root)
    env.virtualenv_root = os.path.join(env.root, 'env')
    env.settings = '%(project)s.settings_%(environment)s' % env


def staging():
    """ use staging environment on remote host"""
    env.environment = 'staging'
    env.user = 'ubuntu'
    env.home =  os.path.join('/home/',env.user, env.project) 
    env.hosts = env.conf['servers']['staging']
    env.local_dir = os.getcwd() + '/'
    _setup_path()


def production():
    """ use production environment on remote host"""
    env.environment = 'staging'
    env.user = 'ubuntu'
    env.home =  os.path.join('/home/',env.user, env.project) 
    env.hosts = env.conf['servers']['production']
    _setup_path()


def bootstrap():
    """ initialize remote host environment (virtualenv, deploy, update) """
    require('root', provided_by=('staging', 'production'))
    run('mkdir -p %(root)s' % env)
    run('mkdir -p %s' % os.path.join(env.home, 'www', 'log'))
    create_virtualenv()
    deploy()
    update_requirements()


def create_virtualenv():
    """ setup virtualenv on remote host """
    require('virtualenv_root', provided_by=('staging', 'production'))
    args = '--clear --distribute'
    run('virtualenv %s %s' % (args, env.virtualenv_root))


def deploy():
    """ rsync code to remote host """
    require('root', provided_by=('staging', 'production'))
    if env.environment == 'production':
        if not console.confirm('Are you sure you want to deploy production?',
                               default=False):
            utils.abort('Production deployment aborted.')
    # defaults rsync options:
    # -pthrvz
    # -p preserve permissions
    # -t preserve times
    # -h output numbers in a human-readable format
    # -r recurse into directories
    # -v increase verbosity
    # -z compress file data during the transfer
    extra_opts = '--omit-dir-times'
    rsync_project(
        env.root,
        local_dir=env.local_dir,
        exclude=RSYNC_EXCLUDE,
        delete=False,
        extra_opts=extra_opts,
    )
    
    with cd(env.code_root):
        run('pwd', shell=True)
        sudo('cp ./configs/_supervisord.conf /etc/supervisord.conf')
    # run('supervisorctl reload', shell=True)


def update_requirements():
    """ update external dependencies on remote host """
    require('code_root', provided_by=('staging', 'production'))
    requirements = os.path.join(env.code_root, 'configs')
    with cd(requirements):
        cmd = ['pip install']
        cmd += ['-E %(virtualenv_root)s' % env]
        cmd += ['--requirement %s' % os.path.join(requirements, 'requirements.txt')]
        run(' '.join(cmd))

