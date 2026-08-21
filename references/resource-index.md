# Resource index

Load only the resource required by the active workflow. Resolve every path from the skill root.

## agents

Agent interface metadata.

- [agents/openai.yaml](../agents/openai.yaml)

## assets

Configurations, synthetic examples, and report templates.

- [assets/config/analysis.yaml](../assets/config/analysis.yaml)
- [assets/config/cleaning.yaml](../assets/config/cleaning.yaml)
- [assets/config/crawler.yaml](../assets/config/crawler.yaml)
- [assets/config/default.yaml](../assets/config/default.yaml)
- [assets/config/models.yaml](../assets/config/models.yaml)
- [assets/config/report.yaml](../assets/config/report.yaml)
- [assets/config/taxonomy.yaml](../assets/config/taxonomy.yaml)
- [assets/examples/hybrid_project.yaml](../assets/examples/hybrid_project.yaml)
- [assets/examples/import_project.yaml](../assets/examples/import_project.yaml)
- [assets/examples/sample_browseract.jsonl](../assets/examples/sample_browseract.jsonl)
- [assets/examples/sample_emotion_lexicon.xlsx](../assets/examples/sample_emotion_lexicon.xlsx)
- [assets/examples/sample_mediacrawler/xhs/jsonl/search_contents.jsonl](../assets/examples/sample_mediacrawler/xhs/jsonl/search_contents.jsonl)
- [assets/examples/sample_posts.csv](../assets/examples/sample_posts.csv)
- [assets/examples/sample_project.yaml](../assets/examples/sample_project.yaml)
- [assets/templates/report/base.html](../assets/templates/report/base.html)

## references

Methods, controls, and bundled sub-skills.

- [references/analysis-contract.md](analysis-contract.md)
- [references/analysis-modes.md](analysis-modes.md)
- [references/architecture.md](architecture.md)
- [references/capability-map.md](capability-map.md)
- [references/collection-strategies.md](collection-strategies.md)
- [references/mediacrawler-installation.md](mediacrawler-installation.md)
- [references/security-and-validation.md](security-and-validation.md)
- [references/skills/environment-diagnostics/SKILL.md](skills/environment-diagnostics/SKILL.md)
- [references/skills/environment-diagnostics/agents/openai.yaml](skills/environment-diagnostics/agents/openai.yaml)
- [references/skills/evidence-validator/SKILL.md](skills/evidence-validator/SKILL.md)
- [references/skills/evidence-validator/agents/openai.yaml](skills/evidence-validator/agents/openai.yaml)
- [references/skills/html-report-generator/SKILL.md](skills/html-report-generator/SKILL.md)
- [references/skills/html-report-generator/agents/openai.yaml](skills/html-report-generator/agents/openai.yaml)
- [references/skills/opinion-analysis-engine/SKILL.md](skills/opinion-analysis-engine/SKILL.md)
- [references/skills/opinion-analysis-engine/agents/openai.yaml](skills/opinion-analysis-engine/agents/openai.yaml)
- [references/skills/opinion-data-cleaner/SKILL.md](skills/opinion-data-cleaner/SKILL.md)
- [references/skills/opinion-data-cleaner/agents/openai.yaml](skills/opinion-data-cleaner/agents/openai.yaml)
- [references/skills/predictive-modeler/SKILL.md](skills/predictive-modeler/SKILL.md)
- [references/skills/predictive-modeler/agents/openai.yaml](skills/predictive-modeler/agents/openai.yaml)
- [references/skills/research-brief-builder/SKILL.md](skills/research-brief-builder/SKILL.md)
- [references/skills/research-brief-builder/agents/openai.yaml](skills/research-brief-builder/agents/openai.yaml)
- [references/skills/user-insight-synthesizer/SKILL.md](skills/user-insight-synthesizer/SKILL.md)
- [references/skills/user-insight-synthesizer/agents/openai.yaml](skills/user-insight-synthesizer/agents/openai.yaml)
- [references/skills/xhs-crawler-planner/SKILL.md](skills/xhs-crawler-planner/SKILL.md)
- [references/skills/xhs-crawler-planner/agents/openai.yaml](skills/xhs-crawler-planner/agents/openai.yaml)
- [references/skills/xhs-data-collector/SKILL.md](skills/xhs-data-collector/SKILL.md)
- [references/skills/xhs-data-collector/agents/openai.yaml](skills/xhs-data-collector/agents/openai.yaml)
- [references/visual-system.md](visual-system.md)

## scripts

Executable entry points, runtime source, and tests.

- [scripts/install_skill.py](../scripts/install_skill.py)
- [scripts/launch.py](../scripts/launch.py)
- [scripts/package_shareable.py](../scripts/package_shareable.py)
- [scripts/runtime/pyproject.toml](../scripts/runtime/pyproject.toml)
- [scripts/runtime/requirements-advanced.txt](../scripts/runtime/requirements-advanced.txt)
- [scripts/runtime/requirements.txt](../scripts/runtime/requirements.txt)
- [scripts/runtime/src/userresearch_xhscrawler_cockpitux/__init__.py](../scripts/runtime/src/userresearch_xhscrawler_cockpitux/__init__.py)
- [scripts/runtime/src/userresearch_xhscrawler_cockpitux/__main__.py](../scripts/runtime/src/userresearch_xhscrawler_cockpitux/__main__.py)
- [scripts/runtime/src/userresearch_xhscrawler_cockpitux/analysis/__init__.py](../scripts/runtime/src/userresearch_xhscrawler_cockpitux/analysis/__init__.py)
- [scripts/runtime/src/userresearch_xhscrawler_cockpitux/analysis/advanced.py](../scripts/runtime/src/userresearch_xhscrawler_cockpitux/analysis/advanced.py)
- [scripts/runtime/src/userresearch_xhscrawler_cockpitux/analysis/base.py](../scripts/runtime/src/userresearch_xhscrawler_cockpitux/analysis/base.py)
- [scripts/runtime/src/userresearch_xhscrawler_cockpitux/analysis/engine.py](../scripts/runtime/src/userresearch_xhscrawler_cockpitux/analysis/engine.py)
- [scripts/runtime/src/userresearch_xhscrawler_cockpitux/brief.py](../scripts/runtime/src/userresearch_xhscrawler_cockpitux/brief.py)
- [scripts/runtime/src/userresearch_xhscrawler_cockpitux/cleaning.py](../scripts/runtime/src/userresearch_xhscrawler_cockpitux/cleaning.py)
- [scripts/runtime/src/userresearch_xhscrawler_cockpitux/cli.py](../scripts/runtime/src/userresearch_xhscrawler_cockpitux/cli.py)
- [scripts/runtime/src/userresearch_xhscrawler_cockpitux/config.py](../scripts/runtime/src/userresearch_xhscrawler_cockpitux/config.py)
- [scripts/runtime/src/userresearch_xhscrawler_cockpitux/crawler/__init__.py](../scripts/runtime/src/userresearch_xhscrawler_cockpitux/crawler/__init__.py)
- [scripts/runtime/src/userresearch_xhscrawler_cockpitux/crawler/adapters.py](../scripts/runtime/src/userresearch_xhscrawler_cockpitux/crawler/adapters.py)
- [scripts/runtime/src/userresearch_xhscrawler_cockpitux/diagnostics.py](../scripts/runtime/src/userresearch_xhscrawler_cockpitux/diagnostics.py)
- [scripts/runtime/src/userresearch_xhscrawler_cockpitux/insights/__init__.py](../scripts/runtime/src/userresearch_xhscrawler_cockpitux/insights/__init__.py)
- [scripts/runtime/src/userresearch_xhscrawler_cockpitux/insights/synthesizer.py](../scripts/runtime/src/userresearch_xhscrawler_cockpitux/insights/synthesizer.py)
- [scripts/runtime/src/userresearch_xhscrawler_cockpitux/insights/validator.py](../scripts/runtime/src/userresearch_xhscrawler_cockpitux/insights/validator.py)
- [scripts/runtime/src/userresearch_xhscrawler_cockpitux/interaction.py](../scripts/runtime/src/userresearch_xhscrawler_cockpitux/interaction.py)
- [scripts/runtime/src/userresearch_xhscrawler_cockpitux/llm/__init__.py](../scripts/runtime/src/userresearch_xhscrawler_cockpitux/llm/__init__.py)
- [scripts/runtime/src/userresearch_xhscrawler_cockpitux/llm/client.py](../scripts/runtime/src/userresearch_xhscrawler_cockpitux/llm/client.py)
- [scripts/runtime/src/userresearch_xhscrawler_cockpitux/models.py](../scripts/runtime/src/userresearch_xhscrawler_cockpitux/models.py)
- [scripts/runtime/src/userresearch_xhscrawler_cockpitux/orchestrator.py](../scripts/runtime/src/userresearch_xhscrawler_cockpitux/orchestrator.py)
- [scripts/runtime/src/userresearch_xhscrawler_cockpitux/planner.py](../scripts/runtime/src/userresearch_xhscrawler_cockpitux/planner.py)
- [scripts/runtime/src/userresearch_xhscrawler_cockpitux/reporting/__init__.py](../scripts/runtime/src/userresearch_xhscrawler_cockpitux/reporting/__init__.py)
- [scripts/runtime/src/userresearch_xhscrawler_cockpitux/reporting/generator.py](../scripts/runtime/src/userresearch_xhscrawler_cockpitux/reporting/generator.py)
- [scripts/runtime/src/userresearch_xhscrawler_cockpitux/storage.py](../scripts/runtime/src/userresearch_xhscrawler_cockpitux/storage.py)
- [scripts/runtime/src/userresearch_xhscrawler_cockpitux/ui/__init__.py](../scripts/runtime/src/userresearch_xhscrawler_cockpitux/ui/__init__.py)
- [scripts/runtime/src/userresearch_xhscrawler_cockpitux/ui/app.py](../scripts/runtime/src/userresearch_xhscrawler_cockpitux/ui/app.py)
- [scripts/runtime/tests/test_advanced.py](../scripts/runtime/tests/test_advanced.py)
- [scripts/runtime/tests/test_cleaning.py](../scripts/runtime/tests/test_cleaning.py)
- [scripts/runtime/tests/test_config_and_models.py](../scripts/runtime/tests/test_config_and_models.py)
- [scripts/runtime/tests/test_end_to_end.py](../scripts/runtime/tests/test_end_to_end.py)
- [scripts/verify_skill.py](../scripts/verify_skill.py)
