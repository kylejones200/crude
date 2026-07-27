//! Shared planning horizon helpers.

use chrono::NaiveDate;

pub fn days_in_month(start_year: u32, start_month: u32, month_index: usize) -> u32 {
    let month = start_month + month_index as u32;
    let year = start_year + (month - 1) / 12;
    let month = ((month - 1) % 12) + 1;
    NaiveDate::from_ymd_opt(year as i32, month, 1)
        .map(|d| {
            if month == 12 {
                NaiveDate::from_ymd_opt(year as i32 + 1, 1, 1)
                    .unwrap()
                    .signed_duration_since(d)
                    .num_days() as u32
            } else {
                NaiveDate::from_ymd_opt(year as i32, month + 1, 1)
                    .unwrap()
                    .signed_duration_since(d)
                    .num_days() as u32
            }
        })
        .unwrap_or(30)
}

pub fn lead_time_for_source(source: &str, foreign_m: u32, canada_m: u32, domestic_m: u32) -> u32 {
    let s = source.to_lowercase();
    if s.contains("foreign") || s.contains("import") {
        foreign_m
    } else if s.contains("canada") {
        canada_m
    } else {
        domestic_m
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn january_2025_has_31_days() {
        assert_eq!(days_in_month(2025, 1, 0), 31);
    }
}
