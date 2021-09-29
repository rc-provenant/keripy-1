# -*- encoding: utf-8 -*-
"""
keri.app.configing module

"""
import os
import json

import msgpack
import cbor2 as  cbor

from hio.help import helping
from hio.base import filing, doing

from .. import help

logger = help.ogler.getLogger()


def openCF(cls=None, filed=True, **kwa):
    """
    Returns contextmanager generated by openFiler with Configer instance as default
    and filed = True
    """
    if cls == None:  # can't reference class before its defined below
        cls = Configer
    return filing.openFiler(cls=cls, filed=True, **kwa)


class Configer(filing.Filer):
    """
    Habitat Config File
    """
    TailDirPath = "keri/cf"
    CleanTailDirPath = "keri/clean/cf"
    AltTailDirPath = ".keri/cf"
    AltCleanTailDirPath = ".keri/clean/cf"
    TempPrefix = "keri_cf_"

    def __init__(self, name="conf", base="main", filed=True, mode="wb+",
                 fext="json", **kwa):
        """
        Setup config file .file at .path

        Parameters:
            name (str): directory path name differentiator directory/file
                When system employs more than one keri installation, name allows
                differentiating each instance by name
            base (str): optional directory path segment inserted before name
                that allows further differentation with a hierarchy. "" means
                optional.
            temp (bool): assign to .temp
                True then open in temporary directory, clear on close
                Otherwise then open persistent directory, do not clear on close
            headDirPath (str): optional head directory pathname for main database
                Default .HeadDirPath
            perm (int): optional numeric os dir permissions for database
                directory and database files. Default .DirMode
            reopen (bool): True means (re)opened by this init
                           False  means not (re)opened by this init but later
            clear (bool): True means remove directory upon close if reopon
                          False means do not remove directory upon close if reopen
            reuse (bool): True means reuse self.path if already exists
                          False means do not reuse but remake self.path
            clean (bool): True means path uses clean tail variant
                             False means path uses normal tail variant
            filed (bool): True means .path is file path not directory path
                          False means .path is directiory path not file path
            mode (str): File open mode when filed
            fext (str): File extension when filed

        """
        super(Configer, self).__init__(name=name,
                                       base=base,
                                       filed=True,
                                       mode=mode,
                                       fext=fext,
                                       **kwa)


    def put(self, data: dict):
        """
        Serialize data dict and write to file given by .path where serialization is
        given by .fext path's extension of either JSON, MsgPack, or CBOR for extension
        .json, .mgpk, or .cbor respectively
        """
        self.file.seek(0)
        self.file.truncate()
        root, ext = os.path.splitext(self.path)
        if ext == '.json':  # json can't dump to binary
            self.file.write(json.dumps(data, indent=2).encode("utf-8"))
        elif ext == '.mgpk':
            msgpack.dump(data, self.file)
        elif ext == '.cbor':
            cbor.dump(data, self.file)
        else:
            raise IOError(f"Invalid file path ext '{path}' "
                          f"not '.json', '.mgpk', or 'cbor'.")
        self.file.flush()
        os.fsync(self.file.fileno())
        return True


    def get(self):
        """
        Return data read from file path as dict
        file may be either json, msgpack, or cbor given by extension .json, .mgpk, or
        .cbor respectively
        Otherwise raise IOError
        """
        self.file.seek(0)
        root, ext = os.path.splitext(self.path)
        if ext == '.json':  # json.load works with bytes as well as str
            it = json.loads(self.file.read().decode("utf-8"))
        elif ext == '.mgpk':
            it = msgpack.load(self.file)
        elif ext == '.cbor':
            it = cbor.load(self.file)
        else:
            raise IOError(f"Invalid file path ext '{path}' "
                         f"not '.json', '.mgpk', or 'cbor'.")

        return it




class ConfigerDoer(doing.Doer):
    """
    Basic Filer Doer

    Attributes:
        done (bool): completion state:
            True means completed
            Otherwise incomplete. Incompletion maybe due to close or abort.
        configer (Configer): instance

    Properties:
        tyme (float): relative cycle time of associated Tymist .tyme obtained
            via injected .tymth function wrapper closure.
        tymth (func): closure returned by Tymist .tymeth() method.
            When .tymth is called it returns associated Tymist .tyme.
            .tymth provides injected dependency on Tymist tyme base.
        tock (float)): desired time in seconds between runs or until next run,
                 non negative, zero means run asap

    """

    def __init__(self, configer, **kwa):
        """
        Parameters:
           tymist (Tymist): instance
           tock (float): initial value of .tock in seconds
           configer (Configer): instance
        """
        super(ConfigerDoer, self).__init__(**kwa)
        self.configer = configer

    def enter(self):
        """"""
        if not self.configer.opened:
            self.configer.reopen()

    def exit(self):
        """"""
        self.configer.close(clear=self.configer.temp)
