# ProductPulse - Metric Definitions

Generated: 2026-05-08

This document is the authoritative metric glossary for the ProductPulse analytics engine.
All formulas are implemented deterministically in Python; this document describes the
governance contract each metric must satisfy.

---

## Monthly Recurring Revenue (MRR)

- **ID:** `monthly_recurring_revenue`
- **Category:** revenue
- **Owner:** Finance
- **Grain:** overall
- **Formula:** Sum of monthly_price for all subscriptions whose status is Active or Past Due.
- **Purpose:** Tracks the predictable monthly revenue base. Primary leading indicator of business health and growth trajectory.
- **Interpretation:** Includes Past Due subscriptions because the revenue is owed even if not yet collected. Excludes Canceled and Expired.
- **Risk if misread:** Including canceled subscriptions inflates MRR and masks revenue loss.
- **Null policy:** drop_row
- **Enabled:** True

---

## Average Revenue Per User (ARPU)

- **ID:** `average_revenue_per_user`
- **Category:** revenue
- **Owner:** Finance
- **Grain:** overall
- **Formula:** MRR divided by the count of unique customers with Active or Past Due subscriptions.
- **Purpose:** Measures revenue efficiency per customer. Used to evaluate pricing strategy and segment-level monetisation.
- **Interpretation:** Use alongside segment breakdowns to avoid averages masking tier differences.
- **Risk if misread:** Using total customers (including inactive) as denominator deflates ARPU.
- **Null policy:** drop_row
- **Enabled:** True

---

## Expansion Revenue

- **ID:** `expansion_revenue`
- **Category:** revenue
- **Owner:** Finance
- **Grain:** overall
- **Formula:** Sum of monthly_price for subscriptions whose plan is Premium or Enterprise and status is Active.
- **Purpose:** Quantifies revenue generated from upsells and plan upgrades. A growing expansion revenue signals successful product-led growth.
- **Interpretation:** Proxy measure using high-tier plans. A proper expansion metric requires prior-period plan comparison, which is available in v2 cohort analysis.
- **Risk if misread:** Treating all premium-plan MRR as expansion overstates growth if these were original plan choices, not upgrades.
- **Null policy:** drop_row
- **Enabled:** True

---

## Contraction Revenue

- **ID:** `contraction_revenue`
- **Category:** revenue
- **Owner:** Finance
- **Grain:** overall
- **Formula:** Sum of monthly_price for subscriptions with status Past Due (revenue at risk of being lost due to billing failure).
- **Purpose:** Flags revenue that is contractually owed but not yet collected, signalling billing health risk.
- **Interpretation:** Treated as contraction proxy in v1. A downgrade-based contraction metric requires prior-period plan snapshots.
- **Risk if misread:** Ignoring this metric leads to MRR overstatement and delayed churn response.
- **Null policy:** drop_row
- **Enabled:** True

---

## Gross Revenue Retention (GRR)

- **ID:** `gross_revenue_retention`
- **Category:** revenue
- **Owner:** Finance
- **Grain:** overall
- **Formula:** Active MRR divided by total billed MRR (Active + Past Due + Canceled revenue). Bounded [0, 1].
- **Purpose:** Measures what percentage of possible revenue is actually being retained, ignoring expansion. Core SaaS health benchmark.
- **Interpretation:** GRR cannot exceed 1.0 (excludes expansion). A GRR below 0.85 is a warning signal for most SaaS businesses.
- **Risk if misread:** Confusing GRR with NRR leads to overestimating retention when expansion is masking underlying churn.
- **Null policy:** drop_row
- **Enabled:** True

---

## Net Revenue Retention (NRR)

- **ID:** `net_revenue_retention`
- **Category:** revenue
- **Owner:** Finance
- **Grain:** overall
- **Formula:** (Active MRR + Expansion MRR) divided by total billed MRR. Can exceed 1.0 if expansion outweighs churn.
- **Purpose:** The gold-standard SaaS retention metric. An NRR above 1.0 means the existing customer base is growing revenue without new acquisition.
- **Interpretation:** NRR > 1.0 indicates net-negative churn. Benchmark: elite SaaS targets >120%.
- **Risk if misread:** Using NRR without GRR hides whether growth comes from retention or expansion.
- **Null policy:** drop_row
- **Enabled:** True

---

## Revenue at Risk

- **ID:** `revenue_at_risk`
- **Category:** revenue
- **Owner:** Finance
- **Grain:** overall
- **Formula:** Sum of monthly_price for all subscriptions belonging to customers flagged as High or Critical churn risk.
- **Purpose:** Quantifies the dollar value exposed to churn so finance and CS can prioritise retention investment.
- **Interpretation:** Derived from churn risk scoring — requires churn engine to run first.
- **Risk if misread:** Underestimating at-risk revenue leads to under-resourcing customer success.
- **Null policy:** drop_row
- **Enabled:** True

---

## Activation Rate

- **ID:** `activation_rate`
- **Category:** product
- **Owner:** Product
- **Grain:** overall
- **Formula:** Count of customers with cumulative key_actions > activation_threshold divided by total customers. Activation threshold is 5 key actions.
- **Purpose:** Measures what proportion of signed-up customers completed the minimum set of actions indicating they derived initial value from the product.
- **Interpretation:** Activation is the first retention lever. Low activation predicts early churn within 30-90 days.
- **Risk if misread:** Using logins instead of key_actions conflates presence with engagement.
- **Null policy:** fill_zero
- **Enabled:** True

---

## Usage Frequency

- **ID:** `usage_frequency`
- **Category:** product
- **Owner:** Product
- **Grain:** overall
- **Formula:** Mean number of monthly logins per active customer across all usage records.
- **Purpose:** Tracks how frequently customers engage with the product. Declining frequency is an early churn signal.
- **Interpretation:** Segment by plan tier — Enterprise customers may have lower individual logins but higher team logins.
- **Risk if misread:** Averaging across all customers including inactive ones deflates frequency.
- **Null policy:** drop_row
- **Enabled:** True

---

## Key Action Rate

- **ID:** `key_action_rate`
- **Category:** product
- **Owner:** Product
- **Grain:** overall
- **Formula:** Total key_actions divided by total logins across all active customers. Measures depth of engagement per session.
- **Purpose:** Measures how productively customers use each session. Low key action rate indicates friction or lack of product discovery.
- **Interpretation:** Use alongside feature adoption to diagnose where in the product flow customers disengage.
- **Risk if misread:** High key_action totals for a single power-user segment can mask poor broader adoption.
- **Null policy:** fill_zero
- **Enabled:** True

---

## Engagement Drop Rate

- **ID:** `engagement_drop_rate`
- **Category:** product
- **Owner:** Product
- **Grain:** overall
- **Formula:** Proportion of active customers whose last-month logins are below 20% of their personal 3-month average, indicating a significant engagement drop.
- **Purpose:** Identifies customers in active decline before they reach the churned state. Key early-warning intervention trigger.
- **Interpretation:** Drop rate should be trended monthly. A spike in drop rate precedes churn spikes by 4-8 weeks.
- **Risk if misread:** Point-in-time measurement without trend context misses seasonal patterns.
- **Null policy:** drop_row
- **Enabled:** True

---

## Feature Adoption Proxy

- **ID:** `feature_adoption_proxy`
- **Category:** product
- **Owner:** Product
- **Grain:** overall
- **Formula:** Mean number of features_used per active customer per usage record.
- **Purpose:** Approximates how broadly customers explore the product feature set. Sticky customers tend to use more features.
- **Interpretation:** A proxy because features_used is a count, not specific feature names. v2 should track named feature adoption.
- **Risk if misread:** High features_used count does not guarantee adoption of high-value features.
- **Null policy:** fill_zero
- **Enabled:** True

---

## Customer Churn Rate

- **ID:** `customer_churn_rate`
- **Category:** customer
- **Owner:** Product
- **Grain:** overall
- **Formula:** Count of customers with Canceled subscriptions divided by total customers.
- **Purpose:** Primary retention health metric. Sustained churn above 3% monthly signals structural product or market fit issues.
- **Interpretation:** Period churn requires a start/end snapshot. This is a stock measure using current subscription states.
- **Risk if misread:** Using total customers including trials in denominator understates churn rate.
- **Null policy:** drop_row
- **Enabled:** True

---

## Retention Rate

- **ID:** `retention_rate`
- **Category:** customer
- **Owner:** Product
- **Grain:** overall
- **Formula:** 1 minus customer_churn_rate. Proportion of customers currently Active.
- **Purpose:** Complement of churn rate. Retention rate above 97% monthly is a strong SaaS health signal.
- **Interpretation:** Retention rate = 1 - churn rate. Tracked together they validate each other.
- **Risk if misread:** High headline retention can mask segment-level retention differences.
- **Null policy:** drop_row
- **Enabled:** True

---

## Average Net Promoter Score (NPS)

- **ID:** `average_nps`
- **Category:** customer
- **Owner:** Customer Success
- **Grain:** overall
- **Formula:** Mean of all NPS score values collected. Scores range 0-10.
- **Purpose:** Measures customer sentiment and likelihood to recommend. Strong leading indicator of organic growth and churn risk.
- **Interpretation:** Scores 0-6 are detractors, 7-8 passives, 9-10 promoters. True NPS = %promoters - %detractors. This metric reports mean score as a simpler signal.
- **Risk if misread:** Low response rate (under 30%) makes mean NPS unreliable as a population estimate.
- **Null policy:** drop_row
- **Enabled:** True

---

## Support Burden

- **ID:** `support_burden`
- **Category:** customer
- **Owner:** Customer Success
- **Grain:** overall
- **Formula:** Mean number of support tickets per active customer.
- **Purpose:** Measures how much operational support load the customer base generates. High support burden correlates with poor product experience and churn risk.
- **Interpretation:** Segment by plan — Enterprise customers will have higher ticket volumes by design due to contract scope.
- **Risk if misread:** Using raw ticket count without normalising by customer count biases toward larger customer bases.
- **Null policy:** fill_zero
- **Enabled:** True

---

## Time to Activation

- **ID:** `time_to_activation`
- **Category:** customer
- **Owner:** Product
- **Grain:** overall
- **Formula:** Mean number of days between signup_date and the date of the first recorded key_action > 0 in product_usage. Only calculated for activated customers.
- **Purpose:** Measures onboarding velocity. Shorter time to activation correlates with higher 90-day retention. A key lever for onboarding optimisation.
- **Interpretation:** Only consider customers who have activated. Non-activated customers are reported separately as activation rate denominator.
- **Risk if misread:** Including non-activated customers with no activation date skews the mean toward infinity or NaN.
- **Null policy:** drop_row
- **Enabled:** True

---

## Gross Profit

- **ID:** `gross_profit`
- **Category:** business_health_profitability
- **Owner:** Finance
- **Grain:** overall
- **Formula:** Revenue - Cost of Goods Sold
- **Purpose:** Measures profit after deducting direct production or delivery costs.
- **Interpretation:** Negative gross profit means COGS exceeds revenue.
- **Risk if misread:** Excluding indirect costs overstates gross profit.
- **Null policy:** error
- **Enabled:** True

---

## Gross Margin

- **ID:** `gross_margin`
- **Category:** business_health_profitability
- **Owner:** Finance
- **Grain:** overall
- **Formula:** Gross Profit / Revenue
- **Purpose:** Measures production/delivery efficiency as a decimal 0-1.
- **Interpretation:** SaaS gross margins typically range from 0.65 to 0.85.
- **Risk if misread:** Including non-COGS costs deflates gross margin.
- **Null policy:** error
- **Enabled:** True

---

## Operating Margin

- **ID:** `operating_margin`
- **Category:** business_health_profitability
- **Owner:** Finance
- **Grain:** overall
- **Formula:** Operating Profit / Revenue
- **Purpose:** Tracks core operational profitability before interest and taxes.
- **Interpretation:** Negative margin means operating costs exceed revenue.
- **Risk if misread:** Excluding one-time charges inflates margin.
- **Null policy:** error
- **Enabled:** True

---

## Net Margin

- **ID:** `net_margin`
- **Category:** business_health_profitability
- **Owner:** Finance
- **Grain:** overall
- **Formula:** Net Profit / Revenue
- **Purpose:** Bottom-line profitability after all expenses.
- **Interpretation:** The final measure of overall business profitability.
- **Risk if misread:** Excluding tax or interest expense overstates net margin.
- **Null policy:** error
- **Enabled:** True

---

## EBITDA

- **ID:** `ebitda`
- **Category:** business_health_profitability
- **Owner:** Finance
- **Grain:** overall
- **Formula:** Net Income + Interest + Taxes + Depreciation + Amortization
- **Purpose:** Approximates operational cash generation. Widely used for cross-company comparison and valuation multiples.
- **Interpretation:** Does not represent actual cash flow.
- **Risk if misread:** Treating EBITDA as free cash flow ignores capex and working capital.
- **Null policy:** error
- **Enabled:** True

---

## Return on Investment (ROI)

- **ID:** `roi`
- **Category:** business_health_profitability
- **Owner:** Finance
- **Grain:** overall
- **Formula:** (Gain - Cost) / Cost
- **Purpose:** Measures the profitability of an investment relative to its cost.
- **Interpretation:** Positive ROI means the investment generated profit.
- **Risk if misread:** Ignoring time horizon inflates ROI for long-duration investments.
- **Null policy:** error
- **Enabled:** True

---

## Annual Recurring Revenue (ARR)

- **ID:** `annual_recurring_revenue`
- **Category:** business_health_revenue
- **Owner:** Finance
- **Grain:** overall
- **Formula:** MRR x 12
- **Purpose:** Annualises the recurring revenue base for investor reporting.
- **Interpretation:** ARR assumes no growth or contraction over the year.
- **Risk if misread:** Using total revenue instead of MRR inflates ARR.
- **Null policy:** error
- **Enabled:** True

---

## Revenue Growth Rate

- **ID:** `revenue_growth_rate`
- **Category:** business_health_revenue
- **Owner:** Finance
- **Grain:** period-over-period
- **Formula:** (Current Revenue - Previous Revenue) / /Previous Revenue/
- **Purpose:** Measures the rate of revenue expansion or contraction between periods.
- **Interpretation:** Compare to industry benchmarks.
- **Risk if misread:** Comparing different period lengths distorts the rate.
- **Null policy:** error
- **Enabled:** True

---

## Revenue Concentration

- **ID:** `revenue_concentration`
- **Category:** business_health_revenue
- **Owner:** Finance
- **Grain:** overall
- **Formula:** Largest Customer Revenue / Total Revenue
- **Purpose:** Identifies dependency on individual customers. High concentration increases risk.
- **Interpretation:** >20% from a single customer is typically a risk flag.
- **Risk if misread:** Measuring by contract value rather than recognised revenue is misleading.
- **Null policy:** error
- **Enabled:** True

---

## Customer Lifetime Value (LTV)

- **ID:** `customer_lifetime_value`
- **Category:** business_health_unit_economics
- **Owner:** Finance
- **Grain:** overall
- **Formula:** (ARPU x Gross Margin) / Churn Rate
- **Purpose:** Estimates the total gross-margin-adjusted revenue expected from a customer.
- **Interpretation:** Returns 0.0 when churn_rate is zero.
- **Risk if misread:** Using total revenue instead of gross margin overstates LTV.
- **Null policy:** error
- **Enabled:** True

---

## Customer Acquisition Cost (CAC)

- **ID:** `customer_acquisition_cost`
- **Category:** business_health_unit_economics
- **Owner:** Finance
- **Grain:** overall
- **Formula:** (Marketing Spend + Sales Spend) / New Customers
- **Purpose:** Total sales and marketing investment to acquire one new customer.
- **Interpretation:** Pair with LTV:CAC ratio. A ratio < 3 signals a broken GTM.
- **Risk if misread:** Excluding any acquisition spend component understates CAC.
- **Null policy:** error
- **Enabled:** True

---

## LTV:CAC Ratio

- **ID:** `ltv_to_cac_ratio`
- **Category:** business_health_unit_economics
- **Owner:** Finance
- **Grain:** overall
- **Formula:** LTV / CAC
- **Purpose:** The primary unit economics health metric. A ratio >= 3.0 is the SaaS benchmark.
- **Interpretation:** Values < 1.0 mean the business is destroying value on acquisition.
- **Risk if misread:** A high ratio driven by very low CAC may indicate under-investment.
- **Null policy:** error
- **Enabled:** True

---

## Free Cash Flow (FCF)

- **ID:** `free_cash_flow`
- **Category:** business_health_cashflow
- **Owner:** Finance
- **Grain:** overall
- **Formula:** Operating Cash Flow - Capital Expenditures
- **Purpose:** Cash available after sustaining and expanding the asset base.
- **Interpretation:** Negative FCF is acceptable in high-growth phases.
- **Risk if misread:** Confusing FCF with net income ignores non-cash and capex items.
- **Null policy:** error
- **Enabled:** True

---

## Cash Runway (Months)

- **ID:** `runway_months`
- **Category:** business_health_cashflow
- **Owner:** Finance
- **Grain:** overall
- **Formula:** Cash Balance / Monthly Burn Rate
- **Purpose:** Months the business can operate before exhausting cash reserves.
- **Interpretation:** <6 months is critical; >18 months provides strategic flexibility.
- **Risk if misread:** Using gross burn instead of net burn overstates urgency.
- **Null policy:** error
- **Enabled:** True

---

## Customer Growth Rate

- **ID:** `customer_growth_rate`
- **Category:** business_health_growth
- **Owner:** Growth
- **Grain:** period-over-period
- **Formula:** (Current Customers - Previous Customers) / /Previous Customers/
- **Purpose:** Tracks the rate at which the customer base expands or contracts.
- **Interpretation:** Evaluate alongside revenue growth to detect downmarket drift.
- **Risk if misread:** Counting trials as customers inflates the rate.
- **Null policy:** error
- **Enabled:** True

---

## Growth Efficiency

- **ID:** `growth_efficiency`
- **Category:** business_health_growth
- **Owner:** Growth
- **Grain:** overall
- **Formula:** Revenue Growth / Sales and Marketing Spend
- **Purpose:** Revenue growth generated per dollar of S&M investment.
- **Interpretation:** Similar to the Magic Number. Track over rolling 12-month periods.
- **Risk if misread:** Including expansion revenue inflates the efficiency metric.
- **Null policy:** error
- **Enabled:** True

---

## Revenue Per Employee

- **ID:** `revenue_per_employee`
- **Category:** business_health_efficiency
- **Owner:** Operations
- **Grain:** overall
- **Formula:** Total Revenue / Employee Count
- **Purpose:** Primary operational productivity benchmark.
- **Interpretation:** SaaS benchmark is typically $150k-$300k+ per employee at scale.
- **Risk if misread:** Excluding contractors understates productivity.
- **Null policy:** error
- **Enabled:** True

---

## Sales Efficiency (Magic Number)

- **ID:** `sales_efficiency`
- **Category:** business_health_efficiency
- **Owner:** Operations
- **Grain:** overall
- **Formula:** New Revenue / Sales and Marketing Spend
- **Purpose:** Measures how effectively S&M spend converts to new revenue.
- **Interpretation:** Values > 1.0 suggest a profitable go-to-market motion.
- **Risk if misread:** Including renewal revenue in new revenue inflates the metric.
- **Null policy:** error
- **Enabled:** True

---

## Customer Concentration Risk

- **ID:** `customer_concentration_risk`
- **Category:** business_health_risk
- **Owner:** Finance
- **Grain:** overall
- **Formula:** Largest Customer Revenue / Total Revenue
- **Purpose:** Quantifies the revenue risk from over-reliance on a single customer.
- **Interpretation:** >20% is a common red-flag threshold.
- **Risk if misread:** Using ARR instead of recognised revenue misrepresents timing risk.
- **Null policy:** error
- **Enabled:** True

---

## Churn Exposure

- **ID:** `churn_exposure`
- **Category:** business_health_risk
- **Owner:** Customer Success
- **Grain:** overall
- **Formula:** Revenue At Risk / Total Revenue
- **Purpose:** Proportion of total revenue threatened by high-risk customers.
- **Interpretation:** >10% churn exposure warrants immediate CS intervention.
- **Risk if misread:** Using customer count instead of revenue understates high-value impact.
- **Null policy:** error
- **Enabled:** True

---

Report generated automatically by ProductPulse Analytics Engine.
