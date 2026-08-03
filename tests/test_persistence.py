"""SQLite persistence: schema, store durability, and ledger aggregation.

The point of the storage swap is that state outlives the process, so most of
these tests work by throwing the store away and building a new one over the same
database file — which is what a backend restart looks like from the data's side.
"""

from __future__ import annotations

import os
import sqlite3
import tempfile
import unittest

from backend import db, ledger, reservations
from backend.agents import gate
from backend.agents.levers import RUNG3_ASSUMED_VALUE_INR
from backend.agents.memory import InterventionMemoryStore
from backend.schemas import DeliveryDecisionRequest, SuppressedLever


class TempDatabaseCase(unittest.TestCase):
    """Gives each test a real file-backed database in a temp directory.

    A file rather than `:memory:` because these tests are specifically about
    surviving a reconnect, and every `:memory:` connection is a fresh blank
    database.
    """

    def setUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self._dir.name, "test.db")
        self.addCleanup(self._dir.cleanup)

    def connect(self) -> sqlite3.Connection:
        connection = db.get_db(self.db_path)
        self.addCleanup(connection.close)
        return connection


class SchemaTests(TempDatabaseCase):
    def test_all_tables_are_created(self):
        connection = self.connect()
        names = {
            row["name"]
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
        }
        self.assertLessEqual(
            {"sessions", "gate_state", "intervention_events", "decisions", "reservations"},
            names,
        )

    def test_init_schema_is_idempotent(self):
        connection = self.connect()
        db.init_schema(connection)
        db.init_schema(connection)  # must not raise on an already-populated db

    def test_reservations_has_the_phase_f_columns(self):
        connection = self.connect()
        columns = {
            row["name"] for row in connection.execute("PRAGMA table_info(reservations)")
        }
        self.assertEqual(
            columns,
            {
                "id",
                "product_id",
                "session_id",
                "quantity",
                "reserved_at",
                "expires_at",
                "released_at",
            },
        )

    def test_action_check_constraint_rejects_unknown_actions(self):
        connection = self.connect()
        with self.assertRaises(sqlite3.IntegrityError):
            with connection:
                connection.execute(
                    "INSERT INTO intervention_events "
                    "(session_id, lever_id, action, source, created_at) "
                    "VALUES ('s1', 'free_delivery_waiver', 'exploded', 'ranked', 1.0)"
                )


class GateStatePersistenceTests(TempDatabaseCase):
    def test_state_survives_a_new_store_over_the_same_database(self):
        first = gate.GateStore(db_path=self.db_path)
        first.record_run("s1", "sig-a", at=1000.0)
        first.record_run("s1", "sig-b", at=2000.0)

        # What a backend restart looks like: same file, brand new store object.
        restarted = gate.GateStore(db_path=self.db_path)
        state = restarted.get("s1")
        self.assertEqual(state.analyses_run, 2)
        self.assertEqual(state.last_signature, "sig-b")
        self.assertEqual(state.last_run_at, 2000.0)

    def test_cooldown_still_suppresses_after_a_restart(self):
        gate.GateStore(db_path=self.db_path).record_run("s1", "sig-a", at=1000.0)

        restarted = gate.GateStore(db_path=self.db_path)
        result = gate.evaluate(0.95, 400, "sig-a", "s1", restarted, now=1010.0)
        self.assertFalse(result.fired, "cooldown must outlive the process that set it")
        self.assertIn("unchanged", result.reason)

    def test_unknown_session_reads_as_empty(self):
        state = gate.GateStore(db_path=self.db_path).get("never-seen")
        self.assertEqual(state.analyses_run, 0)
        self.assertIsNone(state.last_signature)

    def test_reset_clears_one_session_only(self):
        store = gate.GateStore(db_path=self.db_path)
        store.record_run("s1", "sig-a")
        store.record_run("s2", "sig-a")
        store.reset("s1")
        self.assertEqual(store.get("s1").analyses_run, 0)
        self.assertEqual(store.get("s2").analyses_run, 1)


class InterventionMemoryPersistenceTests(TempDatabaseCase):
    def test_events_survive_a_new_store(self):
        first = InterventionMemoryStore(db_path=self.db_path)
        first.record("s1", "free_delivery_waiver", "shown")
        first.record("s1", "free_delivery_waiver", "shown")
        first.record("s1", "targeted_discount_code", "dismissed")

        restarted = InterventionMemoryStore(db_path=self.db_path)
        session = restarted.get("s1")
        self.assertEqual(session.shown_count("free_delivery_waiver"), 2)
        self.assertTrue(session.was_dismissed("targeted_discount_code"))

    def test_delivered_render_rows_do_not_inflate_shown_count(self):
        """The repetition penalty must count ranking exposure only.

        `build_intervention_plan` records "shown" for all three top-ranked
        levers; the delivery layer separately records the one lever it actually
        rendered. Both land in `intervention_events`, and conflating them would
        silently change every score.
        """
        store = InterventionMemoryStore(db_path=self.db_path)
        store.record("s1", "price_drop_alert", "shown")

        ledger.record_decision(
            self.connect(),
            DeliveryDecisionRequest(
                session_id="s1",
                outcome="delivered",
                lever_id="price_drop_alert",
                intensity_rung=1,
                surface="inline",
            ),
        )

        self.assertEqual(store.get("s1").shown_count("price_drop_alert"), 1)

    def test_sessions_stay_isolated_in_the_database(self):
        store = InterventionMemoryStore(db_path=self.db_path)
        store.record("s1", "free_delivery_waiver", "dismissed")
        self.assertTrue(store.get("s1").was_dismissed("free_delivery_waiver"))
        self.assertFalse(store.get("s2").was_dismissed("free_delivery_waiver"))


class SessionLedgerTests(TempDatabaseCase):
    def test_empty_session_returns_a_zeroed_ledger(self):
        result = ledger.build_session_ledger(self.connect(), "nobody")
        self.assertEqual(result.shownByRung, [0, 0, 0, 0])
        self.assertEqual(result.spendAvoidedInr, 0)
        self.assertEqual(result.held, [])

    def test_held_decisions_are_counted_by_reason(self):
        connection = self.connect()
        for reason in ("gate_held", "gate_held", "fatigue_cap"):
            ledger.record_decision(
                connection,
                DeliveryDecisionRequest(
                    session_id="s1", outcome="held", reason=reason, detail="because"
                ),
            )

        result = ledger.build_session_ledger(connection, "s1")
        self.assertEqual(result.heldByReason, {"gate_held": 2, "fatigue_cap": 1})
        self.assertEqual(len(result.held), 3)

    def test_spend_avoided_multiplies_count_by_assumed_unit_value(self):
        connection = self.connect()
        for _ in range(3):
            ledger.record_decision(
                connection,
                DeliveryDecisionRequest(
                    session_id="s1",
                    outcome="held",
                    reason="margin_approval_required",
                    suppressed=[
                        SuppressedLever(
                            lever_id="targeted_discount_code", reason="margin_approval_required"
                        ),
                        SuppressedLever(
                            lever_id="free_delivery_waiver", reason="margin_approval_required"
                        ),
                    ],
                ),
            )

        result = ledger.build_session_ledger(connection, "s1")
        expected = 3 * (
            RUNG3_ASSUMED_VALUE_INR["targeted_discount_code"]
            + RUNG3_ASSUMED_VALUE_INR["free_delivery_waiver"]
        )
        self.assertEqual(result.spendAvoidedInr, expected)
        self.assertEqual(result.spendAvoidedByLever["targeted_discount_code"].count, 3)
        self.assertEqual(len(result.suppressedRung3), 6)

    def test_shown_by_rung_tracks_the_delivered_intensity(self):
        connection = self.connect()
        for rung, lever in ((0, "trust_badge_reassurance"), (1, "price_drop_alert"), (1, "saved_payment_prompt")):
            ledger.record_decision(
                connection,
                DeliveryDecisionRequest(
                    session_id="s1", outcome="delivered", lever_id=lever, intensity_rung=rung
                ),
            )
        result = ledger.build_session_ledger(connection, "s1")
        self.assertEqual(result.shownByRung, [1, 2, 0, 0])

    def test_ignored_is_delivered_minus_answered(self):
        connection = self.connect()
        store = InterventionMemoryStore(db_path=self.db_path)
        for lever in ("price_drop_alert", "trust_badge_reassurance", "emi_plan_highlight"):
            ledger.record_decision(
                connection,
                DeliveryDecisionRequest(
                    session_id="s1", outcome="delivered", lever_id=lever, intensity_rung=1
                ),
            )
        store.record("s1", "price_drop_alert", "accepted")
        store.record("s1", "trust_badge_reassurance", "dismissed")

        result = ledger.build_session_ledger(connection, "s1")
        self.assertEqual(result.outcomes.accepted, 1)
        self.assertEqual(result.outcomes.dismissed, 1)
        self.assertEqual(result.outcomes.ignored, 1, "the unanswered exposure is the ignored one")

    def test_feedback_without_a_render_never_drives_ignored_negative(self):
        connection = self.connect()
        # The companion widget has its own accept path and can report an outcome
        # for a lever the delivery layer never recorded a render for.
        InterventionMemoryStore(db_path=self.db_path).record("s1", "checkout_assist_chat", "accepted")
        result = ledger.build_session_ledger(connection, "s1")
        self.assertEqual(result.outcomes.ignored, 0)

    def test_intervene_decisions_are_not_counted_as_held(self):
        connection = self.connect()
        ledger.record_decision(
            connection,
            DeliveryDecisionRequest(
                session_id="s1", outcome="delivered", lever_id="price_drop_alert", intensity_rung=1
            ),
        )
        result = ledger.build_session_ledger(connection, "s1")
        self.assertEqual(result.held, [])
        self.assertEqual(result.heldByReason, {})

    def test_timestamps_are_milliseconds(self):
        connection = self.connect()
        ledger.record_decision(
            connection,
            DeliveryDecisionRequest(session_id="s1", outcome="held", reason="cooldown"),
            at=1_700_000_000.5,
        )
        self.assertEqual(ledger.build_session_ledger(connection, "s1").held[0].at, 1_700_000_000_500)

    def test_ledger_survives_a_reconnect(self):
        first = self.connect()
        ledger.record_decision(
            first,
            DeliveryDecisionRequest(
                session_id="s1",
                outcome="held",
                reason="low_confidence",
                suppressed=[
                    SuppressedLever(lever_id="targeted_discount_code", reason="confidence_gate")
                ],
            ),
        )
        first.close()

        reopened = self.connect()
        result = ledger.build_session_ledger(reopened, "s1")
        self.assertEqual(result.heldByReason, {"low_confidence": 1})
        self.assertEqual(
            result.spendAvoidedInr, RUNG3_ASSUMED_VALUE_INR["targeted_discount_code"]
        )


class SilenceRateTests(TempDatabaseCase):
    def test_no_decisions_reads_as_zero(self):
        """Not a division by zero, and not "perfectly restrained" either."""
        result = ledger.build_session_ledger(self.connect(), "nobody")
        self.assertEqual(result.silenceRate, 0.0)

    def test_mixed_run_divides_holds_by_all_decisions(self):
        connection = self.connect()
        for reason in ("gate_held", "fatigue_cap"):
            ledger.record_decision(
                connection,
                DeliveryDecisionRequest(session_id="s1", outcome="held", reason=reason),
            )
        ledger.record_decision(
            connection,
            DeliveryDecisionRequest(
                session_id="s1", outcome="delivered", lever_id="price_drop_alert", intensity_rung=1
            ),
        )
        self.assertEqual(ledger.build_session_ledger(connection, "s1").silenceRate, 0.6667)

    def test_all_holds_is_total_silence(self):
        connection = self.connect()
        ledger.record_decision(
            connection, DeliveryDecisionRequest(session_id="s1", outcome="held", reason="cooldown")
        )
        self.assertEqual(ledger.build_session_ledger(connection, "s1").silenceRate, 1.0)

    def test_another_session_does_not_count(self):
        connection = self.connect()
        ledger.record_decision(
            connection, DeliveryDecisionRequest(session_id="s1", outcome="held", reason="cooldown")
        )
        ledger.record_decision(
            connection,
            DeliveryDecisionRequest(
                session_id="s2", outcome="delivered", lever_id="price_drop_alert", intensity_rung=1
            ),
        )
        self.assertEqual(ledger.build_session_ledger(connection, "s1").silenceRate, 1.0)


class CriticRejectionTests(TempDatabaseCase):
    def test_rejection_never_counts_as_something_the_shopper_saw(self):
        connection = self.connect()
        ledger.record_critic_rejection(
            connection,
            session_id="s1",
            lever_id="targeted_discount_code",
            reason="addresses cost, diagnosed cause is product uncertainty",
            root_cause="product_uncertainty",
        )
        result = ledger.build_session_ledger(connection, "s1")
        self.assertEqual(result.shownByRung, [0, 0, 0, 0])
        self.assertEqual(result.outcomes.ignored, 0)

    def test_rejection_does_not_inflate_spend_avoided(self):
        """Rung-3 policy suppressions are the ₹ total; alignment failures are not.

        The client's live copy of the ledger never sees a critic rejection, so
        counting one here would make the panel's total jump on rehydration.
        """
        connection = self.connect()
        ledger.record_critic_rejection(
            connection,
            session_id="s1",
            lever_id="targeted_discount_code",
            reason="misaligned",
        )
        result = ledger.build_session_ledger(connection, "s1")
        self.assertEqual(result.spendAvoidedInr, 0)
        self.assertEqual(result.suppressedRung3, [])

    def test_rejection_is_invisible_to_the_repetition_penalty(self):
        store = InterventionMemoryStore(db_path=self.db_path)
        ledger.record_critic_rejection(
            self.connect(), session_id="s1", lever_id="price_drop_alert", reason="misaligned"
        )
        session = store.get("s1")
        self.assertEqual(session.shown_count("price_drop_alert"), 0)
        self.assertFalse(session.was_dismissed("price_drop_alert"))

    def test_rung3_suppressions_still_total_alongside_rejections(self):
        connection = self.connect()
        ledger.record_decision(
            connection,
            DeliveryDecisionRequest(
                session_id="s1",
                outcome="held",
                reason="margin_approval_required",
                suppressed=[
                    SuppressedLever(lever_id="free_delivery_waiver", reason="margin_approval_required")
                ],
            ),
        )
        ledger.record_critic_rejection(
            connection, session_id="s1", lever_id="targeted_discount_code", reason="misaligned"
        )
        result = ledger.build_session_ledger(connection, "s1")
        self.assertEqual(result.spendAvoidedInr, RUNG3_ASSUMED_VALUE_INR["free_delivery_waiver"])
        self.assertEqual(len(result.suppressedRung3), 1)


class ExplanationVerdictPersistenceTests(TempDatabaseCase):
    def test_explanation_verdict_round_trips_through_annotate(self):
        store = InterventionMemoryStore(db_path=self.db_path)
        store.record("s1", "review_summary_surface", "shown")
        connection = self.connect()
        ledger.annotate_latest_event(
            connection,
            session_id="s1",
            lever_id="review_summary_surface",
            action="shown",
            explanation_verdict="regenerated",
        )
        row = connection.execute(
            "SELECT explanation_verdict FROM intervention_events "
            "WHERE session_id = 's1' AND lever_id = 'review_summary_surface' "
            "ORDER BY id DESC LIMIT 1"
        ).fetchone()
        self.assertEqual(row["explanation_verdict"], "regenerated")

    def test_setting_only_explanation_verdict_does_not_touch_other_columns(self):
        store = InterventionMemoryStore(db_path=self.db_path)
        store.record("s1", "review_summary_surface", "shown")
        connection = self.connect()
        ledger.annotate_latest_event(
            connection,
            session_id="s1",
            lever_id="review_summary_surface",
            action="shown",
            root_cause="product_uncertainty",
        )
        ledger.annotate_latest_event(
            connection,
            session_id="s1",
            lever_id="review_summary_surface",
            action="shown",
            explanation_verdict="template_fallback",
        )
        row = connection.execute(
            "SELECT root_cause, explanation_verdict FROM intervention_events "
            "WHERE session_id = 's1' AND lever_id = 'review_summary_surface' "
            "ORDER BY id DESC LIMIT 1"
        ).fetchone()
        self.assertEqual(row["root_cause"], "product_uncertainty")
        self.assertEqual(row["explanation_verdict"], "template_fallback")

    def test_annotate_is_a_noop_when_every_optional_param_is_none(self):
        store = InterventionMemoryStore(db_path=self.db_path)
        store.record("s1", "review_summary_surface", "shown")
        connection = self.connect()
        before = connection.execute(
            "SELECT id FROM intervention_events WHERE session_id = 's1' ORDER BY id DESC LIMIT 1"
        ).fetchone()["id"]
        ledger.annotate_latest_event(
            connection, session_id="s1", lever_id="review_summary_surface", action="shown"
        )
        row = connection.execute(
            "SELECT explanation_verdict FROM intervention_events WHERE id = ?", (before,)
        ).fetchone()
        self.assertIsNone(row["explanation_verdict"])


class ReservationTests(TempDatabaseCase):
    def test_a_hold_is_counted_until_it_expires(self):
        connection = self.connect()
        reservations.reserve(connection, "s1", "p-1001", at=1000.0)
        self.assertEqual(reservations.active_count(connection, "p-1001", now=1100.0), 1)
        # Read-time expiry: nothing swept the row, it simply stops counting.
        just_after = 1000.0 + reservations.HOLD_SECONDS + 1
        self.assertEqual(reservations.active_count(connection, "p-1001", now=just_after), 0)

    def test_expiry_is_ten_minutes_out(self):
        connection = self.connect()
        reservations.reserve(connection, "s1", "p-1001", at=1000.0)
        row = connection.execute("SELECT reserved_at, expires_at FROM reservations").fetchone()
        self.assertEqual(row["expires_at"] - row["reserved_at"], 600.0)

    def test_the_same_session_never_stacks_holds(self):
        """The gate allows 10 analyses a session; one shopper is still one unit."""
        connection = self.connect()
        self.assertTrue(reservations.reserve(connection, "s1", "p-1001", at=1000.0))
        self.assertFalse(reservations.reserve(connection, "s1", "p-1001", at=1030.0))
        self.assertEqual(reservations.active_count(connection, "p-1001", now=1100.0), 1)

    def test_a_lapsed_hold_can_be_taken_again(self):
        connection = self.connect()
        reservations.reserve(connection, "s1", "p-1001", at=1000.0)
        later = 1000.0 + reservations.HOLD_SECONDS + 1
        self.assertTrue(reservations.reserve(connection, "s1", "p-1001", at=later))

    def test_different_sessions_each_hold_a_unit(self):
        connection = self.connect()
        reservations.reserve(connection, "s1", "p-1001", at=1000.0)
        reservations.reserve(connection, "s2", "p-1001", at=1000.0)
        self.assertEqual(reservations.active_count(connection, "p-1001", now=1100.0), 2)

    def test_release_drops_only_this_session_and_product(self):
        connection = self.connect()
        reservations.reserve(connection, "s1", "p-1001", at=1000.0)
        reservations.reserve(connection, "s2", "p-1001", at=1000.0)
        reservations.reserve(connection, "s1", "p-2002", at=1000.0)

        self.assertEqual(reservations.release(connection, "s1", "p-1001", at=1050.0), 1)
        self.assertEqual(reservations.active_count(connection, "p-1001", now=1100.0), 1)
        self.assertEqual(reservations.active_count(connection, "p-2002", now=1100.0), 1)

    def test_releasing_twice_is_harmless(self):
        connection = self.connect()
        reservations.reserve(connection, "s1", "p-1001", at=1000.0)
        reservations.release(connection, "s1", "p-1001", at=1050.0)
        self.assertEqual(reservations.release(connection, "s1", "p-1001", at=1060.0), 0)

    def test_release_without_a_hold_reports_nothing_released(self):
        self.assertEqual(reservations.release(self.connect(), "s1", "never-held"), 0)

    def test_holds_survive_a_reconnect(self):
        first = self.connect()
        reservations.reserve(first, "s1", "p-1001", at=1000.0)
        first.close()
        self.assertEqual(reservations.active_count(self.connect(), "p-1001", now=1100.0), 1)


class RungValueParityTests(unittest.TestCase):
    def test_assumed_values_match_the_client_constant(self):
        """Pinned against `RUNG3_ASSUMED_VALUE_INR` in interventionPolicy.ts.

        The two copies exist because the panel renders live from the client's
        and rehydrates from the server's; if they drift, the ledger's ₹ total
        changes when you reload the page.
        """
        self.assertEqual(
            RUNG3_ASSUMED_VALUE_INR,
            {
                "targeted_discount_code": 200,
                "free_delivery_waiver": 40,
                "delivery_speed_upgrade": 60,
            },
        )


if __name__ == "__main__":
    unittest.main()
