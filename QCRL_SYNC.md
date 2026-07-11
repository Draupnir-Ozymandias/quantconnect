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

-----------------------------------------------------------------------------
QCRL_SYNC — 2026-07-10

Results Database / ResearchTools thread status:

Confirmed working end-to-end:
- main.py saves full ResearchReport to qcrl/v2/experiments/...
- main.py saves normalized experiment record to qcrl/v2/records/...
- run_id generation working
- generated_at_utc metadata working
- completed_at_algorithm_time metadata working
- record_source separation working

Current ObjectStore state:
- Total records: 309
- v2 records: 1
- legacy records: 308

Confirmed v2 record:
BTCUSD_1d_candle_streak_martingale_20260710T190732Z_07a7a0eb0afd

Normalized record fields verified:
- coin
- timeframe
- entry_model
- filter_model
- stake_mode
- net_profit
- win_rate
- trades
- ruined
- max_drawdown
- max_loss_streak
- max_recovery_depth
- risk_adjusted_score
- tail_risk_score
- record_source

ResearchTools v2 smoke test passed:
- load()
- select(record_source="v2")
- select(record_source="legacy")
- show()
- top()
- cohort summaries

Discovery Layer can now consume:
records = tools.select(record_source="v2")
or
records = store.load_all()

Next proposed Results Database / ResearchTools enhancements:
- tools.v2()
- tools.legacy()
- tools.latest()
- tools.dedupe()
- tools.export_csv()
- tools.experiment_dashboard()

----------------------------------------------------------------------------------------------------
QCRL_SYNC — 2026-07-10

ResearchTools v2 enhancement pass completed.

Confirmed working:
- tools.v2()
- tools.legacy()
- tools.latest()
- tools.latest_v2()
- tools.dedupe()
- tools.duplicates()
- tools.dashboard_text()

Record source separation:
- Total records: 309
- v2 records: 1
- legacy records: 308

Deduplication:
- Original records: 309
- Deduped records: 308
- Duplicate config groups: 1

Duplicate identified:
- legacy_BTCUSD_1d_b3bc3082e98d
- BTCUSD_1d_candle_streak_martingale_20260710T190732Z_07a7a0eb0afd

Root cause:
- Legacy date format used 2026-1-1 / 2026-7-7
- v2 date format used 2026-01-01 / 2026-07-07

Patch applied:
- config_signature() now normalizes date strings
- start/end date formats no longer break duplicate detection

Next proposed target:
- ResearchTools.experiment_dashboard()
- Research audit output
- suspicious record flags
- best-by-timeframe summaries
- worst tail-risk summaries
