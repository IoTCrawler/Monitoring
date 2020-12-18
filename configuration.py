import configparser
import os
import sys

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

class Config:
    """Interact with configuration variables."""

    parser = configparser.ConfigParser()
    configFilePath = (os.path.join(os.getcwd(), 'config.ini'))
    parser.read(configFilePath)

    @classmethod
    def get(cls, section, key):
        """Get prod values from config.ini."""
        try:
            return cls.parser.get(section, key)
        except configparser.NoOptionError:
            return ""

    @classmethod
    def getAllOptions(cls):
        config = {}
        for section in cls.parser.sections():
            options = {}
            for key in cls.parser[section]:
                value = cls.parser.get(section, key)
                options[key] = value
            config[section] = options
        return config

    @classmethod
    def update(cls, section, key, value):
        if section not in cls.parser.sections():
            cls.parser.add_section(section)
        cls.parser.set(section, key, value)
        with open(cls.configFilePath, 'w') as configfile:
            cls.parser.write(configfile)

    @classmethod
    def getEnvironmentVariables(cls):

        # print(os.environ['NGSI_HOST'])
        envMap = {}
        env = ['NGSI_ADDRESS', 'SE_HOST', 'SE_PORT', 'SE_CALLBACK']
        for v in env:
            envMap[v] = Config.getEnvironmentVariable(v)
        return envMap

    @classmethod
    def getEnvironmentVariable(cls, variable, default=None):
        try:
            return os.environ[variable]
        except KeyError:
            return default

    @classmethod
    def showEnvironmentVariables(cls):
        for key in os.environ:
            eprint("ENV:", key, "=", os.environ[key])


if __name__ == "__main__":
    print(Config.get('NGSI', 'host'))
    print(Config.getAllOptions())
    Config.update("testsection", "testkey", "testvalue")
