import unittest
import ArtifactoryAccess
import SharedTestFunctions
import xml.etree.ElementTree as ET

'''
Test the basic functionality of the migration against an actual Artifactory instance
Test the following aspects:
  * Basic maven artifacts
  * Users
  * Repositories
  * LDAP
'''
class TestBasicFunctional(unittest.TestCase):

    def setUp(self):
        self.art = self.__class__.art

    def tearDown(self):
        pass

    def test_ldap_test(self):
        self.assertTrue(self.art.ping())
        strConf = ET.tostring(self.art.get_configuration().getroot())
        # Hackish check but should signal the presence of the string in the conf
        self.assertTrue('ldap://ldap.test.com/dc=jfrog' in strConf)
        self.assertTrue('(objectClass=groupOfUniqueNames)' in strConf)

    def test_artifacts_test(self):
        self.assertTrue(self.art.ping())
        self.assertTrue(self.art.artifact_exists('releases', 'com/jfrog/test-package/1.0/test-package-1.0.jar'))
        self.assertTrue(self.art.artifact_exists('releases', 'com/jfrog/test-package/1.0/test-package-1.0.pom'))
        pass

    def test_users_exist_test(self):
        self.assertTrue(self.art.ping())
        # Paco
        user = self.art.get_user('paco')
        self.assertTrue(user)
        self.assertTrue(user['admin'])
        self.assertEqual(user['email'], 'paco@foo.com')
        # Jose Arcadio (Buendia)
        user = self.art.get_user('jose-arcadio')
        self.assertTrue(user)
        self.assertFalse(user['admin'])
        self.assertEqual(user['email'], 'jose.arcadio@gmail.com')
        # deployment
        user = self.art.get_user('deployment')
        self.assertTrue(user)
        self.assertFalse(user['admin'])
        self.assertEqual(user['email'], 'changeme1@yourcompany.com')
        pass

    def test_repos_exist_test(self):
        self.assertTrue(self.art.ping())
        # Third Party
        repo = self.art.get_repository('thirdparty')
        self.assertTrue(repo)
        self.assertEqual(repo['description'], '3rd party')
        self.assertEqual(repo['packageType'], 'maven')
        self.assertEqual(repo['repoLayoutRef'], 'maven-2-default')
        self.assertFalse(repo['suppressPomConsistencyChecks'])
        self.assertFalse(repo['handleSnapshots'])
        self.assertTrue(repo['handleReleases'])
        self.assertEqual(repo['snapshotVersionBehavior'], 'unique')
        # Central
        repo = self.art.get_repository('central')
        self.assertTrue(repo)
        self.assertEqual(repo['packageType'], 'maven')
        self.assertEqual(repo['repoLayoutRef'], 'maven-2-default')
        self.assertFalse(repo['suppressPomConsistencyChecks'])
        self.assertFalse(repo['handleSnapshots'])
        self.assertTrue(repo['handleReleases'])
        self.assertEqual(repo['url'], 'https://repo1.maven.org/maven2/')
        self.assertFalse(repo['username'])
        self.assertFalse(repo['password'])
        # Releases
        repo = self.art.get_repository('releases')
        self.assertTrue(repo)
        self.assertEqual(repo['description'], 'Releases')
        self.assertEqual(repo['packageType'], 'maven')
        self.assertEqual(repo['repoLayoutRef'], 'maven-2-default')
        self.assertFalse(repo['suppressPomConsistencyChecks'])
        self.assertFalse(repo['handleSnapshots'])
        self.assertTrue(repo['handleReleases'])
        self.assertEqual(repo['snapshotVersionBehavior'], 'unique')
        # Snapshots
        repo = self.art.get_repository('snapshots')
        self.assertTrue(repo)
        self.assertEqual(repo['description'], 'Snapshots')
        self.assertEqual(repo['packageType'], 'maven')
        self.assertEqual(repo['repoLayoutRef'], 'maven-2-default')
        self.assertFalse(repo['suppressPomConsistencyChecks'])
        self.assertTrue(repo['handleSnapshots'])
        self.assertFalse(repo['handleReleases'])
        self.assertEqual(repo['snapshotVersionBehavior'], 'unique')
        self.assertEqual(repo['maxUniqueSnapshots'], 0)
        # Apache Snapshots
        repo = self.art.get_repository('apache-snapshots')
        self.assertTrue(repo)
        self.assertEqual(repo['packageType'], 'maven')
        self.assertEqual(repo['repoLayoutRef'], 'maven-2-default')
        self.assertFalse(repo['suppressPomConsistencyChecks'])
        self.assertTrue(repo['handleSnapshots'])
        self.assertFalse(repo['handleReleases'])
        self.assertEqual(repo['url'], 'https://repository.apache.org/snapshots/')
        self.assertFalse(repo['username'])
        self.assertFalse(repo['password'])
        # Public
        repo = self.art.get_repository('public')
        self.assertTrue(repo)
        self.assertEqual(repo['description'], 'Public Repositories')
        self.assertEqual(repo['packageType'], 'maven')
        self.assertEqual(repo['repoLayoutRef'], 'maven-2-default')
        self.assertEqual(len(repo['repositories']), 4)
        self.assertEqual(sorted(repo['repositories']), sorted(('releases', 'snapshots', 'thirdparty', 'central')))
        pass

    @classmethod
    def setUpClass(cls):
        cls.art_name, cls.art = SharedTestFunctions.create_art_instance()
        SharedTestFunctions.performImport('basicNexus2', cls.art)

    @classmethod
    def tearDownClass(cls):
        SharedTestFunctions.delete_art_instance(cls.art_name)

if __name__ == '__main__':
    unittest.main()