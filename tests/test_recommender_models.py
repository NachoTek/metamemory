"""Tests for MODEL_SPECS covering all 5 model sizes."""

import pytest

from meetandread.hardware.recommender import MODEL_SPECS, ModelInfo, get_model_info, get_all_model_info


class TestModelSpecsCompleteness:
    """Verify MODEL_SPECS contains exactly the expected 5 model sizes."""

    EXPECTED_SIZES = {"tiny", "base", "small", "medium", "large"}

    def test_model_specs_has_five_entries(self):
        """MODEL_SPECS should contain exactly 5 model entries."""
        assert set(MODEL_SPECS.keys()) == self.EXPECTED_SIZES
        assert len(MODEL_SPECS) == 5

    def test_all_entries_are_model_info(self):
        """Every value in MODEL_SPECS should be a ModelInfo instance."""
        for key, info in MODEL_SPECS.items():
            assert isinstance(info, ModelInfo), f"{key} is not a ModelInfo"
            assert info.size == key


class TestMediumLargeSpecs:
    """Verify medium and large model specifications."""

    def test_medium_specs(self):
        """Medium model should have expected RAM, description, accuracy, latency."""
        medium = MODEL_SPECS["medium"]
        assert medium.ram_required_gb == 2.0
        assert medium.accuracy_rating == "High"
        assert medium.latency_profile == "Slow"
        assert "Medium" in medium.description
        assert "high accuracy" in medium.description.lower()

    def test_large_specs(self):
        """Large model should have expected RAM, description, accuracy, latency."""
        large = MODEL_SPECS["large"]
        assert large.ram_required_gb == 3.0
        assert large.accuracy_rating == "Best"
        assert large.latency_profile == "Slowest"
        assert "Large" in large.description
        assert "best accuracy" in large.description.lower()

    def test_medium_heavier_than_small(self):
        """Medium should require more RAM than small."""
        assert MODEL_SPECS["medium"].ram_required_gb > MODEL_SPECS["small"].ram_required_gb

    def test_large_heaviest(self):
        """Large should require the most RAM of all models."""
        max_ram = max(m.ram_required_gb for m in MODEL_SPECS.values())
        assert MODEL_SPECS["large"].ram_required_gb == max_ram


class TestGetModelInfo:
    """Test get_model_info() for all sizes and error case."""

    def test_get_model_info_medium(self):
        """get_model_info('medium') returns the correct ModelInfo."""
        info = get_model_info("medium")
        assert isinstance(info, ModelInfo)
        assert info.size == "medium"
        assert info.ram_required_gb == 2.0

    def test_get_model_info_large(self):
        """get_model_info('large') returns the correct ModelInfo."""
        info = get_model_info("large")
        assert isinstance(info, ModelInfo)
        assert info.size == "large"
        assert info.ram_required_gb == 3.0

    def test_get_model_info_all_sizes(self):
        """get_model_info works for every size in MODEL_SPECS."""
        for size in MODEL_SPECS:
            info = get_model_info(size)
            assert info.size == size

    def test_get_model_info_unknown_raises(self):
        """get_model_info raises ValueError for unknown model size."""
        with pytest.raises(ValueError, match="Unknown model size"):
            get_model_info("gigantic")

    def test_get_model_info_empty_raises(self):
        """get_model_info raises ValueError for empty string."""
        with pytest.raises(ValueError, match="Unknown model size"):
            get_model_info("")


class TestGetAllModelInfo:
    """Test get_all_model_info() returns all 5 models."""

    def test_get_all_model_info_count(self):
        """get_all_model_info() returns 5 ModelInfo objects."""
        all_info = get_all_model_info()
        assert len(all_info) == 5
        sizes = {info.size for info in all_info}
        assert sizes == {"tiny", "base", "small", "medium", "large"}
