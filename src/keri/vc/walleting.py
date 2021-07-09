# -*- encoding: utf-8 -*-
"""
keri.vc.walleting module

"""
from ..core.coring import Counter, CtrDex, Prefixer, Seqner, Diger, Siger
from ..core.parsing import Parser, Colds
from ..core.scheming import JSONSchema, CacheResolver
from ..db import dbing, koming
from ..kering import ShortageError, ColdStartError, ExtractionError, UnverifiedProofError
from ..vc.proving import Credentialer

# TODO: create this and populate with needed schema for now
cache = CacheResolver()


def openPocket(name="test", **kwa):
    """
    Returns contextmanager generated by openLMDB but with Baser instance
    """
    return dbing.openLMDB(cls=Pocketer, name=name, **kwa)


def parseCredential(ims=b'', wallet=None, typ=JSONSchema()):
    """
    Parse the ims bytearray as a CESR Proof Format verifiable credential

    Parameters:
        ims (bytearray) of serialized incoming verifiable credential in CESR Proof Format.
        wallet (Wallet) storage for the verified credential
        typ (JSONSchema) class for resolving schema references:

    """
    try:
        creder = Credentialer(raw=ims, typ=typ)
    except ShortageError as e:
        raise e
    else:
        del ims[:creder.size]
    cold = Parser.sniff(ims)
    if cold is Colds.msg:
        raise ColdStartError("unable to parse VC, attachments expected")

    ctr = Parser.extract(ims=ims, klas=Counter, cold=cold)
    if ctr.code != CtrDex.AttachedMaterialQuadlets:
        raise ExtractionError("Invalid attachment to VC {}, expected {}"
                              "".format(ctr.code, CtrDex.AttachedMaterialQuadlets))

    pags = ctr.count * 4
    if len(ims) != pags:
        raise ShortageError("VC proof attachment invalid length {}, expected {}"
                            "".format(len(ims), pags))

    prefixer, seqner, diger, isigers = parseProof(ims)

    wallet.processCredential(creder, prefixer, seqner, diger, isigers)


def parseProof(ims=b''):
    cold = Parser.sniff(ims)
    if cold is Colds.msg:
        raise ColdStartError("unable to parse VC, attachments expected")

    ctr = Parser.extract(ims=ims, klas=Counter, cold=cold)
    if ctr.code != CtrDex.TransIndexedSigGroups or ctr.count != 1:
        raise ExtractionError("Invalid attachment to VC {}, expected one {}"
                              "".format(ctr.code, CtrDex.TransIndexedSigGroups))


    prefixer = Parser.extract(ims=ims, klas=Prefixer)
    seqner = Parser.extract(ims=ims, klas=Seqner)
    diger = Parser.extract(ims=ims, klas=Diger)

    ictr = Parser.extract(ims=ims, klas=Counter)
    if ictr.code != CtrDex.ControllerIdxSigs:
        raise ExtractionError("Invalid attachment to VC {}, expected {}"
                              "".format(ctr.code, CtrDex.ControllerIdxSigs))

    isigers = []
    for i in range(ictr.count):
        isiger = Parser.extract(ims=ims, klas=Siger)
        isigers.append(isiger)

    return prefixer, seqner, diger, isigers


def buildProof(prefixer, seqner, diger, sigers):
    """
    
    Parameters:
        prefixer (Prefixer) Identifier of the issuer of the credential
        seqner (Seqner) is the sequence number of the event used to sign the credential
        diger (Diger) is the digest of the event used to sign the credential
        sigers (list) are the cryptographic signatures on the credential
    
    """
    
    prf = bytearray()
    prf.extend(Counter(CtrDex.TransIndexedSigGroups, count=1).qb64b)
    prf.extend(prefixer.qb64b)
    prf.extend(seqner.qb64b)
    prf.extend(diger.qb64b)

    prf.extend(Counter(code=CtrDex.ControllerIdxSigs, count=len(sigers)).qb64b)
    for siger in sigers:
        prf.extend(siger.qb64b)
    
    return prf
    
    
class Pocketer(dbing.LMDBer):
    """
    Pocketer is the store for the wallet (get it?).


        .issus is named subDB of issuer prefix identifiers to Credential SAIDs
            representing the credentials issued by an Issuer
            DB is keyed by identifer prefix of the Issuer of the credential
            More than one value per DB key is allowed
        .subjs is named subDB of subject prefix identifiers to Credential SAIDs
            representing the credentials issued TO the subject identified by the prefix
            DB is keyed by identifer prefix of the subject of the credential
            More than one value per DB key is allowed
        .sers is the named subDB of raw serialized bytes of the Credential.  Represents
            what was signed
            key is Credential SAID
            Only one value per DB key is allowed
        .seals is the named subDB of the Event Location Seal triple of pre+snu+dig
            of the location in the KEL where the VC was signed
            key is Credential SAID
            Only one value per DB key is allowed
        .sigs is named sub DB of event proof quadruples from transferable
            signers. Each quadruple is concatenation of  four fully qualified items
            of validator. These are: transferable prefix, plus latest establishment
            event sequence number plus latest establishment event digest,
            plus indexed event signature.
            When latest establishment event is multisig then there will
            be multiple quadruples one per signing key, each a dup at same db key.
            dgKey
            DB is keyed by Credential SAID
            More than one value per DB key is allowed


    """
    TailDirPath = "keri/pck"
    AltTailDirPath = ".keri/pck"
    TempPrefix = "keri_pck_"

    def __init__(self, headDirPath=None, reopen=True, **kwa):
        """
        Setup named sub databases.

        Parameters:
            name is str directory path name differentiator for main database
                When system employs more than one keri database, name allows
                differentiating each instance by name
            temp is boolean, assign to .temp
                True then open in temporary directory, clear on close
                Othewise then open persistent directory, do not clear on close
            headDirPath is optional str head directory pathname for main database
                If not provided use default .HeadDirpath
            mode is int numeric os dir permissions for database directory
            reopen is boolean, IF True then database will be reopened by this init
        """

        super(Pocketer, self).__init__(headDirPath=headDirPath, reopen=reopen, **kwa)


    def reopen(self, **kwa):
        """
        Open sub databases
        """
        super(Pocketer, self).reopen(**kwa)

        self.sers = self.env.open_db(key=b'sers.')
        self.seals = self.env.open_db(key=b'seals.')
        self.sigs = self.env.open_db(key=b'sigs.', dupsort=True)
        self.issus = self.env.open_db(key=b'issus.', dupsort=True)
        self.subjs = self.env.open_db(key=b'subjs.', dupsort=True)
        self.schms = self.env.open_db(key=b'schms.', dupsort=True)

        return self.env

    def getSigs(self, key):
        """
        Use dgKey()
        Return list of indexed witness signatures at key
        Returns empty list if no entry at key
        Duplicates are retrieved in lexocographic order not insertion order.
        """
        return self.getVals(self.sigs, key)

    def getSigsIter(self, key):
        """
        Use dgKey()
        Return iterator of indexed witness signatures at key
        Raises StopIteration Error when empty
        Duplicates are retrieved in lexocographic order not insertion order.
        """
        return self.getValsIter(self.sigs, key)

    def putSigs(self, key, vals):
        """
        Use dgKey()
        Write each entry from list of bytes indexed witness signatures vals to key
        Adds to existing signatures at key if any
        Returns True If no error
        Apparently always returns True (is this how .put works with dupsort=True)
        Duplicates are inserted in lexocographic order not insertion order.
        """
        return self.putVals(self.sigs, key, vals)

    def addSig(self, key, val):
        """
        Use dgKey()
        Add indexed witness signature val bytes as dup to key in db
        Adds to existing values at key if any
        Returns True if written else False if dup val already exists
        Duplicates are inserted in lexocographic order not insertion order.
        """
        return self.addVal(self.sigs, key, val)

    def cntSigs(self, key):
        """
        Use dgKey()
        Return count of indexed witness signatures at key
        Returns zero if no entry at key
        """
        return self.cntVals(self.sigs, key)

    def delSigs(self, key, val=b''):
        """
        Use dgKey()
        Deletes all values at key if val = b'' else deletes dup val = val.
        Returns True If key exists in database (or key, val if val not b'') Else False
        """
        return self.delVals(self.sigs, key, val)



    def getIssus(self, key):
        """
        Use dgKey()
        Return list of indexed witness signatures at key
        Returns empty list if no entry at key
        Duplicates are retrieved in lexocographic order not insertion order.
        """
        return self.getIoVals(self.issus, key)

    def getIssusIter(self, key):
        """
        Use dgKey()
        Return iterator of indexed witness signatures at key
        Raises StopIteration Error when empty
        Duplicates are retrieved in lexocographic order not insertion order.
        """
        return self.getIoValsIter(self.issus, key)

    def putIssus(self, key, vals):
        """
        Use dgKey()
        Write each entry from list of bytes indexed witness signatures vals to key
        Adds to existing signatures at key if any
        Returns True If no error
        Apparently always returns True (is this how .put works with dupsort=True)
        Duplicates are inserted in lexocographic order not insertion order.
        """
        return self.putIoVals(self.issus, key, vals)

    def addIssu(self, key, val):
        """
        Use dgKey()
        Add indexed witness signature val bytes as dup to key in db
        Adds to existing values at key if any
        Returns True if written else False if dup val already exists
        Duplicates are inserted in lexocographic order not insertion order.
        """
        return self.addIoVal(self.issus, key, val)

    def cntIssus(self, key):
        """
        Use dgKey()
        Return count of indexed witness signatures at key
        Returns zero if no entry at key
        """
        return self.cntIoVals(self.issus, key)

    def delIssus(self, key):
        """
        Use dgKey()
        Deletes all values at key if val = b'' else deletes dup val = val.
        Returns True If key exists in database (or key, val if val not b'') Else False
        """
        return self.delIoVals(self.issus, key)



    def getSubjs(self, key):
        """
        Use dgKey()
        Return list of indexed witness signatures at key
        Returns empty list if no entry at key
        Duplicates are retrieved in lexocographic order not insertion order.
        """
        return self.getIoVals(self.subjs, key)

    def getSubjsIter(self, key):
        """
        Use dgKey()
        Return iterator of indexed witness signatures at key
        Raises StopIteration Error when empty
        Duplicates are retrieved in lexocographic order not insertion order.
        """
        return self.getIoValsIter(self.subjs, key)

    def putSubjs(self, key, vals):
        """
        Use dgKey()
        Write each entry from list of bytes indexed witness signatures vals to key
        Adds to existing signatures at key if any
        Returns True If no error
        Apparently always returns True (is this how .put works with dupsort=True)
        Duplicates are inserted in lexocographic order not insertion order.
        """
        return self.putIoVals(self.subjs, key, vals)

    def addSubj(self, key, val):
        """
        Use dgKey()
        Add indexed witness signature val bytes as dup to key in db
        Adds to existing values at key if any
        Returns True if written else False if dup val already exists
        Duplicates are inserted in lexocographic order not insertion order.
        """
        return self.addIoVal(self.subjs, key, val)

    def cntSubjs(self, key):
        """
        Use dgKey()
        Return count of indexed witness signatures at key
        Returns zero if no entry at key
        """
        return self.cntIoVals(self.subjs, key)

    def delSubjs(self, key):
        """
        Use dgKey()
        Deletes all values at key if val = b'' else deletes dup val = val.
        Returns True If key exists in database (or key, val if val not b'') Else False
        """
        return self.delIoVals(self.subjs, key)


    def getSchms(self, key):
        """
        Use dgKey()
        Return list of indexed witness signatures at key
        Returns empty list if no entry at key
        Duplicates are retrieved in lexocographic order not insertion order.
        """
        return self.getIoVals(self.schms, key)

    def getSchmsIter(self, key):
        """
        Use dgKey()
        Return iterator of indexed witness signatures at key
        Raises StopIteration Error when empty
        Duplicates are retrieved in lexocographic order not insertion order.
        """
        return self.getIoValsIter(self.schms, key)


    def putSchms(self, key, vals):
        """
        Use dgKey()
        Write each entry from list of bytes indexed witness signatures vals to key
        Adds to existing signatures at key if any
        Returns True If no error
        Apparently always returns True (is this how .put works with dupsort=True)
        Duplicates are inserted in lexocographic order not insertion order.
        """
        return self.putIoVals(self.schms, key, vals)

    def addSchm(self, key, val):
        """
        Use dgKey()
        Add indexed witness signature val bytes as dup to key in db
        Adds to existing values at key if any
        Returns True if written else False if dup val already exists
        Duplicates are inserted in lexocographic order not insertion order.
        """
        return self.addIoVal(self.schms, key, val)

    def cntSchms(self, key):
        """
        Use dgKey()
        Return count of indexed witness signatures at key
        Returns zero if no entry at key
        """
        return self.cntIoVals(self.schms, key)


    def delSchms(self, key):
        """
        Use dgKey()
        Deletes all values at key if val = b'' else deletes dup val = val.
        Returns True If key exists in database (or key, val if val not b'') Else False
        """
        return self.delIoVals(self.schms, key)



    def putSers(self, key, val):
        """
        Use dgKey()
        Write serialized event bytes val to key
        Does not overwrite existing val if any
        Returns True If val successfully written Else False
        Return False if key already exists
        """
        return self.putVal(self.sers, key, val)


    def setSers(self, key, val):
        """
        Use dgKey()
        Write serialized event bytes val to key
        Overwrites existing val if any
        Returns True If val successfully written Else False
        """
        return self.setVal(self.sers, key, val)


    def getSers(self, key):
        """
        Use dgKey()
        Return event at key
        Returns None if no entry at key
        """
        return self.getVal(self.sers, key)


    def delSers(self, key):
        """
        Use dgKey()
        Deletes value at key.
        Returns True If key exists in database Else False
        """
        return self.delVal(self.sers, key)


    def putSeals(self, key, val):
        """
        Use dgKey()
        Write sealialized event bytes val to key
        Does not overwrite existing val if any
        Returns True If val successfully written Else False
        Return False if key already exists
        """
        return self.putVal(self.seals, key, val)


    def setSeals(self, key, val):
        """
        Use dgKey()
        Write sealialized event bytes val to key
        Overwrites existing val if any
        Returns True If val successfully written Else False
        """
        return self.setVal(self.seals, key, val)


    def getSeals(self, key):
        """
        Use dgKey()
        Return event at key
        Returns None if no entry at key
        """
        return self.getVal(self.seals, key)


    def delSeals(self, key):
        """
        Use dgKey()
        Deletes value at key.
        Returns True If key exists in database Else False
        """
        return self.delVal(self.seals, key)



class Wallet:
    """
    Wallet represents all credentials received or verified


    """
    def __init__(self, hab, db: Pocketer=None, name="test", temp=False):
        """
        Create a Wallet associated with a Habitat

        Parameters:
            hab (Habitat) is the local environment associate with this wallet

        """
        self.hab = hab
        self.name = name
        self.temp = temp

        self.db = db if db is not None else Pocketer(name=self.name, temp=self.temp)

    def processCredential(self, creder, prefixer, seqner, diger, sigers):
        """
        Verify the data of the credential against the schema, the SAID of the credential and
        the CESR Proof on the credential and if valid, store the credential

        Parameters:
            creder (Credentialer) that contains the credential to process
            prefixer (Prefixer) Identifier of the issuer of the credential
            seqner (Seqner) is the sequence number of the event used to sign the credential
            diger (Diger) is the digest of the event used to sign the credential
            sigers (list) are the cryptographic signatures on the credential
        """
        if not self.hab.verify(creder, prefixer, seqner, diger, sigers):
            raise UnverifiedProofError("invalid signatures on credential")


        self.saveCredential(creder, prefixer, seqner, diger, sigers)


    def saveCredential(self, creder, prefixer, seqner, diger, sigers):
        """
        Write the credential and associated indicies to the database
        
        Parameters:
            creder (Credentialer) that contains the credential to process
            prefixer (Prefixer) Identifier of the issuer of the credential
            seqner (Seqner) is the sequence number of the event used to sign the credential
            diger (Diger) is the digest of the event used to sign the credential
            sigers (list) are the cryptographic signatures on the credential
        """
        said = creder.said.encode("utf-8")
        schema = creder.schema.encode("utf-8")
        issuer = creder.issuer.encode("utf-8")
        subject = creder.subject["id"].encode("utf-8")
        raw = creder.raw
        self.db.putSers(key=said, val=raw)

        # Signer KEL Location and signatures
        triple = prefixer.qb64b + seqner.qb64b + diger.qb64b
        self.db.putSeals(said, triple)
        self.db.putSigs(said, [siger.qb64b for siger in sigers])  # idempotent

        # Look up indicies
        self.db.addIssu(key=issuer, val=said)
        self.db.addSubj(key=subject, val=said)
        self.db.addSchm(key=schema, val=said)



    def getCredentials(self, schema=None):
        """
        Return list of (creder, prefixer, seqner, diger, sigers) for each credential
        that matches schema

        Parameters:
            schema: qb64 SAID of the schema for the credential

        """
        saids = self.db.getSchms(key=schema.encode("utf-8"))

        creds = []
        for said in saids:
            raw = self.db.getSers(key=said)
            creder = Credentialer(raw=bytes(raw))

            trip = bytearray(self.db.getSeals(said))

            prefixer = Prefixer(qb64b=trip, strip=True)
            seqner = Seqner(qb64b=trip, strip=True)
            diger = Diger(qb64b=trip, strip=True)

            sigs = self.db.getSigs(said)
            sigers = [Siger(qb64b=bytearray(sig)) for sig in sigs]

            creds.append((creder, prefixer, seqner, diger, sigers))

        return creds
