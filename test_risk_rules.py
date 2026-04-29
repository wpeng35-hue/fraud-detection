from risk_rules import label_risk, score_transaction


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _base_tx(**overrides):
    """Minimal low-risk transaction; override individual signals as needed."""
    tx = {
        "device_risk_score": 10,
        "is_international": 0,
        "amount_usd": 100,
        "velocity_24h": 1,
        "failed_logins_24h": 0,
        "prior_chargebacks": 0,
    }
    tx.update(overrides)
    return tx


# ---------------------------------------------------------------------------
# label_risk — boundary values
# ---------------------------------------------------------------------------

class TestLabelRisk:
    def test_low_below_threshold(self):
        assert label_risk(0) == "low"
        assert label_risk(29) == "low"

    def test_medium_at_lower_boundary(self):
        assert label_risk(30) == "medium"

    def test_medium_below_high_threshold(self):
        assert label_risk(59) == "medium"

    def test_high_at_lower_boundary(self):
        assert label_risk(60) == "high"

    def test_high_at_max(self):
        assert label_risk(100) == "high"


# ---------------------------------------------------------------------------
# score_transaction — each signal in isolation with exact expected values
# ---------------------------------------------------------------------------

class TestDeviceRiskSignal:
    def test_low_device_risk_adds_nothing(self):
        assert score_transaction(_base_tx(device_risk_score=39)) == 0

    def test_medium_device_risk_adds_10(self):
        assert score_transaction(_base_tx(device_risk_score=40)) == 10
        assert score_transaction(_base_tx(device_risk_score=69)) == 10

    def test_high_device_risk_adds_25(self):
        assert score_transaction(_base_tx(device_risk_score=70)) == 25
        assert score_transaction(_base_tx(device_risk_score=100)) == 25

    def test_boundary_at_40(self):
        assert score_transaction(_base_tx(device_risk_score=39)) == 0
        assert score_transaction(_base_tx(device_risk_score=40)) == 10

    def test_boundary_at_70(self):
        assert score_transaction(_base_tx(device_risk_score=69)) == 10
        assert score_transaction(_base_tx(device_risk_score=70)) == 25


class TestInternationalSignal:
    def test_domestic_adds_nothing(self):
        assert score_transaction(_base_tx(is_international=0)) == 0

    def test_international_adds_15(self):
        assert score_transaction(_base_tx(is_international=1)) == 15


class TestAmountSignal:
    def test_small_amount_adds_nothing(self):
        assert score_transaction(_base_tx(amount_usd=499)) == 0

    def test_medium_amount_adds_10(self):
        assert score_transaction(_base_tx(amount_usd=500)) == 10
        assert score_transaction(_base_tx(amount_usd=999)) == 10

    def test_large_amount_adds_25(self):
        assert score_transaction(_base_tx(amount_usd=1000)) == 25
        assert score_transaction(_base_tx(amount_usd=5000)) == 25

    def test_boundary_at_500(self):
        assert score_transaction(_base_tx(amount_usd=499)) == 0
        assert score_transaction(_base_tx(amount_usd=500)) == 10

    def test_boundary_at_1000(self):
        assert score_transaction(_base_tx(amount_usd=999)) == 10
        assert score_transaction(_base_tx(amount_usd=1000)) == 25


class TestVelocitySignal:
    def test_low_velocity_adds_nothing(self):
        assert score_transaction(_base_tx(velocity_24h=2)) == 0

    def test_medium_velocity_adds_5(self):
        assert score_transaction(_base_tx(velocity_24h=3)) == 5
        assert score_transaction(_base_tx(velocity_24h=5)) == 5

    def test_high_velocity_adds_20(self):
        assert score_transaction(_base_tx(velocity_24h=6)) == 20
        assert score_transaction(_base_tx(velocity_24h=20)) == 20

    def test_boundary_at_3(self):
        assert score_transaction(_base_tx(velocity_24h=2)) == 0
        assert score_transaction(_base_tx(velocity_24h=3)) == 5

    def test_boundary_at_6(self):
        assert score_transaction(_base_tx(velocity_24h=5)) == 5
        assert score_transaction(_base_tx(velocity_24h=6)) == 20


class TestFailedLoginsSignal:
    def test_no_failures_adds_nothing(self):
        assert score_transaction(_base_tx(failed_logins_24h=1)) == 0

    def test_some_failures_adds_10(self):
        assert score_transaction(_base_tx(failed_logins_24h=2)) == 10
        assert score_transaction(_base_tx(failed_logins_24h=4)) == 10

    def test_many_failures_adds_20(self):
        assert score_transaction(_base_tx(failed_logins_24h=5)) == 20
        assert score_transaction(_base_tx(failed_logins_24h=10)) == 20

    def test_boundary_at_2(self):
        assert score_transaction(_base_tx(failed_logins_24h=1)) == 0
        assert score_transaction(_base_tx(failed_logins_24h=2)) == 10

    def test_boundary_at_5(self):
        assert score_transaction(_base_tx(failed_logins_24h=4)) == 10
        assert score_transaction(_base_tx(failed_logins_24h=5)) == 20


class TestPriorChargebacksSignal:
    def test_no_chargebacks_adds_nothing(self):
        assert score_transaction(_base_tx(prior_chargebacks=0)) == 0

    def test_one_chargeback_adds_5(self):
        assert score_transaction(_base_tx(prior_chargebacks=1)) == 5

    def test_multiple_chargebacks_adds_20(self):
        assert score_transaction(_base_tx(prior_chargebacks=2)) == 20
        assert score_transaction(_base_tx(prior_chargebacks=5)) == 20

    def test_boundary_at_1(self):
        assert score_transaction(_base_tx(prior_chargebacks=0)) == 0
        assert score_transaction(_base_tx(prior_chargebacks=1)) == 5

    def test_boundary_at_2(self):
        assert score_transaction(_base_tx(prior_chargebacks=1)) == 5
        assert score_transaction(_base_tx(prior_chargebacks=2)) == 20


# ---------------------------------------------------------------------------
# score_transaction — score clamping
# ---------------------------------------------------------------------------

class TestScoreClamping:
    def test_score_cannot_exceed_100(self):
        # All signals at max: 25+15+25+20+20+20 = 125 → clamped to 100
        tx = _base_tx(
            device_risk_score=100,
            is_international=1,
            amount_usd=5000,
            velocity_24h=10,
            failed_logins_24h=10,
            prior_chargebacks=5,
        )
        assert score_transaction(tx) == 100

    def test_score_cannot_go_below_0(self):
        # All signals absent, score starts at 0 and cannot be negative
        assert score_transaction(_base_tx()) == 0


# ---------------------------------------------------------------------------
# score_transaction — combined profiles
# ---------------------------------------------------------------------------

class TestCombinedProfiles:
    def test_all_low_risk_signals_scores_low(self):
        tx = _base_tx(
            device_risk_score=5,
            is_international=0,
            amount_usd=20,
            velocity_24h=1,
            failed_logins_24h=0,
            prior_chargebacks=0,
        )
        assert label_risk(score_transaction(tx)) == "low"

    def test_confirmed_chargeback_profile_scores_high(self):
        # Transaction 50003: confirmed $1,250 chargeback
        tx = _base_tx(
            device_risk_score=81,
            is_international=1,
            amount_usd=1250,
            velocity_24h=6,
            failed_logins_24h=5,
            prior_chargebacks=0,
        )
        assert label_risk(score_transaction(tx)) == "high"

    def test_additive_scoring_across_signals(self):
        # device medium (+10) + international (+15) + medium amount (+10) = 35
        tx = _base_tx(
            device_risk_score=50,
            is_international=1,
            amount_usd=750,
        )
        assert score_transaction(tx) == 35
        assert label_risk(35) == "medium"
