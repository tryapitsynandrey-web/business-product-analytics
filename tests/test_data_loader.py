from __future__ import annotations

import pandas as pd
import pytest

from adapters.data_loader import DataLoader


def _write_csv(path, rows):
    pd.DataFrame(rows).to_csv(path, index=False)


def test_load_all_reads_requested_datasets_and_parses_date_columns(tmp_path):
    data_dir = tmp_path / "synthetic"
    data_dir.mkdir()
    _write_csv(
        data_dir / "customers.csv",
        [
            {
                "customer_id": "C1",
                "signup_date": "2026-01-05",
                "segment": "SMB",
            }
        ],
    )
    _write_csv(
        data_dir / "transactions.csv",
        [
            {
                "transaction_id": "T1",
                "customer_id": "C1",
                "transaction_date": "not-a-date",
            }
        ],
    )

    datasets = DataLoader(data_dir=data_dir).load_all(["customers", "transactions"])

    assert set(datasets) == {"customers", "transactions"}
    assert pd.api.types.is_datetime64_any_dtype(datasets["customers"]["signup_date"])
    assert datasets["customers"].loc[0, "signup_date"] == pd.Timestamp("2026-01-05")
    assert pd.isna(datasets["transactions"].loc[0, "transaction_date"])


def test_load_all_raises_clear_error_for_missing_required_dataset(tmp_path):
    loader = DataLoader(data_dir=tmp_path)

    with pytest.raises(FileNotFoundError, match="Required dataset 'customers' not found"):
        loader.load_all(["customers"])


def test_load_all_uses_default_dataset_list_and_skips_missing_date_columns(tmp_path):
    data_dir = tmp_path / "synthetic"
    data_dir.mkdir()
    for name in [
        "customers",
        "subscriptions",
        "transactions",
        "product_usage",
        "support_tickets",
        "nps_scores",
        "acquisition_channels",
        "targets",
    ]:
        _write_csv(data_dir / f"{name}.csv", [{"id": f"{name}-1"}])

    datasets = DataLoader(data_dir=data_dir).load_all()

    assert set(datasets) == {
        "customers",
        "subscriptions",
        "transactions",
        "product_usage",
        "support_tickets",
        "nps_scores",
        "acquisition_channels",
        "targets",
    }
    assert datasets["customers"]["id"].iloc[0] == "customers-1"
