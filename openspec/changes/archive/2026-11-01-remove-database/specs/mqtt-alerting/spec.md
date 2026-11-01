## ADDED Requirements

### Requirement: Alert before storage
The MQTT message SHALL be published before the detection image is saved, and saving SHALL NOT delay the publish. The timestamp SHALL be taken before detection runs.

#### Scenario: Slow disk
- **WHEN** saving the detection image is slow
- **THEN** the detection message is still published without waiting for it

## REMOVED Requirements

### Requirement: Alert has priority
**Reason**: Replaced by "Alert before storage", since there is no database write anymore.
**Migration**: None.
