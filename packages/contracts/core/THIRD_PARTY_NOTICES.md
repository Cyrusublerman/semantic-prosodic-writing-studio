# Third-Party Notices

Status: inventory baseline pending licence verification and owner licensing decision.

## Runtime dependencies

- Pydantic `2.13.4`
- uuid-utils `0.17.0`
- rfc8785 `0.1.4`
- packaging `25.0`

## Python validation and build dependencies

- pytest `9.0.2`
- Hypothesis `6.156.6`
- jsonschema `4.26.0`
- build `1.3.0`
- pytest-cov as installed by CI until incorporated into the locked test graph

## JavaScript validation and generation dependencies

- @hyperjump/json-schema `1.17.7`
- Ajv `8.20.0`
- ajv-formats `3.0.1`
- canonicalize `3.0.0`
- json-schema-to-typescript `15.0.4`
- TypeScript `6.0.3`

## Required completion work

Before external distribution or stable promotion:

1. verify each dependency's exact licence from its distributed package metadata;
2. record copyright and notice obligations;
3. generate machine-readable Python and Node dependency inventories;
4. include licences required by binary or source redistribution;
5. resolve the project licence separately for code, schemas, fixtures, generated declarations and documentation;
6. review whether generated artifacts inherit or require notices from their generators;
7. make the inventory reproducible from lock files.

This file is not a legal conclusion and does not grant a licence to the project. The package remains `LicenseRef-Proprietary` until the owner approves and commits an explicit licensing decision.
