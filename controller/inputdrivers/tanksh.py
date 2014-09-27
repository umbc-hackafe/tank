from code import InteractiveConsole

raw_input = input

def main(client, args=[]):
    console = InteractiveConsole({"tank": client})

    console.interact(banner="TANKSH (%s%s)" %
            (client.__dict__['_ServerProxy__host'],
                client.__dict__['_ServerProxy__handler']))
