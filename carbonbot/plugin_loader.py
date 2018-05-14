#!/usr/bin/env python3

import sys
import traceback
from os import path, listdir
from importlib.util import spec_from_file_location
import carbonbot as cb


BASE_DIR = path.join(path.dirname(path.realpath(__file__)), "..")
DEFAULT_DIR = "plugins"


class FailedPlugin:
    def register_with(*args, **kwargs):
        pass


def strip_extension(filename: str) -> str:
    return filename[:filename.rindex(".")]


def _load_module(name, path):
    # Get a module loading object
    try:
        loader = spec_from_file_location(name, path).loader

    except:
        print("Failed to prepare module `{}` for loading.".format(name), file=sys.stderr, end=" ")
        traceback.print_exc(file=sys.stderr)
        return FailedPlugin()

    # Actually load the module
    try:
        module = loader.load_module()

    except:
        print("Failed to load module `{}`.".format(name), file=sys.stderr, end=" ")
        traceback.print_exc(file=sys.stderr)
        return FailedPlugin()

    module.CARBONBOT_MODULE_NAME = name

    # Return the module
    return module


def load_all(directory=DEFAULT_DIR) -> dict:
    if not path.isabs(directory):
        directory = path.join(BASE_DIR, directory)

    f = lambda filename: path.join(directory, filename)

    return {
        strip_extension(filename):
            _load_module(
                name=strip_extension(filename),
                path=f(filename)
            )
            for filename in listdir(directory)
            if path.isfile(f(filename)) and filename.endswith(".py")
    }


def register_all(carbon: "cb.Carbon", plugins) -> None:
    for plugin in plugins:
        name = "couldn't detect name, this is probably not a module loaded with plugin_loader"
        try:
            name = plugin.CARBONBOT_MODULE_NAME
            plugin.register_with(carbon)

        except:
            print("Failed to register module `{}`.".format(name), file=sys.stderr, end=" ")
            traceback.print_exc(file=sys.stderr)
            continue

        print("Plugin `{}` registered".format(name))


def load_and_register_all(carbon: "cb.Carbon", directory=DEFAULT_DIR) -> list:
    plugins = load_all(directory)
    register_all(carbon, plugins.values())
    return plugins

