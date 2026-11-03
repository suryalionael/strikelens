# shared/

Things used by more than one part of StrikeLens.

- `schema/`: JSON Schemas (Draft 2020-12) for tags, fights, and fighters. The
  tagger, the API, and the CV pipeline all read and write data in these shapes.
  Human tags and CV suggestions use the same tag schema. See
  [docs/tag-schema.md](../docs/tag-schema.md).
