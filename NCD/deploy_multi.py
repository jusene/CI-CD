#!/usr/bin/env python
# -*- coding=utf-8 -*-

import argparse
import os
import yaml
import sys
import subprocess
import urllib2
import json
import logging
import multiprocessing
from config import config as Q

basedir = os.path.dirname(os.path.abspath(__file__))
logging.basicConfig(level=logging.INFO, format="%(asctime)s - Deploy - %(levelname)s: %(message)s")


def Parser():
    '''
    analy parameter
    '''
    parser = argparse.ArgumentParser()
    parser.add_argument("-a", '--appname', help="Get deploy appname")
    parser.add_argument("-e", '--env', help="Get deploy env")
    parser.add_argument("-u", '--url', help="Get package url")
    parser.add_argument("-t", '--time', help="Get package timestamp")
    parser.add_argument("-p", '--project', help="Get project name")
    parser.add_argument("-v", '--version', help="Get project version")
    parser.add_argument("-d", "--dir", default=None, help="Get nginx dir name")
    parser.add_argument("-f", "--first", default=None, help="Get node first deploy")
    parser.add_argument("-n", "--node", default=None, help="Get node name")
    args = parser.parse_args()
    return args



def manifest(appname, env):
    '''
    fetch resource：

    appname: 
        want a app param

    env:
        want a env param
    '''
    try:
        header = {"User-Agent": "Mozilla/5.0 (compatible; MSIE 9.0; Windows NT 6.1; Trident/5.0;",
              "Accept": "application/json"}
        request = urllib2.Request("http://192.168.55.156:5000/deploy?app={app}&env={env}".format(app=appname, env=env),
                              headers=header)
        resp = urllib2.urlopen(request)
        conf = json.loads(resp.read())
        return conf
    except Exception as e:
        logging.error("fetch resource error，please check manifest and request http://192.168.55.156:5000/deploy?app={app}&env={env}".format(app=appname, env=env))
        sys.exit(500)



class Deploy(object):
    '''
    application class：

        Method of deploying various environments
    '''
    def __init__(self, args):
        self.apps = args.appname
        self.env = args.env
        self.url = args.url
        self.time = args.time
        self.project = args.project
        self.version = args.version
        self.directory = args.dir
        self.first = args.first
        self.node = args.node

    def nodejs(self, host, app):
        logging.info('****** Deploy NodeJS App ******')
        retcode = subprocess.call(
            'ansible-playbook {playbook} -e host={ho} -e url={url} -e app={app} -e time={time} -e project={project} \
            -e env={env} -e version={version} -e dir={dir} -e node={node} -e first={first}'.format(
                playbook='/'.join([basedir, 'playbook', 'ansible_node.yml']),
                ho=host,
                url=self.url,
                app=app,
                time=self.time,
                project=self.project,
                version=self.version,
                env=self.env,
                dir=self.directory,
                node=self.node,
                first=self.first), shell=True)
        return retcode

    def java(self, host, app, jmx, remote):
        logging.info('****** Deploy Java App ******')
        retcode = subprocess.call(
            'ansible-playbook {playbook} -e host={ho} -e url={url} -e app={app} -e time={time} -e project={project} \
             -e env={env} -e version={version} -e jmx={jmx} -e remote={remote}'.format(
                playbook='/'.join([basedir, 'playbook', 'ansible_java.yml']),
                ho=host,
                url=self.url,
                app=app,
                time=self.time,
                project=self.project,
                version=self.version,
                env=self.env,
                jmx=jmx,
                remote=remote), shell=True)
        return retcode

    def js(self, host, app):
        logging.info('****** Deploy JavaScript App ******')
        retcode = subprocess.call(
            'ansible-playbook {playbook} -e host={ho} -e url={url} -e app={app} -e time={time} -e project={project} \
             -e env={env} -e version={version} -e dir={dir}'.format(
                playbook='/'.join([basedir, 'playbook', 'ansible_js.yml']),
                ho=host,
                url=self.url,
                app=app,
                time=self.time,
                project=self.project,
                version=self.version,
                env=self.env,
                dir=self.directory), shell=True)
        return retcode

def Process_pool():
    '''
    Queue selection
    '''
    Pool = []
    Que = []
    def wrap(*args, **kwargs):
        if args[1] in Q.get(ENV).QUEUE:
            Que.append(args[0])
        else:
            Pool.append(args[0])
        return Pool, Que
    return wrap

if __name__ == "__main__":
    args = Parser()
    ENV = args.env
    deploy = Deploy(args)
    pool = Process_pool()
    for app in deploy.apps.split(','):
        conf = manifest(app, deploy.env)
        hosts = conf['hosts']
        jmx = conf['jmx']
        remote = conf['remote']
        for host in hosts:
            if deploy.directory is None:
                p1 = multiprocessing.Process(target=deploy.java,args=(host,app,jmx,remote))
                process_pool, queue_pool = pool(p1, app)
            else:
                if deploy.node is None:
                    p2 = multiprocessing.Process(target=deploy.js,args=(host,app))
                    process_pool, queue_pool = pool(p2, app)
                else:
                    p3 = multiprocessing.Process(target=deploy.nodejs,args=(host,app))
                    process_pool, queue_pool = pool(p3, app)

    for q in queue_pool:
        q.start()
        q.join()

    for p in process_pool:
        p.start()
