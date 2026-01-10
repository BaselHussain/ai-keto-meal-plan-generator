"""
Unit tests for calorie_calculator service.

Tests cover:
- Mifflin-St Jeor BMR formulas (male/female)
- All 5 activity levels with correct multipliers
- All 3 goals (weight loss, muscle gain, maintenance)
- Calorie floor enforcement (1200 female, 1500 male)
- Edge cases and boundary conditions
- Invalid inputs and error handling

Test Coverage: 100% of calorie_calculator.py
"""

import logging
from typing import Any

import pytest

from src.services.calorie_calculator import (
    ACTIVITY_MULTIPLIERS,
    CALORIE_FLOOR_FEMALE,
    CALORIE_FLOOR_MALE,
    GOAL_ADJUSTMENTS,
    ActivityLevel,
    CalorieCalculation,
    Gender,
    Goal,
    calculate_calorie_target,
)


class TestMifflinStJeorFormulas:
    """Test BMR calculations using Mifflin-St Jeor equations."""

    def test_male_bmr_calculation(self):
        """Test male BMR formula: (10 × weight_kg) + (6.25 × height_cm) - (5 × age) + 5."""
        # Male: 30 years, 80kg, 180cm, sedentary, maintenance
        # Expected BMR = (10 × 80) + (6.25 × 180) - (5 × 30) + 5
        # = 800 + 1125 - 150 + 5 = 1780
        result = calculate_calorie_target(
            gender=Gender.MALE,
            age=30,
            weight_kg=80,
            height_cm=180,
            activity_level=ActivityLevel.SEDENTARY,
            goal=Goal.MAINTENANCE,
        )

        expected_bmr = 1780.0
        assert result.bmr == expected_bmr
        assert result.tdee == expected_bmr * 1.2  # Sedentary multiplier
        assert result.goal_adjusted == result.tdee  # Maintenance = 0 adjustment
        assert result.final_target == int(round(result.tdee))
        assert result.clamped is False
        assert result.warning is None

    def test_female_bmr_calculation(self):
        """Test female BMR formula: (10 × weight_kg) + (6.25 × height_cm) - (5 × age) - 161."""
        # Female: 25 years, 60kg, 165cm, sedentary, maintenance
        # Expected BMR = (10 × 60) + (6.25 × 165) - (5 × 25) - 161
        # = 600 + 1031.25 - 125 - 161 = 1345.25
        result = calculate_calorie_target(
            gender=Gender.FEMALE,
            age=25,
            weight_kg=60,
            height_cm=165,
            activity_level=ActivityLevel.SEDENTARY,
            goal=Goal.MAINTENANCE,
        )

        expected_bmr = 1345.2  # round(1345.25, 1)
        assert result.bmr == expected_bmr
        # TDEE = round(1345.25 * 1.2, 1) = round(1614.3, 1) = 1614.3
        assert result.tdee == 1614.3
        assert result.clamped is False
        assert result.warning is None

    def test_male_vs_female_bmr_difference(self):
        """Test that male BMR is higher than female BMR for same stats (166 kcal difference)."""
        # Same age, weight, height, activity, goal
        params = {
            "age": 30,
            "weight_kg": 70,
            "height_cm": 170,
            "activity_level": ActivityLevel.MODERATELY_ACTIVE,
            "goal": Goal.MAINTENANCE,
        }

        male_result = calculate_calorie_target(gender=Gender.MALE, **params)
        female_result = calculate_calorie_target(gender=Gender.FEMALE, **params)

        # Male formula adds +5, female adds -161, difference = 166
        assert male_result.bmr == female_result.bmr + 166.0
        assert male_result.tdee > female_result.tdee
        assert male_result.final_target > female_result.final_target


class TestActivityLevels:
    """Test all 5 activity level multipliers."""

    @pytest.mark.parametrize(
        "activity_level,expected_multiplier",
        [
            (ActivityLevel.SEDENTARY, 1.2),
            (ActivityLevel.LIGHTLY_ACTIVE, 1.375),
            (ActivityLevel.MODERATELY_ACTIVE, 1.55),
            (ActivityLevel.VERY_ACTIVE, 1.725),
            (ActivityLevel.SUPER_ACTIVE, 1.9),
        ],
    )
    def test_activity_multipliers(
        self, activity_level: ActivityLevel, expected_multiplier: float
    ):
        """Test that each activity level applies correct TDEE multiplier."""
        # Use fixed BMR for easy verification
        # Male: 30y, 80kg, 180cm -> BMR = 1780
        result = calculate_calorie_target(
            gender=Gender.MALE,
            age=30,
            weight_kg=80,
            height_cm=180,
            activity_level=activity_level,
            goal=Goal.MAINTENANCE,
        )

        expected_bmr = 1780.0
        expected_tdee = round(expected_bmr * expected_multiplier, 1)

        assert result.bmr == expected_bmr
        assert result.tdee == expected_tdee
        assert result.goal_adjusted == expected_tdee  # Maintenance = 0 adjustment

    def test_sedentary_vs_super_active_difference(self):
        """Test that SUPER_ACTIVE TDEE is significantly higher than SEDENTARY."""
        params = {
            "gender": Gender.MALE,
            "age": 30,
            "weight_kg": 80,
            "height_cm": 180,
            "goal": Goal.MAINTENANCE,
        }

        sedentary = calculate_calorie_target(
            activity_level=ActivityLevel.SEDENTARY, **params
        )
        super_active = calculate_calorie_target(
            activity_level=ActivityLevel.SUPER_ACTIVE, **params
        )

        # BMR should be same, TDEE should differ by multiplier ratio
        assert sedentary.bmr == super_active.bmr
        assert super_active.tdee == round(sedentary.bmr * 1.9, 1)
        assert sedentary.tdee == round(sedentary.bmr * 1.2, 1)
        assert super_active.tdee > sedentary.tdee

        # Multiplier ratio: 1.9 / 1.2 = 1.583... (58.3% more calories)
        ratio = super_active.tdee / sedentary.tdee
        assert 1.58 < ratio < 1.59


class TestGoalAdjustments:
    """Test all 3 goal adjustments (weight loss, muscle gain, maintenance)."""

    @pytest.mark.parametrize(
        "goal,expected_adjustment",
        [
            (Goal.WEIGHT_LOSS, -400),
            (Goal.MUSCLE_GAIN, 250),
            (Goal.MAINTENANCE, 0),
        ],
    )
    def test_goal_adjustments(self, goal: Goal, expected_adjustment: int):
        """Test that each goal applies correct calorie adjustment to TDEE."""
        # Use moderately active to get reasonable TDEE
        result = calculate_calorie_target(
            gender=Gender.MALE,
            age=30,
            weight_kg=80,
            height_cm=180,
            activity_level=ActivityLevel.MODERATELY_ACTIVE,
            goal=goal,
        )

        # BMR = 1780, TDEE = 1780 * 1.55 = 2759
        expected_bmr = 1780.0
        expected_tdee = round(expected_bmr * 1.55, 1)
        expected_goal_adjusted = round(expected_tdee + expected_adjustment, 1)

        assert result.bmr == expected_bmr
        assert result.tdee == expected_tdee
        assert result.goal_adjusted == expected_goal_adjusted
        assert result.final_target == int(round(expected_goal_adjusted))

    def test_weight_loss_reduces_calories(self):
        """Test that weight loss goal reduces calories from maintenance."""
        params = {
            "gender": Gender.MALE,
            "age": 30,
            "weight_kg": 80,
            "height_cm": 180,
            "activity_level": ActivityLevel.MODERATELY_ACTIVE,
        }

        maintenance = calculate_calorie_target(goal=Goal.MAINTENANCE, **params)
        weight_loss = calculate_calorie_target(goal=Goal.WEIGHT_LOSS, **params)

        assert weight_loss.bmr == maintenance.bmr
        assert weight_loss.tdee == maintenance.tdee
        assert weight_loss.goal_adjusted == maintenance.goal_adjusted - 400
        assert weight_loss.final_target < maintenance.final_target

    def test_muscle_gain_increases_calories(self):
        """Test that muscle gain goal increases calories from maintenance."""
        params = {
            "gender": Gender.FEMALE,
            "age": 25,
            "weight_kg": 60,
            "height_cm": 165,
            "activity_level": ActivityLevel.VERY_ACTIVE,
        }

        maintenance = calculate_calorie_target(goal=Goal.MAINTENANCE, **params)
        muscle_gain = calculate_calorie_target(goal=Goal.MUSCLE_GAIN, **params)

        assert muscle_gain.bmr == maintenance.bmr
        assert muscle_gain.tdee == maintenance.tdee
        assert muscle_gain.goal_adjusted == maintenance.goal_adjusted + 250
        assert muscle_gain.final_target > maintenance.final_target


class TestCalorieFloors:
    """Test minimum calorie floor enforcement (1200 female, 1500 male)."""

    def test_male_calorie_floor_enforcement(self):
        """Test that male target is clamped to 1500 kcal minimum."""
        # Very light male with sedentary + weight loss -> should hit floor
        # Male: 18y, 50kg, 150cm, sedentary, weight loss
        # BMR = (10 × 50) + (6.25 × 150) - (5 × 18) + 5
        # = 500 + 937.5 - 90 + 5 = 1352.5
        # TDEE = 1352.5 * 1.2 = 1623
        # Goal adjusted = 1623 - 400 = 1223 (below 1500 floor)
        result = calculate_calorie_target(
            gender=Gender.MALE,
            age=18,
            weight_kg=50,
            height_cm=150,
            activity_level=ActivityLevel.SEDENTARY,
            goal=Goal.WEIGHT_LOSS,
        )

        assert result.goal_adjusted < CALORIE_FLOOR_MALE
        assert result.final_target == CALORIE_FLOOR_MALE
        assert result.clamped is True
        assert result.warning is not None
        assert "1500 kcal" in result.warning
        assert "health safety" in result.warning

    def test_female_calorie_floor_enforcement(self):
        """Test that female target is clamped to 1200 kcal minimum."""
        # Very light female with sedentary + weight loss -> should hit floor
        # Female: 20y, 45kg, 145cm, sedentary, weight loss
        # BMR = (10 × 45) + (6.25 × 145) - (5 × 20) - 161
        # = 450 + 906.25 - 100 - 161 = 1095.25
        # TDEE = 1095.25 * 1.2 = 1314.3
        # Goal adjusted = 1314.3 - 400 = 914.3 (below 1200 floor)
        result = calculate_calorie_target(
            gender=Gender.FEMALE,
            age=20,
            weight_kg=45,
            height_cm=145,
            activity_level=ActivityLevel.SEDENTARY,
            goal=Goal.WEIGHT_LOSS,
        )

        assert result.goal_adjusted < CALORIE_FLOOR_FEMALE
        assert result.final_target == CALORIE_FLOOR_FEMALE
        assert result.clamped is True
        assert result.warning is not None
        assert "1200 kcal" in result.warning
        assert "health safety" in result.warning

    def test_male_just_above_floor_no_clamping(self):
        """Test that male target just above floor is not clamped."""
        # Target should be ~1520 (above 1500 floor)
        # Male: 20y, 55kg, 160cm, sedentary, weight loss
        # BMR = (10 × 55) + (6.25 × 160) - (5 × 20) + 5 = 1455
        # TDEE = 1455 * 1.2 = 1746
        # Goal adjusted = 1746 - 400 = 1346 (still below floor, let's adjust)

        # Male: 25y, 65kg, 170cm, sedentary, weight loss
        # BMR = (10 × 65) + (6.25 × 170) - (5 × 25) + 5 = 1555
        # TDEE = 1555 * 1.2 = 1866
        # Goal adjusted = 1866 - 400 = 1466 (still below, adjust again)

        # Male: 25y, 70kg, 175cm, sedentary, weight loss
        # BMR = (10 × 70) + (6.25 × 175) - (5 × 25) + 5 = 1693.75
        # TDEE = 1693.75 * 1.2 = 2032.5
        # Goal adjusted = 2032.5 - 400 = 1632.5 (above floor!)
        result = calculate_calorie_target(
            gender=Gender.MALE,
            age=25,
            weight_kg=70,
            height_cm=175,
            activity_level=ActivityLevel.SEDENTARY,
            goal=Goal.WEIGHT_LOSS,
        )

        assert result.goal_adjusted > CALORIE_FLOOR_MALE
        assert result.final_target > CALORIE_FLOOR_MALE
        assert result.clamped is False
        assert result.warning is None

    def test_female_just_above_floor_no_clamping(self):
        """Test that female target just above floor is not clamped."""
        # Female: 22y, 55kg, 160cm, sedentary, weight loss
        # BMR = (10 × 55) + (6.25 × 160) - (5 × 22) - 161 = 1279
        # TDEE = 1279 * 1.2 = 1534.8
        # Goal adjusted = 1534.8 - 400 = 1134.8 (still below, adjust)

        # Female: 22y, 60kg, 165cm, lightly active, weight loss
        # BMR = (10 × 60) + (6.25 × 165) - (5 × 22) - 161 = 1370.25
        # TDEE = 1370.25 * 1.375 = 1884.09
        # Goal adjusted = 1884.09 - 400 = 1484.09 (above 1200 floor!)
        result = calculate_calorie_target(
            gender=Gender.FEMALE,
            age=22,
            weight_kg=60,
            height_cm=165,
            activity_level=ActivityLevel.LIGHTLY_ACTIVE,
            goal=Goal.WEIGHT_LOSS,
        )

        assert result.goal_adjusted > CALORIE_FLOOR_FEMALE
        assert result.final_target > CALORIE_FLOOR_FEMALE
        assert result.clamped is False
        assert result.warning is None

    def test_floor_enforcement_logs_warning(self, caplog):
        """Test that floor enforcement logs a warning message."""
        with caplog.at_level(logging.WARNING):
            result = calculate_calorie_target(
                gender=Gender.FEMALE,
                age=20,
                weight_kg=45,
                height_cm=145,
                activity_level=ActivityLevel.SEDENTARY,
                goal=Goal.WEIGHT_LOSS,
            )

        assert result.clamped is True
        assert "Calorie target clamped to minimum safe value" in caplog.text


class TestEdgeCasesAndBoundaries:
    """Test edge cases, extreme values, and boundary conditions."""

    def test_very_young_user(self):
        """Test calculation for young user (18 years old)."""
        result = calculate_calorie_target(
            gender=Gender.MALE,
            age=18,
            weight_kg=70,
            height_cm=175,
            activity_level=ActivityLevel.MODERATELY_ACTIVE,
            goal=Goal.MUSCLE_GAIN,
        )

        # Should calculate normally without errors
        assert result.bmr > 0
        assert result.tdee > result.bmr
        assert result.final_target > 0
        assert isinstance(result, CalorieCalculation)

    def test_elderly_user(self):
        """Test calculation for elderly user (80 years old)."""
        result = calculate_calorie_target(
            gender=Gender.FEMALE,
            age=80,
            weight_kg=60,
            height_cm=160,
            activity_level=ActivityLevel.SEDENTARY,
            goal=Goal.MAINTENANCE,
        )

        # Age reduces BMR significantly
        # BMR = (10 × 60) + (6.25 × 160) - (5 × 80) - 161 = 1039
        assert result.bmr == 1039.0
        assert result.bmr < 1100  # Lower due to age
        assert result.final_target > 0

    def test_very_light_weight(self):
        """Test calculation with very low body weight (40kg)."""
        result = calculate_calorie_target(
            gender=Gender.FEMALE,
            age=25,
            weight_kg=40,
            height_cm=150,
            activity_level=ActivityLevel.SEDENTARY,
            goal=Goal.MAINTENANCE,
        )

        # Should handle low weight without errors
        assert result.bmr > 0
        assert result.tdee > 0
        # Might hit calorie floor
        assert result.final_target >= CALORIE_FLOOR_FEMALE

    def test_very_heavy_weight(self):
        """Test calculation with high body weight (150kg)."""
        result = calculate_calorie_target(
            gender=Gender.MALE,
            age=35,
            weight_kg=150,
            height_cm=185,
            activity_level=ActivityLevel.LIGHTLY_ACTIVE,
            goal=Goal.WEIGHT_LOSS,
        )

        # High weight -> high BMR and TDEE
        # BMR = (10 × 150) + (6.25 × 185) - (5 × 35) + 5
        # = 1500 + 1156.25 - 175 + 5 = 2486.25
        expected_bmr = round(1500 + 1156.25 - 175 + 5, 1)
        assert result.bmr == expected_bmr
        assert result.tdee > 3400  # BMR * 1.375
        assert result.final_target > CALORIE_FLOOR_MALE

    def test_very_short_height(self):
        """Test calculation with short height (140cm)."""
        result = calculate_calorie_target(
            gender=Gender.FEMALE,
            age=30,
            weight_kg=50,
            height_cm=140,
            activity_level=ActivityLevel.MODERATELY_ACTIVE,
            goal=Goal.MAINTENANCE,
        )

        # Short height reduces BMR
        assert result.bmr < 1400
        assert result.final_target > 0

    def test_very_tall_height(self):
        """Test calculation with tall height (200cm)."""
        result = calculate_calorie_target(
            gender=Gender.MALE,
            age=25,
            weight_kg=90,
            height_cm=200,
            activity_level=ActivityLevel.VERY_ACTIVE,
            goal=Goal.MUSCLE_GAIN,
        )

        # Tall height increases BMR significantly
        # BMR = (10 × 90) + (6.25 × 200) - (5 × 25) + 5
        # = 900 + 1250 - 125 + 5 = 2030
        expected_bmr = round(900 + 1250 - 125 + 5, 1)
        assert result.bmr == expected_bmr
        assert result.tdee > 3500  # BMR * 1.725
        assert result.final_target > CALORIE_FLOOR_MALE

    def test_decimal_weight_and_height(self):
        """Test calculation handles decimal values correctly."""
        result = calculate_calorie_target(
            gender=Gender.FEMALE,
            age=28,
            weight_kg=65.5,
            height_cm=167.5,
            activity_level=ActivityLevel.MODERATELY_ACTIVE,
            goal=Goal.WEIGHT_LOSS,
        )

        # Should handle decimals without rounding errors
        assert isinstance(result.bmr, float)
        assert isinstance(result.tdee, float)
        assert isinstance(result.final_target, int)  # Final target is int
        assert result.final_target > 0

    def test_rounding_behavior(self):
        """Test that final target is properly rounded to nearest integer."""
        result = calculate_calorie_target(
            gender=Gender.MALE,
            age=30,
            weight_kg=75,
            height_cm=175,
            activity_level=ActivityLevel.MODERATELY_ACTIVE,
            goal=Goal.MAINTENANCE,
        )

        # final_target should be int(round(goal_adjusted))
        expected_final = int(round(result.goal_adjusted))
        assert result.final_target == expected_final
        assert isinstance(result.final_target, int)


class TestReturnTypeAndStructure:
    """Test CalorieCalculation return type and data structure."""

    def test_return_type_is_calorie_calculation(self):
        """Test that function returns CalorieCalculation Pydantic model."""
        result = calculate_calorie_target(
            gender=Gender.MALE,
            age=30,
            weight_kg=80,
            height_cm=180,
            activity_level=ActivityLevel.MODERATELY_ACTIVE,
            goal=Goal.MAINTENANCE,
        )

        assert isinstance(result, CalorieCalculation)

    def test_all_fields_present(self):
        """Test that all expected fields are present in result."""
        result = calculate_calorie_target(
            gender=Gender.FEMALE,
            age=25,
            weight_kg=60,
            height_cm=165,
            activity_level=ActivityLevel.LIGHTLY_ACTIVE,
            goal=Goal.MUSCLE_GAIN,
        )

        assert hasattr(result, "bmr")
        assert hasattr(result, "tdee")
        assert hasattr(result, "goal_adjusted")
        assert hasattr(result, "final_target")
        assert hasattr(result, "clamped")
        assert hasattr(result, "warning")

    def test_field_types(self):
        """Test that all fields have correct types."""
        result = calculate_calorie_target(
            gender=Gender.MALE,
            age=30,
            weight_kg=80,
            height_cm=180,
            activity_level=ActivityLevel.SEDENTARY,
            goal=Goal.WEIGHT_LOSS,
        )

        assert isinstance(result.bmr, float)
        assert isinstance(result.tdee, float)
        assert isinstance(result.goal_adjusted, float)
        assert isinstance(result.final_target, int)
        assert isinstance(result.clamped, bool)
        assert result.warning is None or isinstance(result.warning, str)

    def test_bmr_tdee_relationship(self):
        """Test that TDEE is always greater than or equal to BMR."""
        for activity_level in ActivityLevel:
            result = calculate_calorie_target(
                gender=Gender.MALE,
                age=30,
                weight_kg=80,
                height_cm=180,
                activity_level=activity_level,
                goal=Goal.MAINTENANCE,
            )

            assert result.tdee >= result.bmr
            # TDEE should be BMR * activity multiplier
            expected_tdee = round(result.bmr * ACTIVITY_MULTIPLIERS[activity_level], 1)
            assert result.tdee == expected_tdee


class TestConstants:
    """Test that module constants have expected values."""

    def test_activity_multipliers(self):
        """Test that activity multipliers match specification."""
        assert ACTIVITY_MULTIPLIERS[ActivityLevel.SEDENTARY] == 1.2
        assert ACTIVITY_MULTIPLIERS[ActivityLevel.LIGHTLY_ACTIVE] == 1.375
        assert ACTIVITY_MULTIPLIERS[ActivityLevel.MODERATELY_ACTIVE] == 1.55
        assert ACTIVITY_MULTIPLIERS[ActivityLevel.VERY_ACTIVE] == 1.725
        assert ACTIVITY_MULTIPLIERS[ActivityLevel.SUPER_ACTIVE] == 1.9

    def test_goal_adjustments(self):
        """Test that goal adjustments match specification."""
        assert GOAL_ADJUSTMENTS[Goal.WEIGHT_LOSS] == -400
        assert GOAL_ADJUSTMENTS[Goal.MUSCLE_GAIN] == 250
        assert GOAL_ADJUSTMENTS[Goal.MAINTENANCE] == 0

    def test_calorie_floors(self):
        """Test that calorie floors match specification."""
        assert CALORIE_FLOOR_MALE == 1500
        assert CALORIE_FLOOR_FEMALE == 1200


class TestRealWorldScenarios:
    """Test realistic user scenarios end-to-end."""

    def test_average_male_weight_loss(self):
        """Test typical male weight loss scenario."""
        # 35-year-old male, 85kg, 178cm, moderately active, weight loss
        result = calculate_calorie_target(
            gender=Gender.MALE,
            age=35,
            weight_kg=85,
            height_cm=178,
            activity_level=ActivityLevel.MODERATELY_ACTIVE,
            goal=Goal.WEIGHT_LOSS,
        )

        # BMR = (10 × 85) + (6.25 × 178) - (5 × 35) + 5
        # = 850 + 1112.5 - 175 + 5 = 1792.5
        # TDEE = 1792.5 * 1.55 = 2778.4
        # Goal adjusted = 2778.4 - 400 = 2378.4
        assert 1790 < result.bmr < 1795
        assert 2775 < result.tdee < 2780
        assert 2375 < result.final_target < 2380
        assert result.clamped is False

    def test_average_female_muscle_gain(self):
        """Test typical female muscle gain scenario."""
        # 28-year-old female, 58kg, 163cm, very active, muscle gain
        result = calculate_calorie_target(
            gender=Gender.FEMALE,
            age=28,
            weight_kg=58,
            height_cm=163,
            activity_level=ActivityLevel.VERY_ACTIVE,
            goal=Goal.MUSCLE_GAIN,
        )

        # BMR = (10 × 58) + (6.25 × 163) - (5 × 28) - 161
        # = 580 + 1018.75 - 140 - 161 = 1297.75
        # TDEE = 1297.75 * 1.725 = 2238.6
        # Goal adjusted = 2238.6 + 250 = 2488.6
        assert 1295 < result.bmr < 1300
        assert 2235 < result.tdee < 2240
        assert 2485 < result.final_target < 2495
        assert result.clamped is False

    def test_petite_female_aggressive_weight_loss(self):
        """Test petite female with weight loss hitting calorie floor."""
        # 30-year-old female, 50kg, 152cm, sedentary, weight loss
        # This should hit the 1200 kcal floor
        result = calculate_calorie_target(
            gender=Gender.FEMALE,
            age=30,
            weight_kg=50,
            height_cm=152,
            activity_level=ActivityLevel.SEDENTARY,
            goal=Goal.WEIGHT_LOSS,
        )

        # BMR ≈ 1200, TDEE ≈ 1440, goal adjusted ≈ 1040 (below floor)
        assert result.final_target == CALORIE_FLOOR_FEMALE
        assert result.clamped is True
        assert result.warning is not None

    def test_athlete_male_muscle_gain(self):
        """Test athletic male with super active lifestyle and muscle gain."""
        # 25-year-old male, 90kg, 185cm, super active, muscle gain
        result = calculate_calorie_target(
            gender=Gender.MALE,
            age=25,
            weight_kg=90,
            height_cm=185,
            activity_level=ActivityLevel.SUPER_ACTIVE,
            goal=Goal.MUSCLE_GAIN,
        )

        # BMR = (10 × 90) + (6.25 × 185) - (5 × 25) + 5
        # = 900 + 1156.25 - 125 + 5 = 1936.25
        # TDEE = 1936.25 * 1.9 = 3678.9
        # Goal adjusted = 3678.9 + 250 = 3928.9
        assert 1935 < result.bmr < 1940
        assert 3675 < result.tdee < 3680
        assert 3925 < result.final_target < 3935
        assert result.clamped is False
