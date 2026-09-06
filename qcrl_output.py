"""Console presentation helpers for QCRL campaign reports."""


def print_directional_report(report, artifact_path, report_path):
    print("Directional cohort verdict:")
    for cohort in report["cohorts"]:
        print(
            f"  {cohort['rank']}. {cohort['group_key']} "
            f"score={cohort['final_score']:.2f} "
            f"classification={cohort['classification']} "
            f"decision={cohort['disposition']} "
            f"profitable={cohort['profitable_samples']}/"
            f"{cohort['run_count']} "
            f"weighted_win_rate={cohort['weighted_win_rate']:.2%} "
            f"total_profit={cohort['total_net_profit']:+g}"
        )
        if cohort["warnings"]:
            print("     warnings=" + ",".join(cohort["warnings"]))

    neighborhood = report.get("neighborhood_interpretation")
    if neighborhood:
        print(
            "Neighborhood selection: "
            f"{neighborhood['decision']} "
            f"value={neighborhood['selected_value']} "
            f"support={neighborhood['supporting_values']}"
        )

    single_gate = report.get("single_gate_interpretation")
    if single_gate:
        print("Single-gate control comparison:")
        for comparison in single_gate["comparisons"]:
            print(
                f"  {comparison['candidate_value']}: "
                f"decision={comparison['decision']} "
                f"profit_delta={comparison['total_net_profit_delta']:+g} "
                f"win_rate_delta="
                f"{comparison['weighted_win_rate_delta']:+.2%} "
                f"trade_retention="
                f"{comparison['total_trade_retention_ratio']:.2%} "
                f"improved_labels="
                f"{comparison['profit_improved_labels']}/"
                f"{comparison['paired_label_count']}"
            )

    attribution = report.get("gate_attribution_interpretation")
    if attribution:
        print("Gate attribution verdict:")
        print(
            f"  diagnostic={attribution['diagnostic_value']} "
            f"not_ready={attribution['diagnostic_not_ready_total']} "
            f"rejected={attribution['diagnostic_rejected_total']}"
        )
        for candidate in attribution["candidates"]:
            comparison = candidate["diagnostic_comparison"]
            print(
                f"  {candidate['candidate_value']}: "
                f"decision={candidate['decision']} "
                f"equivalent_to_diagnostic="
                f"{candidate['equivalent_to_diagnostic']} "
                f"rejected={candidate['rejected_signal_total']} "
                f"incremental_profit="
                f"{comparison['total_net_profit_delta']:+g} "
                f"incremental_win_rate="
                f"{comparison['weighted_win_rate_delta']:+.2%}"
            )

    side_attribution = report.get("side_attribution_interpretation")
    if side_attribution:
        print(
            "Directional-side attribution: "
            f"verdict={side_attribution['verdict']}"
        )
        for side in side_attribution["sides"]:
            print(
                f"  {side['direction']}: "
                f"decision={side['disposition']} "
                f"profit={side['total_net_profit']:+g} "
                f"win_rate={side['weighted_win_rate']:.2%} "
                f"trades={side['total_trades']:g} "
                f"profitable={side['profitable_samples']}/"
                f"{side['run_count']}"
            )

    print(f"Next action: {report['decision_summary']['next_action']}")
    print(f"Directional evidence: {artifact_path}")
    print(f"Directional report:   {report_path}")
