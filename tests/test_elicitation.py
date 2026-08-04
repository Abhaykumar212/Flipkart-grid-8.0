"""Unit tests for interactive elicitation flow (/api/elicitation-response) and ledger counts."""

from __future__ import annotations

import os
import sqlite3
import tempfile
import unittest

from backend import db, ledger
from backend.schemas import ElicitationResponseRequest, SessionLedgerResponse
from backend.main import elicitation_response


class ElicitationTests(unittest.TestCase):
    def setUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self._dir.name, "test.db")
        # Ensure thread connection uses our test db
        db._local.connection = db._connect(self.db_path)

    def tearDown(self) -> None:
        db.reset_thread_connection()
        try:
            self._dir.cleanup()
        except Exception:
            pass

    def test_elicitation_chip_mapping(self) -> None:
        chips_and_causes = [
            ("Price", "cost_friction"),
            ("Trust or quality", "trust_friction"),
            ("Still comparing", "product_uncertainty"),
        ]

        for index, (chip, expected_cause) in enumerate(chips_and_causes):
            session_id = f"test_sess_{index}"
            req = ElicitationResponseRequest(
                session_id=session_id,
                chip=chip,
                probability=0.85,
            )
            resp = elicitation_response(req)

            self.assertEqual(resp.status, "success")
            self.assertIsNotNone(resp.analysis)
            self.assertEqual(resp.analysis.primary_root_cause.category, expected_cause)
            self.assertIsNotNone(resp.intervention_plan)
            self.assertGreater(len(resp.intervention_plan.top_interventions), 0)

            # Check that top intervention matches the expected category
            top_lever = resp.intervention_plan.top_interventions[0]
            self.assertIsNotNone(top_lever.lever_id)
            self.assertTrue(top_lever.explanation is not None)

            # Check decision persistence in SQLite
            connection = db.get_db()
            row = connection.execute(
                "SELECT decision_type, root_cause FROM decisions WHERE session_id = ? ORDER BY id DESC LIMIT 1",
                (session_id,),
            ).fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row["decision_type"], "elicited")
            self.assertEqual(row["root_cause"], expected_cause)

    def test_session_ledger_asked_vs_inferred_counts(self) -> None:
        connection = db.get_db()
        session_id = "ledger_split_session"

        # Record 2 inferred decisions, 1 elicited decision, 1 do_nothing
        ledger.record_decision(
            connection,
            ledger.DeliveryDecisionRequest(
                session_id=session_id,
                outcome="delivered",
                lever_id="price_drop_alert",
                root_cause="cost_friction",
            ),
        )
        ledger.record_decision(
            connection,
            ledger.DeliveryDecisionRequest(
                session_id=session_id,
                outcome="delivered",
                lever_id="trust_badge_reassurance",
                root_cause="trust_friction",
            ),
        )
        ledger.record_decision(
            connection,
            ledger.DeliveryDecisionRequest(
                session_id=session_id,
                outcome="elicited",
                reason="user_elicited",
                lever_id="emi_plan_highlight",
                root_cause="cost_friction",
            ),
        )
        ledger.record_decision(
            connection,
            ledger.DeliveryDecisionRequest(
                session_id=session_id,
                outcome="held",
                reason="low_confidence",
            ),
        )

        ledger_resp: SessionLedgerResponse = ledger.build_session_ledger(connection, session_id)
        self.assertEqual(ledger_resp.inferred_count, 2)
        self.assertEqual(ledger_resp.elicitation_count, 1)
        self.assertEqual(len(ledger_resp.held), 1)


if __name__ == "__main__":
    unittest.main()
