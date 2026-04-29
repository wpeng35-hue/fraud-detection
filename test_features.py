import pandas as pd
import pytest

from features import build_model_frame


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_transactions(**overrides):
    row = {
        "transaction_id": 1,
        "account_id": 100,
        "amount_usd": 200.0,
        "failed_logins_24h": 0,
    }
    row.update(overrides)
    return pd.DataFrame([row])


def _make_accounts(**overrides):
    row = {
        "account_id": 100,
        "prior_chargebacks": 0,
    }
    row.update(overrides)
    return pd.DataFrame([row])


# ---------------------------------------------------------------------------
# Join behaviour
# ---------------------------------------------------------------------------

class TestJoin:
    def test_account_columns_merged(self):
        txns = _make_transactions()
        accts = _make_accounts(prior_chargebacks=2)
        df = build_model_frame(txns, accts)
        assert df["prior_chargebacks"].iloc[0] == 2

    def test_unmatched_transaction_kept_with_null_account(self):
        txns = _make_transactions(account_id=999)
        accts = _make_accounts(account_id=100)
        df = build_model_frame(txns, accts)
        assert len(df) == 1
        assert pd.isna(df["prior_chargebacks"].iloc[0])

    def test_multiple_transactions_same_account(self):
        txns = pd.DataFrame([
            {"transaction_id": 1, "account_id": 100, "amount_usd": 50.0, "failed_logins_24h": 0},
            {"transaction_id": 2, "account_id": 100, "amount_usd": 200.0, "failed_logins_24h": 1},
        ])
        accts = _make_accounts()
        df = build_model_frame(txns, accts)
        assert len(df) == 2
        assert (df["account_id"] == 100).all()

    def test_each_transaction_gets_its_own_account(self):
        txns = pd.DataFrame([
            {"transaction_id": 1, "account_id": 100, "amount_usd": 50.0, "failed_logins_24h": 0},
            {"transaction_id": 2, "account_id": 200, "amount_usd": 50.0, "failed_logins_24h": 0},
        ])
        accts = pd.DataFrame([
            {"account_id": 100, "prior_chargebacks": 0},
            {"account_id": 200, "prior_chargebacks": 3},
        ])
        df = build_model_frame(txns, accts)
        df = df.set_index("transaction_id")
        assert df.loc[1, "prior_chargebacks"] == 0
        assert df.loc[2, "prior_chargebacks"] == 3


# ---------------------------------------------------------------------------
# is_large_amount feature
# ---------------------------------------------------------------------------

class TestIsLargeAmount:
    def test_below_threshold_is_zero(self):
        df = build_model_frame(_make_transactions(amount_usd=999.99), _make_accounts())
        assert df["is_large_amount"].iloc[0] == 0

    def test_at_threshold_is_one(self):
        df = build_model_frame(_make_transactions(amount_usd=1000.0), _make_accounts())
        assert df["is_large_amount"].iloc[0] == 1

    def test_above_threshold_is_one(self):
        df = build_model_frame(_make_transactions(amount_usd=5000.0), _make_accounts())
        assert df["is_large_amount"].iloc[0] == 1

    def test_zero_amount_is_zero(self):
        df = build_model_frame(_make_transactions(amount_usd=0.0), _make_accounts())
        assert df["is_large_amount"].iloc[0] == 0

    def test_column_is_integer_dtype(self):
        df = build_model_frame(_make_transactions(), _make_accounts())
        assert df["is_large_amount"].dtype in (int, "int32", "int64")


# ---------------------------------------------------------------------------
# login_pressure feature
# ---------------------------------------------------------------------------

class TestLoginPressure:
    @pytest.mark.parametrize("logins,expected", [
        (0, "none"),
        (1, "low"),
        (2, "low"),
        (3, "high"),
        (5, "high"),
        (100, "high"),
    ])
    def test_login_pressure_category(self, logins, expected):
        df = build_model_frame(
            _make_transactions(failed_logins_24h=logins),
            _make_accounts(),
        )
        assert str(df["login_pressure"].iloc[0]) == expected

    def test_login_pressure_is_categorical(self):
        df = build_model_frame(_make_transactions(), _make_accounts())
        assert hasattr(df["login_pressure"], "cat")

    def test_login_pressure_categories_are_ordered(self):
        df = build_model_frame(_make_transactions(), _make_accounts())
        cats = list(df["login_pressure"].cat.categories)
        assert cats == ["none", "low", "high"]


# ---------------------------------------------------------------------------
# Output schema
# ---------------------------------------------------------------------------

class TestOutputSchema:
    def test_required_columns_present(self):
        df = build_model_frame(_make_transactions(), _make_accounts())
        for col in ("transaction_id", "account_id", "amount_usd",
                    "failed_logins_24h", "is_large_amount", "login_pressure"):
            assert col in df.columns, f"missing column: {col}"

    def test_row_count_matches_transactions(self):
        txns = pd.DataFrame([
            {"transaction_id": i, "account_id": 100, "amount_usd": 50.0, "failed_logins_24h": 0}
            for i in range(5)
        ])
        df = build_model_frame(txns, _make_accounts())
        assert len(df) == 5
