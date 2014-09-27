import pkgutil

class NoDriverInModuleException(Exception): pass

# Define a dict to add all of our finds to.
all = {}

def load(path):
    # Path needs to be a list in order for the following calls to work.
    if type(path) != list: path = [path]
    # Walk the directory.
    for loader, name, ispkg in pkgutil.walk_packages(path):
        module = loader.find_module(name).load_module(name)

        # Try to find the modules 'main' argument and add it to the
        # list.
        try:
            if 'main' in dir(module):
                all[name] = module.main
            else:
                raise NoDriverInModuleException("No main in %s" % name)

        except Exception as e:
            print("Skipping module {}: {}".format(name, e))


def run(inputdriver, args=[]):
    if inputdriver in all:
        all[inputdriver](args)
    else:
        raise NoDriverInModuleException("No main in %s" % inputdriver)

# Load all of the drivers in this path.
load(__path__)
