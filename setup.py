#!/usr/bin/env python

import subprocess,re,sys,os,time

import src.lib.gdm.gdm as gdm
import src.lib.name.user as user
import src.lib.logging.logger as logger
import src.lib.version.version as version

from distutils.cmd import Command
from subprocess import Popen, call, PIPE
from setuptools import setup, find_packages
from distutils.errors import DistutilsError, DistutilsExecError

class Check():
    def __init__(self):
        self.sys_dependencies = {
            'rpm': ('python-devel','sqlite3-dbf','syslog-ng','sendmail-cf',
                'sendmail-devel','procmail','opencv-core','opencv-python'),
            'eix': ('mail-mta/sendmail','app-admin/syslog-ng','dev-lang/python',
                'dev-python/sqlite3dbm','mail-filter/procmail','media-libs/opencv'),
            'apt': ('libopencv-dev','python-opencv','python-dev','procmail','sqlite3',
                'sendmail-bin','sendmail-cf','sensible-mda','syslog-ng','sendmail-base')
        }

        self.package_manager  = {
            'rpm': ('centos','fedora','scientific','opensuse'),
            'apt': ('debian','ubuntu','linuxmint'),
            'eix': ('gentoo',)
        }

    def system_query_command(self):
        if version.system_package_manager() == 'rpm':
            system_query_command = 'rpm -qa'
        elif version.system_package_manager() == 'apt':
            system_query_command = 'dpkg --list'
        elif version.system_package_manager() == 'eix':
            system_query_command = 'eix -e --only-names'
        return system_query_command

    def grep_system_packages(self,package_name):
        comm = subprocess.Popen([self.system_query_command() + ' ' + str(package_name) + ' 2> /dev/null'],
            shell=True, stdout=subprocess.PIPE)
        if not comm.stdout.readline(): 
            logger.log("ERROR", "Package " + str(package_name) + " was not found.")
        else:
            logger.log("INFO", "Package " + str(package_name) + " was found.")

    def pip_package_check(self):
        packages = [
            'opencv-python', 'python-crontab'
        ]

        for package in packages:

            pip_query = subprocess.Popen(["pip show \'"+str(package)+"\' 2> /dev/null"],
                shell=True, stdout=subprocess.PIPE)

            if '' not in pip_query.stdout.readlines():
                logger.log("INFO", "Package " + str(package) + " was found.")
            else:
                logger.log("ERROR", "Package " + str(package) + " was not found.")

    def main(self):
        try:
            for item in self.sys_dependencies[version.system_package_manager()]:
                self.grep_system_packages(item)
        except DistutilsExecError as distutilsExecError:
            logger.log("ERROR", "Exception DistutilsExecError: " + str(distutilsExecError))
        except Exception as exception:
            logger.log("ERROR", "Exception exception: " + str(exception))

class PrepareBuild():
    def modify_conf_files(self,username):
        logger.log('INFO', 'Modifying config files.')
        subprocess.Popen(["find src/system/* -type f -iname *.conf -exec sed -i 's/username/" + username + "/g' {} \;"],
        shell=True, stdout=subprocess.PIPE)

    def cron_tab(self):
        #Count need to be 1 in order to write to the crontab
        #Basically, checking for grep being None or not None will
        # not work in this case and we need to check for 2 occurances.
        count=0
        command="/bin/bash /home/root/.ssh/is_imagecapture_running.sh"
        cron = CronTab(user='root')
        job = cron.new(command=command)
        job.minute.every(1)
        install = re.search('install', str(sys.argv[1]), re.M | re.I)
        for item in cron:
            grep = re.search(r'\/is_imagecapture_running.sh', str(item))
            if grep is not None:
                count+=1
        if count < 2 and install is not None:
            logger.log("INFO", "Installing crontab.")
            cron.write()

    def pip_install_package(self,package):
        logger.log("INFO", "Installing opencv-python via pip")
        os.system("su " + str(user.name()) + " -c 'pip install --user " + str(package) + "'")

if __name__ == '__main__':

    prepareBuild = PrepareBuild()
    argument = re.match(r'(install|check|build|sdist)\b', str(sys.argv[1]))

    if argument is None:
        logger.log("ERROR","Option is not supported.")
        sys.exit(0)
    elif argument.group() == 'check':
        check = Check()
        logger.log("INFO","Grepping System Packages")
        check.main()
        logger.log("INFO","Grepping PIP Packages")
        check.pip_package_check()
        sys.exit(0)

    username  = str(user.name())
    pam       = str(gdm.pam_d()[0])
    pkgm      = str(version.system_package_manager())

    conf_path = 'src/system/autologin/conf'
    conf_name = [conf_path+'/slim.conf',conf_path+'/mdm.conf',conf_path+'/gdm.conf']

    prepareBuild.modify_conf_files(username)

    logger.log('INFO', 'Entering setup in setup.py')

    setup(name='ImageCapturePy',
    version='1.0.0',
    url='https://github.com/amboxer21/ImageCapturePy',
    license='GPL-3.0',
    author='Anthony Guevara',
    author_email='amboxer21@gmail.com',
    description='A program to capture a picture and geolocation data upon 3 incorrect or '
        + 'number of specified attempts at the login screen. This data is then e-mailed to you.',
    packages=find_packages(exclude=['tests']),
    long_description=open('README.md').read(),
    classifiers=[
        'Intended Audience :: Developers',
        'Intended Audience :: End Users/Desktop',
        'Intended Audience :: System Administrators',
        'Development Status :: 4 - Beta',
        'Natural Language :: English',
        'Environment :: Console',
        'Environment :: No Input/Output (Daemon)',
        'Programming Language :: Python :: 2.7',
        'Operating System :: POSIX :: Linux',
        'License :: OSI Approved :: GNU General Public License (GPL)', 
    ],
    data_files=[
        ('/etc/pam.d/', [conf_name[0],conf_name[1],conf_name[2]]),
        ('/etc/pam.d/', ['src/system/autologin/' + pkgm + '/pam/' + pam]),
        ('/usr/local/bin/', ['src/imagecapture.py']),
        ('/home/root/.ssh/' ,['src/system/home/user/.ssh/is_imagecapture_running.sh'])],
    zip_safe=True,
    setup_requires=['python-crontab'],)
    #setup_requires=['pytailf', 'opencv-python','python-crontab'],)

    prepareBuild.pip_install_package('opencv-python')

    from crontab import CronTab
    prepareBuild.cron_tab()
