# Source Documentation

## Overview

LA Agenda Alerts monitors three public government agenda sources for changes.

## Monitored Sources

### 1. LA City Council (city_council)

- **Primary URL:** https://lacity.gov/government/city-council
- **Cadence:** Weekly agendas published typically on Tuesdays and Fridays
- **Content:** Main City Council meeting agendas, council file system
- **Change Types Monitored:**
  - New agenda items added
  - Items removed
  - Meeting time changes
  - Attachment additions/changes

### 2. PLUM Committee (plum_committee)

- **Primary URL:** https://lacity.gov/government/city-council/committees/planning-and-land-use-management-plum
- **Cadence:** Weekly, typically on Tuesdays
- **Content:** Planning and Land Use Management Committee agenda
- **Change Types Monitored:**
  - New agenda items
  - Item removals
  - Attachment updates

### 3. LA County Board of Supervisors (county_bos)

- **Primary URL:** https://bos.lacounty.gov/
- **Cadence:** Weekly on Tuesdays
- **Content:** LA County Board of Supervisors agenda
- **Change Types Monitored:**
  - New agenda items
  - Meeting schedule changes
  - Attachment updates

## Monitoring Strategy

1. **Fetch Frequency:** 3x daily (08:00, 13:00, 18:00)
2. **Snapshot Storage:** HTML and linked PDFs stored in `data/raw/`
3. **Deduplication:** SHA256 hashes for PDFs, content fingerprinting for HTML
4. **Retention:** Raw data retained for 30 days, logs retained for 90 days

## Reliability Considerations

- All sources are public government websites with high availability
- No authentication required
- Stable URL structures (monitored for changes)
- Rate limiting implemented (respectful crawling)
