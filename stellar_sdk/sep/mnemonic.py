"""
SEP: 0005
Title: Key Derivation Methods for Stellar Accounts
"""

import hashlib
import hmac
import os
import struct
from enum import Enum, unique
from typing import Union

from mnemonic import Mnemonic
from mnemonic.mnemonic import PBKDF2_ROUNDS

from ..exceptions import ValueError


@unique
class Language(Enum):
    JAPANESE = "japanese"
    FRENCH = "french"
    ENGLISH = "english"
    SPANISH = "spanish"
    ITALIAN = "italian"
    KOREAN = "korean"
    CHINESE_SIMPLIFIED = "chinese_simplified"
    CHINESE_TRADITIONAL = "chinese_traditional"


class StellarMnemonic(Mnemonic):
    STELLAR_ACCOUNT_PATH_FORMAT = "m/44'/148'/%d'"
    FIRST_HARDENED_INDEX = 0x80000000
    SEED_MODIFIER = b"ed25519 seed"

    def __init__(self, language: Union[str, Language] = Language.ENGLISH) -> None:
        if isinstance(language, Language):
            language = language.value
        else:
            if language not in set(item.value for item in Language):
                raise ValueError("This language is not supported.")

        super().__init__(language)

    @classmethod
    def to_seed(cls, mnemonic: str, passphrase: str = "", index: int = 0) -> bytes:
        mnemonic = cls.normalize_string(mnemonic)
        passphrase = cls.normalize_string(passphrase)
        passphrase = "mnemonic" + passphrase
        mnemonic = mnemonic.encode("utf-8")
        passphrase = passphrase.encode("utf-8")
        stretched = hashlib.pbkdf2_hmac("sha512", mnemonic, passphrase, PBKDF2_ROUNDS)
        return cls.derive(stretched[:64], index)

    def generate(self, strength: int = 128) -> str:
        if strength not in (128, 160, 192, 224, 256):
            raise ValueError(
                "Strength should be one of the following [128, 160, 192, 224, 256], but it is not (%d)."
                % strength
            )
        return self.to_mnemonic(os.urandom(strength // 8))

    @staticmethod
    def derive(seed: bytes, index: int) -> bytes:
        # References https://github.com/satoshilabs/slips/blob/master/slip-0010.md
        master_hmac = hmac.new(StellarMnemonic.SEED_MODIFIER, digestmod=hashlib.sha512)
        master_hmac.update(seed)
        il = master_hmac.digest()[:32]
        ir = master_hmac.digest()[32:]
        path = StellarMnemonic.STELLAR_ACCOUNT_PATH_FORMAT % index
        for x in path.split("/")[1:]:
            data = (
                struct.pack("x")
                + il
                + struct.pack(">I", StellarMnemonic.FIRST_HARDENED_INDEX + int(x[:-1]))
            )
            i = hmac.new(ir, digestmod=hashlib.sha512)
            i.update(data)
            il = i.digest()[:32]
            ir = i.digest()[32:]
        return il