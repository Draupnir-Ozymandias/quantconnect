# region imports
from AlgorithmImports import *
# endregion

# Experiment Metadata
# ===================
# Generates factual experiment metadata from the runtime configuration.
# Manual metadata is intentionally limited to LAB_VERSION and optional RUN_NOTES.

import hashlib
import json


class ExperimentMetadataBuilder:
    METADATA_VERSION = "qcrl.metadata.v1"

    @staticmethod
    def build(algo):
        identity = ExperimentMetadataBuilder.identity_configuration(algo)
        canonical = json.dumps(
            identity,
            sort_keys=True,
            separators=(",", ":")
        )
        configuration_hash = hashlib.sha256(
            canonical.encode("utf-8")
        ).hexdigest()

        start_year = int(getattr(algo, "start_year", 0))
        end_year = int(getattr(algo, "end_year", start_year))
        coin = str(getattr(algo, "coin", "unknown")).upper()
        timeframe = str(getattr(algo, "timeframe", "unknown")).lower()

        entry_model = str(
            getattr(algo, "entry_model_name", "unknown")
        ).lower()
        filter_model = str(
            getattr(algo, "filter_model_name", "none")
        ).lower()
        stake_mode = str(
            getattr(algo, "stake_mode", "unknown")
        ).lower()

        experiment_group = ExperimentMetadataBuilder._slug(
            "_".join([
                coin.lower(),
                ExperimentMetadataBuilder._year_label(
                    start_year,
                    end_year
                ),
                timeframe,
                entry_model,
                filter_model,
                stake_mode
            ])
        )

        experiment_family = ExperimentMetadataBuilder._family(algo)
        experiment_name = ExperimentMetadataBuilder._name(algo)

        tags = ExperimentMetadataBuilder._tags(
            algo,
            start_year,
            end_year
        )

        automatic_note = (
            "Auto-generated from runtime configuration. "
            f"Configuration hash: {configuration_hash[:16]}."
        )

        user_note = str(
            getattr(algo, "run_notes", "")
        ).strip()

        if user_note:
            experiment_notes = f"{automatic_note} Notes: {user_note}"
        else:
            experiment_notes = automatic_note

        return {
            "metadata_version": ExperimentMetadataBuilder.METADATA_VERSION,
            "metadata_source": "runtime_generated",
            "configuration_hash": configuration_hash,
            "experiment_id": f"exp_{configuration_hash[:16]}",
            "experiment_group": experiment_group,
            "experiment_name": experiment_name,
            "experiment_notes": experiment_notes,
            "experiment_tags": tags,
            "experiment_year": start_year,
            "experiment_year_end": end_year,
            "experiment_asset": coin,
            "experiment_timeframe": timeframe,
            "experiment_family": experiment_family
        }

    @staticmethod
    def identity_configuration(algo):
        """
        Return only behaviorally relevant runtime values.

        Irrelevant parameters are intentionally excluded. For example,
        EMA periods do not affect a no-filter run, and martingale settings
        do not affect a flat-stake run.
        """
        entry_model = str(
            getattr(algo, "entry_model_name", "unknown")
        ).lower()
        filter_model = str(
            getattr(algo, "filter_model_name", "none")
        ).lower()
        stake_mode = str(
            getattr(algo, "stake_mode", "unknown")
        ).lower()

        identity = {
            "lab_version": str(
                getattr(algo, "lab_version", "unknown")
            ),
            "coin": str(getattr(algo, "coin", "unknown")).upper(),
            "timeframe": str(
                getattr(algo, "timeframe", "unknown")
            ).lower(),
            "start": ExperimentMetadataBuilder._date_text(
                getattr(algo, "start_year", 0),
                getattr(algo, "start_month", 0),
                getattr(algo, "start_day", 0)
            ),
            "end": ExperimentMetadataBuilder._date_text(
                getattr(algo, "end_year", 0),
                getattr(algo, "end_month", 0),
                getattr(algo, "end_day", 0)
            ),
            "entry_model": entry_model,
            "filter_model": filter_model,
            "stake_mode": stake_mode,
            "base_wager": float(
                getattr(algo, "base_wager", 0.0)
            ),
            "bankroll": float(
                getattr(algo, "initial_bankroll", 0.0)
            )
        }

        if entry_model == "fixed_bias":
            identity["bias"] = str(
                getattr(algo, "bias", "up")
            ).lower()

        if entry_model == "candle_streak":
            identity["streak_length"] = int(
                getattr(algo, "streak_length", 2)
            )
            identity["streak_mode"] = str(
                getattr(algo, "streak_mode", "follow")
            ).lower()

        if filter_model == "ema_trend":
            identity["ema_fast"] = int(
                getattr(algo, "ema_fast", 0)
            )
            identity["ema_slow"] = int(
                getattr(algo, "ema_slow", 0)
            )

        if stake_mode == "martingale":
            identity["multiplier"] = float(
                getattr(algo, "multiplier", 0.0)
            )
            identity["max_steps"] = int(
                getattr(algo, "max_steps", 0)
            )

        return identity

    @staticmethod
    def _family(algo):
        entry_model = str(
            getattr(algo, "entry_model_name", "unknown")
        ).lower()
        filter_model = str(
            getattr(algo, "filter_model_name", "none")
        ).lower()
        stake_mode = str(
            getattr(algo, "stake_mode", "unknown")
        ).lower()

        entry_family = entry_model

        if entry_model == "fixed_bias":
            entry_family += "_" + str(
                getattr(algo, "bias", "up")
            ).lower()

        if entry_model == "candle_streak":
            entry_family += "_" + str(
                getattr(algo, "streak_mode", "follow")
            ).lower()

        return ExperimentMetadataBuilder._slug(
            f"{entry_family}__{filter_model}__{stake_mode}"
        )

    @staticmethod
    def _name(algo):
        coin = str(getattr(algo, "coin", "UNKNOWN")).upper()
        timeframe = str(getattr(algo, "timeframe", "unknown")).lower()
        start_year = int(getattr(algo, "start_year", 0))
        end_year = int(getattr(algo, "end_year", start_year))

        year_label = ExperimentMetadataBuilder._year_label(
            start_year,
            end_year
        )

        entry_label = ExperimentMetadataBuilder._entry_label(algo)
        filter_label = ExperimentMetadataBuilder._filter_label(algo)
        stake_label = ExperimentMetadataBuilder._stake_label(algo)

        return (
            f"{coin} {timeframe} {year_label} | "
            f"{entry_label} | {filter_label} | {stake_label}"
        )

    @staticmethod
    def _entry_label(algo):
        entry_model = str(
            getattr(algo, "entry_model_name", "unknown")
        ).lower()

        if entry_model == "fixed_bias":
            bias = str(getattr(algo, "bias", "up")).title()
            return f"Fixed Bias {bias}"

        if entry_model == "previous_candle":
            return "Previous Candle Follow"

        if entry_model == "previous_candle_reverse":
            return "Previous Candle Reverse"

        if entry_model == "candle_streak":
            length = int(getattr(algo, "streak_length", 2))
            mode = str(
                getattr(algo, "streak_mode", "follow")
            ).title()
            return f"{length}-Bar Candle Streak {mode}"

        return entry_model.replace("_", " ").title()

    @staticmethod
    def _filter_label(algo):
        filter_model = str(
            getattr(algo, "filter_model_name", "none")
        ).lower()

        if filter_model == "none":
            return "No Filter"

        if filter_model == "ema_trend":
            fast = int(getattr(algo, "ema_fast", 0))
            slow = int(getattr(algo, "ema_slow", 0))
            return f"EMA Trend {fast}/{slow}"

        return filter_model.replace("_", " ").title()

    @staticmethod
    def _stake_label(algo):
        stake_mode = str(
            getattr(algo, "stake_mode", "unknown")
        ).lower()
        base = ExperimentMetadataBuilder._number_text(
            getattr(algo, "base_wager", 0)
        )

        if stake_mode == "martingale":
            multiplier = ExperimentMetadataBuilder._number_text(
                getattr(algo, "multiplier", 0)
            )
            max_steps = int(getattr(algo, "max_steps", 0))
            return (
                f"Martingale Base {base}, "
                f"x{multiplier}, Max {max_steps}"
            )

        if stake_mode == "flat":
            return f"Flat Stake {base}"

        return stake_mode.replace("_", " ").title()

    @staticmethod
    def _tags(algo, start_year, end_year):
        tags = []

        def add(value):
            text = ExperimentMetadataBuilder._slug(value)
            if text and text not in tags:
                tags.append(text)

        coin = str(getattr(algo, "coin", "unknown")).lower()
        timeframe = str(getattr(algo, "timeframe", "unknown")).lower()
        entry_model = str(
            getattr(algo, "entry_model_name", "unknown")
        ).lower()
        filter_model = str(
            getattr(algo, "filter_model_name", "none")
        ).lower()
        stake_mode = str(
            getattr(algo, "stake_mode", "unknown")
        ).lower()

        add(coin)
        add(timeframe)

        for year in range(start_year, end_year + 1):
            add(str(year))

        add(entry_model)
        add(filter_model)
        add(stake_mode)
        add(str(getattr(algo, "lab_version", "unknown")))

        if entry_model == "fixed_bias":
            add(f"bias_{getattr(algo, 'bias', 'up')}")

        if entry_model == "candle_streak":
            add(f"streak_{int(getattr(algo, 'streak_length', 2))}")
            add(str(getattr(algo, "streak_mode", "follow")).lower())

        if filter_model == "ema_trend":
            add(f"ema_fast_{int(getattr(algo, 'ema_fast', 0))}")
            add(f"ema_slow_{int(getattr(algo, 'ema_slow', 0))}")

        if stake_mode == "martingale":
            add(
                "multiplier_"
                + ExperimentMetadataBuilder._number_text(
                    getattr(algo, "multiplier", 0)
                )
            )
            add(f"max_steps_{int(getattr(algo, 'max_steps', 0))}")

        return tags

    @staticmethod
    def _date_text(year, month, day):
        return (
            f"{int(year):04d}-"
            f"{int(month):02d}-"
            f"{int(day):02d}"
        )

    @staticmethod
    def _year_label(start_year, end_year):
        if start_year == end_year:
            return str(start_year)

        return f"{start_year}-{end_year}"

    @staticmethod
    def _slug(value):
        text = str(value).strip().lower()
        output = []
        previous_separator = False

        for ch in text:
            if ch.isalnum():
                output.append(ch)
                previous_separator = False
            else:
                if not previous_separator:
                    output.append("_")
                    previous_separator = True

        return "".join(output).strip("_")

    @staticmethod
    def _number_text(value):
        number = float(value)

        if number.is_integer():
            return str(int(number))

        return f"{number:g}"
