# QCRL Sync Log

## Workstream A — Architecture / Engine
Owner: QCRL Architecture Overview

Current focus:
- Results Database
- ExperimentStore
- run_id
- timestamps
- ResearchTools v2

Exports:
- Experiment records
- Selection/query API
- ObjectStore key format

## Workstream B — Analysis / Discovery
Owner: QC - analysis

Current focus:
- Stability Engine
- Consensus Engine
- Cluster Engine
- Archetype Engine
- Confidence Engine

Consumes:
- ResearchReport JSON
- ExperimentStore query output

----------------------------------------------------------------
QCRL_SYNC — 2026-07-10

Workstream A / Architecture thread has accepted ownership of:
- Results Database
- ExperimentStore
- run_id generation
- generated_at_utc timestamps
- ObjectStore layout
- normalized experiment records
- ResearchTools v2 retrieval API

Boundary contract:
Discovery Layer must consume normalized experiment records through:

class ExperimentStore:
    def load_all(self):
        pass

    def select(self, **filters):
        pass

    def get(self, run_id):
        pass

    def load_report(self, run_id):
        pass

Current ObjectStore issue:
Existing report key is configuration-based and may overwrite prior runs. Architecture thread will replace it with run-based keys.

Proposed ObjectStore layout:
qcrl/v2/experiments/{coin}/{timeframe}/{year}/{run_id}.json
qcrl/v2/records/{run_id}.json
qcrl/v2/manifests/{year}/{coin}_{timeframe}.json

Discovery thread should continue designing:
discovery/stability_engine.py

against a clean ExperimentStore abstraction only.
------------------------------------------------------------

QCRL_SYNC — 2026-07-10

Architecture / Results Database thread completed first ExperimentStore v1 implementation.

New file:
- experiment_store.py

Implemented API:
class ExperimentStore:
    def load_all(self, include_legacy=True)
    def select(self, **filters)
    def get(self, run_id)
    def load_report(self, run_id)
    def save_report_and_record(self, report)
    def top(self, records=None, sort_by="risk_adjusted_score", n=10, reverse=True)

ObjectStore layout now targeted:
- qcrl/v2/experiments/{coin}/{timeframe}/{year}/{run_id}.json
- qcrl/v2/records/{run_id}.json

report_models.py now generates:
- schema_version
- record_schema_version
- run_id
- generated_at_utc
- completed_at_algorithm_time
- experiment_group
- experiment_name
- experiment_tags
- normalized experiment record

main.py now saves:
- full nested ResearchReport
- normalized flat experiment record
- Run ID in Debug output

Discovery Layer can now safely begin against:
records = store.load_all()
cohort = store.select(coin="BTCUSD", timeframe="1h")

Discovery should not depend on ObjectStore internals.
