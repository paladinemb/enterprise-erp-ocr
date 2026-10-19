# Third-party components

This integration uses the published packages from
[RapidAI/TableStructureRec](https://github.com/RapidAI/TableStructureRec):
`wired-table-rec 1.2.0`, `lineless-table-rec 0.1.0`, `table-cls 1.2.0`.
Their Apache-2.0 license is retained in `TableStructureRec-LICENSE`.
OCR is provided by [RapidAI/RapidOCR](https://github.com/RapidAI/RapidOCR), version 2.1.0.
The packages load their upstream ONNX models on first use; model artifacts are
not redistributed by this repository. See upstream repositories for model provenance.

The existing frontend uses SheetJS CE 0.20.3 (Apache-2.0).
The bundled legacy Tesseract.js files remain in dist/vendor but are no longer loaded.
