# Copyright (C) 2015  Arthur Yidi
# License: BSD Simplified

class AttrDict(dict):
    def __getattr__(self, key):
        return self.__getitem__(key)

    def __setattr__(self, key, value):
        self[key] = value

    def __str__(self):
        string = "{\n"
        indent = " " * 4
        for key in sorted(dict.keys(self)):
            string += indent + "%s: %s\n" % (key, self.__getitem__(key))
        string += "}"
        return string

    def __getitem__(self, key):
        val = dict.__getitem__(self, key)
        return val(self) if callable(val) else val
