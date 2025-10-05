Open Siddur Project (AI aided version)

This is a work in progress to convert the Open Siddur Project to use AI to aid in the conversion of the liturgical texts.

Features:
* A new version of JLPTEI (2) with a simplified schema.
* Less emphasis on UI: This is primarily about converting texts from any input format to JLPTEI, and converting the JLPTEI to useful output formats and combining texts in novel ways.

To compile the schema:

Prerequisites:
You need a working version of podman (open source implementation of docker).

The main schema is in `schema/jlptei.odd.xml`. To compile it, run:
```bash
$ scripts/build-schema.sh
```

The output will be in the `schema` directory as RelaxNG XML (and, eventually, ISO Schematron).
