import json
import logging
from ..core import Menu, Progress, DataTree
from . import Setup, Repo, Security, Options, Safety

# The main menu. This is the first menu that appears when the tool is started,
# and it's the hub that everything else can be accessed through. It contains
# special options for saving and loading a configuration to and from a file,
# running verification on an entire configuration at any time, and running a
# full migration based on the current configuration.
class Main(Menu):
    # Initialize the main menu by setting up the options.
    def __init__(self, scr):
        Menu.__init__(self, scr, [], "Nexus -> Artifactory")
        self.log = logging.getLogger(__name__)
        self.log.debug("Initializing Main Menu.")
        save, load = ['|', self.save], [self.preload, '|', self.load]
        self.saveopt = self.mkopt('s', "Save Configuration", save, save=False)
        self.loadopt = self.mkopt('l', "Load Configuration", load, save=False)
        def validate(_): self.scr.validate()
        self.opts = [
            self.mkopt('i', "Initial Setup", [self.submenu(Setup), validate]),
            self.mkopt('r', "Repository Migration Setup", self.submenu(Repo)),
            self.mkopt('u', "Security Migration Setup", self.submenu(Security)),
            # self.mkopt('o', "Options Migration Setup", self.submenu(Options)),
            None,
            self.saveopt,
            self.loadopt,
            self.mkopt('v', "Verify Configuration", self.doverify, save=False),
            self.mkopt('x', "Run Migration", self.runmigration, save=False),
            None,
            self.mkopt('h', "Help", '?'),
            self.mkopt('q', "Exit", None, hdoc=False)]
        self.scr.validate()
        self.scr.oldstate = self.scr.state.clone()
        self.log.debug("Main Menu initialized.")

    # Run full verification on the configuration, using the menu's verify()
    # function. Print the result.
    def doverify(self, _):
        self.log.info("Verifying current state.")
        self.scr.validate()
        if self.scr.state.valid == True:
            self.log.info("Current state verified successfully.")
            self.scr.msg = ('val', "Configuration verified successfully.")
        else:
            self.log.warning("Current state verified, errors found.")
            self.scr.msg = ('err', "Configuration verified, errors found.")

    # Run the actual migration, and print the result.
    def runmigration(self, _):
        self.log.info("Attempting to run migration.")
        self.scr.validate()
        if self.scr.state.valid != True:
            self.log.warning("Unable to run migration, errors found.")
            self.scr.msg = ('err', "Cannot run migration, errors found.")
            return
        status = Progress(self.scr).show(self.scr.state.todict())
        if status == True:
            self.log.info("Migration successfully run.")
            self.scr.msg = ('val', "Migration successful!")
        else:
            self.log.warning("Error running migration: %s.", status)
            self.scr.msg = ('err', "Migration error: " + status)

    # Serialize the current configuration state as a JSON object, and save it to
    # a file. The parameter 'sel' is the menu option that ran this function.
    def save(self, sel):
        if sel['val'] == None: return
        self.log.info("Saving configuration to file %s.", sel['val'])
        f = None
        try:
            f = open(sel['val'], 'w')
            self.scr.state.prune()
            data = self.scr.state.todict()
            self.scr.format.trim(data)
            json.dump(data, f, indent=4)
            self.log.info("Configuration saved successfully.")
            self.scr.msg = ('val', "Successfully saved to specified file.")
            self.scr.oldstate = self.scr.state.clone()
            sel['stat'] = True
        except:
            self.log.exception("Error saving configuration:")
            self.scr.msg = ('err', "Unable to save to specified file.")
            sel['stat'] = False
        finally:
            if f != None: f.close()
        if sel['stat'] == True and self.loadopt['val'] == None:
            self.loadopt['val'] = sel['val']

    # Before loading a JSON object from a file, if there are unsaved changes,
    # ensure that the user wants to discard them.
    def preload(self, sel):
        if self.scr.modified() and not Safety(self.scr).show(): return False

    # Load a JSON object from a file, and apply the configuration state
    # specified by that object as the current state. The parameter 'sel' is the
    # menu option that ran this function.
    def load(self, sel):
        path, f = sel['val'], None
        if path == None: return
        self.log.info("Loading configuration from file %s.", path)
        try:
            f = open(path, 'r')
            data = json.load(f)
            self.scr.format.trim(data)
            self.scr.state = DataTree(self.scr, data)
            self.scr.validate()
            if self.scr.state.valid == True:
                self.log.info("Configuration loaded successfully.")
                self.scr.msg = ('val', "Configuration loaded successfully.")
            else:
                self.log.warning("Configuration loaded, errors found.")
                self.scr.msg = ('err', "Configuration loaded, errors found.")
            self.scr.oldstate = self.scr.state.clone()
            sel['stat'] = True
        except:
            self.log.exception("Error loading configuration:")
            self.scr.msg = ('err', "Unable to load from specified file.")
            sel['stat'] = False
        finally:
            if f != None: f.close()
        if sel['stat'] == True and self.saveopt['val'] == None:
            self.saveopt['val'] = path
            sel['val'] = path
