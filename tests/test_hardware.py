"""Tests for hardware detection and model recommendation modules.

Covers: HardwareDetector, SystemSpecs, ModelRecommender, recommend_model_size
"""

import pytest
import sys
sys.path.insert(0, 'src')

from meetandread.hardware.detector import HardwareDetector, SystemSpecs
from meetandread.hardware.recommender import (
    ModelRecommender,
    ModelInfo,
    recommend_model_size,
    get_model_info,
    get_all_model_info,
    MODEL_SPECS,
)


class TestSystemSpecs:
    """Test SystemSpecs dataclass."""
    
    def test_create_specs(self):
        """Test creating SystemSpecs with all fields."""
        specs = SystemSpecs(
            total_ram_gb=16.0,
            available_ram_gb=8.0,
            cpu_count_logical=8,
            cpu_count_physical=4,
            cpu_freq_mhz=2400.0,
            is_64bit=True,
            platform='Windows'
        )
        assert specs.total_ram_gb == 16.0
        assert specs.available_ram_gb == 8.0
        assert specs.cpu_count_logical == 8
        assert specs.cpu_count_physical == 4
        assert specs.cpu_freq_mhz == 2400.0
        assert specs.is_64bit is True
        assert specs.platform == 'Windows'


class TestRecommendModelSize:
    """Test model size recommendation algorithm.
    
    After the dual-mode removal, recommend_model_size always returns 'tiny'
    for real-time transcription. Post-processing uses larger models via
    PostProcessingQueue.
    """
    
    def test_high_end_recommendation(self):
        """Test high-end hardware recommends 'tiny' for real-time."""
        specs = SystemSpecs(
            total_ram_gb=16, available_ram_gb=8,
            cpu_count_logical=8, cpu_count_physical=4,
            cpu_freq_mhz=2400, is_64bit=True, platform='Windows'
        )
        assert recommend_model_size(specs) == 'tiny'
    
    def test_exact_boundary_12gb_8cores(self):
        """Test 12GB RAM and 8 cores recommends 'tiny' for real-time."""
        specs = SystemSpecs(
            total_ram_gb=12, available_ram_gb=6,
            cpu_count_logical=8, cpu_count_physical=4,
            cpu_freq_mhz=2200, is_64bit=True, platform='Windows'
        )
        assert recommend_model_size(specs) == 'tiny'
    
    def test_mid_range_recommendation(self):
        """Test mid-range hardware (8GB, 6 cores) recommends 'tiny' for real-time."""
        specs = SystemSpecs(
            total_ram_gb=8, available_ram_gb=4,
            cpu_count_logical=6, cpu_count_physical=3,
            cpu_freq_mhz=2200, is_64bit=True, platform='Windows'
        )
        assert recommend_model_size(specs) == 'tiny'
    
    def test_low_ram_recommendation(self):
        """Test <6GB RAM recommends 'tiny'."""
        specs = SystemSpecs(
            total_ram_gb=4, available_ram_gb=2,
            cpu_count_logical=8, cpu_count_physical=4,  # Good CPU
            cpu_freq_mhz=2400, is_64bit=True, platform='Windows'
        )
        assert recommend_model_size(specs) == 'tiny'
    
    def test_low_cpu_recommendation(self):
        """Test <4 cores recommends 'tiny'."""
        specs = SystemSpecs(
            total_ram_gb=16, available_ram_gb=8,  # Good RAM
            cpu_count_logical=2, cpu_count_physical=2,
            cpu_freq_mhz=2400, is_64bit=True, platform='Windows'
        )
        assert recommend_model_size(specs) == 'tiny'
    
    def test_exact_boundary_6gb(self):
        """Test exact 6GB boundary recommends 'tiny' for real-time."""
        specs = SystemSpecs(
            total_ram_gb=6, available_ram_gb=3,
            cpu_count_logical=8, cpu_count_physical=4,
            cpu_freq_mhz=2400, is_64bit=True, platform='Windows'
        )
        assert recommend_model_size(specs) == 'tiny'
    
    def test_exact_boundary_4cores(self):
        """Test exact 4 cores boundary recommends 'tiny' for real-time."""
        specs = SystemSpecs(
            total_ram_gb=16, available_ram_gb=8,
            cpu_count_logical=4, cpu_count_physical=2,
            cpu_freq_mhz=2400, is_64bit=True, platform='Windows'
        )
        assert recommend_model_size(specs) == 'tiny'


class TestModelInfo:
    """Test ModelInfo dataclass and retrieval functions."""
    
    def test_get_model_info_tiny(self):
        """Test retrieving tiny model info."""
        info = get_model_info('tiny')
        assert isinstance(info, ModelInfo)
        assert info.size == 'tiny'
        assert info.ram_required_gb == 0.2
        assert info.accuracy_rating == 'Basic'
        assert info.latency_profile == 'Fastest'
    
    def test_get_model_info_base(self):
        """Test retrieving base model info."""
        info = get_model_info('base')
        assert info.size == 'base'
        assert info.ram_required_gb == 0.5
        assert info.accuracy_rating == 'Good'
        assert info.latency_profile == 'Fast'
    
    def test_get_model_info_small(self):
        """Test retrieving small model info."""
        info = get_model_info('small')
        assert info.size == 'small'
        assert info.ram_required_gb == 1.5
        assert info.accuracy_rating == 'Very Good'
        assert info.latency_profile == 'Moderate'
    
    def test_get_model_info_invalid(self):
        """Test invalid model size raises ValueError."""
        with pytest.raises(ValueError):
            get_model_info('invalid')
    
    def test_get_all_model_info(self):
        """Test retrieving all model info."""
        all_info = get_all_model_info()
        assert len(all_info) == 5
        sizes = [info.size for info in all_info]
        assert 'tiny' in sizes
        assert 'base' in sizes
        assert 'small' in sizes
        assert 'medium' in sizes
        assert 'large' in sizes


class TestModelRecommender:
    """Test ModelRecommender class."""
    
    def test_detect_and_recommend(self):
        """Test detection and recommendation."""
        recommender = ModelRecommender()
        result = recommender.detect_and_recommend()
        assert result in ['tiny', 'base', 'small', 'medium', 'large']
    
    def test_get_recommendation_caches(self):
        """Test get_recommendation returns cached value."""
        recommender = ModelRecommender()
        first = recommender.get_recommendation()
        second = recommender.get_recommendation()
        assert first == second
    
    def test_get_recommended_info(self):
        """Test getting ModelInfo for recommendation."""
        recommender = ModelRecommender()
        info = recommender.get_recommended_info()
        assert isinstance(info, ModelInfo)
        assert info.size in ['tiny', 'base', 'small', 'medium', 'large']
    
    def test_get_detected_specs(self):
        """Test getting detected specs."""
        recommender = ModelRecommender()
        specs = recommender.get_detected_specs()
        assert isinstance(specs, SystemSpecs)
        assert specs.total_ram_gb > 0
        assert specs.cpu_count_logical > 0
    
    def test_get_recommendation_summary(self):
        """Test getting recommendation summary."""
        recommender = ModelRecommender()
        summary = recommender.get_recommendation_summary()
        assert isinstance(summary, str)
        assert len(summary) > 0


class TestHardwareDetectorMock:
    """Test HardwareDetector with mock specs."""
    
    def test_has_minimum_requirements_single_mode(self):
        """Test single-mode minimum requirements."""
        detector = HardwareDetector()
        
        # Good specs
        good_specs = SystemSpecs(
            total_ram_gb=8, available_ram_gb=4,
            cpu_count_logical=4, cpu_count_physical=2,
            cpu_freq_mhz=2000, is_64bit=True, platform='Windows'
        )
        assert detector.has_minimum_requirements(good_specs, dual_mode=False) is True
        
        # Low RAM
        low_ram = SystemSpecs(
            total_ram_gb=2, available_ram_gb=1,
            cpu_count_logical=4, cpu_count_physical=2,
            cpu_freq_mhz=2000, is_64bit=True, platform='Windows'
        )
        assert detector.has_minimum_requirements(low_ram, dual_mode=False) is False
        
        # Low cores
        low_cores = SystemSpecs(
            total_ram_gb=8, available_ram_gb=4,
            cpu_count_logical=1, cpu_count_physical=1,
            cpu_freq_mhz=2000, is_64bit=True, platform='Windows'
        )
        assert detector.has_minimum_requirements(low_cores, dual_mode=False) is False
    
    def test_has_minimum_requirements_dual_mode(self):
        """Test dual-mode minimum requirements."""
        detector = HardwareDetector()
        
        # Good specs
        good_specs = SystemSpecs(
            total_ram_gb=16, available_ram_gb=8,
            cpu_count_logical=8, cpu_count_physical=4,
            cpu_freq_mhz=2400, is_64bit=True, platform='Windows'
        )
        assert detector.has_minimum_requirements(good_specs, dual_mode=True) is True
        
        # Insufficient for dual mode
        insufficient = SystemSpecs(
            total_ram_gb=6, available_ram_gb=3,
            cpu_count_logical=4, cpu_count_physical=2,
            cpu_freq_mhz=2000, is_64bit=True, platform='Windows'
        )
        assert detector.has_minimum_requirements(insufficient, dual_mode=True) is False
    
    def test_get_warning_message_meets_requirements(self):
        """Test no warning when requirements met."""
        detector = HardwareDetector()
        good_specs = SystemSpecs(
            total_ram_gb=16, available_ram_gb=8,
            cpu_count_logical=8, cpu_count_physical=4,
            cpu_freq_mhz=2400, is_64bit=True, platform='Windows'
        )
        assert detector.get_warning_message(good_specs, dual_mode=False) is None
    
    def test_get_warning_message_below_requirements(self):
        """Test warning when below requirements."""
        detector = HardwareDetector()
        bad_specs = SystemSpecs(
            total_ram_gb=2, available_ram_gb=1,
            cpu_count_logical=1, cpu_count_physical=1,
            cpu_freq_mhz=1000, is_64bit=True, platform='Windows'
        )
        warning = detector.get_warning_message(bad_specs, dual_mode=False)
        assert warning is not None
        assert 'RAM' in warning or 'CPU' in warning
    
    def test_get_specs_summary(self):
        """Test specs summary generation."""
        detector = HardwareDetector()
        specs = SystemSpecs(
            total_ram_gb=16, available_ram_gb=8,
            cpu_count_logical=8, cpu_count_physical=4,
            cpu_freq_mhz=2400, is_64bit=True, platform='Windows'
        )
        summary = detector.get_specs_summary(specs)
        assert isinstance(summary, str)
        assert '16.0GB' in summary or '16GB' in summary
        assert '8' in summary  # cores
        assert 'Windows' in summary


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
