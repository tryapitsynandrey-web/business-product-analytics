from __future__ import annotations

import pandas as pd

from adapters.synthetic_data_generator import SyntheticDataGenerator


EXPECTED_DATASETS = {
    "customers",
    "subscriptions",
    "transactions",
    "product_usage",
    "support_tickets",
    "nps_scores",
    "acquisition_channels",
    "targets",
}


def test_generate_all_writes_expected_files_and_relationships(tmp_path):
    generator = SyntheticDataGenerator(
        seed=7,
        num_customers=12,
        as_of_date="2026-05-01",
        output_dir=tmp_path,
    )

    datasets = generator.generate_all()

    assert set(datasets) == EXPECTED_DATASETS
    assert {path.stem for path in tmp_path.glob("*.csv")} == EXPECTED_DATASETS
    assert len(datasets["customers"]) == 12
    assert len(datasets["subscriptions"]) == 12

    customer_ids = set(datasets["customers"]["customer_id"])
    subscription_ids = set(datasets["subscriptions"]["subscription_id"])
    assert set(datasets["subscriptions"]["customer_id"]).issubset(customer_ids)
    assert set(datasets["transactions"]["customer_id"]).issubset(customer_ids)
    assert set(datasets["transactions"]["subscription_id"]).issubset(subscription_ids)
    assert set(datasets["product_usage"]["customer_id"]).issubset(customer_ids)
    assert datasets["targets"]["date"].nunique() == 1


def test_generator_is_deterministic_for_same_seed_and_as_of_date(tmp_path):
    first = SyntheticDataGenerator(
        seed=99,
        num_customers=10,
        as_of_date="2026-05-01",
        output_dir=tmp_path / "first",
    ).generate_all()
    second = SyntheticDataGenerator(
        seed=99,
        num_customers=10,
        as_of_date="2026-05-01",
        output_dir=tmp_path / "second",
    ).generate_all()

    for name in EXPECTED_DATASETS:
        pd.testing.assert_frame_equal(first[name], second[name])


def test_generator_uses_default_as_of_date_when_none(tmp_path):
    generator = SyntheticDataGenerator(seed=1, num_customers=1, output_dir=tmp_path)

    assert generator.end_date == pd.Timestamp("2026-05-01")


def test_individual_generator_methods_preserve_foreign_key_relationships(tmp_path):
    generator = SyntheticDataGenerator(
        seed=13,
        num_customers=30,
        as_of_date="2026-05-01",
        output_dir=tmp_path,
    )

    customers = generator.generate_customers()
    subscriptions = generator.generate_subscriptions(customers)
    transactions = generator.generate_transactions(subscriptions)
    product_usage = generator.generate_product_usage(customers)
    support_tickets = generator.generate_support_tickets(customers)
    nps_scores = generator.generate_nps_scores(customers)
    acquisition_channels = generator.generate_acquisition_channels()
    targets = generator.generate_targets()

    customer_ids = set(customers["customer_id"])
    subscription_ids = set(subscriptions["subscription_id"])
    assert customers["customer_id"].is_unique
    assert subscriptions["subscription_id"].is_unique
    assert transactions["transaction_id"].is_unique
    assert set(subscriptions["customer_id"]).issubset(customer_ids)
    assert set(transactions["customer_id"]).issubset(customer_ids)
    assert set(transactions["subscription_id"]).issubset(subscription_ids)
    assert set(product_usage["customer_id"]).issubset(customer_ids)
    if not support_tickets.empty:
        assert set(support_tickets["customer_id"]).issubset(customer_ids)
    if not nps_scores.empty:
        assert set(nps_scores["customer_id"]).issubset(customer_ids)
        assert nps_scores["score"].between(0, 10).all()
    assert set(acquisition_channels["channel_name"]) == set(generator.channels)
    assert targets["metric_name"].tolist() == ["MRR", "Churn Rate", "Activation Rate", "NPS"]
