-- Ad-hoc analytics query: supplier scorecard ranked by on-time delivery,
-- the query a demand planning analyst would run directly against the
-- warehouse before a quarterly supplier review.
select
    supplier_id, supplier_name, region_of_origin, reliability_score,
    purchase_orders,
    round(late_rate * 100, 1) as late_rate_pct,
    round(avg_actual_lead_time_days, 1) as avg_actual_lead_time_days,
    round(avg_fill_rate * 100, 1) as avg_fill_rate_pct,
    case
        when late_rate >= 0.30 then 'Critical'
        when late_rate >= 0.20 then 'Watch'
        else 'Healthy'
    end as delivery_status
from gold.supplier_performance
order by late_rate desc;
