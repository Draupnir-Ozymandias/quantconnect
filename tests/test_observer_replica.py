from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import unittest

from infra.stream.bootstrap_replica import validate_settings, stop_units
from infra.stream.install_replica import within_deadline
from infra.aws.prepare_observer_changesets import budget_parameters, budget_only


class ReplicaTests(unittest.TestCase):
    def test_budget_update_preserves_every_other_parameter_without_values(self):
        parameters = [{"ParameterKey":"MonthlyBudgetUsd","ParameterValue":"25"},
                      {"ParameterKey":"ProbeSecretArn","ParameterValue":"masked"},
                      {"ParameterKey":"RepositoryCommit","ParameterValue":"old"}]
        result = budget_parameters(parameters,75)
        self.assertEqual(result[0],{"ParameterKey":"MonthlyBudgetUsd","ParameterValue":"75"})
        self.assertTrue(all(p.get("UsePreviousValue") is True and "ParameterValue" not in p for p in result[1:]))

    def test_budget_only_guard_rejects_instance_and_replacement_changes(self):
        safe = {"Changes":[{"ResourceChange":{"LogicalResourceId":"MonthlyCostBudget","Action":"Modify","Replacement":"False"}}]}
        self.assertTrue(budget_only(safe))
        self.assertFalse(budget_only({"Changes":[]}))
        for name, replacement in (("CollectorInstance","False"),("MonthlyCostBudget","True")):
            self.assertFalse(budget_only({"Changes":[{"ResourceChange":{"LogicalResourceId":name,"Action":"Modify","Replacement":replacement}}]}))
    def test_replica_settings_fail_closed(self):
        validate_settings("example-bucket", "eu-west-1", "ireland", "ssh-ed25519 ABC123=", 48)
        cases = [("bad/", "eu-west-1", "ireland", "", 48),
                 ("example-bucket", "amsterdam", "ireland", "", 48),
                 ("example-bucket", "eu-west-1", "bad label", "", 48),
                 ("example-bucket", "eu-west-1", "ireland", "PRIVATE KEY", 48),
                 ("example-bucket", "eu-west-1", "ireland", "ssh-ed25519 ABC\ncommand", 48),
                 ("example-bucket", "eu-west-1", "ireland", "", 0)]
        for args in cases:
            with self.assertRaises(ValueError): validate_settings(*args)

    def test_absolute_stop_survives_reboot_and_stops_not_terminates(self):
        deadline = datetime(2026, 10, 8, 20, tzinfo=timezone.utc)
        service, timer = stop_units(deadline)
        self.assertIn("shutdown -h now", service)
        self.assertIn("OnCalendar=2026-10-08 20:00:00 UTC", timer)
        self.assertIn("Persistent=true", timer)

    def test_cohort_reserves_verification_before_stop(self):
        deadline = datetime(2026, 10, 8, 20, tzinfo=timezone.utc)
        metadata = {"stop_at_utc": deadline.isoformat()}
        within_deadline({"market_starts": [int(deadline.timestamp()) - 1200]}, metadata)
        with self.assertRaises(ValueError):
            within_deadline({"market_starts": [int(deadline.timestamp()) - 1000]}, metadata)

    def template(self):
        return json.loads((Path(__file__).resolve().parents[1] / "infra/aws/qcrl-observer-replica.json").read_text())

    def test_template_public_only_permissions_and_namespace(self):
        template = self.template()
        self.assertNotIn("ProbeSecretArn", template["Parameters"])
        policies = template["Resources"]["Role"]["Properties"]["Policies"]
        text = json.dumps(policies)
        self.assertNotIn("secretsmanager", text)
        self.assertNotIn("s3:DeleteObject", text)
        self.assertIn("runtime/streams/*", text)
        self.assertIn("cloudformation:SignalResource", text)
        bootstrap = template["Resources"]["ObserverInstance"]["Properties"]["UserData"]["Fn::Base64"]["Fn::Sub"]
        self.assertNotIn("/opt/qcrl ", bootstrap)
        self.assertNotIn("systemctl start qcrl-stream", bootstrap)

    def test_template_cost_and_security_bounds(self):
        template = self.template()
        instance = template["Resources"]["ObserverInstance"]["Properties"]
        self.assertEqual(instance["InstanceInitiatedShutdownBehavior"], "stop")
        self.assertEqual(instance["MetadataOptions"]["HttpTokens"], "required")
        self.assertTrue(instance["BlockDeviceMappings"][0]["Ebs"]["Encrypted"])
        self.assertEqual(template["Parameters"]["RuntimeHours"]["Default"], 48)
        self.assertEqual(template["Resources"]["ArtifactBucket"]["DeletionPolicy"], "Retain")
        self.assertNotIn("NATGateway", json.dumps(template))
        self.assertIn("NoWorldOpenSsh", template["Rules"])


if __name__ == "__main__":
    unittest.main()
