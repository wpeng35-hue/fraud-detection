import pandas as pd
import pytest

from analyze_fraud import score_transactions, summarize_results


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_scored(**overrides):
    """Single scored transaction row with sensible defaults."""
    row = {
        "transaction_id": 1,
        "account_id": 100,
        "amount_usd": 200.0,
        "device_risk_score": 10,
        "is_international": 0,
        "velocity_24h": 1,
        "failed_logins_24h": 0,
        "prior_chargebacks": 0,
        "risk_score": 0,
        "risk_label": "low",
    }
    row.update(overrides)
    return row


def _txns_df(rows):
    return pd.DataFrame(rows)


def _minimal_transactions():
    return pd.DataFrame([{
        "transaction_id": 1,
        "account_id": 100,
        "amount_usd": 200.0,
        "device_risk_score": 10,
        "is_international": 0,
        "velocity_24h": 1,
        "failed_logins_24h": 0,
    }])


def _minimal_accounts():
    return pd.DataFrame([{
        "account_id": 100,
        "prior_chargebacks": 0,
    }])


def _empty_chargebacks():
    return pd.DataFrame(columns=["transaction_id"])


# ---------------------------------------------------------------------------
# score_transactions — output schema and value ranges
# ---------------------------------------------------------------------------

class TestScoreTransactions:
    def test_risk_score_column_present(self):
        result = score_transactions(_minimal_transactions(), _minimal_accounts())
        assert "risk_score" in result.columns

    def test_risk_label_column_present(self):
        result = score_transactions(_minimal_transactions(), _minimal_accounts())
        assert "risk_label" in result.columns

    def test_risk_score_within_valid_range(self):
        txns = pd.DataFrame([
            {"transaction_id": i, "account_id": 100, "amount_usd": float(i * 100),
             "device_risk_score": i * 10 % 100, "is_international": i % 2,
             "velocity_24h": i % 8, "failed_logins_24h": i % 6}
            for i in range(1, 11)
        ])
        accts = pd.DataFrame([{"account_id": 100, "prior_chargebacks": 1}])
        result = score_transactions(txns, accts)
        assert result["risk_score"].between(0, 100).all()

    def test_risk_label_only_valid_values(self):
        result = score_transactions(_minimal_transactions(), _minimal_accounts())
        assert set(result["risk_label"]).issubset({"low", "medium", "high"})

    def test_row_count_preserved(self):
        txns = pd.DataFrame([
            {"transaction_id": i, "account_id": 100, "amount_usd": 50.0,
             "device_risk_score": 5, "is_international": 0,
             "velocity_24h": 1, "failed_logins_24h": 0}
            for i in range(5)
        ])
        accts = _minimal_accounts()
        result = score_transactions(txns, accts)
        assert len(result) == 5

    def test_high_risk_transaction_labelled_high(self):
        txns = pd.DataFrame([{
            "transaction_id": 1,
            "account_id": 100,
            "amount_usd": 1500.0,
            "device_risk_score": 85,
            "is_international": 1,
            "velocity_24h": 8,
            "failed_logins_24h": 6,
        }])
        accts = pd.DataFrame([{"account_id": 100, "prior_chargebacks": 2}])
        result = score_transactions(txns, accts)
        assert result["risk_label"].iloc[0] == "high"

    def test_low_risk_transaction_labelled_low(self):
        txns = pd.DataFrame([{
            "transaction_id": 1,
            "account_id": 100,
            "amount_usd": 10.0,
            "device_risk_score": 5,
            "is_international": 0,
            "velocity_24h": 1,
            "failed_logins_24h": 0,
        }])
        accts = pd.DataFrame([{"account_id": 100, "prior_chargebacks": 0}])
        result = score_transactions(txns, accts)
        assert result["risk_label"].iloc[0] == "low"


# ---------------------------------------------------------------------------
# summarize_results — aggregation correctness
# ---------------------------------------------------------------------------

class TestSummarizeResults:
    def test_transaction_count_per_label(self):
        scored = _txns_df([
            _make_scored(transaction_id=1, amount_usd=100.0, risk_label="low"),
            _make_scored(transaction_id=2, amount_usd=200.0, risk_label="low"),
            _make_scored(transaction_id=3, amount_usd=300.0, risk_label="high"),
        ])
        summary = summarize_results(scored, _empty_chargebacks())
        counts = summary.set_index("risk_label")["transactions"]
        assert counts["low"] == 2
        assert counts["high"] == 1

    def test_total_amount_per_label(self):
        scored = _txns_df([
            _make_scored(transaction_id=1, amount_usd=100.0, risk_label="low"),
            _make_scored(transaction_id=2, amount_usd=200.0, risk_label="low"),
            _make_scored(transaction_id=3, amount_usd=500.0, risk_label="high"),
        ])
        summary = summarize_results(scored, _empty_chargebacks())
        totals = summary.set_index("risk_label")["total_amount_usd"]
        assert totals["low"] == pytest.approx(300.0)
        assert totals["high"] == pytest.approx(500.0)

    def test_avg_amount_per_label(self):
        scored = _txns_df([
            _make_scored(transaction_id=1, amount_usd=100.0, risk_label="low"),
            _make_scored(transaction_id=2, amount_usd=300.0, risk_label="low"),
        ])
        summary = summarize_results(scored, _empty_chargebacks())
        avg = summary.set_index("risk_label")["avg_amount_usd"]
        assert avg["low"] == pytest.approx(200.0)

    def test_chargeback_rate_zero_when_no_chargebacks(self):
        scored = _txns_df([
            _make_scored(transaction_id=1, risk_label="high"),
            _make_scored(transaction_id=2, risk_label="high"),
        ])
        summary = summarize_results(scored, _empty_chargebacks())
        rate = summary.set_index("risk_label")["chargeback_rate"]
        assert rate["high"] == pytest.approx(0.0)

    def test_chargeback_rate_all_fraud(self):
        scored = _txns_df([
            _make_scored(transaction_id=1, risk_label="high"),
            _make_scored(transaction_id=2, risk_label="high"),
        ])
        chargebacks = pd.DataFrame({"transaction_id": [1, 2]})
        summary = summarize_results(scored, chargebacks)
        rate = summary.set_index("risk_label")["chargeback_rate"]
        assert rate["high"] == pytest.approx(1.0)

    def test_chargeback_rate_partial(self):
        scored = _txns_df([
            _make_scored(transaction_id=1, risk_label="high"),
            _make_scored(transaction_id=2, risk_label="high"),
            _make_scored(transaction_id=3, risk_label="high"),
            _make_scored(transaction_id=4, risk_label="high"),
        ])
        chargebacks = pd.DataFrame({"transaction_id": [1, 2]})
        summary = summarize_results(scored, chargebacks)
        rate = summary.set_index("risk_label")["chargeback_rate"]
        assert rate["high"] == pytest.approx(0.5)

    def test_chargebacks_only_counted_in_matching_label(self):
        scored = _txns_df([
            _make_scored(transaction_id=1, risk_label="low"),
            _make_scored(transaction_id=2, risk_label="high"),
        ])
        # chargeback belongs to the "low" transaction
        chargebacks = pd.DataFrame({"transaction_id": [1]})
        summary = summarize_results(scored, chargebacks)
        by_label = summary.set_index("risk_label")
        assert by_label.loc["low", "chargeback_rate"] == pytest.approx(1.0)
        assert by_label.loc["high", "chargeback_rate"] == pytest.approx(0.0)

    def test_unknown_chargeback_transaction_id_ignored(self):
        scored = _txns_df([
            _make_scored(transaction_id=1, risk_label="low"),
        ])
        chargebacks = pd.DataFrame({"transaction_id": [9999]})
        summary = summarize_results(scored, chargebacks)
        rate = summary.set_index("risk_label")["chargeback_rate"]
        assert rate["low"] == pytest.approx(0.0)

    def test_output_columns_present(self):
        scored = _txns_df([_make_scored()])
        summary = summarize_results(scored, _empty_chargebacks())
        for col in ("risk_label", "transactions", "total_amount_usd",
                    "avg_amount_usd", "chargebacks", "chargeback_rate"):
            assert col in summary.columns, f"missing column: {col}"

    def test_output_sorted_by_risk_label(self):
        scored = _txns_df([
            _make_scored(transaction_id=1, risk_label="medium"),
            _make_scored(transaction_id=2, risk_label="low"),
            _make_scored(transaction_id=3, risk_label="high"),
        ])
        summary = summarize_results(scored, _empty_chargebacks())
        assert list(summary["risk_label"]) == sorted(summary["risk_label"].tolist())
