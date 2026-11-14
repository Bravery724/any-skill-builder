# Public examples

`questionnaire.json` is a small English proposal fixture for a weekly-update skill. It demonstrates a single choice, conditional follow-up, multi-select output, and AI recommendations. It does not claim subject research or personal facts.

`weekly-update-questionnaire.json` adapts the completed example's historical questions to the current Questionnaire mode. The original `complete/questionnaire.json`, decisions, outputs, and evaluation evidence remain unchanged so their historical record stays inspectable.

`evaluation-plan.json` adapts two historical task cases into an unexecuted plan for `prepare_evaluation.py`, with coverage criteria strengthened after a new independent review. It references the existing fictional raw inputs and contains no run results. Preparation writes pending records; the historical outputs do not become fresh executions by using this plan. See the [execution loop](../any-skill-builder/references/evaluation-loop.md).

Use a fresh private workspace as shown in the main [README](../README.md). `set-questions --rebind-project` binds an authored fixture to another project name only while the run is empty and preserves the initialized mode. It cannot rebind saved answers or another run's identity.

For real work, research the requested subject and author suitable questions. Do not treat a fixture as evidence that the topic has been investigated. Image choices require actual assets and provenance.

See [the complete weekly-update walkthrough](complete/README.md) for source notes, decisions, a finished skill, raw task inputs, and recorded evaluation evidence. The [host-validation examples](host-validation/README.md) belong to the historical v0.2.3 CLI validation; they do not certify the redesigned offline workflow.
