#!/usr/bin/env pytho

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
            'eix': ('',),
            'apt': ('libopencv-dev','python-opencv','python-dev','procmail','sqlite3',
                'sendmail-bin','sendmail-cf','sensible-mda','syslog-ng','sendmail-base')}
        self.package_manager  = {
            'rpm': ('centos','fedora','scientific','opensuse'),
            'apt': ('debian','ubuntu','linuxmint'),
            'eix': ('gentoo',)}

    def system_query_command(self):
        if self.system_package_manager() == 'rpm':
            system_query_command = 'rpm -qa'
        elif self.system_package_manager() == 'apt':
            system_query_command = 'dpkg --list'
        elif self.system_package_manager() == 'eix':
            system_query_command = 'eix --only-names'
        return system_query_command

    def grep_system_packages(self,package_name):
        comm = subprocess.Popen([self.system_query_command() + " " + str(package_name)],
            shell=True, stdout=subprocess.PIPE)
        if comm is not None:
            logger.log("INFO", "Package " + str(comm.stdout.read()).strip() + " was found.")
        else:
            logger.log("ERROR", "Package " + str(comm.stdout.read()).strip() + " was not found.")

    def list_system_packages(self):
        packages = []
        comm = subprocess.Popen([self.system_query_command()], shell=True, stdout=subprocess.PIPE)
        if comm is not None:
            packages.append(comm.stdout.read())
        return packages

    def system_package_manager(self):
        for key,value in self.package_manager.items():
            manager = re.search(version.release().lower(),str(value), re.I | re.M)
            if manager is not None:
                return key
        if manager is None:
            return False

    def main(self):
        try:
            for item in self.sys_dependencies[self.system_package_manager()]:
                self.grep_system_packages(item)
        except DistutilsExecError as distutilsExecError:
            logger.log("ERROR", "Exception DistutilsExecError: " + str(distutilsExecError))

class PrepareBuild():
    def modify_conf_files(self,username):
        logger.log('INFO', 'Modifying config files.')
        subprocess.Popen(["find src/system/* -type f -iname *.conf -exec sed -i 's/username/" + username + "/g' {} \;"],
        shell=True, stdout=subprocess.PIPE)

    def cron_tab(self):
        command="/bin/bash /home/root/.ssh/is_imagecapture_running.sh"
        cron = CronTab(user='root')
        job = cron.new(command=command)
        job.minute.every(1)
        for item in cron:
            install = re.search('install', str(sys.argv[1]), re.M | re.I)
            if install is not None:
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
        logger.log("INFO","Grepping System Packages")
        Check().main()
        sys.exit(0)

    try:

        username = str(user.name())
        pam      = str(gdm.pam_d()[0])
        pkgm     = str(version.system_package_manager())

        conf_path = 'src/system/autologin/conf'
        conf_name = [conf_path+'/slim.conf',conf_path+'/mdm.conf',conf_path+'/gdm.conf']

        prepareBuild.modify_conf_files(username)

        logger.log('INFO', 'Entering setup in setup.py')
        setup(name='ImageCapturePy',
        version='1.0.0',
        url='https://github.com/amboxer21/ImageCapturePy',
        license='NONE',
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
        setup_requires=['pytailf', 'opencv-python','python-crontab'],)

        from crontab import CronTab
        prepareBuild.cron_tab()

    except DistutilsError:
        if argument.group() != 'check':
            prepareBuild.pip_install_package('opencv-python')
