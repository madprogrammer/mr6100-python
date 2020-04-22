## MR6100 series UHF RFID reader Python library

This library allows to interact with Marktrace UHF RFID reader.
* FCC ID [WKXMR6100](https://fccid.io/WKXMR6100).

Might be used as a reference to work with other Chinese UHF readers from AliExpress.

Supported communication modes:
* Synchronous TCP using `socket` (`uhf_reader.UHFReader` class)
* Asyncronous TCP or serial using [Twisted](https://www.twistedmatrix.com/)
