import logging
import time
import ArtifactoryAccess
from subprocess import call, check_output, CalledProcessError

'''
Spins up Artifactory instances
'''
class ArtifactoryDocker:
    def __init__(self):
        self.log = logging.getLogger(__name__)

    def create_new_instance(self, version, port, name, dockerIP, license_contents):
        self.log.info("Creating new Artifactory instance with name " + name + " and version " + version)
        code = call(['docker', 'run', '--name', name, '-d', '-p', port + ":8081",
              'jfrog-docker-reg2.bintray.io/jfrog/artifactory-pro:' + version])
        if code != 0:
            return False
        url = 'http://' + dockerIP + ':' + port + '/artifactory'
        art = ArtifactoryAccess.ArtifactoryAccess(url, 'admin', 'password')
        # Wait up to 2 minutes for the instance to come up
        for i in range(0, 12):
            self.log.info('Sleeping for 10 seconds to let Artifactory startup...')
            time.sleep(10)
            if art.get_license():
                return art.install_license(license_contents)
            else:
                self.log.info('Artifactory is still not up.')
        return False

    def delete_instance(self, name):
        self.log.info('Deleting artifactory container with name: ' + name)
        call(['docker', 'stop', name])
        call(['docker', 'rm', name])
