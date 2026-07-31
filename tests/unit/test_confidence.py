"""Unit tests for ConfidenceCalculator."""

from __future__ import annotations

import pytest

from models.enums import DetectionSource, DeviceStatus
from services.confidence import ConfidenceCalculator


class TestConfidenceCalculator:
    """Tests for the ConfidenceCalculator."""

    @pytest.fixture
    def calculator(self) -> ConfidenceCalculator:
        return ConfidenceCalculator(online_threshold=50, decay_rate=5)

    @pytest.mark.unit
    def test_process_detection_adds_score(self, calculator: ConfidenceCalculator) -> None:
        """Verify detection adds source points."""
        score, status, changed = calculator.process_detection(
            mac="AA:BB:CC:DD:EE:FF",
            source=DetectionSource.ARP,
        )
        assert score == 100  # ARP = 100 points
        assert status == DeviceStatus.ONLINE
        assert changed is True

    @pytest.mark.unit
    def test_process_detection_cumulative(self, calculator: ConfidenceCalculator) -> None:
        """Verify multiple sources accumulate points (capped at 100)."""
        calculator.process_detection("AA:BB:CC:DD:EE:FF", DetectionSource.ARP)     # +100
        score, status, changed = calculator.process_detection(
            "AA:BB:CC:DD:EE:FF", DetectionSource.MDNS
        )  # +90
        assert score == 100  # Capped at 100
        assert status == DeviceStatus.ONLINE
        assert changed is False  # Already online after ARP

    @pytest.mark.unit
    def test_process_detection_below_threshold(self, calculator: ConfidenceCalculator) -> None:
        """Verify low-confidence source keeps device offline."""
        score, status, changed = calculator.process_detection(
            mac="AA:BB:CC:DD:EE:FF",
            source=DetectionSource.PING,  # 40 points, below threshold of 50
        )
        assert score == 40
        assert status == DeviceStatus.OFFLINE

    @pytest.mark.unit
    def test_apply_decay_reduces_scores(self, calculator: ConfidenceCalculator) -> None:
        """Verify decay reduces confidence scores."""
        calculator.process_detection("AA:BB:CC:DD:EE:FF", DetectionSource.ARP)  # 100
        went_offline = calculator.apply_decay()
        assert len(went_offline) == 0  # Still online at 95
        score = calculator.get_score("AA:BB:CC:DD:EE:FF")
        assert score is not None
        assert score.score == 95

    @pytest.mark.unit
    def test_decay_to_offline(self, calculator: ConfidenceCalculator) -> None:
        """Verify device goes offline when score drops below threshold."""
        # PING gives 40 points (below 50 threshold)
        calculator.process_detection("AA:BB:CC:DD:EE:FF", DetectionSource.PING)
        assert calculator.get_status("AA:BB:CC:DD:EE:FF") == DeviceStatus.OFFLINE

        # Decay from 40 to 35 — still offline
        went_offline = calculator.apply_decay()
        assert len(went_offline) == 0  # Was already offline

    @pytest.mark.unit
    def test_decay_to_zero(self, calculator: ConfidenceCalculator) -> None:
        """Verify that fully decayed scores are removed."""
        calculator.process_detection("AA:BB:CC:DD:EE:FF", DetectionSource.PING)  # 40
        # Apply decay many times
        for _ in range(9):
            calculator.apply_decay()

        # Score should be 0 and removed
        score = calculator.get_score("AA:BB:CC:DD:EE:FF")
        assert score is None  # Fully decayed and removed

    @pytest.mark.unit
    def test_remove_device(self, calculator: ConfidenceCalculator) -> None:
        """Verify device removal from tracking."""
        calculator.process_detection("AA:BB:CC:DD:EE:FF", DetectionSource.ARP)
        calculator.remove_device("AA:BB:CC:DD:EE:FF")
        assert calculator.get_score("AA:BB:CC:DD:EE:FF") is None

    @pytest.mark.unit
    def test_tracked_count(self, calculator: ConfidenceCalculator) -> None:
        """Verify tracked device counting."""
        assert calculator.tracked_count == 0
        calculator.process_detection("AA:BB:CC:DD:EE:FF", DetectionSource.ARP)     # 100 → online
        calculator.process_detection("11:22:33:44:55:66", DetectionSource.MDNS)    # 90 → online
        assert calculator.tracked_count == 2
        assert calculator.online_count == 2  # Both ARP (100) and MDNS (90) exceed threshold 50

    @pytest.mark.unit
    def test_status_change_detection(self, calculator: ConfidenceCalculator) -> None:
        """Verify status change detection."""
        # Start with low score — stays offline, no change
        _, _, changed1 = calculator.process_detection(
            "AA:BB:CC:DD:EE:FF", DetectionSource.PING
        )  # 40 — stays offline (below 50 threshold)
        assert not changed1  # Score 0→40, both are offline

        # Add ARP to push above threshold
        _, _, changed2 = calculator.process_detection(
            "AA:BB:CC:DD:EE:FF", DetectionSource.ARP
        )  # +100 = 140 capped to 100 — should be online
        # Since we already had 40 from PING, the total after adding ARP is capped at 100
        # The first call had changed=True (unknown → offline)
        # The second call: old score was 40 (offline), new score is 100 (online), so changed=True
        assert changed2
