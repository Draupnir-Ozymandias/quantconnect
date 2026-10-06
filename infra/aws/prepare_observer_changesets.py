"""Administrative CloudShell preparation only: preview, never execute changes."""
import argparse
import json
from pathlib import Path
import subprocess
import time


def aws(region, *args):
    result = subprocess.run(["aws", "--region", region, *args, "--output", "json", "--no-cli-pager"],
                            check=True, capture_output=True, text=True)
    return json.loads(result.stdout) if result.stdout.strip() else {}


def budget_parameters(parameters, amount):
    if not any(p["ParameterKey"] == "MonthlyBudgetUsd" for p in parameters):
        raise ValueError("existing stack lacks expected budget parameter")
    return [{"ParameterKey": p["ParameterKey"], **({"ParameterValue": str(amount)}
            if p["ParameterKey"] == "MonthlyBudgetUsd" else {"UsePreviousValue": True})}
            for p in parameters]


def budget_only(changeset):
    changes = changeset.get("Changes", [])
    return bool(changes) and all(c["ResourceChange"]["LogicalResourceId"] == "MonthlyCostBudget"
        and c["ResourceChange"]["Action"] == "Modify"
        and c["ResourceChange"].get("Replacement") == "False" for c in changes)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--budget", type=int, default=75)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    import re
    if not re.fullmatch(r"[0-9a-f]{40}", args.commit) or not 25 <= args.budget <= 100:
        raise SystemExit("require full pushed commit and bounded initial budget")
    identity = aws("eu-west-1", "sts", "get-caller-identity")
    if identity["Account"] != "690971215658":
        raise SystemExit("wrong AWS account")
    original = aws("us-east-2", "cloudformation", "describe-stacks", "--stack-name", "qcrl-collector")["Stacks"][0]
    if original["StackStatus"] not in ("CREATE_COMPLETE", "UPDATE_COMPLETE"):
        raise SystemExit("primary stack is not idle/healthy")
    values = {p["ParameterKey"]: p.get("ParameterValue") for p in original["Parameters"]}
    key = " ".join(values["SshPublicKey"].split()[:2])
    from infra.stream.bootstrap_replica import validate_settings
    validate_settings("placeholder-bucket", "eu-west-1", "ireland", key, 48)
    if values["SshIngressCidr"] == "0.0.0.0/0":
        raise SystemExit("world-open operator ingress refused")
    template = Path(__file__).with_name("qcrl-observer-replica.json")
    aws("eu-west-1", "cloudformation", "validate-template", "--template-body", "file://" + str(template))
    stamp = str(int(time.time()))
    parameters = [{"ParameterKey": k, "ParameterValue": v} for k, v in
        {"RepositoryCommit": args.commit, "ObserverLabel": "ireland", "RuntimeHours": "48",
         "SshPublicKey": key, "SshIngressCidr": values["SshIngressCidr"]}.items()]
    replica = aws("eu-west-1", "cloudformation", "create-change-set", "--stack-name", "qcrl-ireland-observer",
        "--change-set-name", "qcrl-ireland-" + stamp, "--change-set-type", "CREATE",
        "--template-body", "file://" + str(template), "--capabilities", "CAPABILITY_IAM",
        "--parameters", json.dumps(parameters))
    budget = None
    if values["MonthlyBudgetUsd"] != str(args.budget):
        budget = aws("us-east-2", "cloudformation", "create-change-set", "--stack-name", "qcrl-collector",
            "--change-set-name", "qcrl-budget-" + stamp, "--change-set-type", "UPDATE",
            "--use-previous-template", "--capabilities", "CAPABILITY_IAM",
            "--parameters", json.dumps(budget_parameters(original["Parameters"], args.budget)))
    record = {"account": identity["Account"], "source_commit": args.commit,
              "replica": replica, "budget": budget, "budget_usd": args.budget,
              "runtime_hours": 48, "executed": False}
    with Path(args.output).open("x") as handle:
        json.dump(record, handle, indent=2)
    print(json.dumps(record, indent=2))
    print("PREPARED ONLY: inspect change sets and scoped IAM before executing.")


if __name__ == "__main__":
    main()
