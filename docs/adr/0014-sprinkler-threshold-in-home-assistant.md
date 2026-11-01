# 0014. The sprinkler decision threshold lives in Home Assistant

- Status: Accepted
- Date: 2026-11-01
- Commits: none (configuration in Home Assistant; recorded here because it determines how the detector's output is used)

## Context
The detector publishes every Cat and Person detection with confidence above its own `confidence_threshold` (0.5 in production). Home Assistant decides what to do with it (ADR 0001). Its automations ("Katzenschreck" for the sprinklers, the push notification and the 4K clip) only acted on confidence >= 0.75.

On 30.10.2026 a cat entered the frame at 09:33:08. The first detections had 0.65, 0.70 and 0.53 and were ignored by Home Assistant. The sprinkler sequence only started at 09:33:11.8, after a detection reached 0.75. Home Assistant itself switched the first sprinkler 0.2 s after the trigger, so the delay came from the threshold, not from processing.

## Decision
- The detector keeps a low threshold (0.5) and reports everything above it. It does not decide whether to spray.
- Home Assistant applies the decision threshold. It was lowered from 0.75 to 0.55 on 01.11.2026 in all automations reacting to `object_detection/Cat` (sprinklers, push, 4K clip, the disabled mail/clip automation), so they fire on the same detections.
- Other guards stay in Home Assistant: 2 min lockout, no sprinkler if a person was detected in the last 60 s, abort when a person is detected during the sequence.

## Consequences
- On 30.10.2026 the sprinklers would have started about 3–4 s earlier.
- More false positives (birds, shadows, leaves) are possible; this has to be observed and the threshold raised again if needed.
- The threshold can be tuned without rebuilding or redeploying the detector. The detector's `confidence_threshold` has to stay below the Home Assistant threshold, otherwise detections never reach it.
- The two thresholds are easy to confuse: `confidence_threshold` in `config.txt` is a filter, not the decision to spray.
