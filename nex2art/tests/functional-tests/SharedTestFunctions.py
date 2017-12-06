import ArtifactoryDocker
import ArtifactoryAccess
import ConfigParser
import random
import os, sys

# Creates an Artifactory docker container based on the config settings.ini
# Returns the name of the container and the access to it
def create_art_instance():
    # Read and verify the config file
    config = ConfigParser.ConfigParser()
    config.read(os.path.dirname(os.path.abspath(__file__)) + '/config/settings.ini')
    if not config.has_section('Artifactory'):
        sys.exit('Missing settings.ini file or Artifactory section')
    if not config.has_option('Artifactory', 'version'):
        sys.exit('Missing version from settings.ini')
    if not config.has_option('Artifactory', 'exposedPort'):
        sys.exit('Missing exposedPort from settings.ini')
    if not config.has_option('Artifactory', 'dockerIP'):
        sys.exit('Missing dockerIP from settings.ini')
    # Extract contents from config and setup URL
    version = config.get('Artifactory', 'version')
    host = config.get('Artifactory', 'dockerIP')
    port = config.get('Artifactory', 'exposedPort')
    url = 'http://' + host + ':' + port + '/artifactory'
    # Create a semi-random name for the container
    container_name = 'nex2art_int_test_' + str(random.randint(1,10000))
    try:
        with open(os.path.dirname(os.path.abspath(__file__)) + '/config/artifactory.lic', 'r') as myfile:
            license_contents=myfile.read()
    except IOError as ex:
        sys.exit('Unable to read license from config/artifactory.lic')
    # Start a new Artifactory instance and set up a connection to it
    docker = ArtifactoryDocker.ArtifactoryDocker()
    if not docker.create_new_instance(version, port, container_name, host, license_contents):
        sys.exit('Failed to create the Artifactory instance')
    return container_name, ArtifactoryAccess.ArtifactoryAccess(url, 'admin', 'password')

# Deletes a container by name
def delete_art_instance(container_name):
    docker = ArtifactoryDocker.ArtifactoryDocker()
    docker.delete_instance(container_name)

# Performs an import from the nexus_conf_dir into the Artifactory referenced by art_access
# The nexus_conf_dir must have: migrateConfig.json and the nexus data/conf directory
# TODO: Needs to be implemented after the no-ui option is added
def performImport(nexus_conf_dir, art_access):
    pass